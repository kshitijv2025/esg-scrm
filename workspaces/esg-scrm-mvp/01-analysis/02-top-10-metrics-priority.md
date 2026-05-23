# Top 10 Metrics — Operations Homepage Priority

## Decision

Add a **summary strip** of 4 KPIs above the existing 6 metric cards. Total: 10 visible.

## Rationale

For a CFO/COO buyer at a garment manufacturer, the top-of-page hierarchy must answer:
1. *What is my overall ESG completeness?* → Supply Chain Coverage %
2. *Are there any active risks requiring action?* → Active Risk Flags
3. *How much of my Scope 3 data do I have?* → Scope 3 Completeness %
4. *What is my total carbon footprint across all scopes?* → Total CO2e

These are the metrics a buyer opens the dashboard to check before anything else.

The existing 6 operational metrics provide the drill-down evidence for each.

## Priority Order (left-to-right, top-to-bottom)

### Summary Strip (Row 0 — 4 KPIs)
| # | Metric | Source Endpoint | Scope | Why |
|---|--------|----------------|-------|-----|
| 1 | **Supply Chain Coverage %** | `/questionnaires/coverage-stats` → `total_coverage` | — | Leading indicator: coverage drives all Scope 3 data quality |
| 2 | **Active Risk Flags** | `/risk/summary` → `total` | — | COO action trigger: how many open risks need attention |
| 3 | **Scope 3 Completeness %** | `/scope3/completeness` → `overall_coverage_pct` | Scope 3 | Data quality signal: what % of categories have supplier responses |
| 4 | **Total CO2e (All Scopes)** | Derived: `emissions_tco2` + `scope3_category1` + `diesel_consumed` + `scope3_category6` | Scope 1+2+3 | Headline carbon number showing full footprint |

### Operational Metrics Grid (Rows 1–2 — existing 6)
| # | Metric | Source | Scope | Why |
|---|--------|--------|-------|-----|
| 5 | Electricity (Scope 2) | `/dashboard/live` → `energy_kwh` | Scope 2 | Operational cost + carbon from purchased electricity |
| 6 | Total Emissions (Scope 1+2) | `/dashboard/live` → `emissions_tco2` | Scope 1+2 | Primary GHG compliance metric |
| 7 | Water Withdrawal | `/dashboard/live` → `water_m3` | Environmental | Material for garment manufacturing (wet processing) |
| 8 | Purchased Goods (Scope 3) | `/dashboard/live` → `scope3_category1` | Scope 3 Cat 1 | Largest Scope 3 category for manufacturers |
| 9 | Diesel Combustion (Scope 1) | `/dashboard/live` → `diesel_consumed` | Scope 1 | Backup generation fuel; also shows chain-broken demo |
| 10 | Business Travel (Scope 3) | `/dashboard/live` → `scope3_category6` | Scope 3 Cat 6 | Emerging category; shows Scope 3 breadth |

## What Was Dropped

None of the original 6 were removed — all remain in the grid below.

## Data Sources

All data comes from existing endpoints already wired to the frontend:
- `/questionnaires/coverage-stats` → `total_coverage` (already fetched in Dashboard)
- `/risk/summary` → `total` (already fetched in RiskAlertsPanel via Promise.all)
- `/scope3/completeness` → `overall_coverage_pct` (already fetched in RiskAlertsPanel)
- `/dashboard/live` → emissions + scope3 values (already fetched)

**No new backend endpoints needed.** Total CO2e is derived client-side from existing data.

## ESG Scope Reference

| Metric | Scope | Category |
|--------|-------|----------|
| Electricity | Scope 2 | Environmental |
| Total Emissions | Scope 1+2 | Environmental |
| Water | Environmental | Environmental |
| Purchased Goods | Scope 3 Cat 1 | Social |
| Diesel | Scope 1 | Environmental |
| Business Travel | Scope 3 Cat 6 | Social |
| Supply Chain Coverage | N/A (data quality) | — |
| Risk Flags | N/A (operational) | — |
| Scope 3 Completeness | Scope 3 | Social |
| Total CO2e | Scope 1+2+3 | All |
