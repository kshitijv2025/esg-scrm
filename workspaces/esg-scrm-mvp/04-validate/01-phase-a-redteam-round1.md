# Phase A (Milestone 1) Red Team — Round 1

**Posture**: L5_DELEGATED
**Scope**: Phase A only — Data Foundation
**Date**: 2026-05-20

---

## Findings Summary

| Severity | Count | Items                                                                                                             |
| -------- | ----- | ----------------------------------------------------------------------------------------------------------------- |
| CRITICAL | 5     | A1.4×2 seed param count, A2.1 table_or_equation missing, A2.2 Bangladesh wrong value, A2.2 DEFRA flights missing  |
| HIGH     | 6     | A3.1×4 missing features, A3.4 column mismatch, A2.3 org scoping, A5.1 path mismatch, A1.7 field_name/unit missing |
| MEDIUM   | 3     | A1.5 DATABASE_URL commented, A1.7 FK constraints, A4 token_version untested                                       |
| PASS     | 14    | A1.1, A1.2, A1.3, A1.6, A2.4, A2.5, A3.3, A4.1-4.6, A5.2, A5.3                                                    |

---

## CRITICAL Findings

### CRIT-1: emission_factors table missing `table_or_equation` column

**Item**: A2.1
**Spec**: `specs/framework-mapping.md § Emission Factor Sources` — column `table_or_equation (TEXT)` required
**Verification**: `grep -A 15 "CREATE TABLE.*emission_factors" src/db/schema.sql src/db/schema_pg.sql`
**Actual**: Both schemas define emission_factors WITHOUT `table_or_equation` column
**Impact**: Seed data cannot populate table_or_equation; any code depending on it gets KeyError
**Status**: CRITICAL — schema drift from spec

### CRIT-2: seed_emission_factors.py standalone crash

**Item**: A1.4 / A2.2
**Spec**: seeds must work independently against both SQLite and PostgreSQL
**Verification**: Count INSERT placeholder `?` vs provided tuple values
**Actual**: Tuple has 7 elements `(factor_name, category, value, unit, country_code, source, year)` but table has 10+ columns (org_id, factor_value, is_active, created_at all unprovided)
**Impact**: `python -m src.db.seed_emission_factors` crashes with parameter count mismatch on standalone run
**Status**: CRITICAL — blocks independent seeding

### CRIT-3: seed_framework_mappings.py standalone crash

**Item**: A1.4
**Verification**: Same pattern as CRIT-2
**Actual**: Tuple has 5 elements `(cluster, metric_name, framework, disclosure_code, description)` but INSERT expects 8 columns
**Impact**: `python -m src.db.seed_framework_mappings` crashes on standalone run
**Status**: CRITICAL — blocks independent seeding

### CRIT-4: Bangladesh emission factor wrong value

**Item**: A2.2
**Spec**: Bangladesh grid electricity = 0.67 tCO2e/MWh from IEA 2023
**Verification**: `grep "Bangladesh" src/db/seed_emission_factors.py`
**Actual**: `("Electricity grid — Bangladesh", "grid_electricity", 0.73, "kgCO2/kWh", "BD", "IEA Emission Factors 2022", 2022)` — 0.73 vs 0.67, year 2022 vs 2023
**Impact**: All Bangladesh grid emission calculations use wrong (inflated) factor
**Status**: CRITICAL — wrong emission factor data

### CRIT-5: DEFRA flight factors absent from seed

**Item**: A2.2
**Spec**: DEFRA 2023 flight factors (short-haul/long-haul per pax-km) must be seeded
**Verification**: `grep -i "flight\|DEFRA.*2023" src/db/seed_emission_factors.py`
**Actual**: No flight factors in seed file
**Impact**: Scope 3 Category 6 (business travel) cannot use DB emission factors
**Status**: CRITICAL — spec requirement unmet

---

## HIGH Findings

### HIGH-1: emission_factors.py endpoint has no org scoping

**Item**: A2.3
**Verification**: `grep -n "org_id" src/api/routes/emission_factors.py` — query has no org_id filter
**Actual**: All emission factors visible to all orgs — cross-tenant data leak
**Impact**: Org A sees Org B's custom emission factors
**Status**: HIGH — org isolation violated

### HIGH-2: emission_factors.py endpoint missing year filter

**Item**: A2.3
**Spec**: list endpoint with filtering by category/region/year
**Verification**: `grep -n "year" src/api/routes/emission_factors.py` — no year parameter
**Actual**: No year filtering capability
**Status**: HIGH — spec requirement unmet

### HIGH-3: upload.py missing data quality warnings

**Item**: A3.1
**Verification**: `grep -in "warn\|quality" src/api/routes/upload.py` — empty
**Actual**: Rows with bad data skipped silently; no WARN-level log
**Status**: HIGH — spec requirement unmet

### HIGH-4: upload.py missing duplicate detection

**Item**: A3.1
**Verification**: `grep -in "duplicate\|dedup" src/api/routes/upload.py` — empty
**Actual**: No duplicate detection (same date + factory + metric)
**Status**: HIGH — spec requirement unmet

### HIGH-5: upload.py missing org-scoped file storage + uploaded_files table

**Item**: A3.1
**Verification**: `grep -n "makedirs\|upload.*dir\|file.save" src/api/routes/upload.py` — empty; `grep "CREATE TABLE.*uploaded_files" src/db/schema.sql`
**Actual**: Files read and discarded after DB insert; `uploaded_files` table does not exist
**Status**: HIGH — spec requirement unmet (file persistence and metadata table both missing)

### HIGH-6: supplier upload column names mismatch spec

**Item**: A3.4
**Verification**: `grep -A 8 "SUPPLIER_REQUIRED_COLUMNS" src/api/routes/upload.py`
**Actual**: Code requires `name, country, industry, tier, annual_spend_usd, phone, preferred_channel, certifications`
**Spec requires**: `supplier_name, country, contact_email, phone, annual_spend, tier, category`
**Mismatches**: `supplier_name→name`, `contact_email→MISSING`, `annual_spend→annual_spend_usd`, `category→industry`; `preferred_channel` and `certifications` are EXTRA in code
**Status**: HIGH — spec requirement unmet

### HIGH-7: /api/dashboard/intensity vs spec path /api/metrics/intensity

**Item**: A5.1
**Verification**: Route registered at `main.py:104` prefix `/api/dashboard` + `dashboard.py:121 @router.get("/intensity")`
**Actual**: Path is `/api/dashboard/intensity`; spec says `/api/metrics/intensity`
**Status**: HIGH — path mismatch (spec needs updating or alias needed)

### HIGH-8: framework_mappings missing field_name and unit columns

**Item**: A1.7
**Spec**: framework_mappings table has `field_name TEXT` and `unit TEXT` columns
**Verification**: `grep -A 20 "CREATE TABLE.*framework_mappings" src/db/schema.sql`
**Actual**: Columns `id, org_id, cluster, metric_name, framework, disclosure_code, disclosure_name, description, created_at` — no `field_name` or `unit`
**Status**: HIGH — schema drift from spec

### HIGH-9: emission_factors.py endpoint has zero test coverage

**Item**: A2.3 (test coverage)
**Verification**: `grep -l "emission_factors\|emission-factors" tests/`
**Actual**: No test imports or calls the emission_factors route
**Status**: HIGH — new module with no tests

---

## MEDIUM Findings

### MED-1: .env.example DATABASE_URL commented out

**Item**: A1.5
**Verification**: `grep "DATABASE_URL" .env.example`
**Actual**: `# DATABASE_URL=postgresql://esg_scrm:...` — commented
**Impact**: Dev setup requires manual uncomment; spec says it should be documented
**Status**: MEDIUM

### MED-2: FK constraints missing in both schemas

**Item**: A1.7
**Verification**: `grep "FOREIGN KEY" src/db/schema.sql src/db/schema_pg.sql`
**Missing**: `questionnaire_responses(template_id) → questionnaire_templates(id)`, `risk_flags(org_id) → organizations(id)`, `suppliers(org_id) → organizations(id)`
**Impact**: Referential integrity not enforced at DB level
**Status**: MEDIUM

### MED-3: token_version upgrade/replay path untested

**Item**: A4.4
**Verification**: `grep -n "token_version" tests/unit/test_auth.py` — only response dict assertions, no mutation test
**Impact**: No regression guard for token_version increment logic
**Status**: MEDIUM

---

## PASS Items

| Item | Description                       | Evidence                                                  |
| ---- | --------------------------------- | --------------------------------------------------------- |
| A1.1 | PostgreSQL docker-compose.yml     | health check, volume, env config all present              |
| A1.2 | schema_pg.sql SERIAL types        | SERIAL used, TEXT throughout, FKs present                 |
| A1.3 | DATABASE_URL detection            | `DATABASE_URL.startswith("postgresql://")` in database.py |
| A1.6 | Connection pooling                | 5-10 connections, 300s recycle, evict logic present       |
| A2.4 | suppliers.py uses DB not hardcode | `_get_spend_based_factor` queries emission_factors table  |
| A2.5 | scope3_coverage_pct from DB       | `fetch_coverage_stats` computes from questionnaire_status |
| A3.3 | /api/uploads/history              | endpoint exists, org-scoped, audit_log table present      |
| A4.1 | bcrypt hashing                    | bcrypt.hashpw/gensalt/checkpw present                     |
| A4.2 | bcrypt in login/register          | hash_password/verify_password throughout auth routes      |
| A4.3 | forgot/reset-password             | token generation, expiry check, hash update all present   |
| A4.4 | token_version in JWT              | in payload, checked on decode, incremented on change      |
| A4.5 | email verification gate           | unverified accounts cannot login (403)                    |
| A4.6 | invite/accept-invite              | both endpoints functional, inactive user flow correct     |
| A5.2 | renewable_kwh + rec_certs         | columns present, renewable_pct calculation correct        |
| A5.3 | wastewater + water stress         | WRI Aqueduct mapping present, endpoint correct            |

---

## Convergence Assessment

**CRITICAL findings**: 5
**HIGH findings**: 9
**Phase A NOT converged** — CRITICAL and HIGH findings must be resolved.

Per autonomous execution model, pre-existing failures (Rule 1, zero-tolerance) must be fixed. These are Phase A implementation gaps that require fixes.

---

## Next Steps

Recommend autonomous fix pass for CRITICAL items (CRIT-1 through CRIT-5) before any Phase B work proceeds.
