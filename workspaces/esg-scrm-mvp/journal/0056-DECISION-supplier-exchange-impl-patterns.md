---
name: 0056-DECISION-supplier-exchange-impl-patterns
description: Implementation patterns for supplier exchange endpoints
metadata:
  type: decision
  session: 2026-05-21
  endpoint-group: suppliers.py
---

# DECISION: Supplier Exchange Implementation Patterns

## Context

`POST /api/suppliers/exchange` and `POST /api/suppliers/exchange/batch` required several non-obvious implementation decisions to pass the test contract.

## Decisions

### 1. `errors` array in import response

Import validation failures must NOT stop processing. The response shape is:

```python
{"imported": N, "updated": N, "total": N, "errors": [{"id": "...", "error": "..."}]}
```

- `errors` is a list, empty when all records succeed
- Validation errors (missing name, missing country) append to `errors` and `continue`
- Partial success is allowed — valid records still import

### 2. Empty suppliers list → 400

```python
if len(suppliers_list) == 0:
    raise HTTPException(status_code=400, detail="'suppliers' list cannot be empty")
```

Unlike batch update (which returns 400 on empty `updates` list), import also returns 400 on empty.

### 3. `supplier_id` as alias for `id` in batch update

The batch endpoint accepts both `id` and `supplier_id` as the identifier key, but only `id` gets excluded from the `fields` dict:

```python
supplier_id = item.get("id") or item.get("supplier_id")
fields = {k: v for k, v in item.items() if k not in ("id", "supplier_id")}
```

### 4. Scope-specific JSON response keys

`GET /api/suppliers/exchange?scope=scope3` returns `{"scope3": [...], "total": N}`, NOT `{"suppliers": [...]}`. Same for `country_risk` scope.

### 5. COALESCE for NOT NULL columns on update

```sql
annual_spend_usd = COALESCE(?, annual_spend_usd)
```

When updating, `None` for `annual_spend_usd` must not trigger NOT NULL constraint. COALESCE preserves existing value.

### 6. Default for missing `annual_spend_usd` on INSERT

```python
record.get("annual_spend_usd") or 0
```

Test records without `annual_spend_usd` fail INSERT if the column is NOT NULL.

### 7. XLSX scope-specific sheet names

```python
scope_sheet_names = {"scope3": "Scope3", "country_risk": "CountryRisk", "summary": "Summary"}
ws.title = scope_sheet_names.get(scope, "Suppliers")
```

## How to Apply

When implementing new bulk-import or batch-update endpoints in `suppliers.py`:

- Always collect validation errors into an `errors` list rather than failing fast
- Return 400 for empty input lists
- Use `COALESCE` for optional fields that map to NOT NULL columns
- Return scope-specific top-level keys in exchange formats
