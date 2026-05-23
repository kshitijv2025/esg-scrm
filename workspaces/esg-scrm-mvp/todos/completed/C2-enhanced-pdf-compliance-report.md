# C2 — Enhanced PDF Compliance Report

**Date:** 2026-05-20
**Phase:** C / The Proof — Framework Mapping + Compliance Reports
**Status:** Complete

## What Was Built

### C2.1 Reports API (reports.py + reports_pdf.py)

- `GET /api/reports/pdf?framework={gri|csrd|tcfd|issb}&period={start}-{end}`
- Uses `reports_pdf.py` for actual PDF generation
- **Verification:** `grep "reports/pdf\|compliance-report" src/api/routes/reports.py src/api/routes/reports_pdf.py`

### C2.2 Enhanced PDF with fpdf2

- Cover page: org name, reporting period, framework
- Emissions summary by scope with bar charts
- Emission factor citations (source, year, region)
- Supplier coverage statement
- Methodology statement
- Per-metric evidence chain summary
- Confidence distribution
- **Verification:** `grep "fpdf\|FPDF\|cover.*page\|bar.*chart\|emission.*factor" src/api/routes/reports_pdf.py`

### C2.3 Download Filename Format

- Filename: `{org}_ESG_Report_{framework}_{date}.pdf`
- **Verification:** `grep "filename\|org.*ESG.*Report" src/api/routes/reports_pdf.py`

### C2.4 Frontend Report Builder Page

- Select framework (GRI for H&M, CSRD for EU buyers)
- Select period
- Include/exclude sections checkboxes
- Preview and download button
- **Verification:** `grep "ReportBuilder\|reports.*pdf\|framework.*select" apps/web/src/`

### C2.5 H&M ESR Response Template

- Generates H&M-specific ESR questionnaire response document
- Matches H&M's exact ESR format and field structure
- Not generic GRI output — specific to H&M requirements
- **Verification:** `grep "ESR\|H&M\|hm_esr\|hmr.*template" src/api/routes/reports_pdf.py`

## Specs Implemented

- `specs/evidence-vault.md` § PDF Compliance Report sections 1-7
- `specs/dashboard-tabs.md`
- Brief Feature 3, competitive analysis finding
