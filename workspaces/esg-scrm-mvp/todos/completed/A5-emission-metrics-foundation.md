# A5 — Emission Metrics Foundation

**Date:** 2026-05-20
**Phase:** A / Data Foundation
**Status:** Complete

## What Was Built

### A5.1 Production Volume + Intensity Endpoints

- `production_volume` column added to metrics table
- `GET /api/metrics/intensity` returns tCO2e per unit and kWh per unit
- Required for GRI 302-3 (energy intensity) and GRI 305-4 (emissions intensity) framework mappings
- **Verification:** `grep "production_volume\|intensity\|GRI.*302\|GRI.*305" src/api/routes/`

### A5.2 Renewable Energy Tracking

- `renewable_kwh` column added to metrics table
- Renewable energy percentage: `renewable_kwh / total_kwh`
- `rec_certificates` table added (id, org_id, source, kwh_certified, period_start, period_end, certificate_url)
- Dashboard displays renewable energy share
- **Verification:** `grep "renewable\|rec_certificate\|RECs" src/db/schema.sql src/api/routes/`

### A5.3 Wastewater + Water Stress

- `wastewater_discharge` and `water_stress_level` columns added to water metrics
- `GET /api/water/wastewater` endpoint added
- Water stress mapping by supplier geography using WRI Aqueduct data
- **Verification:** `grep "wastewater\|water_stress\|WRI\|Aqueduct" src/api/routes/ src/db/`

## Specs Implemented

- `specs/dashboard-metrics.md` Cluster 1, G6 Water Stress
- `specs/framework-mapping.md` renewable energy share
