# What's Left For Full Product Development

**Date**: 2026-05-17
**Basis**: Full codebase audit (20 findings) against specs and investor deliverables
**Current State**: Demo Prototype — functional API + frontend, but all data is hardcoded/CSV

---

## The Core Problem

The product has two disconnected data paths:

```
BUILT BUT UNUSED:  Smart Meters → MQTT → ETL → SQLite  (writes data nobody reads)
WHAT ACTUALLY RUNS: CSV/hardcoded dicts → API routes → Frontend  (serves all traffic)
```

The ETL pipeline, questionnaire engine, WebSocket alerts, and hash chain are all built — but not wired into the API. Every API response is deterministic hardcoded data. No real ERP, WhatsApp, or IoT connection exists.

---

## Phase 1: Fix Critical Spec Mismatches (1-2 sessions)

These break the API contract that any frontend or integration partner would rely on.

| #   | Finding                    | What's Wrong                                                                                                                  | What To Do                                                            |
| --- | -------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| C1  | API response shapes        | `/operations-summary` returns flat array (spec: keyed object); `/risk/summary` returns aggregate stats (spec: 4 chip objects) | Rewrite response shapes in `dashboard.py` and `risk.py` to match spec |
| C2  | RiskFlag schema incomplete | Missing 5 fields: `cluster_name`, `supplier`, `title`, `detail`, `recommendation`                                             | Add missing fields to risk flag data in `risk.py`                     |

**Effort**: ~200 LOC across 2 files. Can be done in one session.

---

## Phase 2: Wire Existing Infrastructure to API (2-3 sessions)

This is the highest-value work — it converts the demo into a working product by connecting what's already built.

| #   | Finding                       | What's Built                                                                                                                                     | What To Do                                                                                                                                                         |
| --- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| H1  | ETL disconnected from API     | Full MQTT→ETL→SQLite pipeline exists. `etl_loop()` never started. `load_latest_metrics()` never called.                                          | (a) Start `etl_loop()` in `main.py`. (b) Replace CSV loading in `dashboard.py` with `load_latest_metrics()`. (c) Wire scope3/suppliers/routes to read from SQLite. |
| H3  | Orphaned questionnaire engine | `src/supplier/questionnaire.py` has 4-tier engine (TIER1=11, TIER2=7, TIER3=6, TIER4=7 questions). API routes have separate hardcoded templates. | Import questionnaire engine in `questionnaires.py` routes. Replace hardcoded tier data.                                                                            |
| H2  | WebSocket alerts not wired    | `src/realtime/alerts.py` has `AlertBus` class + `ws_alerts_endpoint()`. Not registered in `main.py`.                                             | Register WebSocket route in `main.py`. Add frontend WebSocket listener.                                                                                            |

**Effort**: ~500 LOC load-bearing logic. 2-3 sessions. This is the single most impactful phase — it turns a demo into a product.

---

## Phase 3: Align Data & Fix Inconsistencies (1 session)

| #   | Finding                   | What's Wrong                                               | What To Do                                                    |
| --- | ------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------- |
| H6  | Scope 3 numbers           | Coverage % and respondent counts differ for cat 2, 3, 6, 7 | Decide: spec or code is authoritative. Align the other.       |
| H7  | Framework field IDs       | Spec uses E1-1, code uses ESRS E1-13                       | Decide which scheme is authoritative. Align.                  |
| M1  | Supplier count            | `questionnaires.py` has 5, `suppliers.py` has 7            | Unify to single source (use questionnaire engine once wired). |
| M4  | Confidence values swapped | Diesel=MEDIUM, water=HIGH (spec says opposite)             | Fix CSV data or spec.                                         |
| M5  | Coverage stats wrong      | Code: 72.2%/64.0%, Spec: 64.4%/61.2%                       | Align.                                                        |
| M3  | PDF page count            | Generates 4 pages, spec says 3                             | Fix report generation.                                        |

**Effort**: ~100 LOC changes + data file edits. One session.

---

## Phase 4: Complete Frontend (1-2 sessions)

| #   | Finding                        | What's Missing                                                                                                                                                   | What To Do                                                                                                                                        |
| --- | ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| H5  | Missing dashboard components   | OperationsGrid (D1): only 4 metrics instead of 5-cluster grid. RiskScoreStrip (D4): different content than spec's 4 chips. TrendChart: no waste/safety overlays. | Add diesel + scope3_cat6 MetricCards. Implement proper OperationsGrid. Add RiskScoreStrip with G2/G3/G8/G5 chips. Add waste series to TrendChart. |
| M7  | Only 4 of 6 metrics shown      | Missing: diesel_consumed, scope3_category6                                                                                                                       | Add 2 more MetricCards. Diesel tamper demo is a key USP but not visible.                                                                          |
| M6  | Hardcoded geopolitical heatmap | Risk tab has hardcoded 5-country table. Supply Chain tab correctly fetches from API.                                                                             | Make Risk tab use the same API endpoint.                                                                                                          |

**Effort**: ~300 LOC JSX changes. 1-2 sessions.

---

## Phase 5: Testing (2 sessions)

| #   | Finding                 | Current State                                                                                                                                                                               | What To Do                                                                |
| --- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| H4  | 85%+ of routes untested | 13 tests covering only risk, scope3, suppliers routes. Zero tests for dashboard, evidence, frameworks, questionnaires, reports, hash_chain, etl, mqtt_client, questionnaire engine, alerts. | Write behavioral tests for each untested module using FastAPI TestClient. |

**Effort**: ~40-50 test functions. 2 sessions.

---

## Phase 6: Production Features (3-5 sessions)

These are features the business plan promises but don't exist in code yet.

| Feature                        | Current State                                                    | What To Build                                                                                        | Effort                               |
| ------------------------------ | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------ |
| Real ERP integration           | SAP B1 adapter in `_demo_mode=True`, reads same CSV as dashboard | Real SAP Business One API client with OAuth, production data fetch, error handling                   | 2 sessions                           |
| WhatsApp Business API          | Template preview only (hardcoded strings)                        | Real Meta Business API integration: send questionnaires, receive responses, parse into supplier data | 2-3 sessions                         |
| Real-time IoT pipeline         | MQTT→ETL→SQLite built but API ignores DB                         | Wire API to read from SQLite; add threshold alerts; implement real-time dashboard updates            | 1 session (on top of Phase 2 wiring) |
| Authentication & authorization | None                                                             | JWT auth, user roles, API key management                                                             | 2 sessions                           |
| Multi-tenancy                  | None                                                             | Tenant isolation in DB, API middleware, per-tenant ESG profiles                                      | 2 sessions                           |
| ML recommendations             | 3 hardcoded strings per supplier                                 | Real ML model for supplier risk scoring, anomaly detection, ESG trend prediction                     | 2-3 sessions                         |
| CRM integration                | Zero capability                                                  | CSV export → Zapier/webhook → Zoho connector → Salesforce connector (phased per CRM strategy)        | 3 sessions (phased)                  |
| Scope 3 calculation engine     | Hardcoded 8 categories                                           | Three-layer calculation (spend-based → supplier-specific → verified) with real emission factors      | 2-3 sessions                         |
| Production deployment          | None                                                             | Docker, CI/CD, environment config, health checks, monitoring, logging                                | 1-2 sessions                         |

---

## Summary: Time to Full Product

| Phase                            | Sessions           | What It Delivers                                        |
| -------------------------------- | ------------------ | ------------------------------------------------------- |
| **Phase 1**: Fix spec mismatches | 1-2                | API contract matches documentation                      |
| **Phase 2**: Wire existing infra | 2-3                | Working data pipeline (ETL→DB→API→Frontend)             |
| **Phase 3**: Align data          | 1                  | Spec/code consistency                                   |
| **Phase 4**: Complete frontend   | 1-2                | All dashboard components                                |
| **Phase 5**: Testing             | 2                  | >80% route coverage                                     |
| **Phase 6**: Production features | 10-15              | ERP, WhatsApp, auth, multi-tenancy, CRM, ML, deployment |
| **Total**                        | **17-25 sessions** | **Production-ready ESG SCRM platform**                  |

**Minimum viable product (demo → investable)**: Phases 1-5 = ~7-10 sessions
**Full product (customer-ready)**: All phases = ~17-25 sessions

---

## Priority Order

The single most impactful work is **Phase 2 (wire ETL to API)**. It converts 4 existing but disconnected modules into a working data pipeline. Without it, every other improvement is cosmetic — the product still serves static data.

Recommended sequence:

1. Phase 2 → 2. Phase 1 → 3. Phase 3 → 4. Phase 4 → 5. Phase 5 → 6. Phase 6

Phase 2 first because fixing response shapes (Phase 1) is wasted effort if the data source changes from CSV to SQLite (Phase 2). Wire the database first, then align the API contract.
