# Metrics Audit — ESG SCRM MVP

## Overview

Complete inventory of every API endpoint returning numeric or KPI data, the fields each returns, and how the frontend consumes them. Cross-referenced against the 4 buyer-validated features from `briefs/01-investor-mvp-scope.md`.

---

## Buyer-Validated Feature Map

| Feature | Description | Relevant Endpoints |
|---------|-------------|-------------------|
| **F1: ESG Data Orchestration** | One KPI → CSRD/ISSB/GRI/TCFD | `/frameworks/compare/{metric}`, `/frameworks/map/{metric}` |
| **F2: Supply-Chain ESG Collection** | WhatsApp questionnaires, Scope 3 | `/questionnaires/*`, `/scope3/*`, `/suppliers/*` |
| **F3: Evidence Vault** | Hash chain, source, confidence, lineage | `/evidence/*`, `/dashboard/live` |
| **F4: Real-Time Monitoring** | Live dashboard, threshold alerts | `/dashboard/live`, `/dashboard/trends`, `/dashboard/alerts` |

---

## Endpoint Inventory

### Dashboard Routes (`src/api/routes/dashboard.py`)

#### `GET /dashboard/live`
Returns all 6 operational metrics with chain-integrity flags.

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `metrics[].value` | float | `2847320` | Primary KPI value |
| `metrics[].unit` | string | `"kWh"` | Engineering unit |
| `metrics[].confidence` | string | `"HIGH"` | HIGH / MEDIUM / LOW |
| `metrics[].trend` | string | `"+3.2% vs last month"` | Directional change |
| `metrics[].source` | string | `"SAP Business One — Utility Invoices"` | Source system |
| `metrics[].period` | string | `"January 2025"` | Reporting period |
| `metrics[].calculation_method` | string | `"direct_measurement"` | How value was derived |
| `metrics[].emission_factor` | string | `"IEA 2023 — Bangladesh Grid Factor"` | Factor source |
| `metrics[].emission_factor_value` | string | `"0.524 kg CO2/kWh"` | Factor applied |
| `metrics[].hash` | string | `"a3f2c8d1e9b4..."` | SHA-256 chain hash |
| `metrics[].chain_valid` | bool | `true` | Chain integrity flag |
| `hash_chain_valid` | bool | `true` | Aggregate integrity |
| `updated_at` | string | ISO8601 | Last refresh timestamp |
| `org_id` | string | `"org_bd_001"` | Tenant identifier |

**Metrics served:** `energy_kwh`, `emissions_tco2`, `water_m3`, `scope3_category1`, `diesel_consumed`, `scope3_category6`

**Frontend usage:** `Dashboard` component (App.jsx:1417) fetches on load. `MetricCard` renders each metric. `chain_valid=false` triggers a "Chain Broken" badge. `EvidencePanel` drilldown shows full hash chain.

**Buyer feature:** F3 (Evidence Vault — hash chain), F4 (Real-Time Monitoring — live metrics)

---

#### `GET /dashboard/trends/{metric_type}`
Returns 5-month history for one metric type.

| Field | Type | Notes |
|-------|------|-------|
| `metric_type` | string | e.g. `"energy_kwh"` |
| `data[].month` | string | e.g. `"Sep 2024"` |
| `data[].value` | float | Historical value |
| `unit` | string | e.g. `"kWh"` |

**Frontend usage:** `TrendChart` renders SVG line chart. No direct fetch — data comes via `/dashboard/trends` combined endpoint.

---

#### `GET /dashboard/trends`
Returns combined 5-month trends for energy, emissions, water.

| Field | Type | Example |
|-------|------|---------|
| `trends[].month` | string | `"Sep 2024"` |
| `trends[].energy` | float | `2710400` |
| `trends[].emissions` | float | `1392.4` |
| `trends[].water` | float | `17820` |

**Frontend usage:** `TrendChart` component (App.jsx:344–576). Renders 3-line SVG chart (green=energy, amber=emissions, blue=water) with dual Y-axes.

**Buyer feature:** F4 (Real-Time Monitoring — trend visualization)

---

#### `GET /dashboard/operations-summary`
Returns 5-cluster summary for the PDF report builder.

| Field | Type |
|-------|------|
| `org_id` | string |
| `period` | string |
| `clusters[].cluster` | string |
| `clusters[].value` | float |
| `clusters[].unit` | string |
| `clusters[].confidence` | string |
| `clusters[].trend` | string |
| `clusters[].source` | string |
| `clusters[].period` | string |
| `clusters[].calculation_method` | string |
| `clusters[].hash` | string |
| `clusters[].chain_valid` | bool |
| `updated_at` | ISO8601 |

**Frontend usage:** Not directly consumed by App.jsx. Consumed by `/reports/esg-pdf`.

**Buyer feature:** F3 (Evidence Vault — summary for audit)

---

#### `GET /dashboard/alerts`
Returns active threshold alerts.

| Field | Type | Example |
|-------|------|---------|
| `alerts[].id` | string | UUID |
| `alerts[].metric_type` | string | `"energy_kwh"` |
| `alerts[].message` | string | `"Daily energy consumption exceeded..."` |
| `alerts[].actual_value` | string | `"108,240 kWh"` |
| `alerts[].threshold` | string | `"105,000 kWh"` |
| `alerts[].severity` | string | `"warning"` |
| `alerts[].triggered_at` | string | ISO8601 |
| `alerts[].acknowledged` | bool | |
| `total` | int | |

**Frontend usage:** App.jsx does NOT fetch this endpoint. Alerts data is hardcoded locally and not displayed in the current UI. Dead endpoint from investor-demo phase.

---

#### `POST /dashboard/alerts/{alert_id}/acknowledge`
Acknowledge an alert.

| Field | Type |
|-------|------|
| `acknowledged` | bool |
| `acknowledged_at` | ISO8601 |

**Frontend usage:** Not wired in App.jsx.

---

### Risk Routes (`src/api/routes/risk.py`)

#### `GET /risk/flags`
Returns risk flags with optional filters.

| Field | Type | Example |
|-------|------|---------|
| `flags[].id` | string | UUID |
| `flags[].flag_text` | string | Risk description |
| `flags[].cluster` | string | `"G6"` |
| `flags[].severity` | string | `"WARNING"` |
| `flags[].days_overdue` | int | |
| `flags[].priority_score` | float | `1.8` (computed) |
| `flags[].created_at` | ISO8601 | |
| `flags[].acknowledged` | bool | |
| `flags[].acknowledged_by` | string | email |
| `total` | int | |

**Frontend usage:** `RiskAlertsPanel` (App.jsx:1118). Fetches and renders active/acknowledged flags. Sort by `priority_score` descending. Acknowledge button calls `POST /risk/flags/{flag_id}/acknowledge`.

**Buyer feature:** F4 (Real-Time Monitoring — risk alerting)

---

#### `GET /risk/summary`
Aggregate risk statistics.

| Field | Type | Example |
|-------|------|---------|
| `total` | int | Active flag count |
| `by_severity.critical` | int | |
| `by_severity.warning` | int | |
| `by_severity.info` | int | |
| `by_cluster` | dict | `{"G6": 1, "G5": 1, ...}` |
| `avg_days_open` | float | |

**Frontend usage:** `RiskAlertsPanel` renders risk summary strip (4 cards: Critical count, Warning count, Info count, Avg Days Open).

---

#### `POST /risk/flags/{flag_id}/acknowledge`
Acknowledge a flag.

| Field | Type |
|-------|------|
| `acknowledged` | bool |
| `acknowledged_at` | ISO8601 |
| `acknowledged_by` | string |

**Frontend usage:** `RiskAlertsPanel.acknowledgeFlag()` (App.jsx:1147). Updates flag state optimistically.

---

#### `GET /risk/scorecard`
2x2 risk quadrant scores.

| Field | Type | Example |
|-------|------|---------|
| `quadrants[].id` | string | `"G2"` |
| `quadrants[].name` | string | `"Supply Chain Compliance"` |
| `quadrants[].score` | int | `72` |
| `quadrants[].tier` | string | `"B"` |
| `quadrants[].trend` | string | `"down"` |
| `quadrants[].active_flags` | int | `2` |

**Frontend usage:** `RiskAlertsPanel` renders 2x2 scorecard grid with score, tier color (A=green, B=amber, C=red), trend arrow, active flag count.

---

#### `GET /risk/geopolitical`
Country-level geopolitical risk scores.

| Field | Type | Example |
|-------|------|---------|
| `countries[].country_code` | string | `"BD"` |
| `countries[].country` | string | `"Bangladesh"` |
| `countries[].political_stability` | int | `42` (0–100) |
| `countries[].trade_exposure` | int | `88` (0–100) |
| `countries[].currency_volatility` | int | `71` (0–100) |
| `countries[].overall_score` | int | `67` (0–100, lower = riskier) |

**Frontend usage:** `SupplyChainPanel` (App.jsx:860) renders a geo table with color-coded bars (green >60, amber >40, red <=40) for each sub-metric. `RiskAlertsPanel` has a static geo heatmap (not sourced from API).

**Buyer feature:** F2 (Supply-Chain ESG — country risk context)

---

### Supplier Routes (`src/api/routes/suppliers.py`)

#### `GET /suppliers/`
List all suppliers.

| Field | Type | Example |
|-------|------|---------|
| `suppliers[].id` | string | `"sup_001"` |
| `suppliers[].name` | string | `"Gujarat Cotton Traders"` |
| `suppliers[].country` | string | `"IN"` |
| `suppliers[].industry` | string | `"Cotton trading"` |
| `suppliers[].tier` | string | `"tier2"` |
| `suppliers[].annual_spend_usd` | int | `2400000` |
| `suppliers[].preferred_channel` | string | `"whatsapp"` |
| `suppliers[].relationship_status` | string | `"active"` |
| `suppliers[].questionnaire_status` | string | `"responded"` |
| `total` | int | |

**Frontend usage:** Not directly consumed. `SupplyChainPanel` uses `/suppliers/risk-ranked` instead.

---

#### `GET /suppliers/risk-ranked`
Suppliers sorted by composite risk score.

| Field | Type | Example |
|-------|------|---------|
| `suppliers[].id` | string | |
| `suppliers[].name` | string | |
| `suppliers[].country` | string | `"India"` |
| `suppliers[].risk_tier` | string | `"A"` / `"B"` / `"C"` |
| `suppliers[].risk_score` | float | `2.1` |
| `suppliers[].active_flags` | int | |
| `suppliers[].certifications` | list[str] | `["GOTS", "OEKO-TEX"]` |
| `total` | int | |

**Frontend usage:** `SupplyChainPanel` fetches via `Promise.all` (App.jsx:870). Renders supplier risk ranking table. Click on row fetches `/suppliers/{id}/profile`.

**Buyer feature:** F2 (Supply-Chain ESG — supplier risk)

---

#### `GET /suppliers/{supplier_id}/profile`
Full ESG profile for a supplier.

| Field | Type | Example |
|-------|------|---------|
| `supplier_id` | string | |
| `name` | string | |
| `country` | string | |
| `tier` | string | |
| `overall_risk_score` | float | `3.4` |
| `risk_tier` | string | `"A"` |
| `financial_health_score` | int | `72` |
| `scope3_coverage_pct` | int | `64` |
| `traceability_status` | string | `"full_chain"` |
| `active_flags` | int | |
| `certifications` | list[str] | |
| `clusters` | dict | `{"labour_rights": 78, "environment": 82, ...}` |
| `ml_recommendations` | list[str] | 3 canned strings |

**Frontend usage:** `SupplyChainPanel` (App.jsx:1049–1111). Renders profile grid (risk score, financial health, scope3 coverage, traceability), ESG cluster score bars, ML recommendations list.

**Buyer feature:** F2 (Supply-Chain ESG — supplier ESG profile)

---

#### `GET /suppliers/{supplier_id}/scope3`
Scope 3 emissions for one supplier.

| Field | Type | Example |
|-------|------|---------|
| `supplier_name` | string | |
| `category` | string | `"Raw materials"` |
| `annual_spend_usd` | int | |
| `scope3_tco2e` | float | `412.8` |
| `calculation_method` | string | `"spend_based"` |
| `emission_factor` | string | |
| `confidence` | string | `"MEDIUM"` |
| `data_source` | string | |

**Frontend usage:** Not directly consumed by App.jsx.

---

### Questionnaire Routes (`src/api/routes/questionnaires.py`)

#### `GET /questionnaires/coverage`
Coverage rate and pending suppliers.

| Field | Type | Example |
|-------|------|---------|
| `coverage_rate` | int | `64` |
| `responding_suppliers` | int | `47` |
| `total_suppliers` | int | `73` |
| `procurement_spend_covered` | int | `38400000` |
| `total_procurement_spend` | int | `60000000` |
| `pending_suppliers[].name` | string | |
| `pending_suppliers[].spend` | int | |
| `pending_suppliers[].channel` | string | `"whatsapp"` |

**Frontend usage:** Not directly consumed by App.jsx.

---

#### `GET /questionnaires/coverage-stats`
Simplified coverage for CoverageHero component.

| Field | Type | Example |
|-------|------|---------|
| `total_coverage` | float | `72.2` |
| `previous_coverage` | float | `64.0` |
| `responding_suppliers` | int | `47` |
| `total_suppliers` | int | `73` |

**Frontend usage:** `CoverageHero` (App.jsx:92–152). Dashboard tab fetches via `/questionnaires/coverage-stats` (App.jsx:1419). Renders coverage percentage, delta, progress bar with "Before Gujarat" marker.

**Buyer feature:** F2 (Supply-Chain ESG — response rate KPI)

---

#### `GET /questionnaires/whatsapp-preview/{supplier_id}`
WhatsApp message preview with parsed response.

| Field | Type | Example |
|-------|------|---------|
| `message_preview` | string | Full WhatsApp message |
| `supplier_response_example` | string | |
| `parsed_response` | dict | `{"1": {"value": 4820000, "unit": "kWh", "confidence": "HIGH"}, ...}` |
| `coverage_impact.supplier_name` | string | |
| `coverage_impact.annual_spend` | int | |
| `coverage_impact.procurement_category` | string | |
| `coverage_impact.coverage_added` | float | `8.2` |
| `coverage_impact.new_total_coverage` | float | `72.2` |

**Frontend usage:** `WhatsAppBusinessPreview` (App.jsx:667–793). Renders WhatsApp conversation UI, supplier response bubbles, coverage impact grid.

**Buyer feature:** F2 (Supply-Chain ESG — WhatsApp engagement demo)

---

### Scope3 Routes (`src/api/routes/scope3.py`)

#### `GET /scope3/categories`
Scope 3 category breakdown.

| Field | Type | Example |
|-------|------|---------|
| `categories[].id` | string | `"cat_1"` |
| `categories[].name` | string | `"Purchased Goods"` |
| `categories[].coverage_pct` | int | `64` |
| `categories[].respondents` | int | `47` |
| `categories[].total` | int | `73` |
| `categories[].tco2e` | float | `4281.7` |

**Frontend usage:** `SupplyChainPanel` (App.jsx:904–923). Renders per-category coverage bars with percentage and respondent counts.

**Buyer feature:** F2 (Supply-Chain ESG — Scope 3 completeness)

---

#### `GET /scope3/completeness`
Overall Scope 3 completeness for the completeness meter.

| Field | Type | Example |
|-------|------|---------|
| `overall_coverage_pct` | int | `47` |
| `total_respondents` | int | Aggregate of above |
| `total_suppliers` | int | Aggregate of above |
| `by_category[].id` | string | |
| `by_category[].name` | string | |
| `by_category[].coverage_pct` | int | |
| `by_category[].tco2e` | float | |

**Frontend usage:** `RiskAlertsPanel` (App.jsx:1240–1293). Renders SVG donut chart (overall %) with per-category bars.

**Buyer feature:** F2 (Supply-Chain ESG — Scope 3 completeness meter)

---

### Evidence Routes (`src/api/routes/evidence.py`)

#### `GET /evidence/drilldown/{metric_type}`
Full evidence record for one metric.

| Field | Type | Example |
|-------|------|---------|
| `data_point_id` | string | `"dp_en_001"` |
| `org_id` | string | `"org_bd_001"` |
| `value` | float | `2847320` |
| `unit` | string | `"kWh"` |
| `metric_type` | string | `"energy_kwh"` |
| `confidence` | string | `"HIGH"` |
| `calculation_method` | string | `"direct_measurement"` |
| `source_system` | string | `"SAP Business One"` |
| `source_record_id` | string | `"INV-2025-0042"` |
| `extraction_timestamp` | string | ISO8601 |
| `emission_factor_source` | string | `"IEA 2023"` |
| `emission_factor_year` | int | `2023` |
| `emission_factor_table` | string | `"Table 4.2 — Bangladesh Grid..."` |
| `emission_factor_value` | float | `0.524` |
| `emission_factor_unit` | string | `"kg CO2/kWh"` |
| `hash` | string | Full SHA-256 |
| `previous_hash` | string | Previous record hash |
| `chain_valid` | bool | |
| `reported_in_frameworks` | list[str] | `["CSRD", "GRI", "TCFD"]` |
| `upstream_records` | list[str] | `["dp_en_001"]` |

**Frontend usage:** `EvidencePanel` (App.jsx:155–340). Triggered by clicking a `MetricCard`. Renders full audit trail: data point ID, value, confidence badge, calculation method, source system, source record ID, extraction time, emission factor details, chain visualization (This Record → Previous Record), chain status badge (green "Integrity Intact" or red "Chain Broken"), framework badges.

**Buyer feature:** F3 (Evidence Vault — primary endpoint for audit evidence)

---

#### `GET /evidence/verify/{metric_type}`
Hash chain verification for one metric.

| Field | Type | Example |
|-------|------|---------|
| `metric_type` | string | |
| `chain_valid` | bool | |
| `hash_computed` | string | SHA-256 recomputed |
| `hash_stored` | string | SHA-256 stored |
| `match` | bool | |
| `verified_at` | string | ISO8601 |

**Frontend usage:** Not directly consumed by App.jsx. Available for auditor verification workflows.

---

#### `GET /evidence/full-chain/{metric_type}`
Full lineage chain (up to 3 hops).

| Field | Type |
|-------|------|
| `chain[].step` | int |
| `chain[].data_point_id` | string |
| `chain[].value` | float |
| `chain[].unit` | string |
| `chain[].source` | string |
| `chain[].hash` | string |
| `chain[].confidence` | string |
| `chain_length` | int |
| `all_valid` | bool |

**Frontend usage:** Not directly consumed by App.jsx.

---

### Framework Routes (`src/api/routes/frameworks.py`)

#### `GET /frameworks/compare/{metric_type}`
Same metric mapped across all frameworks side-by-side.

| Field | Type | Example |
|-------|------|---------|
| `metric` | string | `"Energy Consumption"` |
| `source_value` | string | `"2,847,320 kWh"` |
| `frameworks[].name` | string | `"CSRD / ESRS E1"` |
| `frameworks[].field_id` | string | `"E1-13"` |
| `frameworks[].value` | string | `"2,847,320 kWh"` |
| `frameworks[].unit` | string | `"kWh"` |
| `frameworks[].confidence` | string | `"HIGH"` |
| `frameworks[].note` | string | Optional context |

**Supported metric types:** `energy_kwh`, `scope3_category_1`, `diesel_consumed`, `scope3_category_6`, `water_m3`, `waste_tonnes`, `scope3_cat2–9`, `scope3_cat11–12`, `gender_pct`, `safety_incidents`, `governance_score`

**Frontend usage:** `FrameworkCompare` (App.jsx:579–663). Metric tab selector (Energy, Scope 3 Cat 1, Diesel, Business Travel). Renders table with framework name, field ID, value, unit, confidence badge.

**Buyer feature:** F1 (ESG Data Orchestration — one metric, multiple frameworks)

---

#### `GET /frameworks/map/{metric_type}`
Full framework output mapping for one metric.

| Field | Type |
|-------|------|
| `source_metric` | string |
| `source_value` | string |
| `frameworks.{framework}.field_id` | string |
| `frameworks.{framework}.label` | string |
| `frameworks.{framework}.value` | string |
| `frameworks.{framework}.unit` | string |
| `frameworks.{framework}.breakdown` | dict |
| `frameworks.{framework}.methodology` | string |
| `frameworks.{framework}.confidence` | string |

**Frontend usage:** Not directly consumed by App.jsx. Used by the PDF report builder.

---

### Reports Routes (`src/api/routes/reports.py`)

#### `GET /reports/esg-pdf`
Streams a 3-page ESG PDF report.

**Sourced from:** `dashboard.py` METRICS, TREND_DATA, ALERTS, and `frameworks.py` FRAMEWORK_OUTPUTS

**Content:**
- Page 1: Cover, organisation info, hash chain integrity status, metrics at a glance, active alerts
- Page 2: Full metric evidence table, chain integrity alert (if diesel broken), 5-month trend table
- Page 3: Framework compliance blocks (CSRD/ESRS E1 per metric), evidence integrity statement

**Frontend usage:** `Dashboard.downloadReport()` (App.jsx:1438). Triggered by "Download Report" button.

**Buyer feature:** F3 (Evidence Vault — auditor-ready export)

---

## Gap Analysis: Implemented vs. Buyer Features

### F1: ESG Data Orchestration Platform
| Buyer Requirement | Status | Gap |
|------------------|--------|-----|
| Connect to ERP (SAP, NetSuite, Xero, S/4HANA) | NOT IMPLEMENTED | No ERP integration layer. Static data from CSV/demo data. |
| Pull data from existing systems | NOT IMPLEMENTED | Data loaded from local `data/operations/summary.csv`. No API pull. |
| Map one KPI to multiple frameworks | IMPLEMENTED | `/frameworks/compare/{metric}` + `/frameworks/map/{metric}` |
| Output: CSRD, ISSB, GRI, TCFD | PARTIAL | 14 metric types mapped to 4 frameworks. Coverage is broad but static. |
| Self-serve onboarding | NOT IMPLEMENTED | No onboarding flow. Hardcoded org_id `"org_bd_001"`. |

**Critical gap:** No ERP connectivity. All "SAP Business One" references are theatrical — the data is CSV-loaded, not API-fetched.

---

### F2: Supply-Chain ESG Data Collection
| Buyer Requirement | Status | Gap |
|------------------|--------|-----|
| Automated ESG questionnaires | IMPLEMENTED | `/questionnaires/tiers/{tier}`, WhatsApp templates |
| Collect via WhatsApp, LINE, WeChat | PARTIAL | WhatsApp preview implemented. LINE/WeChat not implemented. |
| Email and web portal fallback | NOT IMPLEMENTED | No email or web portal endpoints. |
| Calculate Scope 3 emissions | IMPLEMENTED | `/scope3/categories`, `/suppliers/{id}/scope3` |
| Mobile-first | IMPLEMENTED | WhatsApp Business Preview component. |
| Localization (Bengali, Vietnamese, Thai, Hindi, Indonesian) | NOT IMPLEMENTED | All UI text in English. All WhatsApp templates English only. |

**Critical gap:** LINE and WeChat channels not implemented. Localization not implemented. No actual WhatsApp API integration — theatrical preview only.

---

### F3: Assurance-Ready Evidence Vault
| Buyer Requirement | Status | Gap |
|------------------|--------|-----|
| Every data point tagged with source, timestamp, methodology, emission factor, confidence | IMPLEMENTED | `/evidence/drilldown/{metric}` returns all 5 tags |
| Full lineage chain | IMPLEMENTED | `/evidence/full-chain/{metric}`, `upstream_records` field |
| SHA-256 hash chain | IMPLEMENTED | Real SHA-256 computed in `evidence.py` and `dashboard.py` |
| Export evidence packages | PARTIAL | PDF export via `/reports/esg-pdf`. No auditor-accepted format (XBRL, iXBRL, JSON for audit firms). |
| Big 4 audit workflow support | NOT IMPLEMENTED | No Deloitte/EY/PwC/KPMG-specific export or integration. |
| 7-year data retention | NOT IMPLEMENTED | No data retention policy or infrastructure. |

**Evidence chain works but audit export is PDF-only.** Big 4 firms typically require structured data formats.

---

### F4: Real-Time ESG Monitoring
| Buyer Requirement | Status | Gap |
|------------------|--------|-----|
| Read sensor data through ERP integration | NOT IMPLEMENTED | No ERP integration. Static CSV data. |
| IoT/smart meters, water flow meters, PLC, BMS | NOT IMPLEMENTED | No IoT data ingestion. |
| Live dashboard: emissions, energy, water, waste | IMPLEMENTED | `/dashboard/live` + `TrendChart`. Waste is hardcoded, not live. |
| Threshold alerts | PARTIAL | Alerts exist in data model (`/dashboard/alerts`) but NOT wired in frontend. |
| Real-time data (hourly or continuous) | NOT IMPLEMENTED | Data is manually loaded CSV. No polling or streaming. |
| Actionable, not noisy alerts | PARTIAL | Alert acknowledgment exists. No alert routing, no threshold configuration. |

**Real-time monitoring is theatrical.** The dashboard shows static demo data. No IoT sensors, no ERP integration, no threshold configuration UI.

---

## Summary of Live Metrics in Frontend

| Metric | Endpoint | Frontend Component | Purpose |
|--------|----------|-------------------|---------|
| `energy_kwh` (value, unit, confidence, trend, chain_valid) | `/dashboard/live` | `MetricCard` | F4 live KPI |
| `emissions_tco2` | `/dashboard/live` | `MetricCard` | F4 live KPI |
| `water_m3` | `/dashboard/live` | `MetricCard` | F4 live KPI |
| `scope3_category1` | `/dashboard/live` | `MetricCard` | F3 evidence |
| `diesel_consumed` | `/dashboard/live` | `MetricCard` (with broken-chain badge) | F3 evidence |
| `scope3_category6` | `/dashboard/live` | `MetricCard` | F3 evidence |
| Combined trend (energy, emissions, water) | `/dashboard/trends` | `TrendChart` | F4 visualization |
| `total_coverage` | `/questionnaires/coverage-stats` | `CoverageHero` | F2 KPI |
| `previous_coverage` | `/questionnaires/coverage-stats` | `CoverageHero` | F2 delta |
| Scope 3 category coverage | `/scope3/categories` | `SupplyChainPanel` | F2 Scope 3 |
| Country geopolitical scores | `/risk/geopolitical` | `SupplyChainPanel` | F2 country risk |
| Supplier risk data | `/suppliers/risk-ranked` | `SupplyChainPanel` | F2 supplier risk |
| Risk flags | `/risk/flags` | `RiskAlertsPanel` | F4 alerting |
| Risk summary | `/risk/summary` | `RiskAlertsPanel` | F4 risk strip |
| Risk scorecard | `/risk/scorecard` | `RiskAlertsPanel` | F4 quadrant view |
| Scope 3 completeness | `/scope3/completeness` | `RiskAlertsPanel` | F2 completeness |
| Framework comparison | `/frameworks/compare/{metric}` | `FrameworkCompare` | F1 framework map |
| Evidence drilldown | `/evidence/drilldown/{metric}` | `EvidencePanel` | F3 audit trail |
| WhatsApp preview | `/questionnaires/whatsapp-preview/{id}` | `WhatsAppBusinessPreview` | F2 engagement |

**16 unique endpoints return numeric/KPI data. 19 distinct frontend components consume them.**

---

## Findings

### Critical
1. **No ERP connectivity** — All "SAP Business One" references are theatrical. The application loads static CSV data. Buyer Feature F1 and F4 are not actually implemented.
2. **WhatsApp/LINE/WeChat are theatrical** — `/questionnaires/whatsapp-preview` returns a static mock message. No actual messaging API integration.
3. **Alert system not wired** — `/dashboard/alerts` data exists but the frontend never fetches it. Threshold alerting is non-functional.

### Important
4. **Localization absent** — No i18n infrastructure. Buyer requires Bengali, Vietnamese, Thai, Hindi, Indonesian for F2.
5. **Big 4 audit export missing** — PDF is insufficient. No XBRL/iXBRL/structured-data export for F3.
6. **Waste metric not live** — `FRAMEWORK_OUTPUTS["waste_tonnes"]` exists in frameworks.py but is not in `METRICS` and not in the frontend metric grid.

### Minor
7. **`/dashboard/alerts` endpoint is orphaned** — Created for investor demo, never wired to frontend.
8. **`ml_recommendations` in supplier profile are canned strings** — Not ML-generated. Could be misleading if presented as AI output.
9. **`water_m3` trend data uses wrong unit for display** — TrendChart shows water in "K" (thousands) but the metric is cubic meters. No unit conversion.
