# TODO-B2-4: Wire WhatsApp Connector to Template System

**GitHub Issue**: (unlinked — needs creation)
**Status**: ACTIVE

## Description

Validate that the WhatsApp connector properly gates questionnaire dispatch against the questions defined in the active template, and that the response parser associates incoming WhatsApp replies with the correct template question IDs.

**Current state** (`src/connectors/whatsapp.py:111-199`, `src/api/routes/whatsapp.py:139-321`):

The send path IS wired:

- `WhatsAppClient.send_questionnaire()` calls `_resolve_template()` to fetch from `questionnaire_templates`
- Questions are formatted via `_format_questionnaire()` into a numbered WhatsApp message
- Sent via Twilio; `whatsapp_messages` row created; supplier status updated

The receive path is partially wired:

- `POST /api/whatsapp/webhook` receives Twilio callbacks
- `_parse_questionnaire_response()` parses numbered replies (`"1. answer"`) and stores to `questionnaire_responses`
- **Gap**: the parser uses `question_id = f"q{number}"` (e.g. `"q1"`, `"q2"`) WITHOUT validating that those question IDs exist in the template sent to this supplier. A reply to a cancelled/old questionnaire would still be stored.

The spec requires: "Validate question IDs match template questions sent to this supplier."

## What to Build

1. **Add template tracking to outbound messages**: When a questionnaire is sent, store the `template_id` alongside the outbound `whatsapp_messages` row (add `template_id` column to `whatsapp_messages` or a join table). This links the dispatched template to the supplier.

2. **Validate incoming responses against the sent template**: In `_parse_questionnaire_response()`, after looking up the supplier, fetch the `template_id` from the most recent outbound questionnaire message for this supplier. Then validate that each `question_id` in the reply exists in that template's `questionnaire_questions` table before storing. Discard (log + ignore) any reply line whose question ID is not in the sent template.

3. **Add audit log for mismatched responses**: When a reply references a question not in the sent template, log at WARN level with `question_id` and `template_id` so the ops team can detect questionnaire version mismatches.

4. **Update webhook response**: Return the count of stored responses and the count of discarded ones so Twilio can surface partial success.

## Specs Authority

- `specs/supplier-collection.md` § WhatsApp Business API — outbound message format
- `specs/supplier-collection.md` § NLUParser — confidence tagging and response parsing
- `specs/supplier-collection.md` § Questionnaire Flow — validate question IDs match template

## Acceptance Criteria

- [x] `_parse_questionnaire_response()` checks that each `question_id` in a WhatsApp reply exists in the template that was sent to that supplier
- [x] Replies to stale/cancelled templates are discarded (not stored in `questionnaire_responses`)
- [x] Mismatched replies are logged at WARN level with `question_id`, `template_id`, `supplier_id`
- [x] Stored responses have `channel='whatsapp'` and `validation_status` set
- [x] `whatsapp_messages` rows for outbound questionnaire dispatches record the `template_id`
- [x] All 103 existing tests pass

## Subtasks

- [ ] Audit current `_parse_questionnaire_response()` logic — 30 min
- [ ] Add `template_id` column to `whatsapp_messages` (via schema migration) — 60 min
- [ ] Update `WhatsAppClient.send_questionnaire()` to record `template_id` on outbound — 30 min
- [ ] Refactor `_parse_questionnaire_response()` to fetch sent template_id and validate question IDs — 90 min
- [ ] Add WARN logging for mismatched question IDs — 30 min
- [ ] Add integration test for stale-template reply discard — 60 min
- [ ] Run full test suite — 10 min

## Definition of Done

- [ ] `_parse_questionnaire_response()` validates every incoming `question_id` against the template actually sent
- [ ] No response can be stored for a template that was not sent to that supplier
- [ ] Mismatched responses are visible in logs for ops investigation
- [ ] All tests pass (`pytest tests/unit/ tests/integration/`)
- [ ] No regression in send or receive paths

## Risk Assessment

- **Medium risk**: Changing the receive path parsing — a bug here could silently drop valid responses
- **Mitigation**: Add explicit log lines before and after the validation gate; test with a reply containing mixed valid/invalid question IDs
- **Low risk**: Schema migration for `whatsapp_messages.template_id` is additive (NULL for old rows is acceptable)
