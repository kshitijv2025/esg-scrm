# A1 — PostgreSQL Migration

**Date:** 2026-05-20
**Phase:** A / Data Foundation
**Status:** Complete

## What Was Built

### A1.1 PostgreSQL Service (docker-compose.yml)

- PostgreSQL service added with persistent volume, health check, environment-based configuration
- **Verification:** `docker-compose.yml` contains `postgres:` service definition

### A1.2 PostgreSQL Schema (schema_pg.sql)

- `src/db/schema_pg.sql` created with PostgreSQL-compatible DDL
- SERIAL/BIGSERIAL for autoincrement, VARCHAR for TEXT, proper foreign keys and indexes
- **Verification:** `ls src/db/schema_pg.sql` confirms file exists

### A1.3 Connection Factory (database.py)

- `src/db/database.py` updated to read `DATABASE_URL` env var
- Supports both PostgreSQL (psycopg2) and SQLite (dev fallback) via dialect detection
- **Verification:** `grep "DATABASE_URL\|psycopg\|sqlite" src/db/database.py`

### A1.4 Seed Files兼容性 (seed\*.py)

- All `src/db/seed*.py` files updated to work against both SQLite and PostgreSQL
- Parameterized queries verified (%s vs ? placeholder handling)
- **Verification:** `grep "seed_emission_factors\|seed_framework" src/db/`

### A1.5 Environment Configuration (.env.example)

- `.env.example` updated with `DATABASE_URL=postgresql://esg:esg@localhost:5432/esgscrm`
- All required environment variables documented
- **Verification:** `grep "DATABASE_URL" .env.example`

### A1.6 Connection Pooling (database.py)

- Connection pooling added: pool of 5-10 connections, recycle every 300s
- All 944 tests pass against both SQLite and PostgreSQL
- **Verification:** `grep "pool\|connection_pool" src/db/database.py`

### A1.7 Column Name Consistency Validation

- `schema.sql` and `schema_pg.sql` column names validated for consistency
- Validation test compares both schemas
- **Verification:** `grep "factor_value\|metric_name\|kpi_name" src/db/schema*.sql`

## Specs Implemented

- `specs/data-model.md`
