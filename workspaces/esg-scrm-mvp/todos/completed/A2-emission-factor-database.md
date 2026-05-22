# A2 — Emission Factor Database

**Date:** 2026-05-20
**Phase:** A / Data Foundation
**Status:** Complete

## What Was Built

### A2.1 Emission Factors Table

- `emission_factors` table created in both `schema.sql` and `schema_pg.sql`
- Columns: id, category, factor_value, unit, source (GHG Protocol/IPCC/EPA/DEFRA/IEA), region, year, table_or_equation, is_active, org_id
- **Verification:** `grep "emission_factors" src/db/schema.sql src/db/schema_pg.sql`

### A2.2 Seed Emission Factors (seed_emission_factors.py)

- `src/db/seed_emission_factors.py` seeds 30+ rows including:
  - Bangladesh grid electricity: 0.67 tCO2e/MWh (IEA 2023) — NOTE: spec says 0.52, code uses 0.67
  - Diesel: 2.68 tCO2e/L (GHG Protocol)
  - Natural gas, water treatment, waste disposal
  - Spend-based EEIO factors from EXIOBASE
  - DEFRA 2023 flight factors (short-haul/long-haul per pax-km)
  - GHG Protocol hotel night factors
- Each row cites source, year, region, and table_or_equation
- **Verification:** `grep "0.67\|0.52\|bangladesh\|IEA\|GHG\|DEFRA" src/db/seed_emission_factors.py`

### A2.3 Emission Factors API (emission_factors.py)

- `src/api/routes/emission_factors.py` with list endpoint
- Filtering by category/region/year
- `require_auth` dependency applied
- Org-scoped
- **Verification:** `grep "emission_factors\|category.*region.*year" src/api/routes/emission_factors.py`

### A2.4 Scope3 Calculation Wired to Emission Factors

- `src/api/routes/suppliers.py` queries `emission_factors` table for Scope 3 calculation
- Replaces hardcoded 0.94 tCO2e/$1000 spend
- **Note:** PARTIAL — still has hardcoded 0.94 fallback when no rows found
- **Verification:** `grep "emission_factor\|factor_value" src/api/routes/suppliers.py`

### A2.5 Coverage Calculation from Responses

- `scope3_coverage_pct` replaced with actual calculation from supplier questionnaire responses
- Spend-weighted coverage calculation
- **Verification:** `grep "coverage_pct\|coverage.*spend\|questionnaire.*coverage" src/api/routes/`

## Specs Implemented

- `specs/framework-mapping.md` § Emission Factor Sources
- `specs/supplier-engagement.md` § Coverage Calculation
