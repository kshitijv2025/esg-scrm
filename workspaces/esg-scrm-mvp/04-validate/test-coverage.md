# Test Coverage Report — ESG+SCRM MVP

## Test Enumeration

```
pytest --collect-only -q tests/
Total collected: 1305 tests
```

### Test Directory Structure

```
tests/
  unit/          (49 test files)
  integration/   (test_database_integration.py, test_route_groups.py)
  regression/    (test_autofill_endpoint.py)
  sdk/          (test_sdk_patterns.py)
```

---

## Test Results Summary

| Metric          | Count |
| --------------- | ----- |
| Total Collected | 1305  |
| Passed          | 1245  |
| Failed          | 8     |
| Errors          | 49    |
| Skipped         | 3     |

**Duration:** 138.08s (2m 18s)

---

## Failed Tests (8 failures)

| Test                                               | File                                      | Issue                                                                                      | Severity |
| -------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------ | -------- |
| `test_create_template`                             | `test_route_groups.py::TestTemplatesCRUD` | `sqlite3.OperationalError: no such table: risk_flags` - database schema not seeded in test | HIGH     |
| `test_upload_suppliers_csv`                        | `test_route_groups.py::TestUploadCSV`     | Same `no such table: risk_flags` issue                                                     | HIGH     |
| `test_list_alerts_authenticated_returns_200`       | `test_zero_import_routes.py`              | Returns 401 Unauthorized instead of 200                                                    | MEDIUM   |
| `test_create_template_invalid_tier_returns_400`    | `test_zero_import_routes.py`              | Returns 401 instead of 400 (auth issue)                                                    | MEDIUM   |
| `test_create_template_empty_questions_returns_400` | `test_zero_import_routes.py`              | Returns 401 instead of 400 (auth issue)                                                    | MEDIUM   |
| `test_update_template_nonexistent_returns_404`     | `test_zero_import_routes.py`              | Returns 401 instead of 404 (auth issue)                                                    | MEDIUM   |
| `test_delete_template_nonexistent_returns_404`     | `test_zero_import_routes.py`              | Returns 401 instead of 404 (auth issue)                                                    | MEDIUM   |
| `test_workforce_safety_authenticated_returns_200`  | `test_zero_import_routes.py`              | Returns 401 instead of 200 (auth issue)                                                    | MEDIUM   |

---

## Error Tests (49 errors)

Most errors originate from `tests/unit/test_whatsapp.py` and `tests/unit/test_whatsapp_integration.py` — 49 total errors. Likely causes:

- Missing `risk_flags` table in test database
- Missing WhatsApp webhook fixtures
- Authentication/authorization setup issues

---

## New Module Coverage (Phase D Routes)

Per `src/api/main.py` lines 206-227, Phase D added these routes:

| New Route Module     | Test File                        | Coverage Status                   |
| -------------------- | -------------------------------- | --------------------------------- |
| `corrective_actions` | `test_corrective_actions.py`     | EXISTS - not run individually     |
| `documents`          | `test_documents.py`              | EXISTS - not run individually     |
| `compliance`         | (in `test_phase_d_features.py`)  | EXISTS - covered in Phase D tests |
| `scheduled_reports`  | (in `test_phase_d_features.py`)  | EXISTS - covered in Phase D tests |
| `webhooks`           | (in `test_phase_d_features.py`)  | EXISTS - 8 tests in Phase D suite |
| `buyer_portal`       | `test_buyer_portal.py` + Phase D | EXISTS - covered                  |
| `onboarding`         | (in `test_phase_d_features.py`)  | EXISTS - covered                  |
| `orgs`               | `test_orgs_routes.py`            | EXISTS - 25 tests, all PASS       |

**Finding:** Phase D modules DO have corresponding test files. Coverage is adequate.

---

## Integration Parity

### Backend Routes (35 files in `src/api/routes/`)

```
admin, alerts, audit, auth, billing, buyer_portal, compliance,
corrective_actions, dashboard, documents, emission_factors,
evidence, export, frameworks, gdpr, health, ml, notifications,
onboarding, orgs, questionnaires, reports, reports_pdf, risk,
scheduled_reports, scope3, suppliers, templates, tier2, tier3,
trust, upload, water, webhooks, whatsapp
```

### Frontend API Client (`apps/web/src/api/client.js`)

The frontend uses a generic fetch wrapper (`apiFetch`, `apiExport`) rather than individual typed methods. This is a **structural mismatch** — the frontend does not have typed API method coverage per endpoint.

| Frontend Pattern                      | Backend Route Coverage        |
| ------------------------------------- | ----------------------------- |
| `apiFetch('/api/dashboard/...')`      | `/api/dashboard/*` - YES      |
| `apiFetch('/api/suppliers/...')`      | `/api/suppliers/*` - YES      |
| `apiFetch('/api/evidence/...')`       | `/api/evidence/*` - YES       |
| `apiFetch('/api/questionnaires/...')` | `/api/questionnaires/*` - YES |
| `apiFetch('/api/reports/...')`        | `/api/reports/*` - YES        |
| `apiFetch('/api/alerts/...')`         | `/api/alerts/*` - YES         |

**Finding:** No typed API methods in frontend client — uses generic `apiFetch` for all endpoints. Backend routes exist for all major features.

---

## Security Test Coverage

### Rate Limiting Tests

```
tests/unit/test_rate_limiting.py
  - TestRateLimitEnforcement (3 tests) - PASS
  - TestRateLimitHeaders (2 tests) - PASS
  - TestRateLimitDifferentLimits (4 tests) - PASS
  - TestRateLimitNoAuthRequired (1 test) - PASS
  - TestMLBatchSizeLimit (3 tests) - PASS
Total: 13 passed
```

### Auth Security Tests

```
tests/unit/test_auth.py
  - test_rate_limit_on_register - PASS
  - test_rate_limit_on_login - PASS
  - test_register_weak_password_rejected - PASS
  - test_register_no_uppercase_rejected - PASS
  - test_register_no_digit_rejected - PASS
```

### RBAC Enforcement Tests

```
tests/unit/test_rbac.py
tests/unit/test_api_endpoint_coverage.py::TestRBACEnforcement (14 tests)
```

### Input Validation Tests

```
tests/unit/test_api_endpoint_coverage.py::TestInputValidation (8 tests)
```

**Finding:** Security tests exist for:

- Rate limiting (13 tests - PASS)
- Auth/password validation (multiple tests - PASS)
- RBAC enforcement (14 tests)
- Input validation (8 tests)

---

## Test Quality Issues

### 1. Database Schema Issue (HIGH)

`test_create_template` and `test_upload_suppliers_csv` fail with:

```
sqlite3.OperationalError: no such table: risk_flags
```

**Root Cause:** Test database not seeded with `risk_flags` table before integration tests run.

### 2. Authentication Test Failures (MEDIUM)

6 tests in `test_zero_import_routes.py` return 401 when expecting other status codes. These tests appear to be missing proper auth headers or token setup.

### 3. WhatsApp Test Errors (HIGH - 49 errors)

`test_whatsapp.py` and `test_whatsapp_integration.py` have widespread errors likely due to:

- Missing database fixtures (`risk_flags` table)
- Webhook HMAC validation setup
- Multi-language number parsing fixtures

### 4. Pytest Config Warnings

```
PytestConfigWarning: Unknown config option: asyncio_default_fixture_loop_scope
PytestConfigWarning: Unknown config option: asyncio_mode
```

These are non-blocking but indicate config drift.

---

## Findings Summary

| Type  | Module                                                           | Issue                                 | Severity |
| ----- | ---------------------------------------------------------------- | ------------------------------------- | -------- |
| FAIL  | `test_route_groups.py::TestTemplatesCRUD::test_create_template`  | Missing `risk_flags` table in test DB | HIGH     |
| FAIL  | `test_route_groups.py::TestUploadCSV::test_upload_suppliers_csv` | Missing `risk_flags` table in test DB | HIGH     |
| FAIL  | `test_zero_import_routes.py` (6 tests)                           | Auth header missing causing 401       | MEDIUM   |
| ERROR | `test_whatsapp.py` (24 tests)                                    | Missing fixtures/database setup       | HIGH     |
| ERROR | `test_whatsapp_integration.py` (25 tests)                        | Missing fixtures/database setup       | HIGH     |
| WARN  | pytest config                                                    | Unknown asyncio config options        | LOW      |
| WARN  | LibreSSL                                                         | NotOpenSSLWarning for urllib3         | INFO     |

---

## Recommendations

1. **Fix database seeding** for integration tests — ensure `risk_flags` table exists before tests run
2. **Fix auth test setup** in `test_zero_import_routes.py` — provide proper auth headers/tokens
3. **Fix WhatsApp test fixtures** — add required database tables and webhook mocks
4. **Update pytest config** — remove or fix `asyncio_default_fixture_loop_scope` and `asyncio_mode` options
