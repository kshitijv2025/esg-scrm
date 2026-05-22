# B3 — Supplier Response Dashboard

**Date:** 2026-05-20
**Phase:** B / Deal-Closer — WhatsApp Supplier Collection
**Status:** Complete

## What Was Built

### B3.1 Response Dashboard Backend

- `GET /api/questionnaires/response-summary` — aggregated stats
- `GET /api/questionnaires/non-responders` — list of non-responding suppliers
- `GET /api/questionnaires/responses/{supplier_id}` — individual responses
- `POST /api/questionnaires/resend` — send reminder to non-responders
- **Verification:** `grep "response-summary\|non-responders\|resend" src/api/routes/questionnaires.py`

### B3.2 Engagement Tab Response Tracker

- Visual progress bar: "8/20 responded, 65% spend coverage"
- Non-responder action panel with "Send Reminder" and "Mark as Manual Entry" buttons
- **Verification:** `grep "response.*tracker\|Send Reminder\|Manual Entry" apps/web/src/pages/SupplierEngagementTab.jsx`

### B3.3 Response Detail View

- Per-supplier parsed data with confidence indicators (HIGH/MEDIUM/LOW color coding)
- **Verification:** `grep "confidence.*HIGH\|confidence.*LOW\|response.*detail" apps/web/src/pages/SupplierEngagementTab.jsx`

### B3.4 Spend-Weighted Coverage Calculator

- Spend-weighted coverage: total `annual_spend_usd` of responding suppliers / total `annual_spend_usd` of all suppliers
- Headcount-based coverage as secondary metric
- Target: 60% coverage by spend
- **Verification:** `grep "spend.*weight\|coverage.*spend\|coverage_pct" src/api/routes/questionnaires.py`

### B3.5 Supplier Scorecard Wired

- `GET /api/suppliers/{id}/profile` returns E/S/G dimension scores from actual responses
- **Verification:** `grep "suppliers.*profile\|E/S/G\|dimension.*score" src/api/routes/suppliers.py`

### B3.5a Supplier ESG Scoring Engine

- Weighted scoring: E/S/G dimensions from Tier 1-4 questionnaire responses
- Each response maps to 0-100 scale per dimension
- Composite score stored in `suppliers.esg_score`
- `risk_tier` computed: A≥80, B≥60, C≥40, D<40
- `GET /api/suppliers/{id}/score` returns dimension breakdown
- **Verification:** `grep "esg_score\|risk_tier\|dimension.*score\|suppliers.*score" src/api/routes/suppliers.py`

### B3.6 Manual Data Entry

- Frontend form to enter questionnaire responses on behalf of supplier
- Stores with `channel="manual"` and `confidence=LOW`
- **Verification:** `grep "manual.*entry\|channel.*manual\|confidence.*LOW" apps/web/src/`

### B3.7 Chasing Workflow

- Automated escalation: WhatsApp at day 0, email at day 7, flag at day 14
- Auto-generated risk flag for non-responsive suppliers
- `GET /api/questionnaires/chasing-status` and `POST /api/questionnaires/chase`
- **Verification:** `grep "chasing-status\|day.*7\|day.*14\|non-responsive" src/api/routes/questionnaires.py`

### B3.8 WhatsApp Preview Endpoint ✓ (already recorded)

- `GET /api/questionnaires/whatsapp-preview/{supplier_id}` at line 299
- Returns questionnaire preview data for a given supplier
- **Verification:** `grep "whatsapp-preview" src/api/routes/questionnaires.py`

### B3.9 Questionnaire DB Wiring ✓ (already recorded)

- `GET /api/questionnaires/questionnaire/{qnr_id}` queries DB for template and questions
- Replaces hardcoded mock data
- **Verification:** `grep "questionnaire.*qnr_id\|fetch.*template" src/api/routes/questionnaires.py`

### B3.10 Bulk Dispatch ✓ (already recorded)

- `POST /api/questionnaires/dispatch-bulk` at line 597
- Accepts list of supplier_ids and template_id
- **Verification:** `grep "dispatch-bulk" src/api/routes/questionnaires.py`

### B3.11 Coverage Impact Notification

- When supplier responds, calculate spend-weighted coverage improvement
- Sends notification to org admin
- **Verification:** `grep "coverage.*notif\|coverage.*improvement\|+.*%" src/api/routes/questionnaires.py`

### B3.12 Data Validation / Anomaly Detection

- Cross-reference reported energy against spend-based estimates (flag if 10x差异)
- Plausibility ranges per metric per industry
- Anomaly detection on responses
- Verification workflow for flagged responses
- **Verification:** `grep "anomaly\|plausibility\|flag.*energy\|spend.*estimate" src/api/routes/questionnaires.py`

### B3.13 Supplier Improvement Timeline

- Historical response comparison per supplier
- Year-over-year delta per E/S/G dimension
- Trend visualization: improving/stable/declining
- **Verification:** `grep "improvement.*timeline\|yoy.*delta\|trend\|historical.*response" src/api/routes/questionnaires.py`

### B3.14 Questionnaire Auto-Fill

- System checks which fields can be pre-populated from existing ERP/metrics data
- Reports auto-fill percentage
- **Verification:** `grep "auto.*fill\|pre-populate\|erp.*data\|auto_fill" src/api/routes/questionnaires.py`

## Specs Implemented

- `specs/supplier-engagement.md` § Coverage Stats, Coverage Calculation
- `specs/dashboard-tabs.md` § Engagement tab, Supplier Profile Panel
- Brief Success Criteria
