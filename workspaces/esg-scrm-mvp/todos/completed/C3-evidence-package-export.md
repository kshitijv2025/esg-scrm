# C3 — Evidence Package Export

**Date:** 2026-05-20
**Phase:** C / The Proof — Framework Mapping + Compliance Reports
**Status:** Complete

## What Was Built

### C3.1 Evidence Export Endpoint

- `GET /api/evidence/export?period={start}-{end}&framework={gri}`
- Generates ZIP containing:
  - evidence_summary.csv
  - raw_data/ folder
  - methodology.pdf
  - integrity_report.pdf
  - framework_mapping.csv
- **Verification:** `grep "export_evidence\|evidence/export\|zipfile\|ZIP" src/api/routes/evidence.py | head -10`

### C3.2 Hash Chain Verification Endpoint

- `GET /api/evidence/verify/{metric_type}` — recomputes each hash_current from entry data + previous hash
- Returns VALID/BROKEN with broken_at location
- **Verification:** `grep "verify_chain\|chain_valid\|broken_at\|verify.*metric" src/api/routes/evidence.py`

### C3.3 Evidence DB-First Architecture

- `src/api/routes/evidence.py` reads from `evidence_chain` database table (not CSV)
- All endpoints have org_id scoping (replaces hardcoded `org_id = "org_bd_001"`)
- CSV fallback retained for demo/investor mode
- `fetch_prev_hash_by_cluster(org_id, cluster)` added to database.py
- `create_evidence_chain_entry()` wired to mqtt_client
- **Verification:** `grep "fetch_evidence_chain\|evidence_chain\|org_id" src/api/routes/evidence.py | head -10`

### C3.4 Frontend Export for Audit Button

- `EvidencePanel.jsx` updated with period input, framework dropdown, "Export for Audit" button
- `apiExport()` utility added to `client.js` for binary blob downloads
- **Verification:** `grep "Export.*Audit\|apiExport\|evidence.*export" apps/web/src/components/EvidencePanel.jsx apps/web/src/api/client.js`

### C3.5 Confidence Scoring Engine

- `compute_confidence()` in `src/evidence/hash_chain.py`
- HIGH≥0.85, MEDIUM≥0.60, LOW<0.60
- Computed from: source reliability (mqtt/sap_b1 > csv_upload > manual), data recency (<30d / 30-90d / >90d), emission factor specificity
- Dynamic `confidence_score` and `confidence_reasons` in API response
- **Verification:** `grep "compute_confidence\|confidence_score\|confidence_reasons" src/evidence/hash_chain.py src/api/routes/evidence.py`

### C3.6 Data Lineage DAG

- `parent_id` column in evidence_chain table
- `GET /api/evidence/lineage/{data_point_id}` returns full DAG
- `_build_dag_from_records()` builds lineage via parent_id references
- **Verification:** `grep "lineage\|parent_id\|dag\|data_point_id" src/api/routes/evidence.py | head -10`

### C3.7 Auditor Access Model

- `POST /api/evidence/auditor-link` — creates time-bounded, read-only, org-scoped access token
- `GET /api/evidence/auditor/{token}` — read-only evidence access without login
- `auditor_router` isolated from app-level `require_auth`
- URL-safe 32-byte random tokens via `secrets.token_urlsafe(32)`
- Expired tokens → HTTP 410, invalid tokens → HTTP 404
- **Verification:** `grep "auditor_link\|auditor.*token\|auditor_router\|require_auth" src/api/routes/evidence.py | head -10`

### C3.8 Evidence Chain Immutability

- SQLite triggers: `evidence_chain_no_update` and `evidence_chain_no_delete` using `RAISE(ABORT)`
- PostgreSQL path noted (raw SQL trigger DDL needs adding to schema_pg.sql for production)
- All three evidence.py endpoints (drilldown, verify, full-chain) try DB first (immutable, trigger-protected), fall back to in-memory CSV dict for demo data
- **Verification:** `grep "evidence_chain_no_update\|evidence_chain_no_delete\|RAISE.*ABORT\|immutab" src/db/database.py`

### C3.9 7-Year Data Retention Policy

- `archive_retention_policy()` in `database.py` — SQL Server/SQLite compatible, CSRD 84-month retention
- `_run_retention_policy()` helper bypasses `get_connection()` → `_ensure_db()` recursion loop
- Recursion guard: module-level `_retention_policy_active` flag
- Soft-delete with archive table — no hard delete before retention period expires
- **Verification:** `grep "archive_retention\|retention_policy\|84.*month\|7.*year\|soft.*delete" src/db/database.py`

## Specs Implemented

- `specs/evidence-vault.md` § Evidence Export, Chain Integrity Verification, Per-Metric Evidence, Confidence Scoring, Data Lineage, Auditor Access
- `specs/dashboard-tabs.md` § Evidence tab
- Briefs/01-investor-mvp-scope.md line 58
