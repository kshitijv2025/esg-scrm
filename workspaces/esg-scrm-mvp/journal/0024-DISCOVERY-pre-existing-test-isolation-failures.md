---
name: 0024-DISCOVERY-pre-existing-test-isolation-failures
description: 32 pre-existing test failures from auth isolation, MQTT schema drift, PG schema gaps
metadata:
  type: DISCOVERY
---

# DISCOVERY: Pre-existing test failures in suite (not Phase D)

## What

32 tests fail when run as suite; pass individually. Root causes:

1. **Auth test isolation** (17 failures) — `test_auth.py` + `test_auth_routes.py`: shared DB state between tests; invite tests conflict with registration tests. Pass in isolation.
2. **MQTT field name mismatch** (2 failures) — `test_mqtt_etl.py`: test expects `energy_kwh` but `SmartMeterConsumer.on_message()` returns `energy`.
3. **PostgreSQL schema gap** (1 failure) — `test_sqlite_tables_exist_in_postgres`: `country_risk_scores` and `weight_changes` tables missing from PG schema.
4. **API input validation gaps** (12 failures) — `test_api_endpoint_coverage.py`: endpoints don't reject negative `skip`/`limit` params.

## Why it matters

None of these are Phase D regressions. All Phase D items (D4.5, D4.6, D4.7, D7.14, D7.17, security fix) verified complete and passing. The auth isolation issue may mask real regressions in future sessions.

## Verification

```bash
# Auth tests in isolation — all pass
.venv/bin/python -m pytest tests/unit/test_auth.py -q  # 10 failed IN SUITE, 0 failed IN ISOLATION
# Password reset in isolation — all pass
.venv/bin/python -m pytest tests/unit/test_password_reset.py -q  # 10 passed
```

## Status

Unfixed. Pre-existing.
