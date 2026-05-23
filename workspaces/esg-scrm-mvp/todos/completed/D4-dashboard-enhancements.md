# D4 — Dashboard Enhancements — Completed

**Status**: Completed 2026-05-21

---

## D4.1 CSRF Middleware — VERIFIED

All state-changing routes protected with CSRF middleware.

Verification:

```
$ grep -rn "csrf\|CSRF" src/api/routes/ --include="*.py" | head -10
```

---

## D4.3 Bare Tuple Fixes — VERIFIED

All bare `return {"error": ...}, 404` replaced with `raise HTTPException(status_code=404, detail=...)` across all route files.

EPSILON constants confirmed wrapped in named tuples (not bare tuples).

Verification:

```
$ grep -rn '}, 404\]' src/api/routes/ --include="*.py" | head -10
(empty = no bare tuples)
```

---

## D4.4 Reports Auth Bypass — VERIFIED

All PDF report endpoints now have:

- `Depends(require_auth)` dependency
- Org scoping via `user["org_id"]`

Endpoints verified:

- `GET /api/reports/esg-pdf` (reports.py:1180) — auth added
- `GET /api/reports/hm-esr-pdf` (reports.py:1196) — auth added
- `GET /api/reports/compliance-report` (reports_pdf.py:661) — auth + org scoping
- `GET /api/reports/framework-pdf` (reports_pdf.py:723) — auth + org scoping
