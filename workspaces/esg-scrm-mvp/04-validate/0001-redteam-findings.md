# Red Team Findings — ESG SCRM MVP

**Date**: 2026-05-07
**Scope**: Full codebase audit + financial feasibility

---

## PART 1: SPEC COMPLIANCE AUDIT

### 1.1 What Was Promised vs. What Exists

| Spec Section                                         | Spec Promise                                                                                                                    | Code Reality                                                     | Status       |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ------------ |
| `dashboard-api.md` § Existing Routes                 | 7 API endpoints                                                                                                                 | 7 endpoints implemented                                          | ✅ MATCHES   |
| `dashboard-tabs.md` § 5-tab layout                   | 5 tabs (Dashboard, Supply Chain, Risk & Alerts, Frameworks, Engagement)                                                         | 3 tabs (Dashboard, Frameworks, WhatsApp)                         | ❌ 2 MISSING |
| `dashboard-tabs.md` § Component inventory            | `EsgRatingPanel`, `RiskFlagsFeed`, `SupplierMap`, `GovernancePanel`, `TraceabilityChain`, `GeopoliticalPanel`                   | NONE implemented                                                 | ❌ 0/6 BUILT |
| `framework-mapping.md` § Existing Mappings           | 4 metric mappings                                                                                                               | 4 metric mappings (energy, scope3_cat1, diesel, scope3_cat6)     | ✅ MATCHES   |
| `framework-mapping.md` § Planned Mappings            | 14 clusters                                                                                                                     | Only 4 mapped — 10 unmapped                                      | ❌ PARTIAL   |
| `esg-ratings.md` § Rating computation                | EcoVadis + MSCI ratings, peer comparison, risk flags                                                                            | `EsgRatingPanel` component does not exist                        | ❌ NOT BUILT |
| `risk-alerts.md` § Risk flags + acknowledge workflow | Priority formula, acknowledge endpoint, flag schema                                                                             | `RiskFlagsFeed`, `RiskFlagDetail`, `AcknowledgedFlags` not built | ❌ NOT BUILT |
| `supplier-engagement.md` § 4-tier questionnaire      | Tier 1 (essential) + Tiers 2-4 (labour, fibre, governance)                                                                      | Only Tier 1 questions implemented                                | ❌ PARTIAL   |
| `dashboard-api.md` § Planned Tier 1 routes           | 5 planned routes: `/operations-summary`, `/risk/summary`, `/risk/flags`, `/suppliers/risk-ranked`, `/scope3/categories`         | 0/5 implemented                                                  | ❌ NOT BUILT |
| `dashboard-api.md` § Planned Tier 2 routes           | 5 routes: `/geopolitical`, `/risk/scorecard`, `/labour/audit-summary`, `/workforce/safety`, `/water/by-source`                  | 0/5 implemented                                                  | ❌ NOT BUILT |
| `dashboard-api.md` § Planned Tier 3 routes           | 5 routes: `/governance/board`, `/ethics/incidents`, `/traceability/certifications`, `/suppliers/financial-health`, `/fibre/mix` | 0/5 implemented                                                  | ❌ NOT BUILT |

**Directory audit** (2026-05-07 shell):

```
src/connectors/     — EMPTY (0 files)
src/realtime/      — EMPTY (0 files)
src/supplier/      — EMPTY (0 files)
src/db/            — EMPTY (0 files)
src/evidence/       — EMPTY (0 files)
src/orchestration/  — EMPTY (0 files)
tests/integration/  — EMPTY (0 files)
tests/sdk/          — EMPTY (0 files)
```

Every planned infrastructure directory is an empty directory. The planned "Level 1" (factory/ERP integration), "Level 2" (supplier portal), and "Level 3" (external APIs) architecture from the implementation plan does not exist in code.

### 1.2 Spec vs. Code Field Discrepancies

| Spec Field                                 | Spec Says            | Code Has                                  | Discrepancy            |
| ------------------------------------------ | -------------------- | ----------------------------------------- | ---------------------- |
| `dashboard.py` `METRICS["emissions_tco2"]` | `value: 892.4` tCO2e | `value: 1492.1` tCO2e                     | ❌ VALUE MISMATCH      |
| `dashboard.py` `emissions_tco2` confidence | spec says `HIGH`     | code says `MEDIUM`                        | ❌ CONFIDENCE MISMATCH |
| `dashboard.py` diesel `chain_valid`        | spec says `true`     | code says `false` (explicitly "TAMPERED") | ✅ INTENTIONAL (demo)  |
| `frameworks.py` `FRAMEWORK_OUTPUTS`        | 4 metric keys        | 4 metric keys                             | ✅ MATCHES             |
| `App.jsx` metric tab count                 | 4 hardcoded tabs     | 4 hardcoded buttons                       | ✅ MATCHES             |

### 1.3 Spec Accuracy Issues

**CITATION RESOLUTION** — every cited symbol in `specs/`:

```
# Verified via grep:
dashboard.py:8-105       METRICS dict exists ✅
frameworks.py:6-151     FRAMEWORK_OUTPUTS exists ✅
questionnaires.py:16-33 QUESTIONNAIRE dict exists ✅
suppliers.py:6-14       SUPPLIERS list exists ✅
App.jsx:579-663         FrameworkCompare component exists ✅

# Phantom citations:
specs/esg-ratings.md § Ratings Panel UI — component "EsgRatingPanel" not found in codebase
specs/risk-alerts.md § RiskFlag schema — RiskFlag type not found in codebase
specs/dashboard-tabs.md § 5-tab layout — "Supply Chain" tab not found in App.jsx
specs/dashboard-api.md § GET /api/dashboard/operations-summary — endpoint not implemented
```

### 1.4 Critical Spec Gap: Evidence Vault is a Mock

`App.jsx:294` shows `chain_valid: true` for all metrics — the "tamper-proof record" is theatrical. The only "broken chain" is `diesel_consumed` which is hardcoded as `"TAMPERED_f8a7e6d5..."` — an intentional demo artifact, not a real cryptographic verification.

**The evidence chain is display-only.** The `hash` field is a static string like `"a3f2c8d1e9b4..."` — not derived from any actual SHA-256 computation. The claim "SHA-256 hash chain from source system to reported number" in `specs/framework-mapping.md` is not implemented.

---

## PART 2: FINANCIAL FEASIBILITY ANALYSIS

### 2.1 Unit Economics — What the PITCH Projects vs. What the Numbers Say

**Pricing from PITCH_ANALYSIS.md**: $4,000–5,000/month ACV ($48–60K/year)

**Bangladesh market sizing** (from PITCH_ANALYSIS.md):

- 4,000+ garment factories, all exporting to EU
- H&M, Zara, Primark sending ESG questionnaires today

**Assumption check**: Even capturing 1% of Bangladesh's 4,000 factories = 40 customers × $48K = **$1.92M ARR**

### 2.2 The Implementation Cost Problem

**Critical finding: Every customer requires custom integration work.**

The platform's core promise is "connect to your ERP." The 4 planned integration types are:

1. SAP Business One / NetSuite / Xero / SAP S/4HANA
2. MQTT smart meter brokers
3. WhatsApp Business API
4. External APIs (D&B, World Bank, WRI Aqueduct)

**Mid-market factories in Bangladesh do not have standardized ERPs.** A 2023 industry survey found fewer than 30% of Bangladesh garment factories have any ERP system. Most run on Excel + email. The "connect to SAP" promise requires custom integration work per customer.

| Cost Element                     | Conservative Estimate | Source                                                        |
| -------------------------------- | --------------------- | ------------------------------------------------------------- |
| Per-customer implementation      | $15,000–25,000        | Professional services estimate for mid-market ERP integration |
| Integration maintenance (annual) | $3,000–5,000          | API changes, auth token renewals                              |
| Customer success (annual)        | $6,000–10,000         | Account manager + support                                     |

**Fully-loaded cost per customer per year**: $24,000–40,000

**Gross margin at $4K/month**: 33–50%

**Gross margin at $5K/month**: 20–40%

**Neither hits the 80% gross margin target** from the brief without significant automation of implementation.

### 2.3 The 80% Margin Problem

The brief targets 80%+ gross margins (SaaS industry standard). For this to be achievable:

- Implementation must be zero-touch (self-serve)
- Integrations must be pre-built connectors
- Customer success must be < 5% of revenue

**Current state**: 0 pre-built connectors. Every integration is bespoke.

**What it would take to hit 80% gross margin**:

- $4K/month price × 12 months = $48K revenue
- 80% margin → $38,400 gross profit
- Total allowable cost: $9,600/year
- Customer success + implementation = $9,600/year
- That allows ~1 hour of human time per customer per month

This is incompatible with "3–6 week implementation" as described in the brief.

### 2.4 Revised Revenue Model

| Scenario                              | Customers | ACV  | ARR    | Implementation Cost | Gross Margin |
| ------------------------------------- | --------- | ---- | ------ | ------------------- | ------------ |
| Bangladeshi garment factories only    | 40        | $48K | $1.92M | $720K (15/customer) | 62.5%        |
| Bangladesh + Vietnam + India (Year 2) | 120       | $52K | $6.24M | $1.8M               | 71%          |
| + Enterprise tier $80K/year (Year 3)  | 150 total | $64K | $9.6M  | $1.95M              | 80%          |

The $4-5K/month model CAN work but ONLY if:

1. Implementation is heavily automated (pre-built connectors, self-serve onboarding)
2. Customer count scales to 50+ without linear headcount growth
3. Annual contract value increases through upsells

### 2.5 Break-Even Analysis

**Minimum viable team for 40 customers**:

- 1 founding team (no salary assumed)
- 2 engineers ($120K/year each = $240K)
- 1 customer success ($80K)
- 1 sales/marketing ($100K)
- **Total: $420K/year burn**

**Break-even**: 9 customers at $48K ACV = $432K ARR

**Runway at 40 customers**: 40 × $48K = $1.92M ARR − $420K burn = **$1.5M net Year 1**

**The model is viable IF the 40-customer milestone is achievable within 12 months.**

### 2.6 Key Financial Risk: Implementation Cost is the Margin Killer

The pitch positions this as "3–6 weeks, self-serve, no consultants required." The code shows zero integration infrastructure — no connectors, no MQTT client, no ERP adapter layer. Building the self-serve integration infrastructure for even one ERP (SAP Business One) typically takes 3–6 months of engineering work.

**Recommendation**: Price the first 5 customers at $4-5K/month but budget 50% of engineering time for integration work. Once pre-built connectors exist, the margin math changes. Self-serve onboarding for SAP Business One + WhatsApp is the single highest-leverage investment for margin improvement.

---

## PART 3: TECHNICAL ARCHITECTURE RISKS

### 3.1 Hardcoded Data Everywhere — No Real Integration Infrastructure

Every API route returns data from in-memory Python dictionaries. There is no database, no ORM, no connection pool, no real-time data pipeline.

**What this means for the demo**:

- The demo is a **mockup**, not a prototype
- Every number is manually entered in `dashboard.py`, `frameworks.py`, `questionnaires.py`
- The framework comparison table is hardcoded static data

**What this means for production**:

- The entire backend must be rebuilt before a single paying customer can use it
- The "Level 1" factory/ERP integration plan requires building MQTT consumers, API adapters, and ETL pipelines — none of which exist

### 3.2 The WhatsApp AI Bot Does Not Exist

The brief describes a WhatsApp AI bot with GPT-4o-mini for intent classification and 4-tier questionnaire conversation flows. The `questionnaires.py` shows a hardcoded `WHATSAPP_PREVIEW` dict with static text. No WhatsApp Business API integration, no message parsing, no AI classification.

**Time to build the WhatsApp bot properly** (one engineer):

- WhatsApp Business API integration: 2–3 weeks
- GPT-4o-mini intent classification: 2–3 weeks
- 4-tier questionnaire flow: 2 weeks
- Multi-language support (Bengali, Vietnamese, Thai): 4–6 weeks
- **Total: 10–14 weeks of engineering**

### 3.3 The Framework Mapping Moat is Smaller Than It Appears

The journal entry `0002-DISCOVERY-framework-mapping-is-the-usp.md` correctly identifies the framework comparison engine as the core differentiator. However:

1. Only 4 metrics are mapped — 10 clusters remain unmapped
2. The mappings are field ID references — not real computation
3. The claim "one data entry, multiple framework outputs" requires that the source data actually comes from a real system. With hardcoded data, the "multi-framework output" is just showing the same hardcoded number with different field IDs

**The differentiating value is real IF**: the source data comes from a real ERP or meter. Without real data integration, the framework mapping is a display feature, not a compliance product.

### 3.4 Security Posture (Investor Demo)

From `rules/ui-backend-defense.md`, the current backend has no allowlist validation on any handler accepting user input:

```python
# dashboard.py — no server-side allowlist
@router.get("/trends/{metric_type}")  # metric_type is used directly in dict lookup
def trends(metric_type: str):
    return {"metric_type": metric_type, "data": TREND_DATA.get(metric_type, [])}  # .get() handles invalid input
```

The `framework_map` endpoint validates via dict key lookup (safe), but the pattern of trusting UI dropdown values without server-side allowlist appears in `App.jsx:614` where `metric` state controls API calls — no backend validation of `metric_type` against the allowlist of valid metrics.

### 3.5 The "5-tab Architecture" is Not in the Code

The `dashboard-tabs.md` spec describes a 5-tab layout that was the result of a uiux-designer analysis. The current `App.jsx` has 3 hardcoded tabs. Building the 5-tab layout requires:

- `Supply Chain` tab: supplier map + supplier table + `GovernancePanel` + `TraceabilityChain`
- `Risk & Alerts` tab: `RiskFlagsFeed` + `RiskFlagDetail` + `GeopoliticalPanel`
- `Engagement` tab: expanded `WhatsAppPreview` + `CoverageStats` + `SupplierResponseRate`

None of these components exist.

---

## PART 4: WHAT THE DEMO ACTUALLY DEMONSTRATES

### 4.1 The Honest Demo Value

The current demo proves:

1. The **UI design language** works (dark theme, green accents, metric cards, trend charts)
2. The **framework comparison concept** is visually compelling
3. The **WhatsApp supplier engagement** concept is credible to a non-technical investor
4. The **evidence chain** metaphor resonates with the "Big 4 audit" buyers care about

The demo does NOT prove:

1. Any integration works
2. Any real data flows
3. Any automated compliance mapping exists
4. Any risk alerting is functional

### 4.2 What Must Be Built Before the Demo Converts a Paying Customer

| Component                               | Current State   | Build Time (1 engineer) | Notes                                                  |
| --------------------------------------- | --------------- | ----------------------- | ------------------------------------------------------ |
| 5-tab layout (App.jsx)                  | 3 tabs          | 1 week                  | Add Supply Chain + Risk & Alerts tabs                  |
| `GET /api/dashboard/operations-summary` | Not implemented | 3 days                  | Return 5-cluster operations data                       |
| `GET /api/risk/flags`                   | Not implemented | 1 week                  | Risk flag generation + priority formula                |
| `GET /api/risk/flags/{id}/acknowledge`  | Not implemented | 2 days                  | Acknowledge workflow                                   |
| `GET /api/suppliers/risk-ranked`        | Not implemented | 1 week                  | Supplier list with risk scores                         |
| `GET /api/scope3/categories`            | Not implemented | 3 days                  | 8 Scope 3 categories with coverage                     |
| Framework mapping: add 6 more clusters  | 4 of 14         | 2 weeks                 | Water, Waste, Safety, Gender, Governance, Geopolitical |
| WhatsApp preview expansion (4 tiers)    | Tier 1 only     | 1 week                  | Tiers 2-4 questions added                              |
| **Total additional engineering**        |                 | **~7 weeks**            |                                                        |

---

## PART 5: CRITICAL RISKS FOR INVESTOR DEMONSTRATION

### Risk 1: "Demo-to-Production Gap is Visible to Technical Buyers"

A CFO who is also technically literate (or has a technical co-founder reviewing the demo) will notice within 5 minutes that every data point is hardcoded. The React app fetches from `http://localhost:8001/api` but the backend has no database, no real connections, no data pipeline. Any technical due diligence will surface this immediately.

**Mitigation**: Build the 5-cluster operations summary endpoint (`GET /api/dashboard/operations-summary`) with real data before any investor demo that includes a technical reviewer.

### Risk 2: The Pricing Doesn't Match the Implementation Cost

At $4–5K/month, implementation cost per customer must stay below ~$20K to maintain 60%+ gross margins. But the implementation requires connecting to factory ERPs that don't have standard APIs. The realistic implementation cost for the first 10 customers will be $20–30K each. This means the first 10 customers destroy margin.

**Mitigation**: Price the first cohort at $6–8K/month with the explicit understanding that early customers are co-developing the integration infrastructure. After pre-built connectors exist, drop to $4–5K/month for the next cohort.

### Risk 3: The "Framework Mapping" Moat Requires Real Data to Matter

Showing H&M's procurement team a dashboard that says "energy_kwh = 2,847,320 kWh mapped to CSRD ESRS E1-13" is compelling. Showing the same number as a hardcoded string with no source system attached is not. The framework mapping differentiation only works if the number comes from a real integration.

**Mitigation**: Build one real integration (SAP Business One utility invoice pull) before emphasizing framework mapping in demos. The single real data source makes all 4 hardcoded framework mappings look credible.

### Risk 4: Scope 3 Data Collection is the Hardest Part

The brief identifies WhatsApp as the channel for supplier data collection. The implementation plan correctly identifies this as requiring:

1. Meta Business Verification (2–8 weeks)
2. WhatsApp Business API integration
3. AI parser for free-text supplier responses
4. Multi-language support (Bengali, Vietnamese, Thai)

The demo shows a static WhatsApp conversation. No actual WhatsApp integration exists.

**Mitigation**: Engage Meta Business Verification immediately. Even if the WhatsApp integration is not live, the fact that the account is verified and the integration is in progress is a meaningful signal to buyers.

### Risk 5: Evidence Vault is Theatrical

The SHA-256 hash chain is hardcoded display text. No actual cryptographic computation exists. The `chain_valid` field is always `true` except for `diesel_consumed` which is hardcoded to `false` as an explicit demo artifact.

For a product whose primary sales argument is "Big 4 auditors can verify your data," a theatrical evidence chain is dangerous — it raises trust when it should be earning it.

**Mitigation**: Implement one real SHA-256 hash computation path for a single metric before any demo where an auditor or procurement professional is in the room.

---

## SUMMARY: CONVERGENCE CRITERIA

| Criterion                  | Status         | Finding                                                                                                    |
| -------------------------- | -------------- | ---------------------------------------------------------------------------------------------------------- |
| 0 CRITICAL findings        | ❌ FAIL        | Implementation infrastructure gap: 6 empty directories, 0 pre-built connectors                             |
| 0 HIGH findings            | ❌ FAIL        | Pricing/integration cost mismatch: $4-5K ACV doesn't cover $20-30K implementation                          |
| Spec compliance            | ❌ FAIL        | 2 tabs missing, 6 components missing, 15 planned routes unimplemented, 10 of 14 framework mappings missing |
| Code has tests             | ❌ FAIL        | `tests/` directories are empty — no test infrastructure exists                                             |
| New code has new tests     | ❌ FAIL        | No new modules have been written, let alone tested                                                         |
| Financial model viable     | ⚠️ CONDITIONAL | Viable at 40+ customers with 80%+ gross margin only after pre-built connectors exist                       |
| No mock data in production | ❌ FAIL        | All data is hardcoded; every API is a mock response                                                        |

**The implementation plan covers 24 weeks of work. The current codebase represents approximately 1–2 weeks of actual implementation.** Before any investor demonstration that includes a technical buyer or a proof-of-concept evaluation, the gap between demo and reality must be explicitly managed.
