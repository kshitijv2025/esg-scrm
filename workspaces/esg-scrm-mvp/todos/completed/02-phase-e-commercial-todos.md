# Phase E: Commercial Infrastructure — Completed

**Closed**: 2026-05-21

## E1. Billing + Subscription

- [x] **E1.1 BUILD**: Stripe integration — install stripe-python SDK, create `subscriptions` table, webhook endpoint
- [x] **E1.2 BUILD**: Subscription plan tiers — Starter/Professional/Enterprise with supplier limits enforced at middleware
- [x] **E1.3 BUILD**: 14-day trial flow — trial org on signup, auto-expiry, sample Bangladesh garment data
- [x] **E1.4 BUILD**: Self-serve signup — public registration, email verification, org creation, auto-start trial
- [x] **E1.5 BUILD**: Pricing page — `/pricing` route, plan comparison, feature checklist, "Start Free Trial" CTA

## E2. Legal + Privacy

- [x] **E2.1 BUILD**: GDPR data export — `POST /api/gdpr/export` + `DELETE /api/gdpr/account` soft-delete
- [x] **E2.2 BUILD**: Privacy policy and terms of service pages — `/privacy` and `/terms` routes
- [x] **E2.3 BUILD**: Multi-org user access — `user_orgs` table, org switcher, scoped permissions per org

## Verification

- `test_gdpr_routes.py`: 12 tests — all passing
- `test_orgs_routes.py`: 17 tests — all passing
- `test_billing_routes.py`: all tests passing
- `test_auth.py`, `test_new_routes.py`: all tests passing
- Full suite: 1218 passed, 3 skipped

## Notes

- GDPR export: `audit_log` table uses `resource_type` + `resource_id` columns (not `resource`)
- Multi-org: backend determines role from `user_orgs` table first, falls back to `users.role`
- Trial flow: `organizations.trial_end` = 14 days from creation, middleware enforces read-only after expiry
