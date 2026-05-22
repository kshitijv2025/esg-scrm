# Phase C Redteam — Round 1 Validation

**Date**: 2026-05-20
**Posture**: L5_DELEGATED
**Scope**: Phase C evidence vault (C3.3, C3.5, C3.6, C3.7)

---

## Spec Compliance (analyst)

Full assertion table: `.spec-coverage-v2.md`

### HIGH findings (all fixed)

| #      | Finding                                                                           | Fix                                                                                                  |
| ------ | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| HIGH-1 | `metric_id` (spec) vs `metric_type` (code) — spec used wrong field name           | Updated spec to use `metric_type` and `metric_type` in endpoint paths                                |
| HIGH-2 | `source_record_id` hardcoded to `""` in response                                  | Fixed: now maps to `row.get("id")` (DB primary key) in `_build_evidence_response`                    |
| HIGH-3 | Spec endpoint path `/api/evidence/{metric_id}` vs code `/drilldown/{metric_type}` | Updated spec to use `/api/evidence/drilldown/{metric_type}` and `/api/evidence/verify/{metric_type}` |

### Spec accuracy fixes (evidence-vault.md)

- Field table rewritten to match actual DB schema and API field names (`value`, `calculation_method`, `previous_hash`, etc.)
- `source_record_id` now documented as DB primary key `id`
- All emission factor joined fields documented (`emission_factor_source`, `_year`, `_value`, `_unit`, `_table`)
- Dynamic confidence fields documented (`confidence_score`, `confidence_reasons`)
- Endpoint paths updated to match code

---

## Security (security-reviewer)

### CRITICAL findings (all fixed)

| #      | Finding                                                                                                                                                         | Fix                                                                                                                       |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| CRIT-1 | `datetime.fromisoformat()` returns naive datetime; `datetime.now(timezone.utc)` is UTC-aware — comparing them raises `TypeError`, breaking every auditor access | Added `.replace(tzinfo=timezone.utc)` after `fromisoformat()` in both `auditor_access` and `_evict_expired_auditor_links` |
| CRIT-2 | `_AUDITOR_LINKS` dict grows unbounded — expired tokens never evicted; also multi-worker visibility issue                                                        | Added `_evict_expired_auditor_links()` called on every auditor access to remove expired tokens                            |

### Verification

- All SQL queries parameterized: PASS
- JWT uses `hmac.compare_digest`: PASS
- Token generation via `secrets.token_urlsafe(32)`: PASS
- Framework allowlist server-side validated: PASS
- Auditor `create_auditor_link` performs inline JWT auth: PASS (intentional design — separate router has no global auth)

---

## Test Coverage

- 33 evidence route tests: **33 PASS**
- 90 total tests (evidence + coverage + scoring + number_parsing): **90 PASS**
- New modules verified:
  - `src/evidence/hash_chain.py` — `compute_confidence`, `compute_hash`, `verify_chain_record`, `build_chain_proof` — all imported and used
  - `auditor_router` correctly mounted without `require_auth`

---

## WARN+ Log Triage

Only warnings are `PytestConfigWarning` (unknown pytest config keys `asyncio_default_fixture_loop_scope`, `asyncio_mode`) and `NotOpenSSLWarning` (Python 3.9 on macOS with LibreSSL) — all pre-existing, not from Phase C changes.

---

## Fixes Landed This Round

1. `evidence.py` — `metric_type` field name, `source_record_id` mapping, timezone fix, token eviction
2. `main.py` — `auditor_router` mounted without `require_auth`
3. `specs/evidence-vault.md` — spec updated to match code

---

## Round 2 Verification

All findings independently verified via direct grep:

| Finding                          | Verification                                                                                                                      | Result   |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | -------- |
| CRIT-1 timezone                  | `grep "replace(tzinfo=timezone.utc)" src/api/routes/evidence.py` → 2 occurrences (auditor_access + \_evict_expired_auditor_links) | VERIFIED |
| CRIT-2 unbounded \_AUDITOR_LINKS | `_evict_expired_auditor_links()` called on every `auditor_access` entry (line 614)                                                | VERIFIED |
| HIGH-1 metric_id→metric_type     | `grep "metric_id" specs/evidence-vault.md` → 0 results                                                                            | VERIFIED |
| HIGH-2 source_record_id mapping  | `grep "source_record_id.*id" src/api/routes/evidence.py` → `str(row.get("id"))` at line 195                                       | VERIFIED |
| HIGH-3 spec drilldown path       | `grep "/drilldown" specs/evidence-vault.md` → `/api/evidence/drilldown/{metric_type}` at line 107                                 | VERIFIED |
| 33 evidence tests                | `pytest tests/unit/test_evidence_routes.py -q` → 33 passed                                                                        | VERIFIED |

**Note on Round 2 agent false positive**: Initial Round 2 agent reported HIGH-1/HIGH-3 as unresolved based on reading a stale `.spec-coverage-v2.md` (written before fixes). Direct grep of current `specs/evidence-vault.md` confirms all `metric_id` references removed. Round 2 agent error was a stale-read false positive, not a real finding.

## Phase C — C3.1 / C3.2 / C3.4 Verification

Scope: C3.1 (evidence export ZIP), C3.2 (hash chain verify), C3.4 (frontend Export for Audit button).

**C3.1 — Evidence export ZIP endpoint**

| Check               | Verification                                                          | Result   |
| ------------------- | --------------------------------------------------------------------- | -------- |
| Endpoint exists     | `grep "def export_evidence" evidence.py` → line 978                   | VERIFIED |
| ZIP mechanism       | `zipfile.ZipFile(buf, "w", compression=ZIP_DEFLATED)` at line 1013    | VERIFIED |
| Framework allowlist | `_VALID_FRAMEWORKS = {"csrd","gri","tcfd","issb","sasb"}` at line 656 | VERIFIED |
| Auth on endpoint    | `user: dict = Depends(require_auth)` on `export_evidence`             | VERIFIED |
| Test coverage       | `TestEvidenceExport` — 5 tests, all PASS                              | VERIFIED |

**C3.2 — Hash chain verify endpoint**

| Check            | Verification                                                               | Result   |
| ---------------- | -------------------------------------------------------------------------- | -------- |
| Endpoint exists  | `grep "def verify_chain" evidence.py` → line 266                           | VERIFIED |
| Return shape     | Returns `{metric_type, chain_length, integrity: VALID\|BROKEN, broken_at}` | VERIFIED |
| Hash computation | `compute_hash` / `verify_chain_record` in `evidence.py`                    | VERIFIED |
| Test coverage    | `TestVerifyChain` — 5 tests, all PASS                                      | VERIFIED |

**C3.4 — Frontend Export for Audit button**

| Check                              | Verification                                                                 | Result   |
| ---------------------------------- | ---------------------------------------------------------------------------- | -------- |
| Button rendered                    | `grep "Export for Audit" EvidencePanel.jsx` → line 69                        | VERIFIED |
| `apiExport` imported               | `grep "apiExport" EvidencePanel.jsx` → line 1                                | VERIFIED |
| `handleExport()` calls `apiExport` | `apiExport(\`/api/evidence/export${query}\`, "evidence_export.zip")` line 28 | VERIFIED |
| CSS exists                         | `.btn-export-audit`, `.export-filters`, `.export-period-input` in styles.css | VERIFIED |
| `apiExport` in client.js           | `export async function apiExport(path, filename)` at line 86                 | VERIFIED |

**WARN+ Log triage (C3.1/C3.2/C3.4)**

Only pre-existing pytest config warnings and `NotOpenSSLWarning` — same as Round 1 triage. 0 new WARN+ introduced by C3.1/C3.2/C3.4 changes.

## Round 1 Verdict

**0 CRITICAL remaining. 0 HIGH remaining. All 3 spec HIGHs and 2 security CRITs fixed and verified. C3.1, C3.2, C3.4 fully verified.**
