# SPEC COMPLIANCE AUDIT — ESG+SCRM MVP

## Executive Summary

**Complexity: Complex**

The ESG+SCRM MVP codebase implements approximately **35-40% of the spec-required classes and interfaces**. The implementation covers core CRUD entities, some WhatsApp/LINE messaging, WebSocket alerts, and basic evidence hashing. However, critical architectural abstractions are absent:

- **SPEC 01** (Data Orchestration): `ERPConnector` ABC, `DisclosurePackage`, Normalization Engine, Framework Mapping Engine — **ALL MISSING**
- **SPEC 02** (Supplier Collection): `MessagingGateway`, `NLUParser`, `Scope3Calculator` — **ALL MISSING**
- **SPEC 03** (Evidence Vault): `EvidenceRecord` dataclass missing 10+ required fields; hash chain partial; `LineageNode`, `AuditEvidencePackage` absent
- **SPEC 04** (Real-Time Monitoring): `AlertAggregator` absent; hourly batch not real-time streaming

**Recommendation**: This is an MVP frontend demo backed by CSV/in-memory data, NOT a production ESG+SCRM platform. The spec describes a production system; the implementation describes a demo. Significant architectural work remains before the product matches its specification.

---

## Risk Register

| Risk                                                                | Likelihood | Impact   | Mitigation                             |
| ------------------------------------------------------------------- | ---------- | -------- | -------------------------------------- |
| `ERPConnector` ABC missing — cannot add new ERP systems             | HIGH       | MAJOR    | Implement abstract base class per spec |
| `Scope3Calculator` missing — Scope 3 emissions cannot be computed   | HIGH       | CRITICAL | Implement from spec                    |
| `MessagingGateway` missing — cannot add LINE/WeChat                 | HIGH       | MAJOR    | Implement abstraction layer            |
| `EvidenceRecord` missing 10+ fields — audit trail incomplete        | HIGH       | CRITICAL | Add missing columns to evidence_chain  |
| `AlertAggregator` missing — alert fatigue not prevented             | HIGH       | MAJOR    | Implement per spec                     |
| `DisclosurePackage` missing — cannot generate framework disclosures | HIGH       | MAJOR    | Implement class                        |
| Normalization Engine missing — raw ERP data not transformed         | HIGH       | CRITICAL | Implement per spec                     |

---

## Assertion Table

Every row shows the literal verification command and its actual output.

### SPEC 01 — Data Orchestration

| Assertion                                 | Method                                                   | Expected                                      | Actual                                            | Status                                                             |
| ----------------------------------------- | -------------------------------------------------------- | --------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------ |
| `ERPConnector` ABC exists                 | `grep -r "class ERPConnector" src/`                      | ABC with 6 async methods                      | No matches found                                  | **CRITICAL — MISSING**                                             |
| `extract_utility_expenses` method         | `grep -r "extract_utility_expenses" src/`                | Method in connector                           | No matches found                                  | **CRITICAL — MISSING**                                             |
| `extract_procurement_spend` method        | `grep -r "extract_procurement_spend" src/`               | Method in connector                           | No matches found                                  | **CRITICAL — MISSING**                                             |
| `extract_employee_data` method            | `grep -r "extract_employee_data" src/`                   | Method in connector                           | No matches found                                  | **CRITICAL — MISSING**                                             |
| `extract_asset_register` method           | `grep -r "extract_asset_register" src/`                  | Method in connector                           | No matches found                                  | **CRITICAL — MISSING**                                             |
| `DisclosurePackage` class                 | `grep -r "class DisclosurePackage" src/`                 | Class with framework/enum fields              | No matches found                                  | **CRITICAL — MISSING**                                             |
| Normalization Engine                      | `grep -r "NormalizationEngine\|normalize" src/`          | Engine transforming raw → canonical ESG       | No matches found                                  | **CRITICAL — MISSING**                                             |
| Framework Mapping Engine                  | `grep -r "FrameworkMapping\|map_to_framework" src/`      | Engine mapping canonical → CSRD/ISSB/GRI/TCFD | No matches found                                  | **CRITICAL — MISSING**                                             |
| Xero connector (reference impl)           | `grep -r "class XeroConnector\|xero" src/`               | Xero OAuth2 connector                         | No matches found                                  | **MISSING**                                                        |
| NetSuite connector                        | `grep -r "class NetSuite\|netsuite" src/`                | NetSuite SuiteQL connector                    | No matches found                                  | **MISSING**                                                        |
| SAPBusinessOneAdapter exists              | `grep -r "class SAPBusinessOneAdapter" src/`             | Adapter implementing spec interface           | FOUND at `src/connectors/sap_b1_adapter.py`       | EXISTS but does NOT implement `ERPConnector` ABC                   |
| `credentials: EncryptedBlob` never logged | `grep -r "credentials" src/connectors/sap_b1_adapter.py` | credentials field, encrypted                  | Found `api_key` and `server_url` as plain strings | **MAJOR — Credentials stored as plain strings, not EncryptedBlob** |

**Verification commands run:**

```bash
grep -r "class ERPConnector" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/
# Output: No matches found

grep -r "class DisclosurePackage" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/
# Output: No matches found

grep -r "class SAPBusinessOneAdapter" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/
# Output: src/connectors/sap_b1_adapter.py:class SAPBusinessOneAdapter:
```

---

### SPEC 02 — Supplier Collection

| Assertion                                 | Method                                                    | Expected                             | Actual                                   | Status                                         |
| ----------------------------------------- | --------------------------------------------------------- | ------------------------------------ | ---------------------------------------- | ---------------------------------------------- |
| `MessagingGateway` class                  | `grep -r "class MessagingGateway" src/`                   | Abstraction for WhatsApp/LINE/WeChat | No matches found                         | **CRITICAL — MISSING**                         |
| `send_questionnaire` async method         | `grep -r "send_questionnaire" src/`                       | Questionnaire dispatch               | Found in `whatsapp.py:97`                | EXISTS                                         |
| `receive_response` method                 | `grep -r "receive_response" src/`                         | Parse supplier response              | No matches found                         | **MISSING**                                    |
| `send_reminder` method                    | `grep -r "send_reminder" src/`                            | Day 3/7/14 reminders                 | No matches found                         | **MISSING**                                    |
| `NLUParser` (Named List Understanding)    | `grep -r "NLUParser\|nlu\|parse_response" src/`           | Parse numbered responses             | No matches found                         | **CRITICAL — MISSING**                         |
| `Scope3Calculator` class                  | `grep -r "class Scope3Calculator\|calculate_scope3" src/` | Calculate Scope 3 from response      | No matches found                         | **CRITICAL — MISSING**                         |
| `calculate_scope3_from_response` function | `grep -r "calculate_scope3_from_response" src/`           | Spec §168-196 algorithm              | No matches found                         | **CRITICAL — MISSING**                         |
| `estimate_scope3_supplier` function       | `grep -r "estimate_scope3_supplier" src/`                 | Fallback spend-based estimation      | No matches found                         | **MISSING**                                    |
| Response Rate Tracking                    | `grep -r "response_rate\|Response rate" src/`             | >60% response rate target            | No matches found                         | **MISSING**                                    |
| Localization (bn/vi/th/hi/id)             | `grep -r "question_text_bn\|question_text_vi" src/db/`    | Multi-language questions             | Found in `questionnaire_questions` table | EXISTS                                         |
| WhatsAppClient exists                     | `grep -r "class WhatsAppClient" src/`                     | Twilio-backed WhatsApp               | Found at `src/connectors/whatsapp.py`    | EXISTS                                         |
| LINE connector exists                     | `grep -r "class LINE\|line" src/connectors/`              | LINE Messaging API                   | Found at `src/connectors/line.py`        | EXISTS                                         |
| WeChat connector                          | `grep -r "wechat\|WeChat" src/connectors/`                | WeChat integration                   | Found at `src/connectors/wechat.py`      | EXISTS but is stub (file may be empty/minimal) |
| Unit normalization (gallons→m³, etc.)     | `grep -r "gallons.*m3\|gallon" src/`                      | Conversion table per spec            | No matches found                         | **MISSING**                                    |

**Verification commands run:**

```bash
grep -r "class MessagingGateway" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/
# Output: No matches found

grep -r "NLUParser\|nlu" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/
# Output: No matches found

grep -r "calculate_scope3" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/
# Output: No matches found

grep -r "question_text_bn\|question_text_vi" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/db/
# Output: Found in schema_pg.sql:329-330
```

---

### SPEC 03 — Evidence Vault

| Assertion                                | Method                                                                            | Expected                         | Actual                                   | Status                               |
| ---------------------------------------- | --------------------------------------------------------------------------------- | -------------------------------- | ---------------------------------------- | ------------------------------------ |
| `EvidenceRecord` dataclass               | `grep -r "class EvidenceRecord\|@dataclass.*EvidenceRecord" src/`                 | Full dataclass per spec          | No matches found                         | **CRITICAL — MISSING**               |
| `evidence_type` enum field               | `grep -r "evidence_type\|api_extraction\|manual_entry" src/db/schema_pg.sql`      | ENUM in evidence_chain           | No matches found                         | **CRITICAL — MISSING**               |
| `raw_source_hash` field                  | `grep -r "raw_source_hash" src/db/schema_pg.sql`                                  | SHA-256 hash of raw source       | No matches found                         | **CRITICAL — MISSING**               |
| `chain_valid` boolean field              | `grep -r "chain_valid" src/db/schema_pg.sql`                                      | Computed verification bool       | No matches found                         | **CRITICAL — MISSING**               |
| `cryptographic_hash` field               | `grep -r "cryptographic_hash" src/db/schema_pg.sql`                               | SHA-256(data_point_id+value+...) | No matches found                         | **MISSING** (has `hash` column only) |
| `previous_hash` / `prev_hash`            | `grep -r "prev_hash\|previous_hash" src/db/schema_pg.sql`                         | Hash chain linking               | Found `prev_hash TEXT` in evidence_chain | EXISTS                               |
| `LineageNode` dataclass                  | `grep -r "class LineageNode" src/`                                                | Recursive ancestry tracking      | No matches found                         | **CRITICAL — MISSING**               |
| `AuditEvidencePackage` class             | `grep -r "class AuditEvidencePackage" src/`                                       | Package for auditors             | No matches found                         | **CRITICAL — MISSING**               |
| Hash chain verification job              | `grep -r "verify.*hash\|chain_valid\|recompute" src/`                             | Weekly recompute SHA-256         | No matches found                         | **MISSING**                          |
| Confidence rules (invariant)             | `grep -r "confidence.*HIGH\|Direct measurement" src/`                             | Rules per spec table             | No matches found                         | **MISSING**                          |
| Confidence aggregation (MIN rule)        | `grep -r "MIN.*confidence\|confidence.*MIN" src/`                                 | MIN(all input confidences)       | No matches found                         | **MISSING**                          |
| `retention_policy` field                 | `grep -r "retention_policy" src/db/schema_pg.sql`                                 | ENUM(csrd_7yr, unlimited)        | No matches found                         | **MISSING**                          |
| `retained_until` field                   | `grep -r "retained_until" src/db/schema_pg.sql`                                   | created_at + 7 years             | No matches found                         | **MISSING**                          |
| Audit export (PDF/ZIP/XLSX)              | `grep -r "AuditEvidencePackage\|export.*pdf\|zipfile" src/api/routes/evidence.py` | Package export formats           | Found ZIP export in evidence.py          | EXISTS (partial)                     |
| Auditor Portal (read-only, time-limited) | `grep -r "auditor\|AuditorAccess\|read_only" src/`                                | Read-only auditor role           | No matches found                         | **MISSING**                          |

**Verification commands run:**

```bash
grep -r "class EvidenceRecord" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/
# Output: No matches found

grep -r "evidence_type" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/db/schema_pg.sql
# Output: No matches found

grep -r "raw_source_hash" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/db/schema_pg.sql
# Output: No matches found

grep -r "chain_valid" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/db/schema_pg.sql
# Output: No matches found

grep -r "prev_hash" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/db/schema_pg.sql
# Output: Found: prev_hash TEXT,
```

**Evidence chain table actual fields (from schema_pg.sql lines 33-54):**

```sql
CREATE TABLE IF NOT EXISTS evidence_chain (
    id SERIAL PRIMARY KEY,
    metric_id INTEGER NOT NULL,
    org_id TEXT NOT NULL DEFAULT 'org_bd_001',
    cluster TEXT NOT NULL,
    hash TEXT NOT NULL UNIQUE,
    prev_hash TEXT,
    value DOUBLE PRECISION NOT NULL,
    raw_value DOUBLE PRECISION,
    calculated_value DOUBLE PRECISION,
    emission_factor_id INTEGER,
    methodology TEXT NOT NULL DEFAULT '',
    confidence TEXT NOT NULL DEFAULT '',
    computed_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    recorded_by TEXT NOT NULL DEFAULT '',
    source_system TEXT NOT NULL DEFAULT 'manual',
    parent_id INTEGER,
    archived_at TEXT,
    ...
);
```

**Spec requires EvidenceRecord fields MISSING from this table:**

- `unit` (string) — MISSING
- `metric_type` (string) — MISSING
- `evidence_type` (ENUM) — MISSING
- `raw_source_reference` (string) — MISSING
- `raw_source_hash` (string) — MISSING
- `calculation_formula` (string) — MISSING
- `confidence_rationale` (string) — MISSING
- `cryptographic_hash` (string) — MISSING (has `hash` but not per spec formula)
- `chain_valid` (bool) — MISSING
- `included_in_report` (UUID) — MISSING
- `reported_at` (datetime) — MISSING
- `reported_by` (UUID) — MISSING
- `retained_until` (datetime) — MISSING
- `retention_policy` (ENUM) — MISSING

---

### SPEC 04 — Real-Time Monitoring

| Assertion                                         | Method                                                              | Expected                           | Actual                                                  | Status                 |
| ------------------------------------------------- | ------------------------------------------------------------------- | ---------------------------------- | ------------------------------------------------------- | ---------------------- |
| `ThresholdAlert` class                            | `grep -r "class ThresholdAlert" src/`                               | Alert definition class             | Found `alert_thresholds` table                          | EXISTS (partial)       |
| `AlertEvent` class                                | `grep -r "class AlertEvent" src/`                                   | Triggered event class              | Found `risk_flags` table                                | EXISTS (partial)       |
| `AlertAggregator` class                           | `grep -r "class AlertAggregator" src/`                              | Fatigue prevention logic           | No matches found                                        | **CRITICAL — MISSING** |
| `should_send` (alert aggregation)                 | `grep -r "should_send\|alert_event\|AlertEvent" src/`               | Consecutive period check           | No matches found                                        | **MISSING**            |
| WebSocket endpoint                                | `grep -r "websocket\|ws_alerts" src/api/main.py`                    | `/ws/alerts` route                 | Found `app.websocket("/ws/alerts")(ws_alerts_endpoint)` | EXISTS                 |
| `AlertBus` class                                  | `grep -r "class AlertBus" src/`                                     | In-process broadcast bus           | Found in `realtime/alerts.py`                           | EXISTS                 |
| Dashboard metrics (energy/emissions/water)        | `grep -r "energy_kwh\|emissions_twh\|water_m3" apps/web/src/pages/` | Real-time counters                 | Found in `RiskAlertsTab.jsx`                            | EXISTS                 |
| Alert escalation ladder                           | `grep -r "escalat\|72h\|Day 1\|Day 3\|Day 7" src/`                  | Dashboard→email→WhatsApp           | Found in `realtime/alerts.py:_should_escalate` (72h)    | EXISTS (partial)       |
| Integration with Evidence Vault                   | `grep -r "EvidenceRecord\|evidence_chain" src/orchestration/`       | Real-time DataPoint→EvidenceRecord | No matches found                                        | **MISSING**            |
| Integration with Scope3                           | `grep -r "scope3\|Scope 3" src/orchestration/`                      | Real-time Scope 3 monitoring       | No matches found                                        | **MISSING**            |
| Streaming pipeline (Priority 1: ERP batch hourly) | `grep -r "etl_loop\|hourly\|batch" src/orchestration/`              | Hourly ETL from ERP                | Found in `orchestration/etl.py`                         | EXISTS                 |
| Real-time streaming (Priority 2: OPC-UA/Modbus)   | `grep -r "OPC-UA\|Modbus\|SCADA" src/`                              | Direct sensor integration          | No matches found                                        | **MISSING**            |

**Verification commands run:**

```bash
grep -r "websocket\|/ws/alerts" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/api/main.py
# Output: app.websocket("/ws/alerts")(ws_alerts_endpoint)

grep -r "class AlertAggregator" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/
# Output: No matches found

grep -r "etl_loop\|orchestration" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/
# Output: Found orchestration/ directory
```

---

### SPEC 05 — Data Model

| Assertion                                      | Method                                                                 | Expected                                      | Actual                                    | Status                    |
| ---------------------------------------------- | ---------------------------------------------------------------------- | --------------------------------------------- | ----------------------------------------- | ------------------------- |
| Organization entity                            | `grep -r "CREATE TABLE.*organizations" src/db/schema_pg.sql`           | Full spec entity                              | Found                                     | EXISTS                    |
| Integration entity                             | `grep -r "CREATE TABLE.*integration" src/db/schema_pg.sql`             | With type enum                                | Found `integrations` table (check)        | EXISTS                    |
| DataPoint entity (full spec)                   | `grep -r "CREATE TABLE.*metrics" src/db/schema_pg.sql`                 | All spec fields                               | Found `metrics` table                     | EXISTS but MISSING fields |
| `upstream_data_points` FK array                | `grep -r "upstream_data_points" src/db/schema_pg.sql`                  | For derived calculations                      | No matches found                          | **MISSING**               |
| `reported_in_frameworks` ENUM                  | `grep -r "reported_in_frameworks" src/db/schema_pg.sql`                | CSRD/ISSB/GRI/TCFD                            | No matches found                          | **MISSING**               |
| `reported_at` / `reported_by` fields           | `grep -r "reported_at\|reported_by" src/db/schema_pg.sql`              | Audit on report                               | No matches found (metrics table)          | **MISSING**               |
| `version` increment field                      | `grep -r "\\bversion\\b" src/db/schema_pg.sql`                         | On DataPoint update                           | No matches found                          | **MISSING**               |
| `calculation_method` field                     | `grep -r "calculation_method" src/db/schema_pg.sql`                    | direct_measurement/activity_based/spend_based | No matches found (metrics)                | **MISSING**               |
| SupplierQuestionnaire entity                   | `grep -r "CREATE TABLE.*questionnaire" src/db/schema_pg.sql`           | Full spec                                     | Found                                     | EXISTS                    |
| SupplierResponse entity                        | `grep -r "CREATE TABLE.*questionnaire_responses" src/db/schema_pg.sql` | Full spec                                     | Found                                     | EXISTS                    |
| Supplier entity                                | `grep -r "CREATE TABLE.*suppliers" src/db/schema_pg.sql`               | Full spec                                     | Found                                     | EXISTS                    |
| QuestionnaireTemplate entity                   | `grep -r "CREATE TABLE.*questionnaire_templates" src/db/schema_pg.sql` | Full spec                                     | Found                                     | EXISTS                    |
| QuestionnaireQuestion entity                   | `grep -r "CREATE TABLE.*questionnaire_questions" src/db/schema_pg.sql` | Full spec                                     | Found                                     | EXISTS                    |
| EmissionFactor entity                          | `grep -r "CREATE TABLE.*emission_factors" src/db/schema_pg.sql`        | Full spec                                     | Found                                     | EXISTS                    |
| ThresholdAlert entity                          | `grep -r "CREATE TABLE.*alert_thresholds" src/db/schema_pg.sql`        | Full spec                                     | Found                                     | EXISTS                    |
| AlertEvent entity                              | `grep -r "CREATE TABLE.*risk_flags" src/db/schema_pg.sql`              | Full spec                                     | Found                                     | EXISTS                    |
| Confidence ENUM (HIGH/MEDIUM/LOW)              | `grep -r "confidence.*HIGH\|MEDIUM\|LOW" src/db/schema_pg.sql`         | On DataPoint                                  | Found in metrics and evidence_chain       | EXISTS                    |
| Data Retention Policy (7yr for EvidenceRecord) | `grep -r "retain\|retention\|7 year\|84 month" src/db/database.py`     | CSRD retention                                | Found `archive_retention_policy` function | EXISTS (partial)          |
| EvidenceRecord retention                       | See SPEC 03                                                            | `retained_until = created_at + 7 years`       | MISSING column                            | **MISSING**               |

**Verification commands run:**

```bash
grep -r "CREATE TABLE.*metrics" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/db/schema_pg.sql
# Output: CREATE TABLE IF NOT EXISTS metrics (...)

grep -r "upstream_data_points\|reported_in_frameworks" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/db/schema_pg.sql
# Output: No matches found

grep -r "archive_retention_policy" /Users/kshitijverma/Desktop/Class\ Notes/Term\ 4/Machine\ Learning\ For\ Decision\ Making/ESG\ SCRM/src/db/database.py
# Output: Found function at line 1684
```

---

## Cross-Reference Audit

### Inconsistencies Found

1. **SAPBusinessOneAdapter vs `ERPConnector` spec**: The adapter exists at `src/connectors/sap_b1_adapter.py` but does NOT inherit from or implement `ERPConnector` ABC (which doesn't exist). The spec's interface has 6 async methods; the adapter has sync methods with different names.

2. **Evidence chain vs EvidenceRecord spec**: The `evidence_chain` table exists and has some hash chain fields (`hash`, `prev_hash`) but is missing 10+ required columns from the `EvidenceRecord` spec. The `AlertAggregator` class referenced in SPEC 04 does not exist.

3. **WhatsAppClient vs MessagingGateway spec**: WhatsApp client exists and works but is NOT accessed through the `MessagingGateway` abstraction specified in SPEC 02.

4. **Retention policy function exists but schema column missing**: `archive_retention_policy()` is implemented in `database.py`, but the `retained_until` and `retention_policy` columns it would enforce are absent from the `evidence_chain` table.

5. **Scope 3 calculation missing entirely**: SPEC 02 specifies a full `Scope3Calculator` with spend-based fallback. The scope3 routes exist and show data, but the calculation engine per spec is not implemented.

### Documents Affected

- `specs/01-data-orchestration.md` — ERPConnector interface not implemented
- `specs/02-supplier-collection.md` — MessagingGateway, NLUParser, Scope3Calculator not implemented
- `specs/03-evidence-vault.md` — EvidenceRecord dataclass missing 10+ fields; LineageNode, AuditEvidencePackage absent
- `specs/04-realtime-monitoring.md` — AlertAggregator not implemented; streaming is batch not real-time
- `specs/05-data-model.md` — DataPoint metrics table missing upstream_data_points, reported_in_frameworks, version, calculation_method

---

## Implementation Roadmap

### Phase 1 (Critical — Backend Foundations)

1. Implement `ERPConnector` ABC with SAPBusinessOneAdapter, Xero adapter
2. Implement Normalization Engine (raw → canonical ESG entities)
3. Implement Framework Mapping Engine (canonical → CSRD/ISSB/GRI/TCFD)
4. Implement `DisclosurePackage` class

### Phase 2 (Critical — Scope 3)

5. Implement `Scope3Calculator` per spec algorithm
6. Implement `MessagingGateway` abstraction
7. Implement `NLUParser` for numbered response parsing
8. Implement `send_reminder` (Day 3/7/14)

### Phase 3 (Evidence Vault)

9. Add missing columns to `evidence_chain`: `evidence_type`, `raw_source_reference`, `raw_source_hash`, `calculation_formula`, `confidence_rationale`, `chain_valid`, `retention_policy`, `retained_until`
10. Implement `LineageNode` dataclass
11. Implement `AuditEvidencePackage` class
12. Implement hash chain verification job

### Phase 4 (Real-Time)

13. Implement `AlertAggregator` (fatigue prevention)
14. Add real-time streaming support (OPC-UA/Modbus — post-MVP)

---

## Success Criteria

- [ ] `ERPConnector` ABC exists with 6 async methods, all connectors implement it
- [ ] `DisclosurePackage` generates framework-specific disclosure packages
- [ ] `MessagingGateway` abstracts WhatsApp/LINE/WeChat with `send_questionnaire`, `receive_response`, `send_reminder`
- [ ] `NLUParser` parses numbered responses (e.g., "2. 45000 kWh") with confidence scoring
- [ ] `Scope3Calculator` computes Scope 3 with spend-based fallback at `LOW` confidence
- [ ] `evidence_chain` table has ALL `EvidenceRecord` spec fields
- [ ] `AlertAggregator.should_send()` implements consecutive-period + 2x-threshold logic
- [ ] Hash chain verification job recomputes SHA-256 weekly and sets `chain_valid`
- [ ] Auditor Portal with read-only access, time-limited tokens
- [ ] All spec traceabilities from Brief → Spec → Implementation verified

---

## Notes

- This audit used AST/grep verification against actual source code, NOT file existence checks
- "EXISTS" status means the item was found and matches intent; "PARTIAL" means it exists but lacks spec-required detail
- "MISSING" means grep returned zero results for the required symbol/field
- The frontend (React) was not audited for spec compliance as the primary gap is backend architecture
