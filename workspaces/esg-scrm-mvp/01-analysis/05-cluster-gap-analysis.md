# ESG Cluster Gap Analysis — Dashboard vs. Recommended Data Clusters

> Source: Friend's recommendations + 4 additional gaps identified in prior analysis
> Date: 2026-05-07

## Current Implementation Summary

### Dashboard Tab 1 (Dashboard)

- `MetricCard` components for 6 metrics: `energy_kwh`, `emissions_tco2`, `water_m3`, `scope3_category1`, `diesel_consumed`, `scope3_category6`
- `CoverageHero` — supplier coverage (47/73 responding)
- `TrendChart` — 5-month trend for energy/emissions/water
- `EvidencePanel` — hash-chain tamper evidence per metric

### Dashboard Tab 2 (Frameworks)

- `FrameworkCompare` — maps `energy_kwh`, `scope3_category_1`, `diesel_consumed`, `scope3_category_6` to CSRD/ESRS E1, ISSB/IFRS S2, GRI 302/305, TCFD

### Dashboard Tab 3 (Supplier Engagement)

- `WhatsAppBusinessPreview` — WhatsApp questionnaire flow for supplier `sup_001`

### API Routes

- `dashboard.py:156` `GET /live` — 6 hardcoded metrics
- `dashboard.py:169` `GET /trends/{metric_type}` — 5-month trend data
- `dashboard.py:178` `GET /trends` — combined trends
- `dashboard.py:192` `GET /alerts`
- `frameworks.py:154` `GET /map/{metric_type}`
- `frameworks.py:173` `GET /compare/{metric_type}`
- `questionnaires.py:88` `GET /suppliers`
- `questionnaires.py:93` `GET /questionnaire/{qnr_id}`
- `questionnaires.py:98` `GET /whatsapp-preview/{supplier_id}`
- `questionnaires.py:103` `GET /coverage`
- `questionnaires.py:119` `GET /coverage-stats`

---

## Cluster-by-Cluster Gap Analysis

### Cluster 1: Energy & GHG

**Status: PARTIALLY COVERED**

| What Exists                                                 | File:Line                              | What Is Missing                            |
| ----------------------------------------------------------- | -------------------------------------- | ------------------------------------------ |
| Site-level electricity (`energy_kwh`)                       | `dashboard.py:12-25`                   | No site/BU breakdown — single factory only |
| Scope 1 diesel (`diesel_consumed`)                          | `dashboard.py:71-87`                   | No site-level breakdown                    |
| Scope 2 emissions (`emissions_tco2` = energy x grid factor) | `dashboard.py:26-39`                   | No Scope 1+2 split by BU                   |
| Scope 3 Cat 1 only                                          | `dashboard.py:54-70`                   | No Scope 1+2 by site                       |
| Renewable energy % in framework output                      | `frameworks.py:15-16` (renewable 11%)  | No actual renewable meter / REC tracking   |
| Emission intensity per tonne/garment                        | Not present                            | Not present                                |
| `% renewable energy`                                        | `frameworks.py:15` (312,005 kWh / 11%) | No actual REC/certificate tracking         |

**Missing dashboard component**: Multi-site/BU energy/emissions breakdown panel with Scope 1+2+3 sub-panel.
**Missing API endpoint**: `GET /energy/by-site`, `GET /emissions/scope-1-2-by-site`, `GET /energy/renewable-breakdown`
**Data missing**: BU-level meter data, renewable energy certificates, production volume (for intensity denominator).

---

### Cluster 2: Fibre Mix, Land & Biodiversity

**Status: NOT COVERED**

Zero fibre, land use, or biodiversity data. The `WhatsAppBusinessPreview` (`App.jsx:667`) shows a questionnaire with only energy/water/waste/spend questions — no fibre type questions.

**Missing dashboard component**: Fibre sourcing panel showing fibre types per SKU (cotton/polyester/viscose blend), supplier country map, certification badges (organic, regenerative, GOTS, Oeko-Tex), estimated land use, biodiversity risk flags.
**Missing API endpoint**: `GET /fibre/mix`, `GET /fibre/certifications`, `GET /fibre/land-use`, `GET /biodiversity/risk-by-supplier`
**Data missing**: Fibre type per SKU, supplier farm/origin locations, organic/regenerative certification status, land use conversion data, deforestation risk flags.

---

### Cluster 3: Waste & Circularity

**Status: NOT COVERED**

Only waste-related data is in the questionnaire (`questionnaires.py:30` — `"Waste recycling rate (%)"`) as an unanswered optional question. The `WhatsAppBusinessPreview` includes waste recycling rate as question 5 (`App.jsx:58`) but it is unanswered.

**Missing dashboard component**: Production waste panel showing cutting scraps, off-spec rates, returns/take-back volumes, disposition records (recycling/landfill/incineration), kg textile waste per unit, % production waste reused/recycled, % revenue from products designed for recyclability.
**Missing API endpoint**: `GET /waste/production`, `GET /waste/circularity`, `GET /waste/returns`
**Data missing**: Production waste logs, returns data, disposition records, recyclability-by-design revenue share.

---

### Cluster 4: Own-Workforce Safety & Wellbeing

**Status: NOT COVERED**

No HRIS or factory EHS data exists in the dashboard. The `CoverageHero` (`App.jsx:92`) tracks supplier coverage, not workforce metrics.

**Missing dashboard component**: Workforce safety panel with headcount, hours worked, injuries, near misses, sick leave, training hours; LTIFR/TRIR charts, safety training hours per employee, absenteeism rates.
**Missing API endpoint**: `GET /workforce/safety`, `GET /workforce/headcount`, `GET /workforce/training`
**Data missing**: Factory EHS logs, injury records, HRIS headcount, working hours, training records.

---

### Cluster 5: Wages, Overtime & Labour Rights in Supplier Factories

**Status: PARTIALLY COVERED**

The `questionnaires.py:8-14` has a `SUPPLIERS` list with `tier` and `country` fields. The `coverage-stats` endpoint shows 47/73 suppliers responding. No wage data, overtime data, unionisation data, grievance mechanism data, or CAP closure tracking.

The `WhatsAppBusinessPreview` questionnaire (`questionnaires.py:16-33`) covers only energy, water, renewables, cotton spend, waste — no labour rights questions.

**Missing dashboard component**: Labour rights panel showing % suppliers with critical non-compliances, % workers covered by collective bargaining, time-to-closure of CAPs, share of volume from high-risk facilities.
**Missing API endpoint**: `GET /labour/audit-summary`, `GET /labour/cap-closure`, `GET /labour/wage-compliance`, `GET /labour/collective-bargaining`
**Data missing**: Audit datasets (wage compliance, overtime, unionisation), grievance mechanism data, CAP closure times, critical non-compliance counts.

---

### Cluster 6: Gender & Inclusion

**Status: NOT COVERED**

No HRIS data exists in the dashboard.

**Missing dashboard component**: D&I panel showing gender split by level (board/management/line), promotion rates by gender, attrition rates by gender, % part-time/fixed-term by gender.
**Missing API endpoint**: `GET /workforce/demographics`, `GET /workforce/promotions`, `GET /workforce/attrition`
**Data missing**: HRIS gender data, job level data, contract type data, promotion/attrition records.

---

### Cluster 7: ESG Governance & Incentives

**Status: NOT COVERED**

No board/committee data, ESG mandate data, or variable remuneration data exists.

**Missing dashboard component**: ESG governance panel showing % board with sustainability expertise, existence of ESG committee, % executive variable pay linked to ESG metrics.
**Missing API endpoint**: `GET /governance/board`, `GET /governance/esg-incentives`
**Data missing**: Board membership records, ESG committee charter, executive compensation ESG linkage.

---

### Cluster 8: Supply-Chain Risk & Compliance Governance

**Status: PARTIALLY COVERED**

The `questionnaires.py:88` `/suppliers` endpoint returns supplier list with `tier` and `country`. The `questionnaires.py:119` `/coverage-stats` shows 47/73 suppliers responding. No supplier segmentation (critical/strategic vs tail), no due-diligence process data, no audit count tracking, no escalation/termination data.

**Missing dashboard component**: Supply chain governance panel showing % strategic suppliers with ESG clauses, audit coverage by tier/country, # terminations due to ESG breaches, avg age of open non-compliances, supplier segmentation (critical/strategic/tail).
**Missing API endpoint**: `GET /suppliers/segmentation`, `GET /suppliers/audit-coverage`, `GET /suppliers/esg-clauses`, `GET /suppliers/escalations`
**Data missing**: Supplier segmentation model, ESG clause coverage, audit counts by tier/country, termination records, open non-compliance age data.

---

### Cluster 9: Ethics, Anti-Corruption & Grievance Channels

**Status: NOT COVERED**

No code-of-conduct training records, whistleblowing logs, or investigations data exists.

**Missing dashboard component**: Ethics panel showing % employees trained on code of conduct, # substantiated corruption/ethics incidents, % cases resolved within X days.
**Missing API endpoint**: `GET /ethics/training-coverage`, `GET /ethics/incidents`, `GET /ethics/grievance`
**Data missing**: CoC training records, anonymised grievance log, investigations/outcomes.

---

### Additional Gap: Scope 3 — Full Categories

**Status: PARTIALLY COVERED**

Only Scope 3 Cat 1 (`dashboard.py:54-70`) and Cat 6 (`dashboard.py:88-104`) are present. Full GHG Protocol Scope 3 includes 15 categories.

**Missing API endpoints**: `GET /emissions/scope3` (all categories), specifically:

- Cat 2 (Capital goods)
- Cat 3 (Energy-related activities)
- Cat 4 (Upstream transportation)
- Cat 5 (Waste generated in operations)
- Cat 7 (Employee commuting)
- Cat 8 (Upstream leased assets)
- Cat 9-15 (Downstream)

---

### Additional Gap: Supplier Financial Health

**Status: NOT COVERED**

No financial distress indicators. The `SUPPLIERS` list (`questionnaires.py:8-14`) has `status: active` for all suppliers with no financial risk scoring.

**Missing dashboard component**: Supplier financial health risk panel with distress indicators integrated into supplier risk scoring.
**Missing API endpoint**: `GET /suppliers/financial-health`
**Data missing**: Financial data feeds (Dun & Bradstreet, Bureau van Dijk), payment history, credit scores.

---

### Additional Gap: Water Usage (ESRS E3, GRI 303)

**Status: PARTIALLY COVERED**

`water_m3` is tracked at `dashboard.py:40-53` as a single facility total. No water stress mapping by geography, no wastewater discharge data, no water recycling rate.

**Missing dashboard component**: Water stewardship panel with water stress by location, wastewater discharge, water recycling %, withdrawal by source (municipal, groundwater, surface).
**Missing API endpoint**: `GET /water/by-source`, `GET /water/wastewater`, `GET /water/stress-map`
**Data missing**: Withdrawal source breakdown, wastewater discharge data, water recycling rate, water stress index by supplier geography.

---

### Additional Gap: Traceability / Chain of Custody

**Status: PARTIALLY COVERED**

The `EvidencePanel` (`App.jsx:155`) shows hash-chain integrity (hash + upstream_hash per metric). This is **data integrity** (hash chain for a single number), not **chain of custody** (verifying that a specific supplier certification is authentic and not fraudulent).

**Missing dashboard component**: Chain of custody panel verifying supplier certification authenticity (e.g., does this GOTS certificate actually come from the certification body?).
**Missing API endpoint**: `GET /traceability/certifications`, `GET /traceability/audit-log`
**Data missing**: Certification body verification feeds, third-party certification registries (e.g., Textile Exchange, GOTS), audit trail of certification renewal.

---

### Additional Gap: Geopolitical / Physical Climate Risk by Supplier Location

**Status: NOT COVERED**

The `SUPPLIERS` list (`questionnaires.py:8-14`) has `country` fields (IN, VN, BD, TH, MM). No risk scoring exists.

**Missing dashboard component**: Supplier geography risk panel showing risk scores by country (World Bank governance indicators, INFORM climate risk, custom geopolitical risk), risk-map visualization.
**Missing API endpoint**: `GET /risk/geopolitical`, `GET /risk/climate-physical`, `GET /risk/supplier-map`
**Data missing**: Risk index data feeds (World Bank, INFORM, custom), supplier facility geocoordinates.

---

## Cluster-to-Component Mapping Table

| Cluster                       | Dashboard Tab       | Component                                                  | Status      | API Route(s)                    |
| ----------------------------- | ------------------- | ---------------------------------------------------------- | ----------- | ------------------------------- |
| 1. Energy & GHG               | Dashboard           | `MetricCard` (energy_kwh, emissions_tco2, diesel_consumed) | PARTIAL     | `/dashboard/live`               |
| 2. Fibre Mix                  | None                | —                                                          | NOT COVERED | —                               |
| 3. Waste & Circularity        | None                | —                                                          | NOT COVERED | —                               |
| 4. Workforce Safety           | None                | —                                                          | NOT COVERED | —                               |
| 5. Labour Rights              | Supplier Engagement | `WhatsAppBusinessPreview` (partial — no labour Qs)         | PARTIAL     | `/questionnaires/*`             |
| 6. Gender & Inclusion         | None                | —                                                          | NOT COVERED | —                               |
| 7. ESG Governance             | None                | —                                                          | NOT COVERED | —                               |
| 8. Supply Chain Governance    | Supplier Engagement | `CoverageHero` + `WhatsAppBusinessPreview`                 | PARTIAL     | `/coverage-stats`, `/suppliers` |
| 9. Ethics                     | None                | —                                                          | NOT COVERED | —                               |
| Scope 3 Full                  | Dashboard           | `MetricCard` (scope3_cat1 only)                            | PARTIAL     | `/dashboard/live`               |
| Supplier Financial Health     | None                | —                                                          | NOT COVERED | —                               |
| Water ESRS E3                 | Dashboard           | `MetricCard` (water_m3 total only)                         | PARTIAL     | `/dashboard/live`               |
| Traceability/Chain of Custody | Dashboard           | `EvidencePanel` (data integrity only)                      | PARTIAL     | `/evidence/drilldown/{metric}`  |
| Geopolitical/Climate Risk     | None                | —                                                          | NOT COVERED | —                               |

---

## Priority Ranking

### Tier 1 — Highest compliance value, easiest to add

1. **Cluster 1 (Energy & GHG) — fill gaps**: Add site/BU breakdown and emission intensity. Existing `MetricCard` infrastructure (`App.jsx:44`) and `TrendChart` (`App.jsx:343`) can be reused. Backend data exists in SAP. **API**: `/energy/by-site`, `/emissions/scope-1-2-by-site`.

2. **Cluster 8 (Supply Chain Governance)**: Expand `CoverageHero` to include supplier segmentation (critical/strategic/tail) and ESG clause coverage. Reuses existing `/suppliers` endpoint. **API**: segmentation endpoint.

3. **Scope 3 Full (Cat 2-15)**: Add remaining Scope 3 categories. `FrameworkCompare` (`App.jsx:579`) already handles multi-framework mapping — just need data. **API**: `/emissions/scope3` (bulk).

### Tier 2 — High compliance value, moderate effort

4. **Cluster 5 (Labour Rights)**: Add labour questions to WhatsApp questionnaire template (`questionnaires.py:25`). Add audit summary endpoint. Reuses existing WhatsApp infrastructure. **API**: `/labour/audit-summary`, `/labour/cap-closure`.

5. **Water ESRS E3**: Expand `water_m3` into full water stewardship panel. Add wastewater discharge and water stress by geography. **API**: `/water/by-source`, `/water/stress-map`.

6. **Cluster 3 (Waste & Circularity)**: Add production waste logs to questionnaire, create waste panel. **API**: `/waste/production`, `/waste/circularity`.

7. **Cluster 2 (Fibre Mix)**: Add fibre type questions to questionnaire, create sourcing panel with certification badges. **API**: `/fibre/mix`, `/fibre/certifications`.

### Tier 3 — Important but lower urgency / harder to implement

8. **Cluster 4 (Workforce Safety)**: Requires factory EHS log integration. **API**: `/workforce/safety`, `/workforce/headcount`.

9. **Cluster 6 (Gender & Inclusion)**: Requires HRIS integration. **API**: `/workforce/demographics`.

10. **Geopolitical/Climate Risk**: Requires external risk data feeds. **API**: `/risk/geopolitical`, `/risk/climate-physical`.

11. **Cluster 7 (ESG Governance)**: Board/executive data often requires manual entry or board portal integration. **API**: `/governance/board`, `/governance/esg-incentives`.

12. **Cluster 9 (Ethics)**: Requires HR/legal system integration. **API**: `/ethics/*`.

13. **Traceability/Chain of Custody**: Requires certification body API integrations (Textile Exchange, GOTS). **API**: `/traceability/*`.

14. **Supplier Financial Health**: Requires financial data provider (D&B, Bureau van Dijk). **API**: `/suppliers/financial-health`.

---

## Key Finding

The current dashboard is a **Scope 1+2 energy/emissions tracker with supply chain coverage measurement**. It is structurally not an ESG platform. All social clusters (4, 5, 6), governance clusters (7, 9), and the circularity/fibre clusters (2, 3) are entirely absent.

The Framework Compare tab (`App.jsx:579`) demonstrates the multi-framework mapping engine — the platform's core differentiator — but maps only 4 metrics.

**Expanding the data pipeline to feed the existing framework mapping infrastructure is the highest-leverage next step.**
