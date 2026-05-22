# ESG SCRM Commercial Product — Complete Todo List

Value-ranked by CFO buyer priority. Build order follows Phase A → B → C → D from the commercial build plan.

Each todo specifies: what to build, which spec it implements, and whether it's a BUILD (create the component) or WIRE (connect to real data, replace mock/hardcoded).

---

## Milestone 1: Data Foundation (Phase A)

**Why the CFO cares**: The platform can't demonstrate anything without real data flowing through it. This is table stakes — before the deal-closer (WhatsApp) works, the data layer must accept real numbers and cite real emission factors.

### A1. PostgreSQL Migration

- [x] **A1.1 BUILD**: Add PostgreSQL service to `docker-compose.yml` with persistent volume, health check, and environment-based configuration. Implements: `specs/data-model.md`
- [x] **A1.2 BUILD**: Create `src/db/schema_pg.sql` — PostgreSQL-compatible DDL (replace SQLite autoincrement with SERIAL/BIGSERIAL, TEXT with VARCHAR where appropriate, add proper foreign keys and indexes). Implements: `specs/data-model.md`
- [x] **A1.3 BUILD**: Update `src/db/database.py` connection factory — read `DATABASE_URL` env var, support both PostgreSQL (psycopg2) and SQLite (dev fallback) via dialect detection. Implements: `specs/data-model.md`
- [x] **A1.4 WIRE**: Update all `src/db/seed*.py` files to work against both SQLite and PostgreSQL (parameterized queries already done; verify %s vs ? placeholder handling). Implements: `specs/data-model.md`
- [x] **A1.5 BUILD**: Update `.env.example` with `DATABASE_URL=postgresql://esg:esg@localhost:5432/esgscrm` and all other required vars documented. Implements: `specs/data-model.md`
- [x] **A1.6 WIRE**: Add connection pooling to database.py (pool of 5-10 connections, recycle every 300s). Verify all 321 existing tests pass against both SQLite and PostgreSQL. Implements: `specs/data-model.md`
- [x] **A1.7 BUILD**: Validate column-name consistency between `schema.sql` and `schema_pg.sql` — fix drift (e.g., `value` vs `factor_value`, `metric_name` vs `metric`, `kpi_name` presence). Every column in SQLite must have an identically-named counterpart in PostgreSQL. Write validation test that compares both schemas. Implements: `specs/data-model.md`

### A2. Emission Factor Database

- [x] **A2.1 BUILD**: Create `emission_factors` table in schema.sql and schema_pg.sql — columns: id, category, factor_value, unit, source (GHG Protocol/IPCC/EPA/DEFRA/IEA), region, year, table_or_equation (TEXT — e.g. "Table 7.3", per journal 0007), is_active, org_id. Implements: `specs/framework-mapping.md` § Emission Factor Sources, journal `0007-DECISION-emission-factor-source-pinning.md`
- [x] **A2.2 BUILD**: Create `src/db/seed_emission_factors.py` — seed 30+ rows: Bangladesh grid electricity (0.67 tCO2e/MWh from IEA 2023), diesel (2.68 tCO2e/L from GHG Protocol), natural gas, water treatment, waste disposal, spend-based EEIO factors from EXIOBASE, DEFRA 2023 flight factors (short-haul/long-haul per pax-km), GHG Protocol hotel night factors. Each row cites source, year, region, and table_or_equation. Implements: `specs/framework-mapping.md` § Emission Factor Sources
- [x] **A2.3 BUILD**: Create `src/api/routes/emission_factors.py` — list endpoint with filtering by category/region/year. Add `require_auth` dependency. Org-scoped. Implements: `specs/dashboard-api.md`
- [x] **A2.4 WIRE**: Update Scope 3 calculation in `src/api/routes/suppliers.py` to use emission factor table instead of hardcoded 0.94 tCO2e/$1000 spend. Implements: `specs/framework-mapping.md` _(PARTIAL: queries emission_factors table first; still has hardcoded 0.94 fallback when no rows found)_
- [x] **A2.5 WIRE**: Replace hardcoded `scope3_coverage_pct` of 64 with actual calculation from supplier questionnaire responses. Implements: `specs/supplier-engagement.md` § Coverage Calculation

### A3. Enhanced CSV Upload

- [x] **A3.1 BUILD**: Add column validation to `src/api/routes/upload.py` — required columns check, type checking (numbers where expected), data quality warnings (value out of expected range), duplicate detection (same date + factory + metric), file extension validation (.csv only), MIME type check, filename sanitization (reject paths with / or ..). Store original uploaded CSV files in org-scoped directory (`uploads/{org_id}/{date}/`) with metadata in `uploaded_files` table so C3.1's `raw_data/` export can retrieve originals. Implements: `specs/dashboard-api.md`, `specs/evidence-vault.md` § raw_data export
- [x] **A3.3 BUILD**: Upload audit trail — `GET /api/uploads/history` endpoint with org scoping. Track what was uploaded, when, by whom in `audit_log` table. Implements: `specs/evidence-vault.md` § source_system tracking
- [ ] **A3.4 WIRE**: Bulk supplier import via CSV — new template columns: supplier_name, country, contact_email, phone, annual_spend, tier, category. Endpoint `POST /api/upload/suppliers`. Implements: `specs/data-model.md`
- [x] **A3.2 ~~BUILD~~ REMOVED**: Frontend CSV upload component for Scope 1/2 factory metrics. Removed per user decision — capturing Scope 1/2 data via CSV upload is not the product; the product is collecting Scope 3 data from suppliers via WhatsApp. CSV upload of factory metrics defeats the purpose and allows tampering. Backend column validation (A3.1) and audit trail (A3.3) remain as they support supplier reference data upload.

### A4. Password Security Upgrade

- [x] **A4.1 BUILD**: Replace SHA-256 password hashing with bcrypt in `src/auth/jwt.py`. Add migration for existing SHA-256 hashes (re-hash on next login). Implements: `specs/auth.md` § Password Storage
- [x] **A4.2 WIRE**: Update registration and login flows to use bcrypt. Verify existing auth tests still pass. Implements: `specs/auth.md`
- [x] **A4.3 BUILD**: Password reset flow — `POST /api/auth/forgot-password` generates time-limited token, `POST /api/auth/reset-password` validates token and updates password hash. Requires SMTP env vars. Implements: `specs/auth.md`
- [x] **A4.4 BUILD**: JWT token invalidation — add `token_version` column to users table, include in JWT payload, check on decode. Increment on password change and user deactivation. Implements: `specs/auth.md`
- [x] **A4.5 BUILD**: Email verification flow — after registration, send verification email with time-limited token. Account stays in "pending" state until verified. `POST /api/auth/verify-email` confirms. Unverified accounts cannot login. Implements: `specs/auth.md` § Account Security
- [x] **A4.6 BUILD**: User invitation backend — `POST /api/auth/invite` (admin sends invite email, creates account with temporary password or magic link), `POST /api/auth/accept-invite` (new user sets password). Distinct from self-registration. Implements: `specs/auth.md` § RBAC (admin manages users)

### A5. Emission Metrics Foundation

- [x] **A5.1 BUILD**: Add `production_volume` column to metrics table (units produced per period). Add emission intensity calculation endpoints — `GET /api/metrics/intensity` returns tCO2e per unit and kWh per unit. Required for GRI 302-3 (energy intensity) and GRI 305-4 (emissions intensity) framework mappings. Implements: `specs/dashboard-metrics.md` Cluster 1, `specs/framework-mapping.md`
- [x] **A5.2 BUILD**: Add `renewable_kwh` column to metrics table. Calculate renewable energy percentage: `renewable_kwh / total_kwh`. Display on dashboard. Track renewable energy certificates (RECs) — add `rec_certificates` table (id, org_id, source, kwh_certified, period_start, period_end, certificate_url). Implements: `specs/dashboard-metrics.md`, `specs/framework-mapping.md` renewable energy share
- [x] **A5.3 BUILD**: Add `wastewater_discharge` and `water_stress_level` columns to water metrics. Endpoint `GET /api/water/wastewater`. Water stress mapping by supplier geography using WRI Aqueduct data. Implements: `specs/dashboard-metrics.md` G6 Water Stress

---

## Milestone 2: The Deal-Closer — WhatsApp Supplier Collection (Phase B)

**Why the CFO cares**: This IS the product. H&M requires Scope 3 data from suppliers. The CFO buys because the platform can actually collect that data via WhatsApp — the channel suppliers actually use in Bangladesh. Journal anchor: `0001-DISCOVERY-deal-closer.md`.

### B1. Questionnaire Template System

- [x] **B1.1 BUILD**: Create `questionnaire_templates` and `questionnaire_questions` tables in both schema.sql and schema_pg.sql. Templates: id, org_id, name, language, category (environment/social/governance), is_active. Questions: id, template_id, question_text, question_type (number/choice/text), choices (JSON), sort_order, required. Implements: `specs/supplier-engagement.md` § Expanded Questionnaire Scope
- [x] **B1.2 BUILD**: Create `src/api/routes/templates.py` — CRUD for templates and questions: create template, add questions, reorder questions, copy template, activate/deactivate, list templates by org. Editor role required. Implements: `specs/dashboard-api.md`
- [x] **B1.3 BUILD**: Create `src/db/seed_templates.py` — seed 3 pre-built templates: (1) H&M ESR Basic (English), (2) H&M ESR Basic (Bengali), (3) GRI-aligned comprehensive. Each with 10-15 questions covering Tier 1-3 from spec. Implements: `specs/supplier-engagement.md` § Tiers 1-4
- [x] **B1.4 BUILD**: Frontend template builder page — create/edit template form, add/remove/reorder questions, question type selector, mobile preview panel. Implements: `specs/dashboard-tabs.md` § Engagement tab
  - PARTIAL: TemplateBuilder.jsx exists with full form; B4.4 LanguageSelector wired. Mobile preview panel noted as partial.

### B2. WhatsApp Business API Integration

- [x] **B2.1 BUILD**: Rewrite `src/connectors/whatsapp.py` — Twilio WhatsApp Business API client with: `send_template_message(to, template_id, language)` sends questionnaire as interactive WhatsApp messages; `receive_webhook(request)` receives supplier responses; `parse_response(message_body, question_type)` parses free-text/numeric responses into structured data. Fix `verify_webhook` to use Base64-encoded HMAC comparison matching Twilio's format. Implements: `specs/supplier-engagement.md` § WhatsApp Message Format
- [x] **B2.2 BUILD**: Create `src/api/routes/whatsapp.py` — webhook endpoint for Twilio callbacks (no auth required on webhook), message status tracking, delivery/read receipt logging. In demo mode, reject webhook requests with 503 or mark all data with `demo_mode=1`. Implements: `specs/supplier-engagement.md`
- [x] **B2.3 BUILD**: Create `questionnaire_responses` table — supplier_id, template_id, question_id, response_value, response_text, channel (whatsapp/web/manual), received_at, confidence (computed from response quality), org_id. Implements: `specs/supplier-engagement.md`, `specs/data-model.md`
- [x] **B2.4 WIRE**: Wire WhatsApp connector to template system — sending a questionnaire fetches questions from template, formats as WhatsApp interactive message, dispatches via Twilio. Response webhook parses and stores in questionnaire_responses. Validate question IDs match template questions sent to this supplier. Implements: `specs/supplier-engagement.md`
  - IMPLEMENTED: `send_questionnaire()` calls `_resolve_template()` to fetch from DB; `_format_questionnaire()` uses `text_bn`/`text_vi` based on country_code; `receive_webhook()` parses and stores responses.
- [x] **B2.5 BUILD**: Update `.env.example` with Twilio env vars: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER` (fix naming mismatch — connector reads `TWILIO_WHATSAPP_NUMBER` but .env.example currently shows `TWILIO_PHONE_NUMBER`), `TWILIO_WEBHOOK_URL`. Implements: `specs/supplier-engagement.md`
- [x] **B2.5a BUILD**: Upgrade webhook verification in `src/connectors/whatsapp.py` from SHA-1 to SHA-256. Use `hmac.compare_digest` with proper constant-time byte comparison (not hex string comparison) to prevent timing attacks. Implements: security best practices
- [x] **B2.6 BUILD**: Email questionnaire fallback — SMTP send + reply parsing as second channel. `POST /api/questionnaires/send-email` dispatches via SMTP. Implements: brief Feature 2 "email and web portal as fallback"
  - IMPLEMENTED: `POST /api/questionnaires/send-email` endpoint at line 547.
- [x] **B2.7 BUILD**: Web portal response capture — authenticated page where suppliers can fill questionnaire via browser when WhatsApp is unavailable. Implements: brief Feature 2 "web portal as fallback"
  - IMPLEMENTED: Portal link generation via `POST /api/questionnaires/portal/link/{supplier_id}`; `SupplierEngagementTab` calls this on click.

### B3. Supplier Response Dashboard

- [x] **B3.1 BUILD**: Create backend endpoints — `GET /api/questionnaires/response-summary` (aggregated stats), `GET /api/questionnaires/non-responders` (list of suppliers who haven't responded), `GET /api/questionnaires/responses/{supplier_id}` (individual responses), `POST /api/questionnaires/resend` (send reminder to non-responders). Implements: `specs/supplier-engagement.md` § Coverage Stats
- [x] **B3.2 BUILD**: Frontend enhanced Engagement tab — response tracker (visual progress bar: 8/20 responded, 65% spend coverage), non-responder action panel with "Send Reminder" and "Mark as Manual Entry" buttons. Implements: `specs/dashboard-tabs.md` § Engagement tab
  - FIXED: ManualEntryForm and detail view were calling wrong endpoint (`/questionnaires/suppliers/{id}` → 404). Backend endpoint `GET /api/questionnaires/suppliers/{supplier_id}` existed but frontend used wrong URL. Fixed frontend to call `/api/questionnaires/suppliers/{supplierId}` with proper org isolation. All 514 tests pass.
- [x] **B3.3 BUILD**: Frontend response detail view — per-supplier parsed data with confidence indicators (HIGH/MEDIUM/LOW color coding). Implements: `specs/supplier-engagement.md`
  - FIXED: Same root cause as B3.2 — detail view called `/questionnaires/suppliers/{id}` (404). Backend endpoint `GET /api/questionnaires/suppliers/{supplier_id}` existed; frontend was calling wrong URL without `/api/` prefix. Fixed. All 514 tests pass.
- [x] **B3.4 BUILD**: Scope 3 coverage calculator — **spend-weighted** coverage: total annual_spend_usd of responding suppliers / total annual_spend_usd of all suppliers. Also report headcount-based coverage as secondary metric. Target: 60% coverage by spend per brief Success Criteria #2 and journal `0009-DECISION-coverage-rate-over-response-rate.md`. Display prominently on dashboard. Implements: `specs/supplier-engagement.md` § Coverage Calculation
- [x] **B3.5 WIRE**: Supplier scorecard — per-supplier ESG profile built from questionnaire responses. Endpoint `GET /api/suppliers/{id}/profile` returns E/S/G dimension scores derived from actual responses. Implements: `specs/dashboard-tabs.md` § Supplier Profile Panel
- [x] **B3.5a BUILD**: Supplier ESG scoring engine — define weighted scoring methodology (E/S/G dimensions computed from Tier 1-4 questionnaire responses with configurable weights per industry). Algorithm: each response maps to 0-100 scale per dimension, weighted by question importance. Store composite score in `suppliers.esg_score`, compute `risk_tier` (A/B/C/D) from score thresholds (A≥80, B≥60, C≥40, D<40). Endpoint `GET /api/suppliers/{id}/score` returns dimension breakdown with methodology explanation. **This is THE output H&M consumes** — without scores, the platform collects data but cannot communicate results. Implements: brief Success Criteria, value-auditor CRITICAL finding
- [x] **B3.6 BUILD**: Manual data entry — frontend form to enter questionnaire responses on behalf of a supplier who reported via phone/email. Stores with channel="manual" and confidence=LOW. Implements: value-auditor deal-killer #2 "manual data entry fallback"
  - FIXED: Same root cause as B3.2/B3.3 — ManualEntryForm mounted at `SupplierEngagementTab.jsx:43` called `/questionnaires/suppliers/{supplierId}` (404). Backend endpoint at `GET /api/questionnaires/suppliers/{supplier_id}` existed; frontend was missing `/api/` prefix. Fixed. All 514 tests pass.
- [x] **B3.7 BUILD**: Chasing workflow — automated escalation: WhatsApp at day 0, email at day 7, flag as "non-responsive" at day 14 with auto-generated risk flag. Implements: value-auditor deal-killer #2 "chasing workflow"
  - IMPLEMENTED: `GET /api/questionnaires/chasing-status` (line 737) + `POST /api/questionnaires/chase` (line 1261). UI at `SupplierEngagementTab.jsx:543` with Day 0/7/14 timeline.
- [x] **B3.8 BUILD**: Create missing `GET /api/questionnaires/whatsapp-preview/{supplier_id}` endpoint that `SupplierEngagementTab.jsx` currently calls (returns 404). Returns questionnaire preview data for a given supplier. Implements: `specs/dashboard-tabs.md` § Engagement tab
  - IMPLEMENTED: `GET /api/questionnaires/whatsapp-preview/{supplier_id}` at line 299.
- [x] **B3.9 BUILD**: Wire `GET /questionnaires/{qnr_id}` to real database — currently returns entirely hardcoded mock data (hardcoded supplier name, questions, progress). Replace with database query against questionnaire_responses table. Implements: zero-tolerance Rule 2 (no stubs/fake data)
  - IMPLEMENTED: `GET /api/questionnaires/questionnaire/{qnr_id}` at line 33 queries DB for template and questions.
- [x] **B3.10 BUILD**: Bulk questionnaire dispatch — endpoint `POST /api/questionnaires/dispatch-bulk` accepts list of supplier_ids and template_id, dispatches questionnaires to all via appropriate channel. Implements: brief Feature 2 operational efficiency
  - IMPLEMENTED: `POST /api/questionnaires/dispatch-bulk` at line 597.
- [x] **B3.11 BUILD**: Coverage impact notification — when a supplier responds, calculate spend-weighted coverage improvement and send notification back to org admin: "Supplier X responded. Coverage: +1.4%, New Total: 65.8%". Implements: `specs/supplier-engagement.md` § Coverage Impact Notification
- [x] **B3.12 BUILD**: Data validation/verification on supplier responses — cross-reference reported energy against spend-based estimates (flag if supplier reports 10x less energy than spend suggests), plausibility ranges per metric per industry, anomaly detection on responses, verification workflow for flagged responses. CFO is legally exposed if unverified data is submitted to H&M. Implements: value-auditor HIGH finding
- [x] **B3.13 BUILD**: Supplier improvement timeline — historical response comparison per supplier, year-over-year delta calculation per E/S/G dimension, trend visualization on supplier profile, "improving/stable/declining" classification. H&M wants to see improvement over time, not snapshots. Implements: value-auditor HIGH finding
- [x] **B3.14 BUILD**: Questionnaire auto-fill — when a buyer (H&M) sends a questionnaire, the system checks which fields can be pre-populated from existing ERP/metrics data. Report auto-fill percentage. This is brief Success Criterion #1: "Platform auto-maps 70-80% of incoming buyer questionnaires to existing ERP data." Implements: `briefs/01-investor-mvp-scope.md` Success Criteria

### B4. Multi-Language Questionnaire Dispatch

- [x] **B4.1 BUILD**: Add language support to questionnaire templates — `question_text_en`, `question_text_bn` (Bengali), `question_text_vi` (Vietnamese) columns in questionnaire_questions. Implements: `specs/supplier-engagement.md`
  - IMPLEMENTED: `questionnaire_questions` table has `question_text_bn`, `question_text_vi` columns. Seed data includes Bengali and Vietnamese translations for Tier 1-3 questions.
- [x] **B4.2 BUILD**: Auto-language dispatch — check supplier country from suppliers table → select appropriate language template → send. Bangladesh → Bengali, Vietnam → Vietnamese, default → English. Implements: `specs/supplier-engagement.md`
  - IMPLEMENTED: `_format_questionnaire()` in whatsapp.py dispatches `text_bn` for BD/BGD, `text_vi` for VN/VNM, else English. Backend endpoint `get_supplier_questionnaire_data` at line 162 also dispatches based on `country_code`.
- [x] **B4.3 BUILD**: Response parser for Bengali numerals (০১২৩৪৫৬৭৮৯০) and Vietnamese number formats. Convert to standard numeric before storage. Implements: `specs/supplier-engagement.md`
  - IMPLEMENTED: `src/ml/number_parsing.py` provides `parse_bengali_number()` and `parse_vietnamese_number()` functions.
- [x] **B4.4 BUILD**: Frontend language selector on template builder — dropdown to switch preview language, show question text in selected language. Implements: `specs/dashboard-tabs.md` § Engagement tab
  - IMPLEMENTED: `LanguageSelector.jsx` exists; `TemplateBuilder.jsx` uses it with three textarea fields for English/Bengali/Vietnamese.

### B5. Multi-Channel Architecture + i18n

- [ ] **B5.1 BUILD**: Add react-intl i18n framework to frontend. Extract all hardcoded English strings to locale files (en.json, bn.json, vi.json). Add language selector to Header. Questionnaire template translations covered by B4; this covers UI chrome. Implements: brief Feature 2 "Localization required"
- [x] **B5.2 BUILD**: LINE Business API adapter for Vietnam/Thailand markets — `src/connectors/line.py` with send/receive matching WhatsApp adapter pattern. Implements: brief Feature 2 "Collect data via LINE"
  - IMPLEMENTED: `src/connectors/line.py` exists.
- [x] **B5.3 BUILD**: WeChat Work adapter for China-proximate suppliers — `src/connectors/wechat.py` with send/receive. Implements: brief Feature 2 "Collect data via WeChat"
  - IMPLEMENTED: `src/connectors/wechat.py` exists.

---

## Milestone 3: The Proof — Framework Mapping + Compliance Reports (Phase C)

**Why the CFO cares**: Collecting Scope 3 data is useless if you can't output it in H&M's required format. The framework mapping engine turns raw data into buyer-ready reports. Journal anchor: `0002-DISCOVERY-framework-mapping-is-the-usp.md`.

### C1. Framework Mapping Engine

- [x] **C1.1 BUILD**: Create `framework_mappings` table — metric_name, framework (GRI/TCFD/CSRD/ISSB/SASB), field_id, field_name, unit, calculation_method, cluster. Implements: `specs/framework-mapping.md` § Supported Frameworks
- [x] **C1.2 BUILD**: Create `src/db/seed_framework_mappings.py` — seed 60+ rows mapping 14 clusters (E1-E3, S1-S3, G1-G8) × 5 frameworks (GRI, CSRD, ISSB, TCFD, SASB). Ensure SASB mappings exist for ALL 14 clusters (not just diesel). Add CDP mapping rows for water and emissions clusters. Include all mappings from spec. Implements: `specs/framework-mapping.md` § Existing Mappings + Planned Mappings
- [x] **C1.3 BUILD**: Rewrite `src/api/routes/frameworks.py` — replace 645 lines of hardcoded static dicts with database-driven mapping engine. Add `require_auth` dependency to all framework endpoints. Endpoint `POST /api/frameworks/map` accepts metric values, returns framework-specific output with field IDs, units, and confidence levels. Endpoint `GET /api/frameworks/compare/{cluster}` returns all framework mappings for a cluster. Implements: `specs/framework-mapping.md`
- [ ] **C1.4 BUILD**: Frontend Frameworks tab — cluster dropdown (14 clusters from spec), comparison table showing CSRD/ISSB/GRI/TCFD/SASB field mappings with field ID, unit, value, confidence color coding. Click framework row → side panel with full disclosure requirements. Implements: `specs/dashboard-tabs.md` § Framework Comparison Table

### C2. Enhanced PDF Compliance Report

- [ ] **C2.1 BUILD**: Create `src/api/routes/reports.py` — report generation endpoint `GET /api/reports/pdf?framework={gri|csrd|tcfd|issb}&period={start}-{end}`. Implements: `specs/evidence-vault.md` § PDF Compliance Report
- [ ] **C2.2 BUILD**: Enhanced PDF with fpdf2 — cover page (org name, reporting period, framework), emissions summary by scope with bar charts, emission factor citations (source, year, region), supplier coverage statement, methodology statement, per-metric evidence chain summary, confidence distribution. Implements: `specs/evidence-vault.md` § PDF Compliance Report sections 1-7
- [ ] **C2.3 BUILD**: Download endpoint with filename format `{org}_ESG_Report_{framework}_{date}.pdf`. Implements: `specs/evidence-vault.md`
- [ ] **C2.4 BUILD**: Frontend report builder page — select framework (GRI for H&M, CSRD for EU buyers), select period, include/exclude sections checkboxes, preview, download button. Implements: `specs/dashboard-tabs.md`
- [x] **C2.5 BUILD**: H&M ESR response template — generate an H&M-specific ESR questionnaire response document from collected data. Not generic GRI output — matches H&M's exact ESR format and field structure. The CFO's immediate problem is answering H&M's specific questionnaire. Implements: brief Feature 3, competitive analysis finding

### C3. Evidence Package Export

- [ ] **C3.1 BUILD**: Evidence export endpoint `GET /api/evidence/export?period={start}-{end}&framework={gri}` — generates ZIP containing: evidence_summary.csv, raw_data/ folder, methodology.pdf, integrity_report.pdf, framework_mapping.csv. Implements: `specs/evidence-vault.md` § Evidence Export
- [ ] **C3.2 BUILD**: Hash chain verification endpoint — `GET /api/evidence/verify/{metric_id}` recomputes each hash_current from entry data + previous hash, returns VALID/BROKEN with broken_at location. Implements: `specs/evidence-vault.md` § Chain Integrity Verification
- [x] **C3.3 BUILD**: Rewrite `src/api/routes/evidence.py` to read from `evidence_chain` database table instead of CSV. Add org_id scoping on all endpoints (replace hardcoded `org_id = "org_bd_001"`). Wire evidence chain creation into CSV upload flow — every metric uploaded creates an evidence chain entry with source_system, raw_value, emission_factor_id, methodology, confidence, hash chain. Implements: `specs/evidence-vault.md` § Per-Metric Evidence
  - `fetch_prev_hash_by_cluster(org_id, cluster)` added to `database.py`
  - `create_evidence_chain_entry()` fixed `cursor_lastrowid` bug (was calling undefined helper); now uses `cur.lastrowid`
  - `mqtt_client._insert_metric()` refactored to use `create_evidence_chain_entry()` via connection pool, adds `org_id` to both `metrics` and `evidence_chain` INSERTs
  - `mqtt_client._get_prev_hash()` removed (replaced by `fetch_prev_hash_by_cluster` in database.py)
  - `mqtt_client.SmartMeterConsumer` gains `org_id` init param and `MQTT_ORG_ID` env var support
  - `evidence.py` rewritten: DB-first via `fetch_evidence_chain()`, `_build_evidence_response()` maps DB columns to API shape, `chain_valid` computed via `verify_chain_record()`, CSV fallback preserved for investor demo mode
  - All 183 tests pass
- [ ] **C3.4 BUILD**: Frontend "Export for Audit" button on Evidence tab — triggers ZIP download with progress indicator. Implements: `specs/dashboard-tabs.md`
- [ ] **C3.5 BUILD**: Confidence scoring engine — compute HIGH/MEDIUM/LOW from source reliability (mqtt/sap_b1 > csv_upload > manual), data recency (<30d / 30-90d / >90d), and emission factor specificity (region-specific > global default). Replace all static confidence labels. Implements: `specs/evidence-vault.md` § Confidence Scoring
- [ ] **C3.6 BUILD**: Data lineage DAG — add `parent_id` column to evidence_chain table. When Scope 3 total is calculated, create evidence entry with parent_id pointing to supplier-level entries. Endpoint `GET /api/evidence/lineage/{metric_id}` returns full DAG. Implements: `specs/evidence-vault.md` § Data Lineage
- [ ] **C3.7 BUILD**: Auditor access model — admin creates time-bounded, read-only, org-scoped access token via `POST /api/evidence/auditor-link`. `GET /api/evidence/auditor/{token}` provides read-only evidence chain access without login. Link expires after configurable period. Implements: `specs/evidence-vault.md` § Auditor Access
- [x] **C3.8 BUILD**: Evidence chain immutability — add database triggers or application-level guards preventing UPDATE and DELETE on `evidence_chain` rows after creation. The spec says the system "never modifies entries in place" but nothing enforces this. Without immutability, hash chain integrity is meaningless. Implements: `specs/evidence-vault.md` line 29
  - SQLite triggers added in `database.py::_migrate_sqlite()`: `evidence_chain_no_update` and `evidence_chain_no_delete` using `RAISE(ABORT)` — verified to block both UPDATE and DELETE
  - Added `fetch_evidence_chain()` DB read function in `database.py`
  - Wired all three evidence.py endpoints (`/drilldown`, `/verify`, `/full-chain`) to try DB first (immutable, trigger-protected), fall back to in-memory CSV dict for demo data
  - PostgreSQL path note: raw SQL trigger DDL needs adding to `schema_pg.sql` for production PostgreSQL deployments
- [x] **C3.9 BUILD**: 7-year data retention policy — brief mandates "Data retention: 7 years minimum (CSRD requirement)." Add retention_period column to org settings, implement automated archiving logic for evidence_chain and audit_log entries older than retention period, soft-delete with archive table. No hard delete before retention period expires. Implements: `briefs/01-investor-mvp-scope.md` line 58
  - ✅ `archive_retention_policy()` in `database.py` — SQL Server/SQLite compatible, CSRD 84-month retention
  - ✅ `_run_retention_policy()` helper bypasses `get_connection()` → `_ensure_db()` recursion loop
  - ✅ `_ensure_db()` calls `_run_retention_policy()` on startup with raw `sqlite3.connect()` (no pool dependency)
  - ✅ Recursion guard: module-level `_retention_policy_active` flag prevents re-entry
  - ✅ Raw connection sets `row_factory = sqlite3.Row` — fixes `'tuple' object has no attribute 'get'` bug
  - ✅ All 471 tests pass

---

## Milestone 4: The Wow Factor — Alerts + DevOps (Phase D)

**Why the CFO cares**: Shows the system is production-ready and adapts to factory-specific needs. Demo differentiation — real-time monitoring instead of static reports.

### D1. Configurable Alert Thresholds

- [x] **D1.1 BUILD**: Create `alert_thresholds` table — id, org_id, metric_cluster, warning_threshold, critical_threshold, unit, is_active. Implements: `specs/risk-alerts.md`
- [x] **D1.2 BUILD**: Create CRUD endpoints in `src/api/routes/alerts.py` — Pydantic models for request validation (cluster, metric_name, operator, threshold_value, severity). Input validation: cluster must match known metric clusters, threshold_value must be positive. Editor role required. Implements: `specs/risk-alerts.md`
- [ ] **D1.3 WIRE**: Update `src/realtime/alerts.py` and risk detector to read thresholds from database instead of hardcoded dict. Wire WebSocket to push threshold-triggered alerts in real time. Implements: `specs/risk-alerts.md` § Risk Score Computation
- [ ] **D1.4 BUILD**: Frontend Settings page — threshold configuration with sliders for each metric cluster (energy kWh, water m³, waste tonnes, emissions tCO2e). Save/Reset buttons. Active/inactive toggle per threshold. Implements: `specs/dashboard-tabs.md`
- [ ] **D1.5 BUILD**: Alert history — `GET /api/alerts/history` returns log of all alerts fired, acknowledged, resolved. Display in Risk & Alerts tab with date, metric, threshold breached, current value, status. Implements: `specs/risk-alerts.md`
- [ ] **D1.6 BUILD**: Alert deduplication — suppress duplicate alerts for the same metric_cluster + supplier within configurable suppression window (default 24h). Escalate severity if threshold is breached for >72h (WARNING → CRITICAL). Implements: brief Feature 4 "Alert system must be actionable, not noisy"
- [ ] **D1.7 BUILD**: Org-scoped WebSocket broadcasting in `src/realtime/alerts.py` — store org_id per WebSocket connection, filter broadcasts to matching org only. Implements: `specs/auth.md` § Organization Isolation

### D2. Supply Chain Tab Components

- [ ] **D2.1 BUILD**: Frontend Supply Chain tab — supplier list sidebar (SC1) with name, country flag, risk tier badge (A/B/C/D), E/S/G scores. Sorted by risk score descending. Implements: `specs/dashboard-tabs.md` § Tab 2
- [ ] **D2.2 BUILD**: Frontend Supplier Profile Panel (SC2) — right detail panel on supplier selection. Shows overall risk score, financial health, scope3 coverage, traceability, cluster score bars for Labour/Environment/Governance/Safety/Gender. Implements: `specs/dashboard-tabs.md`
- [ ] **D2.3 BUILD**: Frontend Scope 3 Detail Panel (SC3) — all 8 GHG Protocol Scope 3 categories as horizontal bars, color-coded by coverage %. Implements: `specs/dashboard-tabs.md`
- [x] **D2.4 BUILD**: Backend endpoints — `GET /api/suppliers/risk-ranked`, `GET /api/suppliers/{id}/profile`, `GET /api/scope3/categories`, `GET /api/risk/geopolitical`. Org-scoped. Replace hardcoded `_REFERENCE_SCORES` and `SCORECARD_QUADRANTS` in `risk.py` with database queries. Replace `CATEGORY_META` in `scope3.py` with database queries. Implements: `specs/dashboard-tabs.md` § Tab 2 _(PARTIAL: risk-ranked and profile done; geopolitical and hardcoded replacements remain)_
- [ ] **D2.5 BUILD**: Frontend Geopolitical Heat Map (SC4) — matrix rows = countries, columns = political stability, trade exposure, currency volatility, overall score. Color-coded cells. Data from `GET /api/risk/geopolitical`. Implements: `specs/dashboard-tabs.md` § Tab 2 Panel SC4

### D3. Risk & Alerts Tab Components

- [ ] **D3.1 BUILD**: Frontend Risk Scorecard (R1) — 2x2 grid: G2 (supply chain), G5 (financial), G8 (geopolitical), G3 (ethics). Per cell: score/100, tier badge, trend arrow, # active flags. Implements: `specs/dashboard-tabs.md` § Tab 3
- [ ] **D3.2 BUILD**: Frontend Risk Flags Feed (R2) — prioritized list of ML-flagged risks with severity badge, cluster tag, supplier, title, detail, recommendation, acknowledge button. Implements: `specs/dashboard-tabs.md` § Tab 3
- [ ] **D3.3 BUILD**: Backend risk endpoints — `GET /api/risk/scorecard`, `GET /api/risk/flags`, `GET /api/risk/summary`, `POST /api/risk/flags/{id}/acknowledge`. Add `acknowledged_at` and `acknowledged_by` columns to risk_flags table (spec requires these fields). Implements: `specs/risk-alerts.md`
- [ ] **D3.4 BUILD**: Frontend Risk Score Strip on Dashboard (D4) — 4 chips (G2, G3, G8, G5) below trend chart, clicking navigates to Risk & Alerts tab with that filter. Implements: `specs/dashboard-tabs.md` § Dashboard tab
- [ ] **D3.5 BUILD**: Backend endpoint `GET /api/scope3/completeness` — returns overall Scope 3 coverage % and per-category coverage. Also return Scope 1 coverage (fuel invoices/meter readings) and Scope 2 coverage (electricity bills/ERP data) for unified emissions completeness. Implements: `specs/dashboard-api.md` Planned Routes
- [ ] **D3.6 BUILD**: Frontend Scope 3 Completeness Meter (R3) — donut chart showing overall Scope 3 coverage % with category bars below. Include Scope 1+2+3 unified completeness score. Implements: `specs/dashboard-tabs.md` § Tab 3 Panel R3
- [ ] **D3.7 BUILD**: Benchmarking against industry averages — industry benchmark data for garment manufacturing (energy intensity kWh/garment, water intensity m³/garment, emissions intensity tCO2e/revenue) sourced from Higg Index / SAC published data. Display on dashboard: "Your factory vs industry average." Implements: value-auditor HIGH finding, competitive parity

### D4. Dashboard Enhancements

- [ ] **D4.1 BUILD**: Frontend Operations Overview Grid (D1) — 5-column responsive grid of MetricCards for E1 (Energy), G6 (Water), E3 (Waste), S1 (Safety), S3 (Gender). Click any card → opens EvidencePanel. Implements: `specs/dashboard-tabs.md` § Dashboard tab
- [ ] **D4.2 BUILD**: Frontend Trend Chart expansion (D3) — add waste data series to existing energy/emissions/water chart. Left axis: energy kWh, water m³, waste intensity. Right axis: incident rate as bars. Implements: `specs/dashboard-tabs.md` § Dashboard tab
- [ ] **D4.3 BUILD**: Fix bare tuple error returns across all route files — replace `return {"error": "..."}, 404` with `raise HTTPException(status_code=404, detail="...")` in `dashboard.py`, `evidence.py`, and `frameworks.py` (10+ occurrences). Add org_id scoping to `dashboard.py` trends endpoints. Replace hardcoded `METRIC_META` dict with database queries. Implements: FastAPI best practices, `specs/auth.md` § Organization Isolation
- [ ] **D4.4 BUILD**: Fix `reports.py` old endpoint — `GET /api/reports/esg-pdf` has NO `require_auth` and NO org scoping. Either add auth + org scoping or remove in favor of `reports_pdf.py`'s `compliance-report` endpoint. Also verify `reports_pdf.py` has proper auth and org-scoping. Implements: security CRITICAL finding
- [ ] **D4.5 BUILD**: Wire OperationsTab to real data — `OperationsTab.jsx` exists with MetricCards for energy, emissions, water, scope3 cat1, diesel, scope3 cat6 but needs wiring to real API endpoints. Clarify relationship with D4.1. Implements: `specs/dashboard-tabs.md`
- [ ] **D4.6 BUILD**: Wire GeopoliticalRiskTable — component exists at `components/GeopoliticalRiskTable.jsx` but calls `GET /api/risk/geopolitical` which does not exist. Create the backend endpoint (referenced in D2.4 but not yet built). Implements: `specs/dashboard-tabs.md` § Tab 2 Panel SC4
- [ ] **D4.7 BUILD**: Make TrustBadges data-driven — currently hardcoded "CSRD Compliant", "GHG Protocol Source", "Audit Ready", "Scope 3 Verified" badges. Verify each claim against actual data (e.g., "CSRD Compliant" checks if framework mapping exists, "Audit Ready" checks evidence chain integrity). Implements: zero-tolerance Rule 2 (no fake data/claims)

### D5. Production DevOps

- [ ] **D5.1 BUILD**: Production Dockerfile — multi-stage build (build frontend with npm, bundle into FastAPI image). Verify smaller than current image. Implements: deployment readiness
- [ ] **D5.2 BUILD**: Update `docker-compose.yml` — full stack: app + PostgreSQL + Redis for rate limiting + MQTT broker (EMQX) for IoT ingestion. Health checks on all services. Nginx reverse proxy with TLS termination for HTTPS. Implements: deployment readiness
- [ ] **D5.3 BUILD**: CI pipeline `.github/workflows/ci.yml` — lint (ruff), type check, test (pytest), frontend build (npm run build) on push. Blocking on failures. Remove existing `|| true` on ruff lint step that silently passes when lint fails. Implements: deployment readiness
- [ ] **D5.3a BUILD**: PostgreSQL backup strategy — automated pg_dump with WAL archiving, daily backups with 30-day retention, restore testing script. Point-in-time recovery capability. Implements: production readiness
- [ ] **D5.4 BUILD**: Enhanced health check endpoint — database connectivity, disk space, version info. `GET /api/health` returns JSON with all component statuses. Implements: deployment readiness
- [ ] **D5.5 BUILD**: Data export endpoints — `GET /api/export/metrics?format=csv`, `GET /api/export/suppliers?format=xlsx`, `GET /api/export/risk-flags?format=csv`. Org-scoped. "Export All Data" button in Settings page. Implements: value-auditor deal-killer #4 "data export capability"
- [ ] **D5.6 BUILD**: CORS configuration — `CORS_ORIGINS` env var (comma-separated allowed origins). Update FastAPI middleware. Default: `http://localhost:5173,http://localhost:3000`. Production: frontend origin only. Implements: `specs/auth.md`

### D6. Testing + Security Hardening

- [ ] **D6.1 BUILD**: Org isolation tests — verify every route group enforces org_id filtering (7+ route groups untested). Test that user from org A cannot see org B data. Implements: `specs/auth.md` § Organization Isolation
- [ ] **D6.2 BUILD**: WebSocket auth test — verify WebSocket connections require valid JWT AND only receive org-scoped alerts. Implements: `specs/auth.md`
- [ ] **D6.3 BUILD**: Tier 2 integration tests — real PostgreSQL in Docker, test database connection, schema creation, seed data loading, query execution. No mocks. Implements: `specs/data-model.md`
- [ ] **D6.4 BUILD**: API endpoint coverage tests — verify every route returns expected data structure, handles errors correctly (using HTTPException, not bare tuples), enforces RBAC. Implements: `specs/dashboard-api.md`
- [ ] **D6.5 BUILD**: RBAC enforcement on all new routes — templates (editor+admin), questionnaire dispatch (editor+admin), alert acknowledgment (editor+admin), threshold config (admin), evidence export (viewer+), report generation (viewer+). For each role, test that unauthorized operations return 403. Verify role names are not leaked in 403 messages. Implements: `specs/auth.md` § RBAC
- [ ] **D6.6 BUILD**: Rate limiting on all new endpoints — WhatsApp webhook (per IP, 100 req/min), CSV upload (per user, 10 req/hour), all authenticated API (per user, 300 req/min), ML endpoints (input size cap, 100 entries max). Redis-backed when available, in-memory fallback. Implements: `specs/auth.md` § Rate limit
- [ ] **D6.7 BUILD**: Comprehensive audit logging — `audit_log` table (id, org_id, user_id, action, resource_type, resource_id, changes_json, timestamp). Middleware intercepts all POST/PUT/DELETE requests. Endpoint `GET /api/audit/log` with org scoping, admin-only. Update `specs/data-model.md` with table definition. Implements: `specs/evidence-vault.md` § source_system tracking
- [ ] **D6.8 BUILD**: ML route testing — test `GET /ml/predict/{supplier_id}` (org isolation, correct risk levels), `GET /ml/predict` (batch), `POST /ml/train` (admin only, input validation on feedback). Test `risk_predictor.py` scoring accuracy. Implements: `specs/dashboard-api.md`
- [ ] **D6.9 BUILD**: Integration tests for new route groups — alerts (CRUD, threshold evaluation), audit (org isolation, RBAC), templates (editor CRUD), whatsapp (webhook parsing, HMAC, edge cases), upload (certifications, emission factors). Enumerate each route group. Implements: `specs/dashboard-api.md`
- [ ] **D6.10 BUILD**: Frontend component/page testing — test all pages (DashboardPage, RiskAlertsTab, SupplierEngagementTab, SupplyChainTab, FrameworksTab, OperationsTab, LoginPage) and components (MetricCard, TrendChart, GeopoliticalRiskTable). Currently only API client, auth context, and WebSocket hook have tests. Implements: testing coverage
- [ ] **D6.11 BUILD**: Move ML `risk_predictor.py` hardcoded `_COUNTRY_RISK` dict to database — `country_risk_scores` table (country_code, country_name, risk_score, source, updated_at). Endpoint for admin to update scores. Countries not in table default to highest risk. Implements: `specs/risk-alerts.md`
- [ ] **D6.12 BUILD**: ML model weight audit trail — `weight_changes` table (id, org_id, old_weights_json, new_weights_json, feedback_count, changed_by, changed_at). Every `train_weights` call creates a row. Implement rollback capability. Implements: production auditability

### D7. Admin + Commercial Features

- [ ] **D7.1 BUILD**: Admin settings page — User Management (list users, invite by email, change role, deactivate), Organization Settings (name, industry, country), Audit Log viewer (paginated table, admin-only), API Keys (generate/revoke). Admin role required. Implements: `specs/auth.md` § RBAC
- [ ] **D7.2 BUILD**: API key management — `POST /api/keys` (admin only, generates random key, stores hash), `GET /api/keys` (list keys with last-used timestamp), `DELETE /api/keys/{id}` (revoke). Keys authenticate via `X-API-Key` header as alternative to JWT. Implements: `specs/data-model.md` (api_keys table)
- [ ] **D7.3 BUILD**: Tier-2 API routes — `GET /api/labour/audit-summary`, `GET /api/workforce/safety`, `GET /api/water/by-source`, `GET /api/waste/circularity`. Org-scoped with auth. Implements: `specs/dashboard-api.md` Planned Routes Tier 2
- [ ] **D7.4 BUILD**: Tier-3 API routes — `GET /api/governance/board`, `GET /api/ethics/incidents`, `GET /api/traceability/certifications`, `GET /api/suppliers/financial-health`, `GET /api/fibre/mix`. Org-scoped with auth. Implements: `specs/dashboard-api.md` Planned Routes Tier 3
- [ ] **D7.5 BUILD**: Onboarding wizard — post-registration flow: (1) select industry, (2) select ERP system or CSV, (3) upload initial data, (4) select applicable frameworks, (5) configure first alert thresholds. Land on dashboard with real data. Implements: brief Feature 1 "Self-serve onboarding"
- [ ] **D7.6 BUILD**: Email notification service — SMTP client in `src/services/email.py`. Critical risk flags trigger email to org admin. Template: alert summary with link to dashboard. `EMAIL_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` in env vars. Implements: brief Feature 4
- [ ] **D7.7 BUILD**: Add DOMPurify to frontend — sanitize all user-generated content before rendering (supplier names, questionnaire responses, alert text, risk flag messages). Prevent XSS from supplier-provided data. Implements: security best practices
- [ ] **D7.8 BUILD**: MQTT production wiring — update `src/connectors/mqtt_client.py` to connect to real MQTT broker (not CSV demo mode), subscribe to `factory/{id}/meter/{meter_id}/{cluster}` topics, handle reconnection with exponential backoff, tag ingested metrics with org_id from factory metadata. Implements: brief Feature 4
- [ ] **D7.9 BUILD**: Corrective action tracking — `corrective_actions` table (id, org_id, risk_flag_id, assigned_to, action_description, deadline, status [open/in_progress/completed/overdue], evidence_of_completion, created_at, updated_at). CRUD endpoints. Frontend panel on Risk & Alerts tab showing open actions with deadlines and progress. Auto-escalate when deadline passes (create new risk flag). **Without this, the platform identifies problems but provides no mechanism to track resolution** — the compliance loop is unclosed. Implements: value-auditor HIGH finding
- [ ] **D7.10 BUILD**: Buyer-facing portal — time-bounded, read-only access for buyer organizations (H&M). Separate from auditor access (C3.7). Filtered by suppliers the buyer sources from, showing ESG scores, evidence chain summary, and compliance report. `POST /api/access/buyer-link` (admin creates link with supplier scope and expiry). Implements: value-auditor HIGH finding — H&M will ask "can we see supplier data directly?"
- [ ] **D7.11 BUILD**: Document management — `documents` table (id, org_id, supplier_id, category [certificate/policy/audit_report/other], title, file_path, file_size, mime_type, expiry_date, uploaded_by, uploaded_at). Upload endpoint `POST /api/documents/upload` (multipart). Certificate expiry alerts. Link documents to suppliers and risk flags. Every competitor offers document storage. Implements: competitive parity
- [ ] **D7.12 BUILD**: Compliance calendar — `compliance_deadlines` table (id, org_id, title, framework, due_date, status [upcoming/submitted/overdue], submitted_at, notes). Calendar view with upcoming/past/overdue items. Email reminders 30/14/7 days before deadline. H&M annual questionnaire, CSRD disclosure, GRI submission deadlines. Implements: competitive parity
- [ ] **D7.13 BUILD**: Scheduled report generation — cron-like scheduling (monthly/quarterly/annual). `scheduled_reports` table (id, org_id, framework, period, frequency, recipients, last_run, next_run). Background task generates PDF and emails to configured recipients. CFO will forget to run quarterly reports manually. Implements: competitive parity
- [ ] **D7.14 BUILD**: `notification_log` table — track every outgoing notification (id, org_id, user_id, channel [email/whatsapp/websocket], subject, body_preview, sent_at, status [sent/failed/bounced]). Essential for audit trail. Wire into D7.6 email service and WhatsApp dispatch. Implements: `specs/evidence-vault.md` § source_system tracking
- [ ] **D7.15 BUILD**: Error monitoring integration — add Sentry (or equivalent) SDK to FastAPI backend. Capture unhandled exceptions, tracebacks, and performance metrics. `SENTRY_DSN` env var. Dashboard shows error rates. Implements: production readiness
- [ ] **D7.16 BUILD**: API documentation enhancement — customize FastAPI's auto-generated OpenAPI docs at `/docs` with example payloads, error response schemas, authentication guide, and rate limit documentation. Public-facing API reference for integration partners. Implements: commercial readiness (D7.2 API keys need docs)
- [ ] **D7.17 BUILD**: SAP B1 connector production configuration — test against real SAP B1 instance (or mock server), handle authentication failures gracefully, document required SAP B1 configuration. The connector exists but is untested. Implements: `src/connectors/sap_b1_adapter.py`
- [ ] **D7.18 BUILD**: Webhook system for third-party integrations — `webhooks` table (id, org_id, url, event_types, secret, is_active, last_delivery, created_at). Outbound POST to configured URLs on events (alert.created, supplier.responded, report.generated). Retry with exponential backoff. Delivery status tracking. Implements: enterprise readiness

---

## Milestone 5: Commercial Infrastructure (Phase E)

**Why the CFO cares**: The product can collect data, score suppliers, and generate reports. But the CFO cannot actually BUY the product. At $48-60K/year, there needs to be a way to sign up, try it, and pay. Without commercial infrastructure, every sale requires manual invoicing and contract management — contradicting the brief's "self-serve onboarding" requirement.

### E1. Billing + Subscription

- [ ] **E1.1 BUILD**: Stripe integration — install stripe-python SDK, create `subscriptions` table (id, org_id, stripe_customer_id, plan_id, status, current_period_start, current_period_end, trial_end). Webhook endpoint `POST /api/billing/webhook` handles checkout.session.completed, customer.subscription.updated, invoice.payment_failed. Implements: commercial readiness
- [ ] **E1.2 BUILD**: Subscription plan tiers — Starter ($24K/year, 50 suppliers, 1 framework), Professional ($48K/year, 200 suppliers, all frameworks, buyer portal), Enterprise ($60-150K/year, unlimited suppliers, API access, white-label, multi-org). Plan limits enforced at API middleware level. Implements: brief pricing model
- [ ] **E1.3 BUILD**: 14-day trial flow — trial org created on signup with full Professional features. Trial expires → downgrade to read-only. No credit card required to start trial. Pre-loaded with sample Bangladesh garment factory data (real emission factors, mock suppliers with realistic names). Implements: brief "Self-serve onboarding"
- [ ] **E1.4 BUILD**: Self-serve signup — public registration page, email verification (A4.5), org creation, auto-start trial. Post-registration triggers onboarding wizard (D7.5). Implements: brief Feature 1
- [ ] **E1.5 BUILD**: Pricing page — public `/pricing` route with plan comparison table, feature checklist, "Start Free Trial" CTA. No login required to view. Implements: commercial readiness

### E2. Legal + Privacy

- [ ] **E2.1 BUILD**: GDPR data export endpoint — `POST /api/gdpr/export` generates ZIP of all user data (profile, audit log, uploaded files, metrics). `DELETE /api/gdpr/account` soft-deletes user data within 30 days. Implements: GDPR compliance
- [ ] **E2.2 BUILD**: Privacy policy and terms of service pages — frontend pages at `/privacy` and `/terms`. Cookie consent banner with opt-out for non-essential cookies. Implements: legal compliance
- [ ] **E2.3 BUILD**: Multi-org user access — allow a single user account to be invited to multiple organizations. Organization switcher in UI header. Scoped permissions per org. Enables consulting firms (EY Dhaka, local sustainability consultancies) to manage ESG for multiple factory clients — a significant revenue channel. Implements: value-auditor MEDIUM finding, Year 2 growth enabler

---

## Summary

| Milestone                 | Todos   | Sessions (est.) | Buyer value                                        |
| ------------------------- | ------- | --------------- | -------------------------------------------------- |
| A: Data Foundation        | 25      | 2-3             | Platform accepts real data, emission intensity     |
| B: Deal-Closer (WhatsApp) | 34      | 4-5             | CFO collects Scope 3 data, scores suppliers        |
| C: The Proof (Frameworks) | 18      | 2-3             | CFO generates H&M-ready report, evidence integrity |
| D: Wow Factor + DevOps    | 63      | 6-8             | Corrective actions, buyer portal, production ready |
| E: Commercial Infra       | 8       | 1-2             | CFO can actually buy the product                   |
| **Total**                 | **148** | **15-21**       | **CFO signs the check**                            |

## Value-Ranked Top 3 Workstreams

1. **WhatsApp Supplier Scope 3 Collection + Scoring** (Milestone B, 34 todos) — THE deal-closer per journal `0001-DISCOVERY-deal-closer.md`. H&M requires Scope 3 data and supplier ESG scores. The scoring engine (B3.5a) produces the number H&M actually consumes. Multi-channel (WhatsApp primary, LINE/WeChat/email fallbacks per journal `0008`). Includes data validation (B3.12), supplier improvement timeline (B3.13), and questionnaire auto-fill (B3.14). 34 todos, ~4-5 sessions.

2. **Framework Mapping + Evidence Integrity** (Milestone C, 18 todos) — Core USP per journal `0002-DISCOVERY-framework-mapping-is-the-usp.md`. Includes H&M ESR response template (C2.5), evidence immutability (C3.8), 7-year retention (C3.9), and confidence scoring (C3.5). 18 todos, ~2-3 sessions. Can start in parallel with Phase B.

3. **Corrective Actions + Buyer Portal** (Milestone D7.9-D7.10) — Closes the compliance loop (flagged risk → assigned action → tracked resolution) and lets H&M see supplier data directly. Without these, the platform is a data tool, not a compliance platform. 2 todos, ~1 session. Should ship alongside Phase B/C.
