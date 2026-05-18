---
name: gap-four-api-wire-ups-missing
description: Frontend panels existed but weren't calling their API endpoints
type: GAP
---

# GAP: Four API wire-ups missing in frontend

## What

Bidirectional parity audit found 4 backend endpoints that existed but had no corresponding frontend API calls:

1. **`GET /api/risk/scorecard`** — `RiskScorecard` (2×2 G2/G5/G8/G3 quadrant) was absent from `RiskAlertsPanel`
2. **`GET /api/scope3/completeness`** — `Scope3CompletenessMeter` (donut + category bars) was absent from `RiskAlertsPanel`
3. **`GET /api/suppliers/{id}/profile`** — Supplier profile panel never fetched; `setSelectedSupplier(s)` was called but no API call made
4. **`GET /api/risk/geopolitical`** — `GovernancePanel` in `SupplyChainPanel` was hardcoded static JSX (Board Independence 67%, Grievance Mechanisms, Ethics Training 94%, ESG Audits Q4 2024)

## Why

The spec `specs/dashboard-tabs.md` listed these panels but the implementation only created the tab routing shell without wiring the data fetch.

## Fix

- `SupplyChainPanel`: added `geopolitical` state, fetch `/risk/geopolitical`, render dynamic geopolitical heatmap table
- `SupplyChainPanel`: `selectSupplier(s)` now fetches `/suppliers/${s.id}/profile` on click
- `RiskAlertsPanel`: added `scorecard` + `completeness` state, fetches `/risk/scorecard` and `/scope3/completeness` in parallel, renders 2×2 scorecard grid and completeness donut
- Hardcoded Governance panel removed entirely

## Verification

- `npm run build` → ✓ built in 353ms, 0 errors
- All 13 backend tests pass
- Field accessors verified: `q.score`, `q.tier`, `q.trend`, `q.active_flags`, `completeness.overall_coverage_pct`, `completeness.by_category`, `supplierProfile.clusters`, `supplierProfile.ml_recommendations` — all match backend response keys

## Status

Fixed in this session.
