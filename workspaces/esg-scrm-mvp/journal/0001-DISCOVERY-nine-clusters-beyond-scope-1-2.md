# DISCOVERY: Nine clusters beyond the current Scope 1/2 energy tracker

**Date**: 2026-05-07

## What was found

The current ESG dashboard (App.jsx + API routes) covers only 4 ESG metrics across 2 clusters:

- Energy/GHG (Scope 1 + 2)
- Water (total m³, no intensity)
- Scope 3 Cat 1 (purchased goods)
- Scope 3 Cat 6 (business travel)

The friend's 9-cluster recommendation adds 5 completely uncovered clusters plus 4 partial gaps:

**Not covered at all (9 clusters)**:

- Cluster 2: Fibre mix / land / biodiversity (E2)
- Cluster 3: Waste & circularity (E3)
- Cluster 4: Own-workforce safety & wellbeing (S1)
- Cluster 6: Gender & inclusion (S3)
- Cluster 7: ESG governance & incentives (G1)
- Cluster 9: Ethics, anti-corruption & grievance (G3)
- Scope 3 upstream/downstream (full 15 categories)
- Supplier financial health (G5)
- Geopolitical/climate risk by location (G8)

**Partially covered (4 clusters)**:

- Cluster 1: Energy/GHG — has the data but no site/BU breakdown, no intensity metrics
- Cluster 5: Supplier labour rights — WhatsApp engagement infrastructure exists, no labour KPIs
- Cluster 8: Supply chain governance — coverage % exists, no segmentation, no ESG clause tracking
- Water — total m³ exists, no water stress mapping, no wastewater

## Why it matters

The current product is a **Scope 1+2 emissions tracker with supplier coverage measurement** — not an ESG platform. The friend has identified the full ESG scope that buyers (H&M, regulators, investors) will expect. The gap is not a feature gap; it is a **scope boundary gap**: the current dashboard cannot demonstrate CSRD/ESRS or GRI compliance for 11 of 14 clusters.

## Where to verify

- `apps/web/src/App.jsx` — 6 MetricCards map to exactly 2 clusters (energy, water)
- `src/api/routes/dashboard.py` — hardcoded METRICS dict has 6 entries
- `src/api/routes/questionnaires.py` — WhatsApp questionnaire has no labour rights questions
- `workspaces/esg-scrm-mvp/01-analysis/05-cluster-gap-analysis.md` — full mapping
