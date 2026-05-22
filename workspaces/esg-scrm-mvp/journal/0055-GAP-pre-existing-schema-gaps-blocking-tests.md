---
name: gap-pre-existing-schema-gaps
description: Pre-existing test failures from missing database tables and unimplemented Phase D features
metadata:
  type: GAP
  round: redteam-2026-05-21
---

## GAP: Pre-existing schema gaps blocking ~192 tests

### Summary

~~The broader unit test suite has 82 failures and 110 errors (1,295 collected total, 1,049 passed).~~ **RESOLVED**: Schema additions fixed all ERROR (setup) failures. 0 errors remain. 114 FAILED tests remain — these are pre-existing implementation bugs, NOT schema issues.

**Before schema fixes**: 82 failures + 110 errors = 192 blocking failures
**After schema fixes**: 114 failures + 0 errors (1,244 collected, 1,127 passed, 3 skipped)

### Tables Added

| Table                  | schema.sql | database.py migration |
| ---------------------- | ---------- | --------------------- |
| `compliance_deadlines` | ✅         | ✅                    |
| `scheduled_reports`    | ✅         | ✅                    |
| `webhooks`             | ✅         | ✅                    |
| `country_risk_scores`  | ✅         | ✅                    |
| `user_orgs`            | ✅         | ✅                    |

### Seed Fixes

- `seed_framework_mappings.py`: Added `org_id` to INSERT (was inserting NULL into NOT NULL column)

### Remaining 114 Failures (Pre-existing Implementation Bugs)

| File                             | Count | Root Cause                                               |
| -------------------------------- | ----- | -------------------------------------------------------- |
| `test_supplier_exchange.py`      | 33    | Exchange endpoints not implemented                       |
| `test_orgs_routes.py`            | 24    | `/api/orgs/*` endpoints not implemented                  |
| `test_questionnaire_autofill.py` | 15    | Autofill feature not implemented                         |
| `test_suppliers_routes.py`       | 8     | Supplier route assertion mismatches                      |
| `test_zero_import_routes.py`     | 7     | Response shape mismatches (e.g., expects `skip` field)   |
| `test_password_reset.py`         | 7     | Password reset endpoints not implemented                 |
| `test_upload_routes.py`          | 5     | Upload route assertion mismatches                        |
| `test_templates_and_reports.py`  | 3     | PDF generation / response shape issues                   |
| `test_schema_consistency.py`     | 3     | Schema consistency assertion bugs                        |
| `test_risk_routes.py`            | 3     | Risk route assertion mismatches                          |
| `test_org_isolation.py`          | 3     | Evidence drilldown uses in-memory cache (not org-scoped) |
| `test_realtime.py`               | 2     | Realtime endpoint issues                                 |
| `test_scope3_routes.py`          | 1     | Scope3 route assertion mismatch                          |

### What Works

- `test_new_routes.py`: **103/103 passed**
- `test_scoring.py`: **all passed**
- `test_phase_d_features.py`: many now pass (previously all ERROR on setup)
- Total: **1,127 passed** (was 1,049)

### Status

**PARTIALLY RESOLVED** — schema additions eliminated all 110 ERROR (setup) failures.
**114 FAILED tests remain** — these are pre-existing bugs in the implementation itself:

- Tests written against unimplemented endpoints
- Tests written against endpoints that return different response shapes
- Tests that check org isolation on an in-memory global cache (not DB)
- Tests that expect human-readable hash values in a SHA256 hex digest field

These require feature implementation, not schema changes. They are tracked as separate work items.
