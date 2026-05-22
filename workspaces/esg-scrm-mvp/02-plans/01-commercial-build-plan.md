# Commercial Product Build Plan

## Strategy

Lead with **Feature 2 (Supplier Collection)** as the deal-closer, supported by CSV upload as the data entry path. The CFO buys because H&M requires Scope 3 data. Everything else supports that sale.

Build order follows buyer priority, not technical dependency:

1. **Phase A**: Data foundation (CSV upload, emission factors, PostgreSQL) — makes the platform accept real data
2. **Phase B**: The deal-closer (WhatsApp supplier collection, questionnaire system) — what the CFO buys
3. **Phase C**: The proof (framework mapping, compliance reports, evidence export) — what makes the CFO confident
4. **Phase D**: The wow factor (real-time monitoring, configurable alerts) — demo differentiation

## Phase A: Data Foundation (3 sessions)

### A1: PostgreSQL Migration

**Why first**: SQLite cannot handle concurrent users or production workloads. Every feature builds on the database.

**Changes**:

- `docker-compose.yml`: Add PostgreSQL service with volume
- `src/db/database.py`: Connection factory reads `DATABASE_URL`, uses `psycopg2` for PostgreSQL, `sqlite3` for dev fallback
- `src/db/seed*.py`: All seeds work against both SQLite and PostgreSQL (parameterized queries already done)
- `.env.example`: Add `DATABASE_URL=postgresql://esg:esg@localhost:5432/esgscrm`
- `tests/`: Verify both SQLite (unit tests) and PostgreSQL (integration) work

**Verification**: `docker compose up` starts Postgres, app connects, all 321 tests pass, seed data loads

### A2: Emission Factor Database

**Why**: Hardcoded 0.94 tCO2e/$1000 spend factor is indefensible to an auditor. Every Scope 3 number depends on this.

**Changes**:

- New table `emission_factors`: id, category, factor_value, unit, source (GHG Protocol/IPCC/EPA), region, year, is_active
- Seed 30 rows: Bangladesh grid electricity (0.67 tCO2e/MWh), diesel (2.68 tCO2e/L), natural gas, water treatment, waste disposal — sourced from GHG Protocol 2024 + IPCC AR6
- `src/api/routes/emission_factors.py`: List endpoint with filtering by category/region
- Update Scope 3 calculation in `suppliers.py` to use emission factor table instead of hardcoded 0.94
- Replace hardcoded `scope3_coverage_pct` of 64 with actual calculation from supplier responses

**Verification**: `pytest tests/unit/test_emission_factors.py` passes, Scope 3 endpoint returns numbers with cited emission factors

### A3: Enhanced CSV Upload + Data Quality

**Why**: The factory enters data via CSV. The upload experience must be smooth.

**Changes**:

- `src/api/routes/upload.py`: Add column validation (required columns, type checking), data quality warnings (value out of expected range), duplicate detection (same date + factory + metric)
- Frontend upload component: drag-and-drop zone, progress indicator, validation errors shown inline
- Upload history: track what was uploaded, when, by whom (audit trail)
- Bulk supplier import via CSV (same upload flow, different template)

**Verification**: Upload a CSV with errors → see clear error messages. Upload valid CSV → data appears on dashboard

## Phase B: The Deal-Closer (4 sessions)

### B1: Questionnaire Template System

**Why**: WhatsApp messages need structured templates. Cannot send ad-hoc questions.

**Changes**:

- New table `questionnaire_templates`: id, org_id, name, language, category (environment/social/governance), is_active, created_at
- New table `questionnaire_questions`: id, template_id, question_text, question_type (number/choice/text), choices (JSON), sort_order, required
- Seed 3 pre-built templates: H&M ESR (English + Bengali), GRI-aligned, Basic Scope 3
- `src/api/routes/templates.py`: CRUD for templates + questions, copy template, activate/deactivate
- Frontend: Template builder page (add questions, reorder, preview in mobile format)

**Verification**: Create a template → add questions → preview → activate. Send to test supplier.

### B2: WhatsApp Business API Integration

**Why**: This IS the product for the CFO. Without live WhatsApp, there is no deal.

**Changes**:

- `src/connectors/whatsapp.py`: Twilio WhatsApp Business API client
  - `send_template_message(to, template_id, language)`: Sends questionnaire questions as interactive WhatsApp messages
  - `receive_webhook(request)`: Receives supplier responses via webhook
  - `parse_response(message_body, question_type)`: Parses free-text/numeric responses into structured data
- `src/api/routes/whatsapp.py`: Webhook endpoint for Twilio callbacks, message status tracking
- `.env.example`: Add `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
- Response storage: New table `questionnaire_responses` (supplier_id, template_id, question_id, response_value, received_at, confidence)

**Verification**: Send a test WhatsApp message → receive a response → see parsed data in dashboard

### B3: Supplier Response Dashboard

**Why**: The CFO needs to see who responded, who didn't, and what the data says.

**Changes**:

- `src/api/routes/questionnaires.py`: New endpoints — response summary, non-responder list, response detail, resend to non-responders
- Frontend: Enhanced Engagement tab
  - Response tracker: visual progress (8/20 responded, 65% spend coverage)
  - Non-responder action panel: "Send reminder" button, "Mark as manual entry"
  - Response detail view: parsed supplier data with confidence indicators
  - Scope 3 coverage calculator: "Based on 8/20 responses, your Scope 3 coverage is X%"
- Supplier scorecard: per-supplier ESG profile built from responses

**Verification**: Send questionnaire → supplier responds → see parsed data on dashboard → see coverage percentage

### B4: Multi-Language Questionnaire Dispatch

**Why**: Suppliers in Bangladesh respond in Bengali. Vietnamese suppliers respond in Vietnamese.

**Changes**:

- Questionnaire templates support `language` field
- Question text stored per-language in `questionnaire_questions` (question_text_en, question_text_bn, question_text_vi)
- Dispatch logic: check supplier country → select appropriate language template → send
- Response parsing handles Bengali numerals (১২৩৪৫৬৭৮৯০), Vietnamese number formats
- Frontend: language selector when creating templates, preview in selected language

**Verification**: Create Bengali template → send to Bangladesh supplier → response parsed correctly

## Phase C: The Proof (3 sessions)

### C1: Framework Mapping Engine

**Why**: The CFO needs to output H&M's specific format. Multi-framework is Year 2.

**Changes**:

- New table `framework_mappings`: metric_name, framework (GRI/TCFD/CSRD/ISSB), field_id, field_name, unit, calculation_method
- Seed 40+ rows mapping 6 KPIs (kWh, water m3, diesel L, CO2, waste kg, headcount) × 4 frameworks
- `src/api/routes/frameworks.py`: New endpoint `POST /api/frameworks/map` — accepts metrics, returns framework-specific output
- `src/api/routes/reports.py`: New endpoint generating framework-specific report (GRI format for H&M, CSRD format for EU buyers)
- Frontend: Frameworks tab shows mapping results, user selects target framework, sees preview

**Verification**: Input 6 KPI values → get GRI-mapped output → get CSRD-mapped output

### C2: Enhanced PDF Compliance Report

**Why**: The CFO needs a document to hand to H&M or an auditor.

**Changes**:

- `src/api/routes/reports_pdf.py`: Enhanced PDF with:
  - Cover page (org name, reporting period, framework)
  - Emissions summary by scope with bar charts
  - Emission factor citations (source, year, region)
  - Supplier coverage statement (X suppliers, Y% of spend)
  - Methodology statement (calculation approach, data sources, limitations)
  - Per-metric evidence chain summary
  - Confidence distribution (X metrics HIGH, Y MEDIUM, Z LOW)
- Download endpoint with filename format: `{org}_ESG_Report_{framework}_{date}.pdf`
- Frontend: Report builder page — select framework, period, include/exclude sections, preview, download

**Verification**: Generate PDF → open it → see real data with emission factor citations and methodology

### C3: Evidence Package Export

**Why**: Auditors need a downloadable package, not just a dashboard login.

**Changes**:

- `src/api/routes/evidence.py`: New endpoint `GET /api/evidence/export` — generates ZIP containing:
  - Evidence summary CSV (metric, source, timestamp, confidence, hash)
  - Source data files (CSV of raw uploads)
  - Methodology document (markdown → PDF)
  - Hash chain integrity verification report
- `src/evidence/hash_chain.py`: Add chain verification endpoint that outputs a signed verification report
- Frontend: "Export for Audit" button on Evidence tab

**Verification**: Export evidence package → unzip → verify hash chain integrity report matches dashboard data

## Phase D: The Wow Factor (2 sessions)

### D1: Configurable Alert Thresholds

**Why**: Shows the system adapts to factory-specific needs, not one-size-fits-all.

**Changes**:

- New table `alert_thresholds`: id, org_id, metric_cluster, warning_threshold, critical_threshold, unit, is_active
- `src/api/routes/alerts.py`: CRUD for thresholds, test alert endpoint
- `src/realtime/risk_detector.py`: Read thresholds from database instead of hardcoded dict
- Frontend: Settings page with threshold sliders (energy, water, waste, emissions per day/week/month)
- Alert history: log of all alerts fired, acknowledged, resolved

**Verification**: Set energy threshold to 4000 kWh → upload data with 4200 kWh → alert fires on dashboard

### D2: Production DevOps

**Why**: Required before any factory actually uses the platform daily.

**Changes**:

- `.github/workflows/ci.yml`: Test → lint → build on push
- `.github/workflows/deploy.yml`: Docker build → push to registry → deploy
- `Dockerfile`: Multi-stage build (build frontend, bundle into FastAPI image)
- `docker-compose.yml`: Full stack (app + PostgreSQL + Redis for rate limiting)
- `.env.example`: Complete with all required vars documented
- Health check endpoint enhancement: database connectivity, MQTT connectivity, disk space
- Nginx reverse proxy config for HTTPS

**Verification**: Push to main → CI passes → Docker image builds → deploy to staging → health check green

## Build Order Summary

| Phase          | Sessions        | What ships                                              | Buyer value                                 |
| -------------- | --------------- | ------------------------------------------------------- | ------------------------------------------- |
| A: Foundation  | 3               | PostgreSQL, emission factors, CSV upload                | Platform accepts real data                  |
| B: Deal-closer | 4               | WhatsApp collection, questionnaires, supplier dashboard | CFO can collect Scope 3 data from suppliers |
| C: Proof       | 3               | Framework mapping, compliance reports, evidence export  | CFO can generate H&M-ready report           |
| D: Wow         | 2               | Configurable alerts, production DevOps                  | Demo differentiation, production ready      |
| **Total**      | **12 sessions** | **Full commercial product**                             | **CFO signs the check**                     |

## What This Plan Does NOT Include (Year 2)

These are explicitly deferred with value-anchors:

- **LINE/WeChat integration** (value-anchor: Vietnamese/Chinese supplier markets, but Bangladesh MVP only needs WhatsApp)
- **Multi-language UI** (value-anchor: Bengali supplier questionnaires ship in Phase B4; full UI localization is Year 2)
- **SAP B1 live API connector** (value-anchor: CSV upload covers Phase A; API connection is upsell for customers with IT capability)
- **NetSuite/Xero/SAP S4HANA connectors** (value-anchor: each new ERP is a market expansion, not a demo requirement)
- **ESG ratings panel** (value-anchor: EcoVadis-style ratings require supplier network density that Year 1 customers don't have)
- **Email notifications** (value-anchor: WhatsApp is the primary notification channel for the target market)
- **Dashboard customization** (value-anchor: CFO wants answers, not drag-and-drop widgets)
- **Data retention policy / 7-year archiving** (value-anchor: required for CSRD compliance, but Year 1 customers need data collection first)
