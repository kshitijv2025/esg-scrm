# TODO-B3-10: Bulk Questionnaire Dispatch — Verification and Completion

**GitHub Issue**: (unlinked — needs creation)
**Status**: ACTIVE

## Description

The `POST /api/questionnaires/dispatch-bulk` endpoint EXISTS at `src/api/routes/questionnaires.py:448-556`. It accepts `{supplier_ids, template_id}` and dispatches via WhatsApp or email per supplier's `preferred_channel`. This todo is for **verification** that the implementation fully satisfies the brief and **completion** of any missing acceptance criteria.

**Current state** (`src/api/routes/questionnaires.py:448-556`):

```python
@router.post("/dispatch-bulk")
def dispatch_bulk(body: dict, user: dict = Depends(require_auth)):
    # - Validates supplier_ids is non-empty list, max 200
    # - Looks up each supplier, verifies org membership
    # - Chooses WhatsApp if phone exists + preferred_channel == "whatsapp"
    # - Calls WhatsAppClient.send_questionnaire() or EmailClient.send_questionnaire()
    # - Returns {status, total, dispatched, errors, results: [...]}
```

## Brief Requirement (per `01-commercial-todos.md` B3.10)

> "endpoint `POST /api/questionnaires/dispatch-bulk` accepts `{supplier_ids: list[str], template_id: str}`, dispatches questionnaires to all suppliers via appropriate channel"

## Verification Checklist

- [ ] **Endpoint exists**: Confirmed at `questionnaires.py:448-556` — DONE
- [ ] **Accepts `{supplier_ids, template_id}`**: Confirmed — DONE
- [ ] **Dispatches via appropriate channel**: WhatsApp or email per `preferred_channel` — CONFIRM: `preferred_channel` column must exist in `suppliers` table
- [ ] **Org isolation**: Each supplier verified as belonging to caller's `org_id` — CONFIRM: `_verify_supplier_org()` check present — DONE
- [ ] **Per-supplier result reporting**: Returns `results: [{supplier_id, supplier_name, status, channel, message_id}]` — CONFIRM — DONE
- [ ] **Error handling**: Partial success returns 200 with `{dispatched, errors}` counts — CONFIRM — DONE
- [ ] **Audit logging**: `dispatch_bulk.completed` log entry with org_id, requested_by, total, dispatched, errors — CONFIRM — DONE
- [ ] **Concurrency safety**: Loop processes suppliers sequentially (no parallel threads) — ACCEPTABLE: no shared state mutated
- [ ] **Unit test coverage**: Test file should exist at `tests/unit/test_questionnaires.py` covering dispatch-bulk — NEED TO VERIFY

## What to Build / Verify

### If verification finds gaps:

1. **Missing `preferred_channel` column**: Add to `suppliers` table, default to `"whatsapp"`
2. **Missing unit tests**: Write tests for:
   - Successful dispatch to mixed WhatsApp/email suppliers
   - Partial failure (some suppliers not found)
   - Org isolation violation (supplier from another org)
   - Max 200 supplier_ids limit enforced
   - `dispatched == 0` returns `{status: "ok", dispatched: 0, errors: N}` gracefully
3. **Missing audit trail**: Ensure each dispatch call logs to `audit_log` table

### If verification finds no gaps:

Mark as **COMPLETED** in `01-commercial-todos.md` with a note that the endpoint ships with the following verified properties.

## Specs Authority

- `specs/supplier-collection.md` § Questionnaire Flow — Step 2 "Supplier Selection" and Step 5 "Dispatch"
- `01-commercial-todos.md` B3.10 — brief description

## Subtasks

- [ ] Read `dispatch_bulk()` implementation end-to-end — 20 min
- [ ] Verify `preferred_channel` column exists in `schema.sql` / `schema_pg.sql` — 10 min
- [ ] Verify unit tests exist for `dispatch-bulk` — 10 min
- [ ] If unit tests missing: write them — 90 min
- [ ] If `preferred_channel` missing: add migration — 30 min
- [ ] Run full test suite — 10 min
- [ ] If all verified: mark B3.10 COMPLETED in main todos file

## Definition of Done

- [ ] `POST /api/questionnaires/dispatch-bulk` handles `{supplier_ids, template_id}` per brief
- [ ] WhatsApp and email channels both work; routing is per `preferred_channel`
- [ ] Org isolation enforced on every supplier lookup
- [ ] Per-supplier status in response allows caller to show success/failure summary
- [ ] Unit tests achieve >80% coverage on the endpoint
- [ ] All 183 tests pass

## Risk Assessment

- **Low risk**: Endpoint already exists and is tested (pending verification)
- **Low risk**: Adding `preferred_channel` if missing is additive migration (backwards compatible)
- **Risk**: 200-supplier cap is enforced in-code — verify it's not bypassable by passing a larger list
