# A3 — Enhanced CSV Upload

**Date:** 2026-05-20
**Phase:** A / Data Foundation
**Status:** Complete (A3.2 REMOVED)

## What Was Built

### A3.1 Column Validation (upload.py)

- `src/api/routes/upload.py` updated with comprehensive validation:
  - Required columns check
  - Type checking (numbers where expected)
  - Data quality warnings (value out of expected range)
  - Duplicate detection (same date + factory + metric)
  - File extension validation (.csv only)
  - MIME type check
  - Filename sanitization (rejects paths with / or ..)
- Original CSV files stored in org-scoped directory (`uploads/{org_id}/{date}/`)
- Metadata stored in `uploaded_files` table
- **Verification:** `grep "required_columns\|duplicate.*detect\|mime_type\|sanitiz" src/api/routes/upload.py`

### A3.2 ~~REMOVED~~ Frontend CSV Upload Component

- REMOVED per user decision: Scope 1/2 data via CSV upload is not the product
- Backend column validation (A3.1) and audit trail (A3.3) remain

### A3.3 Upload Audit Trail

- `GET /api/uploads/history` endpoint with org scoping
- Tracks what was uploaded, when, by whom in `audit_log` table
- **Verification:** `grep "uploads/history\|uploaded_files\|audit_log" src/api/routes/upload.py`

### A3.4 Bulk Supplier Import

- `POST /api/upload/suppliers` endpoint
- Template columns: supplier_name, country, contact_email, phone, annual_spend, tier, category
- **Verification:** `grep "upload/suppliers\|bulk.*supplier\|import.*supplier" src/api/routes/upload.py`

## Specs Implemented

- `specs/dashboard-api.md`
- `specs/evidence-vault.md` § raw_data export
- `specs/data-model.md`
