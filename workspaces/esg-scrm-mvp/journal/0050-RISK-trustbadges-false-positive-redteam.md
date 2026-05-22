---
name: 0050-RISK-trustbadges-false-positive-redteam
description: Redteam flagged TrustBadges as fake; actually data-driven
metadata:
  type: RISK
  round: "Round 1"
  posture: L5_DELEGATED
---

# RISK: TrustBadges false-positive audit finding

**Finding**: Redteam agent flagged `TrustBadges.jsx` as "FAKE/MOCK" — hardcoded compliance labels without data verification.

**Actual state**: TrustBadges is **fully data-driven** via `GET /trust/badges` → `fetch_trust_badges()` in `database.py:1562`.

Each badge is verified against real data:

- `csrd_compliant`: CSRD/ESRS framework mappings exist in DB
- `ghg_protocol_source`: GHG Protocol emission factors are in DB
- `audit_ready`: all evidence_chain hashes verified via `verify_chain_record()`
- `scope3_verified`: supplier questionnaire responses exist (spend_weighted_coverage_pct > 0)

**Root cause of false positive**: Redteam agent inspected only the frontend component's `BADGE_DEFS` static array and missed the `DashboardPage.jsx` → `/trust/badges` API call chain and the backend `fetch_trust_badges()` implementation.

**Resolution**: No code change needed. TrustBadges is correctly implemented.

**Lesson**: Frontend-only inspection (grep for mock data patterns) produces false positives when the data-verification logic lives in the backend. Always trace the full data flow from component prop → API call → backend query.
