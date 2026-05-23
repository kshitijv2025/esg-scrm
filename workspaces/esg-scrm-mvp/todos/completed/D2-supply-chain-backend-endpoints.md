# D2.4 — Supply Chain Backend Endpoints

**Date:** 2026-05-20
**Phase:** D / The Wow Factor — Supply Chain Tab
**Status:** Partial (risk-ranked + profile done; geopolitical + hardcoded replacements remain)

## What Was Built

### Backend Endpoints

- `GET /api/suppliers/risk-ranked` — suppliers sorted by risk score
- `GET /api/suppliers/{id}/profile` — per-supplier ESG profile
- `GET /api/scope3/categories` — Scope 3 categories with coverage data
- Org-scoped on all endpoints
- **Verification:** `grep "suppliers/risk-ranked\|suppliers.*profile\|scope3/categories" src/api/routes/suppliers.py src/api/routes/scope3.py`

## Pending (Not Yet Implemented)

- D2.1 — Frontend Supply Chain tab: supplier list sidebar with risk tier badges
- D2.2 — Frontend Supplier Profile Panel with E/S/G scores
- D2.3 — Frontend Scope 3 Detail Panel with GHG Protocol Scope 3 category bars
- D2.5 — Frontend Geopolitical Heat Map (requires D2.4 geopolitical endpoint + D4.6)

## Note

PARTIAL: risk-ranked and profile endpoints done; `GET /api/risk/geopolitical` endpoint and hardcoded replacements (`_REFERENCE_SCORES`, `SCORECARD_QUADRANTS` in risk.py, `CATEGORY_META` in scope3.py) still need completion per original todo.

## Specs Implemented

- `specs/dashboard-tabs.md` § Tab 2
