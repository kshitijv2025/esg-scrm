# RISK: In-Memory `_AUDITOR_LINKS` Dict Is Per-Worker

**Date**: 2026-05-20
**Phase**: C
**Round**: 1 audit
**Type**: RISK

## Finding

`_AUDITOR_LINKS` is an in-memory dict. Each uvicorn worker process has its own Python interpreter and its own `_AUDITOR_LINKS` dict. Tokens created in worker A are invisible to workers B, C, and D.

Under multi-worker deployment (e.g., `uvicorn --workers 4`), an auditor link created by one request may be served by a different worker on a subsequent request — resulting in 404 for a valid token.

## Production Implication

Standard production deployment uses multiple workers for concurrency. This bug causes intermittent auditor link failures in production even though:

- Token is valid in `_AUDITOR_LINKS`
- Expiry check passes
- The only failure is worker mismatch

## Current State

`_evict_expired_auditor_links()` was added to prevent unbounded growth, but eviction only cleans tokens LOCAL to the worker that serves the request. Dead tokens in OTHER workers' dicts are never evicted.

## Fix Approaches

1. **Database-backed store** (recommended): Persist auditor links to DB table with expiry column. All workers share the same store. Token lookup via DB query.

2. **Redis shared dict**: Use Redis `Hash` or `String` for `_AUDITOR_LINKS` with TTL. All workers share same Redis instance.

3. **Single-worker deployment**: Constrain uvicorn to `--workers 1`. Works for low-traffic deployments but does not scale.

## Recommendation

Move to database-backed store. `auditor_links` table already exists in `schema.sql`. The `create_auditor_link` endpoint and `auditor_access` endpoint should read/write this table instead of the in-memory dict.

## Severity

**MEDIUM** — works in dev (single worker), fails intermittently in production (multi-worker). Auditor link clicks will return 404 for ~75% of workers in a 4-worker deployment after the creating worker has processed the request.

## Files Affected

- `src/api/routes/evidence.py` (`_AUDITOR_LINKS` dict, `create_auditor_link`, `auditor_access`, `_evict_expired_auditor_links`)
- `src/db/schema.sql` (already has `auditor_links` table)

## References

- `src/api/routes/evidence.py:549` — `_AUDITOR_LINKS` definition
- `src/api/routes/evidence.py:552-561` — `_evict_expired_auditor_links`
- `src/api/routes/evidence.py:558` — `create_auditor_link`
- `src/api/routes/evidence.py:611` — `auditor_access`
