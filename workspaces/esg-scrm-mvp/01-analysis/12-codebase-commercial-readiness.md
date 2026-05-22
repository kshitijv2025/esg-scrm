# Codebase Commercial Readiness Assessment

## Executive Summary

The codebase is a **functional prototype** with solid engineering foundations (321 tests, JWT auth, multi-tenancy scaffolding, WebSocket alerts). It is **not** a commercial product. 4 of 4 investor-validated features are partially built at best. The fastest path to commercial readiness is to complete Feature 2 (supplier collection) as the deal-closer, with CSV upload as the data entry path for Features 1 and 3.

## Route-by-Route Backend Audit

### Auth Routes (`src/api/routes/auth.py`)

- **Status**: COMMERCIAL-READY
- Register + login with password strength validation (min 8 chars, upper+lower+digit)
- Rate limiting: 5 req/60s per IP on login/register
- Generic error messages (no user enumeration, no role leakage)
- JWT token generation with org_id + role
- **Missing**: Password reset, email verification, user invitation

### Suppliers Routes (`src/api/routes/suppliers.py`)

- **Status**: PARTIAL
- CRUD endpoints exist with pagination
- Scope 3 spend-based estimates (hardcoded 0.94 tCO2e/$1000 — needs emission factor database)
- ML recommendations endpoint (dynamic, not hardcoded)
- org_id filtering present
- **Missing**: Supplier onboarding workflow, supplier document attachment, supplier response tracking

### Risk Routes (`src/api/routes/risk.py`)

- **Status**: PARTIAL
- Risk flags with severity/cluster/priority scoring
- Geopolitical risk from dynamic supplier countries
- Threshold-based flag generation
- **Missing**: Configurable thresholds via API, risk flag deduplication, alert suppression windows

### Dashboard Routes (`src/api/routes/dashboard.py`)

- **Status**: PARTIAL
- Live metrics endpoint (aggregates from metrics table)
- Trends endpoint (time-series)
- Operations summary
- Alert count
- **Missing**: Industry-specific presets, buyer-specific views, target vs actual comparison

### Framework Routes (`src/api/routes/frameworks.py`)

- **Status**: THEATRICAL
- Returns static framework metadata (framework name, field IDs)
- **No mapping engine** — cannot take a KPI value and output which GRI/TCFD/CSRD/ISSB fields it maps to
- **Critical gap**: This is Feature 1 (the core USP) and 0% of the actual logic exists

### Questionnaires Routes (`src/api/routes/questionnaires.py`)

- **Status**: PARTIAL
- Routes exist for listing tiers, coverage stats, WhatsApp template
- Auth + org_id filtering present
- **Missing**: Questionnaire template system, question routing, response capture, response parsing, multi-language templates

### Evidence Routes (`src/api/routes/evidence.py`)

- **Status**: PARTIAL
- Evidence chain lookup with hash verification
- Chain visual endpoint
- Verify endpoint (checks hash integrity)
- **Missing**: Methodology tagging, emission factor references, data lineage DAG, evidence package export for auditors

### Reports Routes (`src/api/routes/reports.py` + `reports_pdf.py`)

- **Status**: PARTIAL
- JSON report endpoint exists
- PDF generation with fpdf2 (framework table, metrics, risk flags, supplier summary)
- org_id filtering on PDF data
- **Missing**: Framework-specific report formats (GRI, TCFD, CSRD), auditor-facing evidence packages, Excel/CSV download

### Upload Routes (`src/api/routes/upload.py`)

- **Status**: PARTIAL
- CSV upload endpoint exists with column mapping
- org_id scoped
- **Missing**: Excel support, upload validation rules, data quality checks on upload, bulk supplier import

### Alerts Routes (`src/api/routes/alerts.py`)

- **Status**: FUNCTIONAL
- WebSocket push for real-time risk flags
- Alert listing with acknowledgment
- **Missing**: Alert deduplication, severity escalation, email/WhatsApp notification channel

### ML Routes (`src/api/routes/ml.py`)

- **Status**: PARTIAL
- Risk prediction endpoint
- Supplier scoring
- **Missing**: Model training, drift detection, A/B testing, model explainability

### WhatsApp Routes (`src/api/routes/whatsapp.py`)

- **Status**: THEATRICAL
- Backend connector exists (`src/connectors/whatsapp.py`)
- No live Twilio/Meta API calls
- No message sending, receiving, or parsing
- **Critical gap**: This is Feature 2 (the deal-closer) and 0% of live messaging works

### Emission Factors Routes (`src/api/routes/emission_factors.py`)

- **Status**: PARTIAL
- Seed data exists for emission factors
- **Missing**: GHG Protocol / IPCC sourced factors, per-region factors, factor versioning

### Templates Routes (`src/api/routes/templates.py`)

- **Status**: PARTIAL
- CRUD for questionnaire templates
- org_id scoped
- **Missing**: Template versioning, template library, pre-built industry templates

### Audit Routes (`src/api/routes/audit.py`)

- **Status**: STUB
- Route exists but minimal functionality
- **Missing**: Full audit log of all write operations, user action tracking, compliance timeline

## Frontend Audit

### Pages

| Page                  | Status     | Connects to API                                              | Mock data present              |
| --------------------- | ---------- | ------------------------------------------------------------ | ------------------------------ |
| DashboardPage         | FUNCTIONAL | Yes — live metrics, trends, alerts                           | No                             |
| SupplyChainTab        | FUNCTIONAL | Yes — suppliers, risk flags, geopolitical                    | No                             |
| RiskAlertsTab         | FUNCTIONAL | Yes — risk flags, alerts                                     | No                             |
| SupplierEngagementTab | THEATRICAL | Partial — supplier list from API, WhatsApp preview is static | Yes — WhatsApp preview is mock |
| OperationsTab         | FUNCTIONAL | Yes — operations summary, live metrics                       | No                             |
| LoginPage             | FUNCTIONAL | Yes — auth API                                               | No                             |

### Components

All 10 extracted components connect to real APIs. The GeopoliticalRiskTable is properly deduplicated across SupplyChainTab and RiskAlertsTab. The TrendChart, MetricCard, EvidencePanel, and Toast all work with real data.

### Critical Frontend Gaps

1. **No framework mapping UI** — Feature 1 has no frontend interface
2. **No questionnaire template builder** — Feature 2 has no management UI
3. **No evidence package export** — Feature 3 has no auditor-facing UI
4. **No settings/admin page** — No user management, org settings, threshold config
5. **No report builder** — No way to generate framework-specific reports from the UI
6. **No multi-language support** — All text is English, no i18n framework

## Data Layer Audit (`src/db/database.py`)

### Tables that exist

- users, organizations, api_keys (auth)
- suppliers, risk_flags, metrics, factories (core data)
- evidence_chain, framework_mappings, templates (compliance)
- questionnaire_tiers, alert_thresholds (configuration)
- audit_log (stub)

### Multi-tenancy status

- **org_id filtering**: suppliers, risk_flags, evidence_chain, metrics (via factory join) — DONE
- **Still hardcoded factory_bd_001**: 12 call sites in seeds and routes
- **RBAC enforced**: require_role checks on routes — DONE

### Missing tables

- emission_factors (proper table with source, version, region)
- questionnaire_responses (supplier response capture)
- data_lineage (provenance DAG)
- notification_log (email/WhatsApp sent tracking)
- user_sessions (session management)

## Integration Readiness

### MQTT Client (`src/connectors/mqtt_client.py`)

- **Demo mode**: Reads CSV files — FUNCTIONAL
- **Live mode**: Would subscribe to MQTT broker — NOT TESTED
- **Missing**: Broker configuration, TLS, authentication, reconnection beyond basic retry

### SAP B1 Adapter (`src/connectors/sap_b1_adapter.py`)

- **Demo mode**: Reads CSV files — FUNCTIONAL
- **Live mode**: Would call SAP B1 Service Layer REST API — NOT IMPLEMENTED
- **Missing**: OAuth2 authentication, API client, error handling, data mapping

### WhatsApp Connector (`src/connectors/whatsapp.py`)

- **Demo mode**: None — just a stub
- **Live mode**: Would call Twilio/Meta Cloud API — NOT IMPLEMENTED
- **Missing**: Everything — message dispatch, webhook receiver, response parsing, template management

## Missing Commercial Features Summary

### BLOCKER (cannot demo without)

| Gap                      | What's needed                                     | Effort       |
| ------------------------ | ------------------------------------------------- | ------------ |
| Framework mapping engine | Static KPI→framework mapping table + API endpoint | 1 session    |
| CSV data upload for demo | Already exists, needs UI polish                   | <0.5 session |
| PDF compliance report    | Already exists with fpdf2, needs framework format | <0.5 session |

### HIGH (needed before first paying customer)

| Gap                               | What's needed                                 | Effort       |
| --------------------------------- | --------------------------------------------- | ------------ |
| WhatsApp Business API integration | Twilio client + webhook + response parser     | 2 sessions   |
| Questionnaire template system     | Schema + CRUD + pre-built templates           | 1 session    |
| Emission factor database          | 20-30 rows with GHG Protocol sourcing         | <0.5 session |
| PostgreSQL migration              | Docker Compose + connection string swap       | <0.5 session |
| Password reset                    | Token-based email flow                        | 0.5 session  |
| User management UI                | Invite, remove, change role                   | 1 session    |
| Auditor evidence export           | Bundle hash chain + methodology + source docs | 1 session    |
| Data lineage tracking             | Provenance DAG for derived values             | 1 session    |

### MEDIUM (sustained commercial use)

| Gap                     | What's needed                           | Effort      |
| ----------------------- | --------------------------------------- | ----------- |
| i18n framework          | React-intl + Bengali/Vietnamese locales | 2 sessions  |
| Configurable thresholds | API + UI for alert threshold management | 0.5 session |
| Action audit log        | Middleware logging all write operations | 0.5 session |
| Email notifications     | SMTP alerts for critical risk flags     | 0.5 session |
| CI/CD pipeline          | GitHub Actions: test → build → deploy   | 1 session   |
| SAP B1 live connector   | Service Layer REST API client           | 2 sessions  |

### LOW (nice to have)

| Gap                     | What's needed                         |
| ----------------------- | ------------------------------------- |
| LINE/WeChat integration | Additional messaging channel adapters |
| Dashboard customization | Drag-and-drop widget layout           |
| API key management      | Generate/revoke programmatic access   |
| Data retention policy   | Auto-archive metrics > 7 years        |
| ESG ratings panel       | Overall score (AAA-CCC)               |
