# DISCOVERY: seed_emission_factors and seed_framework_mappings crash on standalone run

## Finding

Both standalone seed files have parameter count mismatches between their INSERT tuples and the actual table column counts. When run directly (`python -m src.db.seed_emission_factors`), they crash with `psycopg2.errors.InvalidParameterCount` (PostgreSQL) or `sqlite3.ProgrammingError` (SQLite).

## seed_emission_factors.py

- INSERT targets `emission_factors(org_id, factor_name, category, factor_value, unit, country_code, source, year, is_active, created_at)` — 10 columns
- Tuple provides: `(factor_name, category, value, unit, country_code, source, year)` — 7 values
- Missing: `org_id`, `factor_value` (named `value` in tuple), `is_active`, `created_at`

## seed_framework_mappings.py

- INSERT targets `framework_mappings(org_id, cluster, metric_name, framework, disclosure_code, disclosure_name, description, created_at)` — 8 columns
- Tuple provides: `(cluster, metric_name, framework, disclosure_code, description)` — 5 values
- Missing: `org_id`, `disclosure_name`, `created_at`

## Fix required

Both seed files must be corrected to provide all required columns with matching names.
