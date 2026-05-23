# Commercial Product Gap Analysis

## Current State Summary

What's built and working (68 backend + 18 frontend tests, all green):

- FastAPI backend with SQLite, JWT auth, rate limiting, password strength
- React frontend with 5 tabs, react-router-dom, responsive design, dark theme
- MQTT smart meter consumer (reads from CSV in demo mode)
- SAP B1 adapter (reads from CSV in demo mode)
- SHA-256 evidence hash chain per metric
- WebSocket alert bus for real-time risk flags
- Supplier table with Scope 3 spend-based estimates
- Risk flags with severity/cluster/priority scoring
- Geopolitical risk scores (10 countries, dynamic from supplier data)
- WhatsApp-style supplier engagement preview (static mock)
- Pagination on all list endpoints

## Brief Requirements vs Reality

### Feature 1: ESG Data Orchestration Platform

**Brief promise:** Maps one internal KPI (e.g., kWh consumed) across multiple disclosure frameworks (CSRD, ISSB, GRI, TCFD). Connects to ERPs (SAP Business One, NetSuite, Xero, SAP S/4HANA). Self-serve onboarding in 3-6 weeks.

| Requirement              | Status     | Gap                                                                                                                                            |
| ------------------------ | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| KPI-to-framework mapping | Missing    | No mapping engine exists. `frameworks.py` returns static framework metadata. No logic to say "kWh maps to GRI 302-1, TCFD Scope 2, CSRD E1-5". |
| SAP B1 connector         | Theatrical | `sap_b1_adapter.py` reads CSV files. No Service Layer REST API call. No authentication to SAP.                                                 |
| NetSuite connector       | Missing    | No code exists.                                                                                                                                |
| Xero connector           | Missing    | No code exists.                                                                                                                                |
| SAP S/4HANA connector    | Missing    | No code exists.                                                                                                                                |
| Self-serve onboarding    | Missing    | Registration creates user + org but no ERP connection wizard, no KPI selection, no framework selection.                                        |
| Multi-framework report   | Missing    | No endpoint generates a cross-framework disclosure report.                                                                                     |

**Gap severity:** CRITICAL. This is Feature 1 in the brief and 0% of the actual logic exists. The dashboard shows metrics but cannot map them to any reporting framework.

### Feature 2: Supply-Chain ESG Data Collection

**Brief promise:** Automated supplier questionnaires via WhatsApp/LINE/WeChat. Suppliers respond mobile-first. Localization in Bengali, Vietnamese, Thai, Hindi, Indonesian. >60% supplier response rate.

| Requirement                   | Status     | Gap                                                                                                                                             |
| ----------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| WhatsApp Business API         | Theatrical | `SupplierEngagementTab.jsx` shows a WhatsApp-style message preview. No Twilio/Meta API call. No message is actually sent or received.           |
| LINE integration              | Missing    | No code exists.                                                                                                                                 |
| WeChat integration            | Missing    | No code exists.                                                                                                                                 |
| Supplier questionnaire engine | Stub       | `questionnaires.py` has routes but `questionnaire.py` has no actual questionnaire template system, question routing, or response capture logic. |
| Multi-language localization   | Missing    | All text is English-only. No i18n framework, no locale files.                                                                                   |
| Questionnaire templates       | Missing    | No template schema for ESG questions by category (labour, environment, governance).                                                             |
| Response capture + parsing    | Missing    | No logic to parse supplier responses into structured data.                                                                                      |

**Gap severity:** CRITICAL. This is the deal-closer per the value audit (H&M Scope 3 compliance = revenue protection). 0% of actual messaging or questionnaire logic exists.

### Feature 3: Assurance-Ready Evidence Vault

**Brief promise:** Full audit trail with data lineage. Every number tagged with source, methodology, emission factor, confidence level. Must survive Big 4 audit. 7-year retention.

| Requirement                  | Status  | Gap                                                                                                                                                           |
| ---------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Per-metric evidence chain    | Partial | `evidence_chain` table exists with hash linking. Frontend shows chain visual with hash previews. But chain only covers raw metrics, not derived calculations. |
| Source + methodology tagging | Missing | Metrics have `source` and `confidence` fields but no methodology, emission factor reference, or calculation audit.                                            |
| Emission factor database     | Missing | No table of emission factors with source (GHG Protocol, IPCC, EPA). Scope 3 uses hardcoded 0.94 tCO2e/$1000 spend.                                            |
| Confidence scoring engine    | Missing | Confidence is a static string on metrics. No engine computes confidence from data quality, recency, source reliability.                                       |
| 7-year retention             | Missing | No data retention policy, no archiving, no immutability guarantees.                                                                                           |
| Data lineage DAG             | Missing | No provenance tracking for derived values. Cannot trace "Scope 3 total" back through calculation steps to raw inputs.                                         |
| Export for auditors          | Missing | No PDF/evidence package export. Auditors cannot review the chain without logging in.                                                                          |

**Gap severity:** HIGH. The hash chain is a good foundation but "assurance-ready" requires methodology tracking, emission factor references, and auditor-facing exports. Current implementation would not survive a Big 4 review.

### Feature 4: Real-Time ESG Monitoring

**Brief promise:** Live dashboard connecting to IoT sensors and ERP systems. Threshold alerts for emissions, energy, water, waste. No new hardware required.

| Requirement              | Status  | Gap                                                                                                                                                                                |
| ------------------------ | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MQTT consumer            | Partial | `mqtt_client.py` subscribes to `factory/{id}/meter/{meter_id}/{cluster}` topics. In demo mode reads CSV. In live mode would connect to broker, but no actual broker config tested. |
| Threshold alerts         | Partial | `risk_detector.py` checks metrics against thresholds and creates risk flags. Thresholds are hardcoded in a dict.                                                                   |
| WebSocket push           | Working | Alert bus pushes new risk flags to connected browsers via WebSocket.                                                                                                               |
| Multi-source ingestion   | Missing | Only MQTT. No ERP polling, no manual entry workflow, no CSV upload.                                                                                                                |
| Configurable thresholds  | Partial | Thresholds exist but are hardcoded in Python, not configurable via UI or API.                                                                                                      |
| Alert fatigue prevention | Missing | No deduplication, no severity escalation, no suppression windows.                                                                                                                  |

**Gap severity:** MODERATE. The MQTT + WebSocket pipeline works. Needs configurable thresholds, real broker testing, and alert management to be production-ready.

---

## Cross-Cutting Commercial Gaps

These are not feature-specific but required for any commercial product.

### Database

- **SQLite cannot scale.** Single-writer lock means concurrent users block each other. No replication, no backup story.
- **Migration:** PostgreSQL via Docker (one `docker-compose.yml` service addition). Connection string via `DATABASE_URL` env var.

### Multi-Tenancy

- **Schema supports org_id** on users and api_keys tables. But metrics, suppliers, risk_flags all use `factory_id` with no org scoping.
- **No tenant isolation.** Any authenticated user can see all data. The `require_auth` middleware checks token validity but doesn't filter by org.

### Role-Based Access Control

- **Users table has role column** (admin/editor/viewer) but it's never checked in route handlers. Every authenticated user has full access.
- **No permission checks** on create/update/delete operations.

### Reporting & Export

- **No PDF generation.** No report templates. No export functionality.
- **No Excel/CSV download** of metrics, suppliers, or risk data.
- **Compliance reports** (GRI, TCFD, CSRD) cannot be generated because framework mapping doesn't exist.

### API Documentation

- **FastAPI auto-generates /docs** (Swagger UI) from route definitions. This works out of the box but lacks request/response examples, authentication instructions, and commercial-grade polish.

### Deployment & DevOps

- **Dockerfile exists** but no production Docker Compose with PostgreSQL.
- **No CI/CD pipeline.** No GitHub Actions workflow for test + build + deploy.
- **No environment management** (staging, production).
- **No health monitoring** beyond `/api/health`.

### Data Import

- **No CSV/Excel upload** for bulk data ingestion. All seed data is hardcoded in `seed.py`.
- **Factory onboarding requires** loading historical data from ERP — no tooling exists.

### Audit Trail

- **No action logging.** User logins, data changes, flag acknowledgements, report generations are not tracked in an audit log.
- **Compliance requires** complete audit trail of who did what, when.

---

## Priority Classification

### Tier A: Must-Have for Demo Credibility

These gaps will be visible during a demo with real factory hardware. Without them, the demo looks like a student project, not a commercial product.

| #   | Gap                                                                                                                                                                                  | Effort     | Impact                                                                |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | --------------------------------------------------------------------- |
| A1  | **Framework mapping engine** — Map 6 sample KPIs (kWh, water m3, diesel L, CO2, waste kg, headcount) to 4 frameworks (GRI, TCFD, CSRD, ISSB). Static mapping table is fine for demo. | 1 session  | Transforms dashboard from "metrics viewer" to "compliance tool"       |
| A2  | **Emission factor database** — 20-30 rows covering energy, water, transport for Bangladesh garment sector. Sourced from GHG Protocol + IPCC. Replace hardcoded 0.94 spend factor.    | <1 session | Auditor credibility — can explain "where does this number come from?" |
| A3  | **PDF compliance report export** — Generate a formatted PDF from dashboard data. Evidence chain + framework mapping + supplier coverage.                                             | 1 session  | Tangible deliverable — CFO can show auditor                           |
| A4  | **CSV data upload** — Upload metrics CSV to bulk-load historical data. Simple file upload endpoint + parser.                                                                         | <1 session | Factory can load their actual data during demo                        |
| A5  | **Configurable alert thresholds** — Move hardcoded thresholds to a `thresholds` table + API endpoint. UI to view/edit.                                                               | <1 session | Shows the system adapts to factory-specific needs                     |
| A6  | **PostgreSQL migration** — Docker Compose with Postgres service. Update `database.py` connection logic. Seed with same data.                                                         | <1 session | Answers "what about scale?" convincingly                              |

### Tier B: Must-Have for Production

These are required before any factory actually uses the platform daily.

| #   | Gap                                                                                                                                           | Effort     | Impact                                                 |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------ |
| B1  | **Multi-tenant data isolation** — All queries scoped by org_id. Middleware injects org context from JWT.                                      | 1 session  | Multiple factories can use the platform simultaneously |
| B2  | **Role-based access control** — Check user.role on create/update/delete routes. Viewer = read-only, Editor = submit data, Admin = full.       | <1 session | Enterprise access control                              |
| B3  | **Action audit log** — New `audit_log` table. Middleware logs every write operation with user_id, action, timestamp, affected record.         | <1 session | Compliance requirement                                 |
| B4  | **WhatsApp Business API integration** — Twilio or Meta Cloud API. Send questionnaire messages, receive responses, parse into structured data. | 2 sessions | Core Feature 2 — deal-closer                           |
| B5  | **Questionnaire template system** — Schema for ESG questions by category, scoring rubric, response validation.                                | 1 session  | Required for Feature 2                                 |
| B6  | **Data quality scoring** — Compute confidence from recency, source reliability, completeness. Replace static confidence labels.               | 1 session  | Feature 3 credibility                                  |
| B7  | **CI/CD pipeline** — GitHub Actions: test → build → Docker push → deploy.                                                                     | 1 session  | Production deployment                                  |
| B8  | **Evidence package export** — Bundle all evidence for a metric into a downloadable audit package (hash chain + source docs + methodology).    | 1 session  | Feature 3 — auditor deliverable                        |

### Tier C: Nice-to-Have for Growth

| #   | Gap                             | Description                                             |
| --- | ------------------------------- | ------------------------------------------------------- |
| C1  | ML risk prediction              | XGBoost model trained on supplier features → risk score |
| C2  | Multi-language UI               | i18n framework + Bengali/Vietnamese/Thai translations   |
| C3  | Dashboard customization         | Drag-and-drop widget layout, saved views                |
| C4  | Email notifications             | SMTP alerts for critical risk flags                     |
| C5  | API key management              | Generate/revoke API keys for programmatic access        |
| C6  | Data retention policy           | Auto-archive metrics older than 7 years                 |
| C7  | NetSuite/Xero/SAP S4 connectors | Additional ERP integrations                             |
| C8  | ESG ratings panel               | Overall score (AAA-CCC), peer benchmarking              |

---

## Recommended Build Order

For the course demo with real factory hardware, execute Tier A in this sequence:

1. **A6 PostgreSQL** — Foundation everything else builds on
2. **A4 CSV upload** — Factory loads real data during demo
3. **A2 Emission factors** — Numbers become defensible
4. **A1 Framework mapping** — Dashboard becomes a compliance tool
5. **A5 Configurable thresholds** — Shows adaptability
6. **A3 PDF report** — Tangible deliverable to hand to auditor

Total estimated effort: 4-6 autonomous sessions for all of Tier A.

For production readiness after demo, execute Tier B in parallel where possible:

- B1 + B2 + B3 can run simultaneously (auth/audit isolation)
- B4 + B5 are sequential (messaging needs questionnaire templates)
- B6 + B8 are sequential (scoring feeds export)
- B7 is independent (CI/CD)
