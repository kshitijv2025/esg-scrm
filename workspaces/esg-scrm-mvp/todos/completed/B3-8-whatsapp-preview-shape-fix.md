# TODO-B3-8: Fix WhatsApp Preview Endpoint Shape

**GitHub Issue**: (unlinked — needs creation)
**Status**: ACTIVE

## Description

Fix `GET /api/questionnaires/whatsapp-preview/{supplier_id}` to return the shape `SupplierEngagementTab.jsx:34` expects.

**Current state** (`src/api/routes/questionnaires.py:161-290`):
The endpoint exists and returns:

```python
{
    "supplier": {"id", "name", "country", "contact_email"},
    "template": {"id", "name", "category", "language"},
    "questions": [{"id", "question_text", "question_type", "sort_order", "required", "response"}],
    "progress": {"total_questions", "answered", "completion_pct"}
}
```

**Required state** (per `SupplierEngagementTab.jsx` consumption):

```python
{
    "message_preview": "<rendered WhatsApp message string>",
    "supplier_response_example": "<example reply in WhatsApp format>",
    "coverage_impact": {
        "supplier_name": str,
        "annual_spend": float,        # from suppliers.annual_spend_usd
        "coverage_added": str,          # e.g. "12.4%" — % of total spend newly covered
        "new_total_coverage": str      # e.g. "68.2%" — running total after this supplier
    }
}
```

The frontend component `SupplierEngagementTab.jsx:34` calls this endpoint and destructures `{message_preview, supplier_response_example, coverage_impact}` — any other top-level key is silently ignored.

## What to Build

1. **Render `message_preview`**: Format the active template's questions as a WhatsApp message (same formatting as `WhatsAppClient._format_questionnaire()`) so buyers can see exactly what the supplier receives.

2. **Render `supplier_response_example`**: Show a sample response in the same numbered format the supplier would reply with (e.g. `"1. 45000 kWh\n2. Yes\n3. Diesel"`). Use the first question's unit as the example value.

3. **Compute `coverage_impact`**:
   - Look up `suppliers.annual_spend_usd` for this supplier
   - Capture `spend_weighted_coverage_pct` BEFORE this supplier's responses (if any)
   - Compute `coverage_added` as the delta if the supplier were fully responded
   - `new_total_coverage` is the running spend-weighted coverage after including this supplier

4. **Remove/suppress the old shape fields** from the response root. The endpoint must return ONLY the three required top-level keys.

## Specs Authority

- `specs/supplier-collection.md` § WhatsApp Business API — message format requirements
- `specs/supplier-collection.md` § Response Rate Tracking — coverage calculation
- `specs/dashboard-tabs.md` § Engagement tab — `whatsapp-preview` panel shape

## Acceptance Criteria

- [ ] `GET /api/questionnaires/whatsapp-preview/{supplier_id}` returns exactly `{message_preview, supplier_response_example, coverage_impact}` as top-level keys — no extra keys
- [ ] `message_preview` is a non-empty string with the full WhatsApp-formatted questionnaire
- [ ] `supplier_response_example` shows numbered example replies using actual question units from the template
- [ ] `coverage_impact.supplier_name` matches the supplier's name in the DB
- [ ] `coverage_impact.annual_spend` is the supplier's `annual_spend_usd`
- [ ] `coverage_impact.coverage_added` is the delta in spend-weighted coverage if this supplier fully responds (computed, not hardcoded)
- [ ] `coverage_impact.new_total_coverage` reflects the running total including this supplier
- [ ] Endpoint returns 404 when supplier does not exist
- [ ] Endpoint returns 403 when supplier belongs to another org
- [ ] All 183 existing tests pass

## Subtasks

- [ ] Read current `whatsapp_preview()` implementation (`questionnaires.py:161-290`) — 30 min
- [ ] Add `_compute_coverage_impact()` helper: takes supplier_id, returns `coverage_added` and `new_total_coverage` — 60 min
- [ ] Refactor endpoint to return `{message_preview, supplier_response_example, coverage_impact}` — 60 min
- [ ] Verify `SupplierEngagementTab.jsx` consumes the new shape without changes — 30 min
- [ ] Add unit test for coverage impact calculation — 30 min
- [ ] Run full test suite (183 tests) — 10 min

## Definition of Done

- [ ] Frontend `SupplierEngagementTab` renders the WhatsApp preview panel correctly with no console errors
- [ ] `coverage_impact` values are computed from live supplier data, not hardcoded
- [ ] All tests pass (`pytest tests/unit/ tests/integration/`)
- [ ] No regression in other questionnaire endpoints

## Risk Assessment

- **Low risk**: Changing only the response shape of one endpoint; existing data flow is untouched
- **Medium risk**: `coverage_impact` calculation depends on `fetch_response_based_coverage()` — ensure it handles the 0-supplier case gracefully
- **Mitigation**: Add explicit `annual_spend_usd = 0` guard; display "N/A" when spend is 0
