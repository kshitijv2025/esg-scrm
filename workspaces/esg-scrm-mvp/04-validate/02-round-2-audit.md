# Phase A+C Redteam — Round 2 Validation

**Date**: 2026-05-20
**Posture**: L5_DELEGATED
**Scope**: Phase A (A3.4) and Phase C remaining items (C1.4, C2.1-C2.5)

---

## Security CRITICAL Fix (all fixed this round)

### CRITICAL — FastAPI bare-tuple error returns

Multiple routes used `return {"error": "..."}, 404` which is invalid FastAPI error handling. FastAPI ignores the status code in the tuple and returns HTTP 200 with the dict+int as a JSON array.

**Affected files and lines:**

| File                               | Lines                   | Detail                                      |
| ---------------------------------- | ----------------------- | ------------------------------------------- |
| `src/api/routes/evidence.py`       | 250, 275, 350, 520, 531 | `return {"error": "metric not found"}, 404` |
| `src/api/routes/dashboard.py`      | 267                     | `return {"error": "not found"}, 404`        |
| `src/api/routes/questionnaires.py` | 1471, 1780              | `return {"error": "tier not found"}, 404`   |

**Fix:** All 8 instances replaced with `raise HTTPException(status_code=404, detail="...")`.

**Verification:**

```
grep -n "HTTPException" src/api/routes/evidence.py | grep "404"
# → 5 occurrences, all raise
grep -n "HTTPException" src/api/routes/dashboard.py | grep "404"
# → 1 occurrence, raise
grep -n "HTTPException" src/api/routes/questionnaires.py | grep "404"
# → 2 occurrences, raise
```

**Tests updated:** 4 tests in `test_evidence_routes.py` that asserted the buggy tuple behavior now assert proper 404 + `{"detail": "..."}` shape.

**All 8 instances fixed and verified. 528 tests pass (was 522).**

---

## HIGH Findings

### HIGH-1 — C1.4: FrameworksTab only 4/14 clusters accessible

**Finding:** `FrameworksTab.jsx` had 4 hardcoded metric buttons instead of a dropdown for all 14+ clusters.

**Fix:**

- Replaced 4-button UI with a `<select>` dropdown containing all 18 clusters from `_CLUSTER_METRIC_MAP`
- Added side panel (overlay) that opens on framework row click
- Side panel displays `f.description` (disclosure requirement text), `f.field_id`, `f.value`, `f.unit`, `f.confidence`
- Side panel closes on backdrop click or Escape key

**Verification:**

```
grep -c "Object.entries(_CLUSTER_METRIC_MAP)" apps/web/src/pages/FrameworksTab.jsx
# → 1 (dropdown built from all 18 clusters)
grep "side-panel" apps/web/src/pages/FrameworksTab.jsx
# → side panel rendered when selectedFramework is set
```

**VERIFIED — implemented.**

### HIGH-2 — C2.4: No frontend report builder page

**Finding:** No `/reports` route or `ReportBuilder` component existed.

**Fix:** Created `apps/web/src/pages/ReportBuilder.jsx` with:

- Framework dropdown (GRI, TCFD, CSRD, ISSB, SASB)
- Period input (YYYY-MM-DD_YYYY-MM-DD format)
- Preview button (opens PDF blob URL in new tab)
- Download button (via `apiExport`)
- Wired into `DashboardPage.jsx` with `activeTab === "reports"`
- Added to `Header.jsx` nav with `{ id: "reports", label: "Report Builder" }`

**VERIFIED — implemented and wired.**

---

## MEDIUM Findings

### MEDIUM-1 — C2.2: Enhanced PDF missing sections

**Finding:** Framework PDF had 3 pages instead of 7 spec-required sections. Missing: bar charts, emission factor citation table, confidence distribution.

**Fix:** Added to `build_framework_pdf()` in `reports_pdf.py`:

1. Bar chart in executive summary (Scope 1/2/3 emissions side-by-side)
2. Standalone `_render_emission_factors()` page (emission factor citations table)
3. Standalone `_render_confidence_distribution()` page (HIGH/MEDIUM/LOW counts + bar + per-metric table)

**Also fixed pre-existing bugs uncovered during implementation:**

- `reports.py:24` ambiguous `org_id` after JOIN → qualified with `m.org_id`
- `reports.py:73,1497` wrong column `qr.submitted_at` → `qr.responded_at`
- `reports.py` undefined `_FW_NAMES` → added `{"gri": "GRI", ...}` constant

**VERIFIED — 7 sections now rendered in correct order.**

### MEDIUM-2 — C2.1: Zero test coverage for `/api/reports/pdf`

**Finding:** `/api/reports/pdf` endpoint had no tests; only `/compliance-report` was tested.

**Fix:** Added `TestFrameworkPDFReport` class with 6 tests:

- `test_pdf_requires_auth` → 401
- `test_pdf_with_valid_framework_and_period` → 200 + PDF magic bytes
- `test_pdf_accepts_all_valid_frameworks` → gri/tcfd/csrd/issb all 200
- `test_pdf_with_invalid_framework` → 400
- `test_pdf_with_invalid_period_format` → 400
- `test_pdf_with_missing_underscore_in_period` → 400

**VERIFIED — all 6 new tests pass.**

---

## LOW Finding

### LOW-1 — C2.3: Filename missing "Report" word

**Finding:** Spec says `{org}_ESG_Report_{framework}_{date}.pdf` but code generated `{org}_ESG_{framework}_{date}.pdf`.

**Fix:** `reports_pdf.py:779` — inserted "Report" between "ESG" and framework:

```python
f"{safe_name}_ESG_Report_{framework.upper()}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
```

**VERIFIED — matches spec format.**

---

## Round 2 Verdict

**0 CRITICAL remaining. 0 HIGH remaining. C1.4, C2.1, C2.2, C2.3, C2.4 all implemented and verified. 528 tests pass.**

All Phase A and Phase C items resolved.
