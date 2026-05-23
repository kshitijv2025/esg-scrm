---
type: GAP
date: 2026-05-19
created_at: 2026-05-19T12:00:00Z
author: agent
session_id: redteam-commercial-todos
project: esg-scrm-mvp
topic: Red team findings — spec and brief gaps
phase: redteam
tags: [redteam, spec-gap, brief-gap, coverage, i18n]
---

# Red Team Spec/Brief Gaps on Commercial Todo List

Red team audit surfaced 37 spec/brief gaps and 24 code issues. The todo list was expanded from 61 to 102 todos to close all gaps.

## Key Spec Gaps Closed

1. **Coverage calculation: headcount vs spend-weighted** — Journal 0009 mandates spend-weighted coverage but specs use headcount language. Todo B3.4 now explicitly uses spend-weighted calculation with `annual_spend` from suppliers table.

2. **No multi-channel messaging** — Journal 0008 mandates "WhatsApp is channel, not data source" and multi-channel from day 1. Added B5.1-B5.3 (react-intl i18n, LINE adapter, WeChat adapter).

3. **Missing `channel` column on questionnaire responses** — B2.3 adds `channel` column (whatsapp/email/web/line/wechat) and `confidence` column to `questionnaire_responses` table.

4. **No manual data entry path** — Suppliers without WhatsApp need manual entry. Added B3.6 (manual data entry UI), B3.7 (chasing workflow for non-responsive suppliers).

5. **No data lineage tracking** — For audit credibility, the provenance of every data point must be traceable. Added C3.6 (data lineage DAG), C3.7 (auditor access model with read-only API keys).

6. **Hardcoded dashboard metrics** — `_REFERENCE_SCORES`, `SCORECARD_QUADRANTS`, `CATEGORY_META`, `METRIC_META` are all hardcoded arrays in the frontend. D2.4 and D4.3 now include replacing these with API calls.

## Key Code Issues Closed

- File upload missing extension/MIME validation (A3.1)
- No password reset flow (A4.3)
- No JWT token invalidation mechanism (A4.4)
- `table_or_equation` column missing from emission_factors table (A2.1)
- No MQTT broker in docker-compose for production (D5.2)
- No CORS configuration (D5.6)
- No data export endpoints (D5.5)
- No Tier-2/3 API routes (D7.3, D7.4)
- No onboarding wizard (D7.5)
- No email notification service (D7.6)

## For Discussion

- The LINE/WeChat adapters (B5.2-B5.3) are marked after core WhatsApp (B1-B4). Should they be promoted to a required Phase B deliverable, or kept as post-launch? The brief mentions "suppliers in Bangladesh" (WhatsApp-primary) but journal 0008 explicitly mentions Vietnam/Thailand (LINE) and China (WeChat).
- The audit logging middleware (D6.7) intercepts all POST/PUT/DELETE. Should GET requests to sensitive endpoints (audit log viewer, user list) also be logged? The current spec doesn't address this.

## Cross-References

- Journal [[0008-DISCOVERY-whatsapp-is-channel-not-data-source]] — Multi-channel mandate
- Journal [[0009-DISCOVERY-coverage-rate-over-response-rate]] — Spend-weighted coverage
- Journal [[0018-DECISION-todo-prioritization]] — Original 61-todo plan (now 102)
