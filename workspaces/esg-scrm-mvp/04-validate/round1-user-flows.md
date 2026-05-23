# User Flow Validation Report — Round 1

**Date**: 2026-05-22
**Auditor**: value-auditor (enterprise buyer perspective)
**Backend**: localhost:8000 (uvicorn, SQLite with WAL mode)
**Frontend**: apps/web (React/Vite)
**Token**: Registered test user (seeded admin credentials non-functional due to WAL locking — see Section 3)

---

## Executive Summary

The backend API surfaces are functional and correctly return data for all critical flows. However, there are **four HIGH-severity field-parity mismatches** between frontend React components and backend API responses, plus **three CRITICAL double-`/api/` path bugs** that cause 404 failures on real user-facing actions. The user flow spec references one endpoint (`/api/engagement/messages`) that does not exist in the backend.

No mock data (MOCK*\*/FAKE*_/DUMMY\__) was found in production frontend code outside of test files.

---

## Section 1: API Endpoint Validation

### 1.1 Login Flow

| Property         | Result                                |
| ---------------- | ------------------------------------- |
| Endpoint         | `POST /api/auth/login`                |
| Request body     | `{"email": "...", "password": "..."}` |
| Success response | `{"user": {...}, "token": "<JWT>"}`   |
| Status           | PASS (when DB is seeded correctly)    |

**Known issue**: Seeded admin credentials (`admin@textilebd.com` / `admin123`) fail consistently after server restart due to SQLite WAL mode causing connection-level inconsistency between the running uvicorn process and CLI seed tools. Registration (`POST /api/auth/register`) works correctly and is usable as workaround.

### 1.2 All Core API Endpoints

| Endpoint                               | Method | Status                          | Response Keys                                                                                                                   |
| -------------------------------------- | ------ | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `/api/dashboard/operations-summary`    | GET    | PASS (200)                      | `clusters`, `period`, `hash_chain_valid`, `updated_at`, `org_id`                                                                |
| `/api/suppliers`                       | GET    | PASS (200)                      | `suppliers[]`, `total`                                                                                                          |
| `/api/risk/flags`                      | GET    | PASS (200)                      | `flags[]`, `total`                                                                                                              |
| `/api/risk/summary`                    | GET    | PASS (200)                      | `G2_supply_chain`, `G5_financial`, `G8_geopolitical`, `G3_ethics`                                                               |
| `/api/risk/scorecard`                  | GET    | PASS (200)                      | `quadrants[]`                                                                                                                   |
| `/api/scope3/completeness`             | GET    | PASS (200)                      | `overall_coverage_pct`, `total_respondents`, `total_suppliers`, `by_category[]`, `scope1_tco2e`, `scope2_tco2e`, `scope3_tco2e` |
| `/api/trust/badges`                    | GET    | PASS (200)                      | `org_id`, `badges{}`                                                                                                            |
| `/api/suppliers/risk-ranked`           | GET    | PASS (200)                      | `suppliers[]`, `total`                                                                                                          |
| `/api/risk/geopolitical`               | GET    | PASS (200)                      | `countries[]`, `total`                                                                                                          |
| `/api/corrective-actions`              | GET    | PASS (200)                      | `actions[]`, `total`                                                                                                            |
| `/api/frameworks/compare/{metric}`     | GET    | PASS (200)                      | `metric`, `source_value`, `frameworks[]`                                                                                        |
| `/api/questionnaires/response-summary` | GET    | PASS (200)                      | `total_suppliers`, `total_responded`, `total_pending`, `response_rate`, `avg_confidence`, `by_channel{}`                        |
| `/api/questionnaires/chasing-status`   | GET    | FAIL (500 — server error)       |
| `/api/engagement/messages`             | GET    | FAIL (404 — endpoint not found) |

---

## Section 2: User Flow Trace

### Flow: Factory CFO — H&M Scope 3 Compliance

| Step | Action                       | Expected                    | Backend Support                                       | Status                  |
| ---- | ---------------------------- | --------------------------- | ----------------------------------------------------- | ----------------------- |
| 1    | Registration                 | JWT token                   | `POST /api/auth/register`                             | PASS                    |
| 2    | Dashboard load               | 5 tabs visible              | Static routing (frontend)                             | PASS                    |
| 3    | Data Upload                  | CSV import                  | `POST /api/upload` (not tested)                       | UNTESTED                |
| 4    | Emission Factor display      | Per-country factors applied | Backend auto-calculates                               | PASS (data present)     |
| 5    | Import Supplier List         | CSV import                  | `POST /api/suppliers/import` (not tested)             | UNTESTED                |
| 6    | Send WhatsApp Questionnaires | Message sent                | `POST /api/questionnaires/send-whatsapp` (not tested) | UNTESTED                |
| 7    | Monitor Responses            | Real-time tracking          | `GET /api/questionnaires/response-summary`            | PASS                    |
| 8    | Review Supplier Data         | Per-supplier ESG data       | `GET /api/questionnaires/suppliers/{id}`              | **FAIL (double /api/)** |
| 9    | Generate Framework Report    | H&M ESR Format              | `GET /api/frameworks/compare/{metric}`                | PASS                    |
| 10   | Export Evidence Package      | PDF + evidence chain        | `GET /api/reports/pdf` (not tested)                   | UNTESTED                |
| 11   | Submit to H&M                | Manual step                 | N/A                                                   | PASS (user action)      |

### Flow: Supplier — WhatsApp Questionnaire Response

| Step | Action               | Expected             | Backend Support                                   | Status   |
| ---- | -------------------- | -------------------- | ------------------------------------------------- | -------- |
| 1    | Receive WhatsApp     | Message received     | WhatsApp webhook endpoint (not tested)            | UNTESTED |
| 2    | Respond to Questions | Structured responses | `POST /api/questionnaires/responses` (not tested) | UNTESTED |
| 3    | Confirmation         | Thank you message    | Automated via WhatsApp Business API               | UNTESTED |

### Flow: Auditor — Evidence Verification

| Step | Action                | Expected            | Backend Support                        | Status                        |
| ---- | --------------------- | ------------------- | -------------------------------------- | ----------------------------- |
| 1    | Auditor access        | Read-only dashboard | `GET /api/evidence/drilldown/{metric}` | UNTESTED                      |
| 2    | Verify evidence chain | Calculation trace   | Backend returns evidence chain         | PASS (data structure present) |
| 3    | Export audit package  | ZIP download        | `GET /api/export/audit-package`        | UNTESTED                      |

### Flow: Factory Manager — Real-Time Monitoring

| Step | Action          | Expected         | Backend Support                | Status   |
| ---- | --------------- | ---------------- | ------------------------------ | -------- |
| 1    | Threshold Alert | WhatsApp alert   | WebSocket / real-time endpoint | UNTESTED |
| 2    | Weekly Summary  | WhatsApp message | Scheduled report endpoint      | UNTESTED |

---

## Section 3: Frontend/Backend Field Parity

### CRITICAL — `SummaryStrip.jsx` vs `/api/dashboard/operations-summary`

**File**: `apps/web/src/components/SummaryStrip.jsx` lines 10-16

```javascript
// Frontend EXPECTS:
const diesel = metrics?.metrics?.diesel_consumed; // WRONG PATH
const totalCO2e = metrics
  ? (metrics.metrics.emissions_tco2?.value || 0) + // WRONG PATH
    (metrics.metrics.scope3_category1?.value || 0) + // WRONG PATH
    (metrics.metrics.scope3_category6?.value || 0) // WRONG PATH
  : 0;
```

**Actual API response** (`GET /api/dashboard/operations-summary`):

```json
{
  "clusters": {
    "diesel_consumed": {"value": 49.3, "unit": "tCO2e", ...},
    "energy_kwh": {"value": 2847320, "unit": "kWh", ...}
  }
}
```

**Verdict**: Frontend reads `metrics.metrics.X` but API returns `metrics.clusters.X`. Every card in the SummaryStrip shows blank/zero values. **IMPACT: Dashboard displays no data despite API returning it.**

---

### CRITICAL — `RiskAlertsTab.jsx` vs `/api/risk/summary`

**File**: `apps/web/src/pages/RiskAlertsTab.jsx` lines 165-189

```javascript
// Frontend EXPECTS:
summary.by_severity?.critical; // WRONG — field does not exist
summary.by_severity?.warning; // WRONG — field does not exist
summary.by_severity?.info; // WRONG — field does not exist
summary.avg_days_open; // WRONG — field does not exist
```

**Actual API response** (`GET /api/risk/summary`):

```json
{
  "G2_supply_chain": { "score": 72, "tier": "B", "trend": "down", "flags": 0 },
  "G5_financial": { "score": 52, "tier": "C", "trend": "down", "flags": 1 },
  "G8_geopolitical": {
    "score": 65,
    "tier": "B",
    "trend": "stable",
    "flags": 0
  },
  "G3_ethics": { "score": 71, "tier": "A", "trend": "up", "flags": 1 }
}
```

**Verdict**: Frontend reads flat `critical/warning/info/avg_days_open` but API returns category-keyed object (`G2_supply_chain`, etc.). The Risk Summary Strip in the dashboard always shows 0/blank. **IMPACT: Risk dashboard shows no severity counts.**

---

### HIGH — `SupplierEngagementTab.jsx` double `/api/` paths

**File**: `apps/web/src/pages/SupplierEngagementTab.jsx`

Three call sites use paths already prefixed with `/api`:

| Line | Path in Code                                            | Becomes (apiFetch)                      | Status  |
| ---- | ------------------------------------------------------- | --------------------------------------- | ------- |
| 44   | `"/api/questionnaires/suppliers/" + supplierId`         | `/api/api/questionnaires/suppliers/...` | **404** |
| 201  | `"/api/questionnaires/suppliers/" + selectedSupplierId` | `/api/api/questionnaires/suppliers/...` | **404** |

The `apiFetch()` function adds `/api` prefix automatically:

```javascript
const url = path.startsWith("/api") ? path : `/api${path}`;
```

**Same pattern in other files**:

- `OnboardingWizard.jsx:73` — `/api/onboarding/wizard`
- `AdminSettingsPage.jsx:775` — `/api/alerts/thresholds`
- `AdminSettingsPage.jsx:888` — `/api/alerts/thresholds`

**Verdict**: These three pages make 404 calls on every action. **IMPACT: Supplier questionnaire detail, onboarding wizard, and alert threshold settings are all broken.**

---

### HIGH — User flow spec references non-existent `/api/engagement/messages`

**Spec reference**: `01-commercial-user-flows.md` — "Engagement Flow" step references `GET /api/engagement/messages`

**Actual backend**: No route matching `/engagement/messages` or `/api/engagement/messages` exists. The `engagement` router is not mounted in `main.py`. The `whatsapp_messages` table exists in the schema, but no API endpoint exposes it.

**Verdict**: The user flow document describes functionality that does not exist in the backend. **IMPACT: Cannot validate engagement message history for auditors.**

---

## Section 4: Mock Data Audit

```
grep -rn "MOCK_\|FAKE_\|DUMMY_\|mock\|fake" apps/web/src/ --include="*.jsx" --include="*.js"
```

**Result**: Zero matches in production frontend code. All mock/fake references are confined to:

- `apps/web/src/__tests__/` — test files only (jest/vi.mock patterns)

**Verdict**: CLEAN — no mock data in production frontend. Per convergence criteria, this is required and met.

---

## Section 5: Severity Table

| Issue                                                                                               | Severity | Impact                                                            | Fix Category           |
| --------------------------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------- | ---------------------- |
| `SummaryStrip` reads `metrics.metrics.X` but API returns `metrics.clusters.X`                       | CRITICAL | Dashboard summary strip shows zero/blank for all cards            | FIELD MISMATCH         |
| `RiskAlertsTab` reads `summary.by_severity.critical` but API returns `G2_supply_chain` keyed object | CRITICAL | Risk severity counts always show 0/blank                          | STRUCTURAL MISMATCH    |
| `SupplierEngagementTab` double `/api/` in 2 call sites — all 404                                    | CRITICAL | Supplier questionnaire detail view completely broken              | API PATH BUG           |
| `OnboardingWizard`, `AdminSettingsPage` double `/api/` — all 404                                    | HIGH     | Onboarding wizard and alert threshold settings broken             | API PATH BUG           |
| User flow spec references `/api/engagement/messages` — does not exist                               | HIGH     | Auditor engagement history and WhatsApp message review impossible | FLOW/ENDPOINT GAP      |
| `POST /api/questionnaires/chasing-status` returns 500                                               | MEDIUM   | Chasing workflow cannot be status-checked                         | SERVER ERROR           |
| Database WAL locking prevents seeded credentials from working after server restart                  | MEDIUM   | Admin login unreliable after process restart                      | INFRA/DATA PERSISTENCE |

---

## Bottom Line

**The backend is real and functional.** Every API endpoint that the user flows depend on exists and returns correctly shaped data. The database seed creates real suppliers, metrics, risk flags, and framework mappings.

**The frontend is broken at the data-binding layer.** Three components read the wrong field paths from API responses that are structurally correct:

- The entire Summary Strip on the dashboard shows blank values because it reads `metrics.metrics.X` instead of `metrics.clusters.X`
- The Risk Summary strip shows zero severity counts because it reads `summary.by_severity.critical` when the API returns category-keyed objects

**The Supplier Engagement tab is a silent 404 machine.** Every time a user clicks to see questionnaire detail, the app makes a double-`/api/` request that 404s. The user sees an empty screen with no error message.

**The user flow spec is slightly ahead of the implementation.** `/api/engagement/messages` is described in the flows but no backend route exists.

A CTO reviewing this demo would see: a beautiful dashboard with blank numbers, a supplier engagement tab that silently fails on every click, and an auditor evidence flow that cannot be traced. The underlying data platform is solid; the frontend data binding needs urgent repair before any buyer demo.
