---
type: RISK
date: 2026-05-19
created_at: 2026-05-19T12:00:00Z
author: agent
session_id: redteam-commercial-todos
project: esg-scrm-mvp
topic: Red team findings on commercial todo list — security gaps
phase: redteam
tags: [security, redteam, whatsapp, evidence-vault, auth]
---

# Red Team Security Findings on Commercial Todo List

Red team audit of the commercial todo list surfaced 23 security findings across the codebase and spec. All were applied as additions/modifications to the todo list at `todos/active/01-commercial-todos.md`.

## Critical Findings (Applied as Todo Fixes)

1. **Twilio webhook HMAC comparison** (B2.1) — webhook signature verification used hex comparison instead of Base64-encoded HMAC. Fixed in todo to use `hmac.compare_digest` with Base64-decoded signature.

2. **Evidence routes read from CSV, not DB** (C3.3) — `src/api/routes/evidence.py` reads from CSV files with hardcoded `org_id = "org_bd_001"`. Todo rewritten to include full migration to DB-backed queries with org_id scoping.

3. **10+ routes missing `require_auth`** (A2.3, C1.3) — emission factors, framework mapping, and other routes have no authentication dependency. Added explicit `require_auth` requirements.

4. **WebSocket broadcasts across orgs** (D1.7) — real-time alerts WebSocket sends to all connected clients regardless of org_id. Todo added for org-scoped broadcasting.

5. **Bare tuple error returns in FastAPI** (D4.3) — several routes return bare tuples instead of proper HTTPException, causing 500 errors. Fixed in todo.

6. **Frontend calls non-existent endpoint** (B3.8) — SupplierEngagementTab calls `/questionnaires/whatsapp-preview` which doesn't exist. Todo added to create the endpoint.

## High Findings (Applied as New Todos)

- Password reset flow (A4.3), JWT token invalidation (A4.4)
- Demo mode webhook protection (B2.2)
- Email fallback for non-WhatsApp suppliers (B2.6, B2.7)
- Confidence scoring engine for data quality (C3.5)
- Alert deduplication (D1.6)
- Geopolitical heat map component (D2.5)
- Scope 3 completeness tracking (D3.5, D3.6)
- Rate limiting on new endpoints (D6.6)
- Comprehensive audit logging (D6.7)
- Admin settings page, API key management (D7.1, D7.2)
- Onboarding wizard (D7.5)
- DOMPurify XSS prevention (D7.7)
- MQTT production wiring (D7.8)

## For Discussion

- Should the confidence scoring engine (C3.5) use a weighted average or a Bayesian approach? The weighted average is simpler but may mask low-quality data points behind high-volume ones.
- Is Tier-3 API routes (D7.4) a v1 launch requirement, or can it ship in v1.1? These cover governance/ethics/traceability which are important but not deal-critical per the brief.

## Cross-References

- Journal [[0001-DISCOVERY-deal-closer]] — Feature 2 (WhatsApp) is THE deal-closer
- Journal [[0002-DISCOVERY-framework-mapping-is-the-usp]] — Framework mapping is core USP
- Journal [[0007-DECISION-emission-factor-source-pinning]] — Emission factor source tracking
- Journal [[0009-DISCOVERY-coverage-rate-over-response-rate]] — Spend-weighted coverage
