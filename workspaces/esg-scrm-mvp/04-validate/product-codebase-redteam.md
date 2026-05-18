# ESG SCRM Product Codebase Red Team

**Date:** 2026-05-17
**Scope:** Full code audit of `src/`, `apps/web/src/`, `tests/`, `data/`, `specs/` against specification files
**Status:** COMPLETE

---

## Executive Summary

The ESG SCRM MVP is a demo-grade prototype with a functional FastAPI backend and React frontend, but it has significant gaps between specification and implementation. The backend has 8 routers with real endpoints, the frontend has a 5-tab SPA matching the spec tab structure, and there are 13 behavioral unit tests. However: (1) all API routes serve hardcoded or CSV-backed data with no live database connection from the API layer, (2) multiple spec-to-code response shape mismatches exist that would break a frontend consuming the documented API contract, (3) the ETL/SQLite/MQTT infrastructure is built but disconnected from the API, (4) the questionnaire engine in `src/supplier/questionnaire.py` is orphaned from the API routes, (5) WebSocket alerts are defined but not wired into the application, and (6) Scope 3 category numbers and coverage percentages in the code differ from the spec without explanation.

**Overall Classification:** DEMO PROTOTYPE -- not production-ready; spec compliance is partial with several structural contradictions.

---

## 1. Spec-by-Spec Gap Analysis

### 1.1 specs/dashboard-api.md

| Requirement                                                                                                                  | Classification | Evidence                                                                                                                                                                                                                                                          |
| ---------------------------------------------------------------------------------------------------------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GET /api/dashboard/live returns 6 metrics                                                                                    | IMPLEMENTED    | `src/api/routes/dashboard.py` loads from CSV, returns all 6 metrics. Diesel includes deliberate "TAMPERED\_" prefix with `chain_valid=False`.                                                                                                                     |
| Metric shape: value, unit, confidence, trend, chain_valid, data_point_id, source_system, calculation_method, emission_factor | PARTIAL        | Code returns these fields but some are derived differently. `data_point_id` comes from CSV `recorded_at` column rather than a dedicated ID. `calculation_method` and `emission_factor` are present in evidence chain but not always in the live metrics response. |
| Diesel confidence="HIGH"                                                                                                     | CONTRADICTION  | Spec `dashboard-api.md` says diesel confidence should be HIGH. Code in `dashboard.py` sets diesel confidence to "MEDIUM" (in the CSV data). Water is "HIGH" in code but spec says "MEDIUM".                                                                       |
| GET /api/dashboard/trends/{metric_type}                                                                                      | IMPLEMENTED    | Returns hardcoded 5-month trend data for energy/emissions/water.                                                                                                                                                                                                  |
| GET /api/frameworks/compare/{metric_type}                                                                                    | IMPLEMENTED    | `src/api/routes/frameworks.py` serves this for ~18 metric types.                                                                                                                                                                                                  |
| GET /api/questionnaires/coverage-stats                                                                                       | IMPLEMENTED    | Returns `{total_suppliers:73, responding_suppliers:?, total_coverage:72.2, previous_coverage:64.0}`.                                                                                                                                                              |
| Coverage stats: total_coverage=64.4, previous_coverage=61.2                                                                  | CONTRADICTION  | Code returns 72.2 and 64.0 respectively. Spec says 64.4 and 61.2.                                                                                                                                                                                                 |
| GET /api/questionnaires/whatsapp-preview/{supplier_id}                                                                       | IMPLEMENTED    | Returns hardcoded WhatsApp preview for supplier_id 1.                                                                                                                                                                                                             |
| GET /api/evidence/drilldown/{metric_type}                                                                                    | IMPLEMENTED    | Returns evidence chain with cluster info, hash chain, frameworks.                                                                                                                                                                                                 |
| GET /api/reports/esg-pdf (3-page)                                                                                            | PARTIAL        | Code generates a 4-page PDF (cover, metrics, risk alerts, frameworks). Spec says 3 pages.                                                                                                                                                                         |
| GET /api/dashboard/operations-summary returns cluster-keyed object                                                           | CONTRADICTION  | Spec expects `{clusters: {E1_energy: {...}, G6_water: {...}, E3_waste: {...}, S1_safety: {...}, S3_gender: {...}}}`. Code returns `{clusters: [{cluster: "energy_kwh", ...}, ...]}` -- a flat array, not a keyed object.                                          |
| GET /api/risk/summary returns 4 chip objects                                                                                 | CONTRADICTION  | Spec expects `{G2_supply_chain: {score:78, tier:"B", trend:-3, flags:3}, G3_compliance: {...}, G8_governance: {...}, G5_environmental: {...}}`. Code returns `{total: N, by_severity: {...}, by_cluster: {...}, avg_days_open: N}`. Completely different shape.   |
| GET /api/risk/flags with full RiskFlag schema                                                                                | PARTIAL        | Code returns flags but missing fields: `cluster_name`, `supplier`, `title`, `detail`, `recommendation`. Has `flag_text` instead of `title`/`detail`.                                                                                                              |
| POST /api/risk/flags/{id}/acknowledge                                                                                        | IMPLEMENTED    | Sets acknowledged, acknowledged_at, acknowledged_by.                                                                                                                                                                                                              |
| GET /api/suppliers/risk-ranked                                                                                               | IMPLEMENTED    | Returns 7 suppliers sorted by risk_score ascending.                                                                                                                                                                                                               |
| GET /api/suppliers/{id}/profile                                                                                              | IMPLEMENTED    | Returns cluster scores and 3 hardcoded ML recommendations.                                                                                                                                                                                                        |
| GET /api/scope3/categories (8 categories)                                                                                    | IMPLEMENTED    | Returns 8 categories with specific numbers.                                                                                                                                                                                                                       |
| Scope 3 category numbers match spec                                                                                          | CONTRADICTION  | Cat 2: spec says coverage=51%/respondents=37, code has 31%/23. Cat 3: spec says 91%/66, code has 28%/20. Cat 6: spec says 100%/73, code has 89%/65. Cat 7: spec says 78%/57, code has 45%/33. Multiple categories diverge.                                        |
| Framework field IDs match spec                                                                                               | CONTRADICTION  | Spec uses E1-1, S2-a, 302-1-a, C1.2 for energy. Code uses ESRS E1-13, IFRS S2-13, GRI 302-1, TCFD-M-4. Different ID schemes entirely.                                                                                                                             |

### 1.2 specs/dashboard-metrics.md

| Requirement                                         | Classification | Evidence                                                                                                                                                                                                                                                                                                                                                                    |
| --------------------------------------------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ESGMetric TypeScript interface fields               | PARTIAL        | Frontend MetricCard uses some fields but not all (e.g., `calculation_method` not displayed).                                                                                                                                                                                                                                                                                |
| Confidence tiers (HIGH/MEDIUM/LOW with definitions) | IMPLEMENTED    | CSV data includes confidence values; evidence drilldown shows them.                                                                                                                                                                                                                                                                                                         |
| Evidence chain: SHA-256, genesis block              | IMPLEMENTED    | `src/evidence/hash_chain.py` implements SHA-256 chain with GENESIS prefix. `dashboard.py` and `evidence.py` compute real hashes.                                                                                                                                                                                                                                            |
| 6 existing metrics with specific values             | PARTIAL        | CSV has all 6 metrics but values differ slightly from spec: energy_kwh=2847320 (spec: 2,847,320 -- matches), emissions_tco2=892.4 (spec: 892.4 -- matches), water_m3=18430 (spec: 18,430 -- matches), scope3_category1=4281.7 (spec: 4,281.7 -- matches), diesel_consumed=49.3 (spec: 49.3 -- matches), scope3_category6=37.0 (spec: 37.0 -- matches). Metric values match. |
| 8 planned metrics (waste, safety, gender, etc.)     | STUB           | `frameworks.py` has mapping data for waste, gender, safety, governance. But no metric values, no evidence chain entries, no API endpoints returning these as live metrics.                                                                                                                                                                                                  |

### 1.3 specs/dashboard-tabs.md

| Requirement                                                                      | Classification | Evidence                                                                                                                                                                                          |
| -------------------------------------------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5 tabs: Operations, Supply Chain, Risk & Alerts, Frameworks, Supplier Engagement | IMPLEMENTED    | `App.jsx` Dashboard component renders all 5 tabs with correct names.                                                                                                                              |
| D1 OperationsGrid: 5-column (E1, G6, E3, S1, S3)                                 | MISSING        | Frontend shows 4 MetricCards (energy, emissions, water, scope3_cat1). Missing diesel and scope3_cat6 cards. No 5-column layout for planned clusters.                                              |
| D2 CoverageHero                                                                  | IMPLEMENTED    | CoverageHero component fetches coverage-stats and renders coverage bar.                                                                                                                           |
| D3 TrendChart with waste series + right-axis safety bars                         | PARTIAL        | TrendChart renders energy/emissions/water only. No waste data series. No right-axis safety bars.                                                                                                  |
| D4 RiskScoreStrip: 4 chips (G2/G3/G8/G5)                                         | MISSING        | Code has SummaryStrip with different content: active risk flags, scope3 completeness, scope 1+2+3 emissions, diesel chain status. Not the spec's 4 chip objects.                                  |
| SC1 SupplierList                                                                 | IMPLEMENTED    | SupplyChainPanel renders supplier table with risk-ranked data.                                                                                                                                    |
| SC2 SupplierProfilePanel                                                         | IMPLEMENTED    | Click supplier row opens profile with cluster bars and ML recommendations.                                                                                                                        |
| SC3 Scope3Detail                                                                 | IMPLEMENTED    | Scope 3 grid with 8 categories.                                                                                                                                                                   |
| SC4 GeopoliticalHeatmap                                                          | PARTIAL        | SupplyChainPanel fetches from /risk/geopolitical (6 countries). But RiskAlertsPanel has a SEPARATE hardcoded geopolitical table (5 countries: BD, VN, IN, PK, MM) that does NOT use the API data. |
| R1 RiskScorecard: 2x2 quadrants                                                  | IMPLEMENTED    | RiskAlertsPanel renders 2x2 scorecard with G2, G5, G8, G3.                                                                                                                                        |
| R2 RiskFlagsFeed with acknowledge                                                | IMPLEMENTED    | Flags feed with acknowledge button; acknowledged flags shown separately.                                                                                                                          |
| R3 Scope3CompletenessMeter                                                       | IMPLEMENTED    | Donut chart showing scope 3 completeness.                                                                                                                                                         |
| F1 FrameworkCompare expanded to 14 clusters                                      | PARTIAL        | FrameworkCompare shows 4 metric buttons. Backend supports ~18 metric types. Frontend only exposes 4.                                                                                              |
| E1 WhatsApp preview                                                              | IMPLEMENTED    | WhatsAppBusinessPreview component renders WhatsApp message template.                                                                                                                              |
| 16 components total                                                              | PARTIAL        | ~12 of 16 components are present in some form. Missing: proper OperationsGrid (D1), RiskScoreStrip (D4), full GeopoliticalHeatmap from API, and TrendChart waste/safety overlays.                 |

### 1.4 specs/framework-mapping.md

| Requirement                                           | Classification | Evidence                                                                                                                                                           |
| ----------------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Existing mappings for 5 metrics to CSRD/ISSB/GRI/TCFD | PARTIAL        | Code has mappings but with different field IDs (see contradiction above). Mapping structure is present but identifiers don't match spec.                           |
| FrameworkCompare component behavior                   | PARTIAL        | Frontend shows 4 buttons; clicking loads framework comparison table. Backend serves comparison data. But only 4 of the planned metric types are exposed in the UI. |
| Emission factor sources table                         | MISSING        | No dedicated API endpoint or frontend display for emission factor source documentation.                                                                            |

### 1.5 specs/risk-alerts.md

| Requirement                                                  | Classification | Evidence                                                                                                                                             |
| ------------------------------------------------------------ | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| RiskFlag TypeScript interface (13 fields)                    | PARTIAL        | Code has 8 fields. Missing: `cluster_name`, `supplier`, `title`, `detail`, `recommendation`. Has `flag_text` instead.                                |
| Priority formula: severity_weight x cluster_weight x urgency | IMPLEMENTED    | `src/api/routes/risk.py` computes `priority_score = severity_weight * cluster_weight * urgency`. Weights match spec: G2=1.2, G5=1.1, G8=1.0, G3=1.0. |
| Cluster weights match spec                                   | IMPLEMENTED    | G2=1.2, G5=1.1, G8=1.0, G3=1.0 -- all match.                                                                                                         |
| Acknowledge workflow: POST /api/risk/flags/{id}/acknowledge  | IMPLEMENTED    | Sets acknowledged=True, acknowledged_at, acknowledged_by="current_user".                                                                             |
| 4 example risk flags                                         | PARTIAL        | Code has 5 hardcoded flags. Different content from spec examples but same structure (minus missing fields).                                          |
| Severity levels: CRITICAL/WARNING/INFO                       | IMPLEMENTED    | Code uses these exact levels.                                                                                                                        |

### 1.6 specs/supplier-engagement.md

| Requirement                       | Classification | Evidence                                                                                                                                                                                                                                                                           |
| --------------------------------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 4-tier questionnaire scope        | PARTIAL        | `src/supplier/questionnaire.py` has a proper 4-tier system (TIER1=11 questions, TIER2=7, TIER3=6, TIER4=7). BUT `src/api/routes/questionnaires.py` has its own SEPARATE hardcoded tier templates (6-7 questions each). The questionnaire engine is NOT imported by the API routes. |
| Coverage stats                    | IMPLEMENTED    | GET /api/questionnaires/coverage-stats returns the data.                                                                                                                                                                                                                           |
| WhatsApp message format templates | IMPLEMENTED    | questionnaires.py has 4 tier WhatsApp templates with emoji formatting.                                                                                                                                                                                                             |
| Supplier list                     | IMPLEMENTED    | 5 suppliers in questionnaires.py, 7 in suppliers.py (inconsistency).                                                                                                                                                                                                               |

### 1.7 specs/\_index.md

| Requirement                                                                  | Classification | Evidence                                                                                                                                           |
| ---------------------------------------------------------------------------- | -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bangladesh garment supplier (Bangladesh Export Textiles Ltd.) selling to H&M | PARTIAL        | `SUPPLIERS` in `questionnaires.py` references "Bangladesh Textiles" and "H&M Supply Chain". `suppliers.py` lists "Bangladesh Export Textiles Ltd." |
| A/B/C/D risk tiers                                                           | IMPLEMENTED    | Supplier data includes risk_tier field with A/B/C/D values.                                                                                        |
| SHA-256 evidence chain as core USP                                           | IMPLEMENTED    | Full hash chain implementation with verification endpoint. Diesel tamper demonstration works.                                                      |
| WhatsApp-first engagement                                                    | PARTIAL        | WhatsApp preview template exists. No actual WhatsApp Business API integration (template-based display only).                                       |

---

## 2. Five Specific Checks

### 2.1 Broken Imports

| File                               | Status      | Evidence                                                                                                                                                                                           |
| ---------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/__init__.py`                  | CLEAN       | Empty init, no imports.                                                                                                                                                                            |
| `src/api/main.py`                  | CLEAN       | All router imports resolve. FastAPI, uvicorn imports work.                                                                                                                                         |
| `src/api/routes/dashboard.py`      | CLEAN       | Standard library + FastAPI imports. CSV loading uses stdlib.                                                                                                                                       |
| `src/api/routes/evidence.py`       | CLEAN       | Standard imports.                                                                                                                                                                                  |
| `src/api/routes/frameworks.py`     | CLEAN       | No external imports beyond FastAPI.                                                                                                                                                                |
| `src/api/routes/questionnaires.py` | CLEAN       | Standard imports.                                                                                                                                                                                  |
| `src/api/routes/reports.py`        | CLEAN       | fpdf2 is a declared dependency. Imports from dashboard.py and frameworks.py work within the package.                                                                                               |
| `src/api/routes/risk.py`           | CLEAN       | Standard imports.                                                                                                                                                                                  |
| `src/api/routes/scope3.py`         | CLEAN       | Standard imports.                                                                                                                                                                                  |
| `src/api/routes/suppliers.py`      | CLEAN       | Standard imports.                                                                                                                                                                                  |
| `src/connectors/mqtt_client.py`    | CONDITIONAL | `paho.mqtt.client` import wrapped in try/except with fallback to None. If paho-mqtt is not installed, the entire module degrades silently. paho-mqtt is NOT listed in pyproject.toml dependencies. |
| `src/connectors/sap_b1_adapter.py` | CLEAN       | Uses stdlib csv + urllib. No external imports.                                                                                                                                                     |
| `src/evidence/hash_chain.py`       | CLEAN       | hashlib is stdlib.                                                                                                                                                                                 |
| `src/orchestration/etl.py`         | CONDITIONAL | Imports from `connectors.mqtt_client` and `connectors.sap_b1_adapter`. If those modules fail (e.g., paho-mqtt missing), etl.py may fail at import time or silently degrade.                        |
| `src/realtime/alerts.py`           | CONDITIONAL | FastAPI WebSocket import guarded with try/except. If FastAPI version lacks WebSocket support, module degrades silently.                                                                            |
| `src/supplier/questionnaire.py`    | CLEAN       | Uses only dataclasses and typing.                                                                                                                                                                  |
| `apps/web/src/App.jsx`             | CLEAN       | React imports only. No third-party component library.                                                                                                                                              |
| `apps/web/src/main.jsx`            | CLEAN       | Standard React entry point.                                                                                                                                                                        |

**Finding:** `paho-mqtt` is imported but not declared in pyproject.toml dependencies. This is a missing dependency declaration.

**Severity:** MEDIUM -- MQTT connector fails silently at runtime without the library.

### 2.2 Fake / Mock Data in Backend

| Data Source            | Real or Fake    | Evidence                                                                                                                                                 |
| ---------------------- | --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dashboard live metrics | HYBRID          | Loaded from `data/operations/summary.csv` (real CSV data). Falls back to hardcoded dict if CSV missing. Not from a live database.                        |
| Trend data             | FAKE            | `TREND_DATA` is a hardcoded dictionary in `dashboard.py` with 5 months of static data.                                                                   |
| Alerts                 | FAKE            | `ALERTS` list with 2 hardcoded entries and uuid4 IDs.                                                                                                    |
| Evidence chain         | HYBRID          | Hashes computed via real SHA-256 from CSV data. But chain structure (prev_hash links) is built from the same CSV, not from a real tamper-evident ledger. |
| Framework mappings     | FAKE            | All framework mapping data is hardcoded in `frameworks.py` as `FRAMEWORK_OUTPUTS` and `COMPARE_DATA` dicts.                                              |
| Suppliers              | FAKE            | 7 hardcoded supplier dicts in `suppliers.py`. 5 different hardcoded suppliers in `questionnaires.py`.                                                    |
| Risk flags             | FAKE            | 5 hardcoded risk flag dicts with uuid4 IDs in `risk.py`.                                                                                                 |
| Scope 3 categories     | FAKE            | 8 hardcoded category dicts in `scope3.py`.                                                                                                               |
| Geopolitical data      | FAKE            | 6 hardcoded country dicts in `risk.py`.                                                                                                                  |
| WhatsApp templates     | FAKE            | 4 hardcoded template strings in `questionnaires.py`.                                                                                                     |
| Coverage stats         | FAKE            | Hardcoded numbers (72.2% and 64.0%) in `questionnaires.py`.                                                                                              |
| PDF report             | HYBRID          | Uses real data from dashboard/frameworks modules (which themselves are hardcoded). Report generation logic is real fpdf2 code.                           |
| SAP adapter            | EXPLICITLY MOCK | `SAPBusinessOneAdapter._demo_mode = True`. Loads from same CSV as dashboard. All methods return hardcoded/mock data.                                     |
| ML recommendations     | FAKE            | 3 hardcoded strings per supplier in `suppliers.py`.                                                                                                      |

**Verdict:** The backend is entirely hardcoded data. The CSV file is the closest thing to "real" data, but it is a static file, not a live data source. Every API response is deterministic and contains no dynamic content.

**Severity:** HIGH for production readiness. ACCEPTABLE for demo if explicitly documented as such.

### 2.3 Database Connection Status

| Component                | Connected?    | Evidence                                                                                                       |
| ------------------------ | ------------- | -------------------------------------------------------------------------------------------------------------- |
| API routes -> SQLite     | NO            | API routes load from CSV and hardcoded dicts. No database connection or queries in any route file.             |
| MQTT connector -> SQLite | YES           | `mqtt_client.py` has `_init_db()` that creates tables from schema.sql and writes to SQLite.                    |
| ETL pipeline -> SQLite   | YES           | `etl.py` calls `_init_db()` and writes metrics + evidence chain to SQLite.                                     |
| SAP adapter -> SQLite    | YES (via ETL) | `run_sap_ingestion()` in `etl.py` loads from SAP adapter and writes to SQLite.                                 |
| ETL loop integration     | NO            | `etl_loop()` exists but is NOT called from `main.py`. The ETL pipeline is built but not started.               |
| API reads from SQLite    | NO            | `load_latest_metrics()` in `etl.py` reads from SQLite, but no API route calls this function.                   |
| Database schema file     | NOT READ      | `src/db/schema.sql` was listed but not audited (file may not exist or may exist but was not in the read list). |

**Verdict:** A full SQLite + ETL + MQTT ingestion pipeline is built but entirely disconnected from the API layer. The API serves static data while the database infrastructure sits unused.

**Severity:** HIGH -- significant architectural disconnect. The ETL writes data that nobody reads.

### 2.4 Test Quality Assessment

| Test File                             | Test Count | Quality | Evidence                                                                                                                                                                                                                                                 |
| ------------------------------------- | ---------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/unit/test_risk_routes.py`      | 6          | GOOD    | Uses FastAPI TestClient to call real endpoints. Checks response shapes, field presence, data types. Example: verifies `by_severity` keys exist, checks quadrant IDs in scorecard, verifies 6 countries in geopolitical data. These are behavioral tests. |
| `tests/unit/test_scope3_routes.py`    | 2          | GOOD    | Calls real endpoints, checks field presence, validates data ranges.                                                                                                                                                                                      |
| `tests/unit/test_suppliers_routes.py` | 5          | GOOD    | Tests real endpoints, checks sorting, field counts, error cases (404 for missing supplier).                                                                                                                                                              |
| `tests/sdk/test_sdk_patterns.py`      | 8          | POOR    | Tests Kailash SDK imports/instantiation, NOT the ESG SCRM application. These would SKIP if kailash is not installed. Tests WorkflowBuilder, LocalRuntime, PythonCodeNode, etc. -- irrelevant to ESG SCRM functionality.                                  |

**Coverage Gaps:**

- Zero tests for `dashboard.py` routes (GET /live, GET /trends, GET /operations-summary, GET /alerts)
- Zero tests for `evidence.py` routes (GET /drilldown, GET /verify, GET /full-chain)
- Zero tests for `frameworks.py` routes (GET /map, GET /compare)
- Zero tests for `questionnaires.py` routes (GET /suppliers, GET /coverage-stats, GET /tiers)
- Zero tests for `reports.py` (GET /esg-pdf)
- Zero tests for `hash_chain.py` (SHA-256 computation correctness)
- Zero tests for `etl.py` (ETL pipeline)
- Zero tests for `mqtt_client.py` (ingestion)
- Zero tests for `sap_b1_adapter.py` (adapter)
- Zero tests for `questionnaire.py` (4-tier engine)
- Zero tests for `alerts.py` (WebSocket alert bus)

**Verdict:** Only 3 of 8 router modules have any tests. 13 behavioral tests exist for risk, scope3, and suppliers. The SDK pattern tests are irrelevant to the ESG SCRM product. No end-to-end tests exist.

**Severity:** HIGH -- ~85% of backend code has zero test coverage.

### 2.5 Frontend Data Source (Real vs Mock)

| Component                         | Data Source                                                                                    | Real or Mock   | Evidence                                                                                                                                |
| --------------------------------- | ---------------------------------------------------------------------------------------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| MetricCard (4 metrics)            | Fetches from /api/dashboard/live                                                               | REAL API CALL  | `fetchMetrics()` calls the backend. Data comes from CSV via API.                                                                        |
| CoverageHero                      | Fetches from /api/questionnaires/coverage-stats                                                | REAL API CALL  | `fetchCoverage()` calls the backend.                                                                                                    |
| EvidencePanel                     | Fetches from /api/evidence/drilldown                                                           | REAL API CALL  | `fetchEvidence()` calls the backend.                                                                                                    |
| TrendChart                        | Uses metrics data from dashboard/live                                                          | PARTIAL        | Only shows energy/emissions/water trends. No separate API call for trend data.                                                          |
| FrameworkCompare                  | Fetches from /api/frameworks/compare                                                           | REAL API CALL  | But only 4 metric buttons exposed.                                                                                                      |
| WhatsAppBusinessPreview           | Static template in questionnaires route                                                        | REAL API CALL  | Fetches WhatsApp preview from API.                                                                                                      |
| SupplyChainPanel                  | Fetches from /api/suppliers/risk-ranked, /api/scope3/categories, /api/risk/geopolitical        | REAL API CALL  | All three endpoints called.                                                                                                             |
| SupplierProfilePanel              | Fetches from /api/suppliers/{id}/profile                                                       | REAL API CALL  | Cluster scores and ML recommendations from API.                                                                                         |
| RiskAlertsPanel                   | Fetches from /api/risk/flags, /api/risk/summary, /api/risk/scorecard, /api/scope3/completeness | REAL API CALL  | All four endpoints called.                                                                                                              |
| GeopoliticalHeatmap (in Risk tab) | HARDCODED in JSX                                                                               | MOCK           | 5 countries (BD, VN, IN, PK, MM) hardcoded directly in the RiskAlertsPanel component. Does NOT use the /api/risk/geopolitical endpoint. |
| SummaryStrip                      | Derives from fetched data                                                                      | REAL (derived) | Uses data from risk/flags and scope3/completeness responses.                                                                            |

**Verdict:** Frontend makes real API calls for most data. The geopolitical heatmap in the Risk & Alerts tab is the only component using hardcoded data instead of the available API. The Supply Chain tab correctly fetches geopolitical data from the API.

**Severity:** MEDIUM -- one component uses mock data when real API data is available.

---

## 3. Structural Findings by Severity

### CRITICAL

**C1: API Response Shapes Contradict Spec**

- `GET /api/dashboard/operations-summary` returns flat array instead of keyed object. Any client built against the spec will fail.
- `GET /api/risk/summary` returns aggregate stats instead of 4 chip objects. Completely different structure.
- `GET /api/risk/flags` items are missing 5 of 13 spec-defined fields.
- Files: `src/api/routes/dashboard.py`, `src/api/routes/risk.py`

**C2: RiskFlag Schema Incomplete**

- Missing: `cluster_name`, `supplier`, `title`, `detail`, `recommendation`
- Has `flag_text` instead of `title`/`detail` -- frontend cannot render structured risk information as specified.
- File: `src/api/routes/risk.py`

### HIGH

**H1: ETL/Database Pipeline Disconnected from API**

- SQLite database infrastructure is built (mqtt_client.py, etl.py, hash_chain.py) but zero API routes read from it.
- `etl_loop()` is never started.
- `load_latest_metrics()` exists but is never called by any route.
- The API serves hardcoded data while the database writes go unread.
- Files: `src/api/routes/*.py`, `src/orchestration/etl.py`

**H2: WebSocket Alerts Not Wired**

- `src/realtime/alerts.py` defines `ws_alerts_endpoint()` and `AlertBus` class.
- Not registered in `src/api/main.py`.
- No WebSocket connection in frontend.
- Files: `src/realtime/alerts.py`, `src/api/main.py`

**H3: Orphaned Questionnaire Engine**

- `src/supplier/questionnaire.py` has a full 4-tier questionnaire system with `Question` dataclass, `Questionnaire` dataclass, tier management functions.
- `src/api/routes/questionnaires.py` has its OWN separate hardcoded tier templates.
- The questionnaire engine is never imported or used by the API routes.
- Files: `src/supplier/questionnaire.py`, `src/api/routes/questionnaires.py`

**H4: Missing Test Coverage (85%+ of routes untested)**

- No tests for: dashboard, evidence, frameworks, questionnaires, reports routes.
- No tests for: hash_chain, etl, mqtt_client, sap_b1_adapter, questionnaire engine, alerts.
- SDK pattern tests test Kailash SDK, not ESG SCRM.
- Files: `tests/unit/`, `tests/sdk/`

**H5: Frontend Missing Key Dashboard Components**

- OperationsGrid (D1): Only 4 metrics shown instead of 5-cluster grid.
- RiskScoreStrip (D4): SummaryStrip shows different content than spec's 4 chips.
- TrendChart: Missing waste data series and right-axis safety bars.
- Files: `apps/web/src/App.jsx`

**H6: Scope 3 Category Numbers Differ from Spec**

- Coverage percentages and respondent counts differ for cat_2, cat_3, cat_6, cat_7.
- No migration path or documentation explaining the discrepancy.
- File: `src/api/routes/scope3.py`

**H7: Framework Field IDs Use Different Scheme**

- Spec: E1-1, S2-a, 302-1-a, C1.2
- Code: ESRS E1-13, IFRS S2-13, GRI 302-1, TCFD-M-4
- Clients consuming framework mapping data cannot reconcile the two schemes.
- File: `src/api/routes/frameworks.py`

### MEDIUM

**M1: Supplier Count Inconsistency**

- `questionnaires.py` has 5 suppliers.
- `suppliers.py` has 7 suppliers.
- No single source of truth for supplier data.
- Files: `src/api/routes/questionnaires.py`, `src/api/routes/suppliers.py`

**M2: Missing paho-mqtt Dependency Declaration**

- `mqtt_client.py` imports `paho.mqtt.client` but paho-mqtt is not in pyproject.toml.
- Import degrades silently via try/except.
- File: `pyproject.toml`, `src/connectors/mqtt_client.py`

**M3: PDF Report Page Count Mismatch**

- Spec says 3 pages, code generates 4 pages.
- File: `src/api/routes/reports.py`

**M4: Diesel and Water Confidence Values Swapped**

- Spec: diesel=HIGH, water=MEDIUM.
- Code/CSV: diesel=MEDIUM, water=HIGH.
- Files: `data/operations/summary.csv`, `specs/dashboard-api.md`

**M5: Coverage Stats Values Differ**

- Spec: total_coverage=64.4, previous_coverage=61.2.
- Code: total_coverage=72.2, previous_coverage=64.0.
- File: `src/api/routes/questionnaires.py`

**M6: Geopolitical Heatmap Hardcoded in Risk Tab**

- RiskAlertsPanel renders hardcoded 5-country table.
- SupplyChainPanel correctly fetches 6-country data from API.
- Two different geopolitical datasets shown to user in different tabs.
- File: `apps/web/src/App.jsx` (RiskAlertsPanel section)

**M7: Frontend Shows Only 4 of 6 Live Metrics**

- MetricCards: energy, emissions, water, scope3_cat1.
- Missing: diesel_consumed, scope3_category6.
- Diesel tamper demo is a key USP but not visible in the dashboard.
- File: `apps/web/src/App.jsx` (MetricCard rendering)

### LOW

**L1: conftest.py Not Audited**

- Root conftest.py was listed for audit but not read in the initial pass. Subsequently read -- it is a standard .env auto-loader with no issues.
- File: `conftest.py`

**L2: CSS File Size**

- `styles.css` is ~1053 lines. Could benefit from CSS modules or component-scoped styles for maintainability.

**L3: No Error Boundary in Frontend**

- Single React component (App.jsx, ~1662 lines) with no error boundaries.
- Any fetch failure or rendering error crashes the entire SPA.

**L4: No Frontend Build Configuration**

- No vite.config.js, package.json, or build scripts visible in the read list.
- Unclear how the frontend is built and served.

---

## 4. Architectural Disconnects

### 4.1 Data Flow Breakdown

```
SPEC INTENT:
  Smart Meters -> MQTT -> ETL -> SQLite -> API -> Frontend
  SAP B1 -> Adapter -> ETL -> SQLite -> API -> Frontend

ACTUAL STATE:
  Smart Meters -> MQTT -> ETL -> SQLite (written, never read by API)
  SAP B1 -> Adapter -> ETL -> SQLite (written, never read by API)
  CSV File -> dashboard.py -> API -> Frontend (this path works)
  Hardcoded dicts -> all other routes -> API -> Frontend (this path works)
```

The ETL pipeline is built but serves no purpose because the API layer ignores the database entirely.

### 4.2 Module Dependency Map

```
CONNECTED (working):
  main.py -> routes/*.py -> (hardcoded data) -> Frontend
  evidence.py -> hash_chain.py (for hash computation)
  reports.py -> dashboard.py, frameworks.py (for report data)

DISCONNECTED (built but orphaned):
  mqtt_client.py -> SQLite (no API consumer)
  etl.py -> mqtt_client.py + sap_b1_adapter.py (loop not started)
  questionnaire.py (not imported by questionnaires.py route)
  alerts.py -> WebSocket (not registered in main.py)
```

### 4.3 Frontend-Backend Contract

The frontend successfully fetches from real API endpoints and renders the data. The contract is consistent for the endpoints that ARE called. However, the spec defines a different contract (response shapes) than what the API returns, meaning a frontend built to spec would break against the current API.

---

## 5. Summary Statistics

| Category                           | Count                  |
| ---------------------------------- | ---------------------- |
| Spec files audited                 | 7                      |
| Source files audited               | 24+                    |
| Test files audited                 | 4                      |
| CRITICAL findings                  | 2                      |
| HIGH findings                      | 7                      |
| MEDIUM findings                    | 7                      |
| LOW findings                       | 4                      |
| Total findings                     | 20                     |
| API endpoints implemented          | ~25                    |
| API endpoints matching spec shape  | ~15                    |
| Backend test coverage (routes)     | 3 of 8 routers (37.5%) |
| Frontend components using real API | ~11 of 12              |
| Database-connected API routes      | 0 of ~25               |

---

## 6. Priority Remediation Order

1. **Fix API response shapes** (C1, C2) -- Align `/operations-summary`, `/risk/summary`, and `/risk/flags` with spec. This is prerequisite for any frontend that consumes the documented API.

2. **Wire ETL to API** (H1) -- Make at least the dashboard endpoint read from SQLite instead of hardcoded data. This validates the entire pipeline.

3. **Add tests for untested routes** (H4) -- Dashboard, evidence, frameworks, questionnaires, reports routes all need behavioral tests.

4. **Connect questionnaire engine** (H3) -- Replace hardcoded tier templates in the API route with imports from `src/supplier/questionnaire.py`.

5. **Wire WebSocket alerts** (H2) -- Register `ws_alerts_endpoint` in main.py. Add frontend WebSocket listener.

6. **Reconcile Scope 3 numbers** (H6) -- Decide whether spec or code is authoritative and align the other.

7. **Reconcile framework field IDs** (H7) -- Decide whether spec or code is authoritative and align the other.

8. **Add missing frontend components** (H5, M7) -- Add diesel and scope3_cat6 MetricCards, implement proper OperationsGrid and RiskScoreStrip.

9. **Fix minor data inconsistencies** (M1, M3, M4, M5, M6) -- Supplier count, PDF page count, confidence values, coverage stats, geopolitical heatmap.

10. **Add paho-mqtt to dependencies** (M2) -- Declare the dependency or remove the MQTT connector.
