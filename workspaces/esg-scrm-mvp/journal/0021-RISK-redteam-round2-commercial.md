---
type: RISK
date: 2026-05-19
created_at: 2026-05-19T14:00:00Z
author: agent
session_id: redteam-round2-commercial
project: esg-scrm-mvp
topic: Red team Round 2 — critical commercial and security gaps
phase: redteam
tags: [redteam, commercial, billing, scoring, security]
---

# Red Team Round 2 — Critical Commercial + Security Findings

3 parallel agents audited the 102-todo list against all specs, briefs, journals, analysis docs, and the full codebase. 3 aggregate findings surfaced: 18 spec gaps, 54 codebase issues, and deal readiness scored 6/10 by value auditor.

## Deal-Breaker Gaps (CRITICAL)

1. **No Supplier ESG Scoring Algorithm** — The platform collects data but cannot tell H&M "this supplier scores 72/100." EcoVadis, Sedex, Higg Index all produce scores. Added B3.5a with weighted E/S/G dimension scoring methodology.

2. **No Billing/Subscription/Trial System** — At $48-60K/year, the product cannot be sold without manual invoicing. No self-serve trial, no payment processing. Added Milestone E (8 todos) with Stripe integration, plan tiers, and 14-day trial.

3. **reports.py Missing Auth** — `GET /api/reports/esg-pdf` has NO authentication and NO org scoping. Anyone can download any org's report. Added D4.4 to fix or remove.

## Security Findings (HIGH)

- `.env.example` naming mismatch: `TWILIO_PHONE_NUMBER` vs `TWILIO_WHATSAPP_NUMBER` — silent config failure
- Webhook SHA-1 instead of SHA-256 in `whatsapp.py` — timing attack vulnerability
- `questionnaires.py` returns hardcoded mock data — zero-tolerance violation
- Evidence chain has no immutability constraint — UPDATE/DELETE possible after creation

## Commercial Parity Gaps (HIGH)

- No corrective action tracking — platform identifies problems but no mechanism to track resolution
- No buyer-facing portal — H&M cannot see supplier data directly
- No benchmarking against industry averages — every competitor offers this
- No H&M ESR response template — generic GRI output doesn't match H&M's format
- No data validation on supplier responses — CFO legally exposed for unverified data
- No supplier improvement timeline — H&M wants trends, not snapshots

## Key Architecture Findings

- Schema drift between SQLite and PostgreSQL (column names differ: `value` vs `factor_value`)
- `factories` table referenced in `reports_pdf.py` but doesn't exist in schema
- No emission intensity metrics (per garment) — blocks GRI 302-3/305-4 framework fields
- No production volume data — can't calculate intensity without units produced
- ML `_COUNTRY_RISK` hardcoded for 10 countries — needs database table

## For Discussion

- Milestone E (billing) — should this be v1 launch or can the product launch with manual invoicing? Value auditor says "no billing = no deal" but Stripe integration is a significant engineering effort.
- Multi-org access (consulting firms) — marked as Year 2 but the architecture should accommodate it now.

## Cross-References

- Journal [[0019-RISK-redteam-commercial-todos]] — Round 1 security findings
- Journal [[0020-GAP-redteam-commercial-todos]] — Round 1 spec/brief gaps
- Journal [[0001-DISCOVERY-deal-closer]] — WhatsApp is THE deal-closer
- Journal [[0002-DISCOVERY-framework-mapping-is-the-usp]] — Framework mapping is core USP
