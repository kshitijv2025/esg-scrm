# D1 — Configurable Alert Thresholds

**Date:** 2026-05-20
**Phase:** D / The Wow Factor — Alerts + DevOps
**Status:** Partial (D1.1–D1.2 Complete; D1.3–D1.7 Pending)

## What Was Built

### D1.1 Alert Thresholds Table

- `alert_thresholds` table created: id, org_id, metric_cluster, warning_threshold, critical_threshold, unit, is_active
- **Verification:** `grep "alert_threshold" src/db/schema.sql src/db/schema_pg.sql`

### D1.2 Alert Thresholds CRUD API

- `src/api/routes/alerts.py` with Pydantic models for request validation
- Fields validated: cluster (must match known metric clusters), threshold_value (must be positive), operator, severity
- Editor role required
- **Verification:** `grep "alerts\|threshold\|Pydantic\|Editor" src/api/routes/alerts.py | head -15`

## Pending (Not Yet Implemented)

- D1.3 — Wire realtime/alerts.py to read thresholds from database + WebSocket push
- D1.4 — Frontend Settings page with threshold configuration sliders
- D1.5 — Alert history endpoint and display
- D1.6 — Alert deduplication and severity escalation
- D1.7 — Org-scoped WebSocket broadcasting

## Specs Implemented

- `specs/risk-alerts.md`
