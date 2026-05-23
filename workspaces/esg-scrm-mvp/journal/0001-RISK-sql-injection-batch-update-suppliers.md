---
name: risk-sql-injection-batch-update-suppliers
description: SQL injection in batch_update_suppliers via dynamic field interpolation
metadata:
  type: RISK
  severity: CRITICAL
  finding_round: redteam-2026-05-22
  status: fixed
---

# RISK: SQL Injection in batch_update_suppliers

## Finding

**File:** `src/api/routes/suppliers.py:348-357`
**Severity:** CRITICAL

The `batch_update_suppliers` endpoint accepted user-controlled JSON keys as SQL field names
via f-string interpolation:

```python
# VULNERABLE (pre-fix)
fields = {k: v for k, v in item.items() if k not in ("id", "supplier_id")}
set_clause = ", ".join([f"{k} = ?" for k in fields])
conn.execute(f"UPDATE suppliers SET {set_clause}, updated_at = ...", values)
```

Payload `{"updates": [{"id": "sup_123", "name = 1; --": "injected"}]}` would produce:
`UPDATE suppliers SET name = 1; -- = ? WHERE ...`

## Fix Applied

Added `_UPDATABLE_SUPPLIER_FIELDS = frozenset({...})` allowlist (matching schema.sql
suppliers table columns) and filtered dict keys against it:

```python
fields = {k: v for k, v in item.items() if k in _UPDATABLE_SUPPLIER_FIELDS}
```

## Verification

- `pytest tests/unit/test_suppliers_routes.py`: 13 passed
- Full suite: 1241 passed · 3 skipped
- All other dynamic SQL field handlers in codebase use explicit allowlists
  (webhooks.py, compliance.py, corrective_actions.py, scheduled_reports.py)
