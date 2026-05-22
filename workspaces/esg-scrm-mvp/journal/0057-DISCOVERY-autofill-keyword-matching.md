---
name: 0057-DISCOVERY-autofill-keyword-matching
description: Keyword ordering and word-boundary lessons from B3.14 autofill
metadata:
  type: discovery
  session: 2026-05-21
  endpoint: /api/questionnaires/auto-fill/{template_id}/{supplier_id}
---

# DISCOVERY: Autofill Keyword Matching — Ordering and Specificity

## Context

Implemented `GET /api/questionnaires/auto-fill/{template_id}/{supplier_id}` (B3.14). Two subtle keyword matching bugs were caught by tests.

## Bug 1: Supplier field match was too greedy

**Problem**: `"How much waste did you generate in tonnes?"` was matching `annual_spend_usd` via the `spend` regex.

**Root cause**: `_SUPPLIER_FIELD_KEYWORDS` was checked BEFORE `_METRIC_KEYWORDS`, and the regex `r"spend|usd"` matched "waste" (false positive from fuzzy matching).

**Fix**: Supplier field regexes must use `\b` word boundaries and be ordered by specificity. The `spend` regex was too broad — it matched `waste` because the string contained "spend" within it.

```python
# Fixed: word boundary on spend
(re.compile(r"\bspend\b", re.IGNORECASE), "annual_spend_usd", "currency"),
```

**Lesson**: When matching keywords in question text, always use `\b` word boundaries to avoid substring false matches.

## Bug 2: Revenue question matched USD via spend field

**Problem**: `"What is your annual revenue in USD?"` matched `annual_spend_usd` because `USD` appeared in the text.

**Fix**: Supplier field matching should check specific field names, not generic currency keywords. `spend` maps to `annual_spend_usd`; revenue has no mapping (returns `not_applicable`).

```python
# revenue intentionally NOT in _SUPPLIER_FIELD_KEYWORDS — no mapping exists
# so it falls through to not_applicable
```

**Lesson**: Not every question should have a data source. If no mapping exists, return `not_applicable`, not a best-effort match.

## Keyword Ordering Matters

The correct order is: **supplier fields first, then metrics**. This is because:

- Supplier data is more specific (e.g., `country` is exact)
- Metrics are broader (e.g., `energy_kwh` from factory IoT)

If metrics were checked first, a question like "What is your energy spend?" would match `energy_kwh` from metrics before `annual_spend_usd` from supplier — wrong answer.

## Formatting Rules

- **Whole numbers**: `18430` → `"18,430"` (no decimal)
- **Decimals**: `892.4` → `"892.4"` (1 decimal place)
- **Currency**: `"$2,400,000 USD"` (with dollar sign and currency code)
- **Units**: Append unit to formatted number, e.g., `"18,430 m³"`

## Schema

Response shape:

```python
{
    "template_id": str,
    "supplier_id": str,
    "auto_fill_percentage": float,  # 1 decimal
    "questions": [
        {
            "q_id": str,
            "text": str,
            "status": "auto_filled" | "not_applicable" | "needs_input",
            "value": str | None,  # None when not auto_filled
            "source": str | None,  # e.g., "metrics.energy_kwh", "suppliers.country"
        }
    ],
    "summary": {
        "auto_filled": int,
        "not_applicable": int,
        "needs_input": int,
    }
}
```
