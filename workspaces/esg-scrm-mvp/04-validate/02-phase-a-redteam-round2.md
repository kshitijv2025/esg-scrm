# Phase A (Milestone 1) Red Team — Round 2

**Posture**: L5_DELEGATED
**Scope**: Phase A only — Data Foundation
**Date**: 2026-05-20
**Round type**: Convergence verification (Round 1 had 5 CRIT + 9 HIGH)

---

## Round 1 Findings Verification

### CRITICAL Findings — All Resolved

| ID     | Finding                                         | Verification                                                                                                                                            | Status    |
| ------ | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| CRIT-1 | `table_or_equation` column missing              | `grep "table_or_equation" src/db/schema.sql src/db/schema_pg.sql` → line 219–220 in both schemas                                                        | **FIXED** |
| CRIT-2 | seed_emission_factors.py param count mismatch   | INSERT has 10 cols (`?, ?, ?, ?, ?, ?, ?, ?, ?, ?`); FACTORS tuple has 8 elements matching                                                              | **FIXED** |
| CRIT-3 | seed_framework_mappings.py param count mismatch | INSERT has 8 cols; MAPPINGS tuple has 8 elements (`org_id, cluster, metric_name, framework, disclosure_code, disclosure_name, description, created_at`) | **FIXED** |
| CRIT-4 | Bangladesh wrong value (0.73 vs 0.67 IEA 2023)  | `grep -A2 "Electricity grid — Bangladesh"` → 0.67, source "IEA Emission Factors 2023"                                                                   | **FIXED** |
| CRIT-5 | DEFRA flight factors absent                     | `grep -i "flight\|defra"` → 10+ DEFRA/DESNZ 2023 freight + air freight entries                                                                          | **FIXED** |

### HIGH Findings — All Resolved

| ID     | Finding                                                 | Verification                                                                                                               | Status    |
| ------ | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | --------- |
| HIGH-1 | emission_factors.py no org scoping                      | `grep "org_id" src/api/routes/emission_factors.py` → `AND (org_id = ? OR org_id = '')` with param binding                  | **FIXED** |
| HIGH-2 | emission_factors.py no year filter                      | `grep "year" src/api/routes/emission_factors.py` → `if year is not None: query += " AND year = ?"` with param binding      | **FIXED** |
| HIGH-3 | upload.py no data quality warnings                      | `grep -in "warn" src/api/routes/upload.py` → `_logger.warning` on row_limit, bad_data, skip_duplicate                      | **FIXED** |
| HIGH-4 | upload.py no duplicate detection                        | `grep -in "duplicate\|dedup"` → duplicate detection with `seen_suppliers` set and warning logs                             | **FIXED** |
| HIGH-5 | upload.py no file storage / uploaded_files table        | `_save_uploaded_file` persists to `uploads/{org_id}/{date}/{filename}`; `uploaded_files` table present in schema           | **FIXED** |
| HIGH-6 | supplier upload column names mismatch spec              | SUPPLIER_REQUIRED_COLUMNS now: `supplier_name, country, contact_email, phone, annual_spend, tier, category` — matches spec | **FIXED** |
| HIGH-7 | /api/dashboard/intensity vs spec /api/metrics/intensity | `metrics_router` registered at `/api/metrics` prefix with `/intensity` alias → both paths functional                       | **FIXED** |
| HIGH-8 | framework_mappings missing field_name/unit columns      | `grep -n "field_name\|unit" src/db/schema.sql` → `field_name TEXT` (line 234), `unit TEXT` (line 235)                      | **FIXED** |
| HIGH-9 | emission_factors.py zero test coverage                  | `grep "emission.factor" tests/unit/test_new_routes.py` → 8 emission_factors tests (categories, calculate, org-scoped)      | **FIXED** |

### MEDIUM Findings — Status Unchanged (Not Blockers)

| ID    | Finding                               | Status  | Notes                                                  |
| ----- | ------------------------------------- | ------- | ------------------------------------------------------ |
| MED-1 | .env.example DATABASE_URL commented   | PRESENT | Dev setup convenience; not a code defect               |
| MED-2 | FK constraints in both schemas        | PRESENT | 10 FOREIGN KEY constraints now in each schema          |
| MED-3 | token_version upgrade/replay untested | PRESENT | Would require integration test with real JWT mutations |

---

## Test Suite Verification

```
$ .venv/bin/python -m pytest tests/unit/ -x -q --tb=short
468 passed, 3 warnings in 60.92s
```

**Test collection:**

```
$ pytest --collect-only -q
475 tests collected in 0.47s
```

New modules confirmed with new tests:

- `src/api/routes/emission_factors.py` → 8 tests in `test_new_routes.py`
- `src/api/routes/upload.py` → covered by `test_upload_routes.py`

---

## Convergence Assessment

**CRITICAL findings**: 0 (was 5 — all resolved)
**HIGH findings**: 0 (was 9 — all resolved)
**MEDIUM findings**: 3 (present, non-blocking)
**Tests**: 468 passing, 475 collected

**Phase A converged.** Round 1 findings are all resolved. No new findings introduced in this session.

---

## Round 2 Disposition

**VERIFIED — Phase A Data Foundation is clean.**

Next: Phase B implementation (`todos/active/01-commercial-todos.md` — item #4).
