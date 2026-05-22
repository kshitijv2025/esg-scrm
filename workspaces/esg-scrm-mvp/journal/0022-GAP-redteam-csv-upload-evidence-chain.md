---
name: gap-redteam-csv-upload-evidence-chain
description: csv_upload source_system in spec but not implemented — spec corrected
metadata:
  type: GAP
  milestone: C3.3
  round: redteam-round-1
  date: 2026-05-20
---

# GAP: csv_upload source_system in evidence-vault.md not implemented

## Finding

`specs/evidence-vault.md` § "Per-Metric Evidence" listed `csv_upload` as a valid `source_system` value alongside `mqtt` and `sap_b1`. The spec also listed `csv_upload (MEDIUM)` in the confidence scoring table. However, `upload.py` only handles reference data (suppliers, emission factors, certifications) — no operational metric upload exists. Metrics are ingested via MQTT only.

## Spec compliance audit result

| Item                                                | Status                                  |
| --------------------------------------------------- | --------------------------------------- |
| `evidence.py` reads DB via `fetch_evidence_chain()` | PASS                                    |
| All evidence endpoints scoped by `org_id`           | PASS                                    |
| CSV upload creates evidence chain entries           | **FAIL** (spec listed, not implemented) |
| MQTT wired to `create_evidence_chain_entry()`       | PASS                                    |
| `fetch_prev_hash_by_cluster` in `database.py`       | PASS                                    |
| `evidence_chain_no_update` trigger                  | PASS                                    |
| `evidence_chain_no_delete` trigger                  | PASS                                    |
| `fetch_evidence_chain()` in `database.py`           | PASS                                    |
| `archive_retention_policy()` in `database.py`       | PASS                                    |
| Retention runs on `_ensure_db()` startup            | PASS                                    |
| 84-month retention period                           | PASS                                    |
| bcrypt for passwords                                | PASS                                    |
| JWT `token_version` column check                    | PASS                                    |

## Fix applied

1. Removed `csv_upload` from `source_system` valid values in `specs/evidence-vault.md`
2. Removed `csv_upload (MEDIUM)` from confidence scoring table in same file
3. Architecture decision: operational metrics = MQTT only; reference data = CSV upload (suppliers, emission factors, certifications) — documented in `upload.py` module docstring

## Verification

- `grep -r "csv_upload" src/` → zero matches
- `grep -r "csv_upload" specs/` → fixed (removed)
- All 464 unit tests pass

## Resolution

Spec corrected. `csv_upload` was a design artifact from before the architecture decision to use MQTT for all operational metric ingestion. No code change required.
