# DISCOVERY: Phase E specs completed — closes redteam convergence gap

**Date**: 2026-05-21
**Finding**: Phase E redteam convergence blocked by missing domain specs

## Context

Phase E (Commercial Infrastructure: E1 billing/subscription + E2 legal/privacy) was fully implemented and verified (1218 tests passing) but redteam could not converge because the Phase E spec files were absent from `specs/`. Only 9 spec files existed; `billing.md`, `gdpr.md`, and `multi-org.md` were all absent.

## What was written

Three spec files created to close the convergence gap:

- **`specs/billing.md`** — Stripe subscriptions, 5 endpoints (plans public, my-plan, subscribe, portal, webhook), 4 webhook event handlers, 3 plan tiers with supplier limits, `_check_plan_limit` enforcement, `_require_active_subscription` middleware. All `src/api/routes/billing.py` line refs verified.
- **`specs/gdpr.md`** — Article 17 erasure + Article 20 portability, 3 endpoints (export, export/{job_id}, delete/account), export job lifecycle, 30-day deletion schedule, data gathered per source. All `src/api/routes/gdpr.py` line refs verified.
- **`specs/multi-org.md`** — Per-org role scoping, 5 endpoints (list_orgs, switch_org, list_members, invite, remove_member), role resolution logic from user_orgs vs users.role, admin-only guard enforcement. All `src/api/routes/orgs.py` line refs verified.

`specs/_index.md` updated to include all three new files.

## Verification

- All file:line citations resolve against `main` via grep.
- No Phase-1/Phase-2 split-state framings.
- No TBD/pending/accessor-pending markers.
- Specs describe shipped behavior only.

## Impact

Phase E redteam can now run spec-compliance sweep against all Phase E spec promises.
