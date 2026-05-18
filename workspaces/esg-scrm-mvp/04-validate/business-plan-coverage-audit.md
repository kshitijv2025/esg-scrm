# Business Plan Coverage Audit — ESG SCRM MVP

**Date**: 2026-05-17
**Trigger**: Investor feedback — "Prepare a business plan to pitch to share"
**Standard**: 13-section investor business plan

---

## Overall Assessment

Substantial content exists for a credible investor business plan (~70% complete). Strongest coverage: problem definition, product description, competitive analysis, technical architecture. Weakest: team/operations, traction/milestones, financial projections beyond unit economics.

**Critical context — product codebase audit (2026-05-17)**: A full codebase audit revealed the product is at "demo prototype" stage. While the architecture is sound (FastAPI backend, React frontend, ETL pipeline, SQLite database, SHA-256 evidence chain), all API routes currently serve hardcoded or CSV-backed data. The ETL pipeline writes to SQLite but no API route reads from it. Key built-but-disconnected modules: questionnaire engine (4-tier, 31 questions), WebSocket alert bus, MQTT ingestion. The business plan should present the product honestly as a working prototype with clear development milestones, not as a near-complete product.

**Critical blockers**: The investor deck and unit economics documents contain errors identified in prior red-team validation (4 CRITICAL in unit economics, 5 CRITICAL in investor deck) that must be corrected before any business plan is assembled.

---

## Section-by-Section Coverage

### 1. Executive Summary / Problem Statement — EXISTS

Strong content across multiple files. `PITCH_ANALYSIS.md` Part 1D defines the core problem ("same data entered 8-12 times per year in different formats"), provides before/after workflow (10 weeks → 5 days), and quantifies mid-market ESG today (70-80% use Excel+Email at 40-60 hours per cycle). Value-audit adds CFO-buyer perspective with revenue-protection framing. Brief scopes problem to mid-market facing CSRD/CSDDD compliance.

### 2. Market Opportunity (TAM/SAM/SOM) — PARTIAL

Deck claims "$50B+ TAM" but validation report flags this as Bangladesh garment export value, not ESG software TAM. Correct approach: "4,000 factories × $50K ACV = $200M SAM" — not formally calculated. Content exists for target geography prioritization (5 Asian markets ranked), specific target companies by country, H&M order value data, consumer ESG preference surveys. **Missing**: formal TAM/SAM/SOM with methodology, CAGR for ESG compliance software, European buyer-side market sizing.

### 3. Solution / Product Description — EXISTS (Updated for Prototype Reality)

Four MVP features with sub-component breakdowns, complexity ratings, cross-feature dependencies, and critical path timeline (17-23 weeks). Technical foundation with emission calculation methods, water usage examples, and Scope 3 flywheel. Full dashboard UX specification with 5-tab architecture, 14 ESG clusters, and wireframes. Seven technical spec files.

**Codebase audit update**: The prototype has ~25 API endpoints and a 5-tab React dashboard, but all data is hardcoded/CSV. Key modules built but not wired: ETL→SQLite pipeline, 4-tier questionnaire engine, WebSocket alert bus. SHA-256 evidence chain is working. The product section should clearly distinguish between what is built vs. what remains.

### 4. Business Model — PARTIAL (Has Critical Errors)

Three pricing tiers ($5K/$9K/$25K per month) with unit economics, but unit economics red team found **4 CRITICAL errors**: GPT-4o-mini COGS overstated 1,000-2,500x, Stripe fee uses wrong rate, BGMEA referral fee internally inconsistent, CUL structure incoherent. Investor deck has GBP/USD mixing and LTV matching no tier. Corrected figures exist in red team reports. **Missing**: revenue projections with annual customer counts per tier, expansion revenue thesis, churn assumptions, currency strategy.

### 5. Go-to-Market Strategy — EXISTS

Dual-track strategy (mid-market 70% + enterprise 30%), five priority markets ranked with specific target companies, messaging platform strategy per market, sales psychology ("sell revenue protection, not compliance"). **Missing**: marketing strategy beyond direct sales, BGMEA partnership details, sales team hiring plan.

### 6. Competitive Landscape and Moat — EXISTS (Very Strong)

Four structural USPs vs Sweep with moat depth. EcoVadis differentiation with 5 weaknesses. Feature-by-feature competitive gap analysis. Replicability timelines (F1: 18-24mo, F2: 12-18mo, F3: 36+mo, F4: 6-12mo). Honest "what competitors do better" assessment.

### 7. Technology and Architecture — EXISTS (Needs Prototype-State Transparency)

Extremely detailed — possibly too detailed for a business plan audience. Full architecture, failure mode analysis (12 failure modes, 6 technical risks), dashboard specification, implementation status (4 of 14 ESG clusters covered). **Missing for business plan**: simplified 1-page architecture overview for non-technical investors.

**Codebase audit update**: The actual architecture has two disconnected data paths. The ETL pipeline writes to SQLite but no API route reads from it. The SAP B1 adapter runs in explicit demo mode. The business plan should present current state (demo data path) and target state (live data path) with clear milestones bridging the gap.

### 8. Team and Operations — MISSING

Almost no content. VC critique describes "three MBA students pitching a data engineering product with no technical founder," later corrected to "technical co-founder with enterprise SaaS experience." Investor required "4-year vesting, 1-year cliff, signed before wire." **Missing**: team bios, roles and responsibilities, org chart, hiring plan, advisory board, key partnerships, operations plan, legal structure.

### 9. Financial Projections (3-5 Year) — PARTIAL (Weak)

Only per-customer unit economics exist (corrected COGS, gross margins, CAC, LTV, payback, LTV:CAC). Revenue targets of "30-50 mid-market customers in 18 months" at $48-60K ACV stated in GTM. **Missing entirely**: 3-year revenue projection, expense projection, path to profitability, cash flow projections, key assumptions, scenario analysis.

### 10. Risk Assessment and Mitigation — EXISTS (Needs Consolidation)

Extensive risk analysis across 6+ documents: 12 technical failure modes, 8 buyer-perspective risks, 5 competitive risks, 14 VC red-team critiques, 5 CRITICAL + 9 HIGH findings on the investor deck. **Missing for business plan**: single consolidated risk register table with investor-friendly language.

### 11. Use of Funds / Investment Ask — PARTIAL

Seed round terms: $1.5-2.5M at $8-10M pre-money (Tier 1) or $500K-1M at $3-4M pre-money (Tier 2), with conditions (5 paying customers, vesting signed), 18-month runway. **Missing**: allocation across categories, milestones tied to funding, monthly burn rate, cash-out date, bridge/pre-seed terms, cap table implications.

### 12. Traction and Milestones — MISSING

Pre-revenue with no pipeline. Working demo/prototype exists (dashboard with 3 tabs, API routes, WhatsApp preview). "90-day sprint to 5 customers" commitment exists. **Missing**: actual customers, pilots, LOIs, waitlist, revenue, usage metrics. Must honestly state pre-revenue status and focus on the 90-day sprint.

### 13. CRM Integration Strategy — PARTIAL

ERP integration well-covered (SAP B1, NetSuite, Xero, S/4HANA). HRIS integration identified for workforce clusters. Messaging platforms documented. **Missing**: CRM specifically (Salesforce, HubSpot, Pipedrive), integration priority ordering, per-system timeline, integration partner strategy.

---

## Summary Scorecard

| #   | Section               | Rating  | Action Needed                              |
| --- | --------------------- | ------- | ------------------------------------------ |
| 1   | Executive Summary     | EXISTS  | Reuse as-is                                |
| 2   | Market Opportunity    | PARTIAL | Derive TAM/SAM/SOM with methodology        |
| 3   | Solution/Product      | EXISTS  | Reuse as-is                                |
| 4   | Business Model        | PARTIAL | Fix 4 CRITICAL errors, build revenue model |
| 5   | Go-to-Market          | EXISTS  | Minor: add marketing strategy              |
| 6   | Competitive/Moat      | EXISTS  | Reuse as-is                                |
| 7   | Technology            | EXISTS  | Simplify for non-technical audience        |
| 8   | Team/Ops              | MISSING | Write from scratch                         |
| 9   | Financial Projections | PARTIAL | Build 3-year P&L                           |
| 10  | Risk Assessment       | EXISTS  | Consolidate into single table              |
| 11  | Use of Funds          | PARTIAL | Write allocation breakdown                 |
| 12  | Traction              | MISSING | Frame pre-revenue honestly                 |
| 13  | CRM Integration       | PARTIAL | Address CRM specifically                   |

---

## Top 5 Priority Actions

1. **Correct CRITICAL errors** in unit economics and investor deck before reusing any figures (GPT-4o-mini COGS overstated 1,000-2,500x, wrong ESRS field IDs, Scope 3 figure 50x too low)
2. **Write the team section** from scratch — was the VC's first critique and remains unaddressed
3. **Build 3-year financial projections** using corrected unit economics — currently only per-customer metrics exist
4. **Derive TAM/SAM/SOM** with disclosed methodology — "$50B+" is export value, not software TAM
5. **Write use-of-funds allocation** showing $1.5-2.5M seed spend across engineering, sales, marketing, infrastructure, operations with milestones

---

## Key Source Files

| File                                             | Covers Sections                                          |
| ------------------------------------------------ | -------------------------------------------------------- |
| `PITCH_ANALYSIS.md`                              | 1-7, 10-11 (single strongest source)                     |
| `04-validate/unit-economics-redteam.md`          | 4 (corrected figures — must use these)                   |
| `04-validate/investor-deck-validation.md`        | 4 (corrections — must apply before reuse)                |
| `01-analysis/07-business-model-replicability.md` | 6 (competitive moat with replication timelines)          |
| `01-analysis/03-value-audit.md`                  | 1, 5 (CFO-buyer perspective, revenue-protection framing) |
| `01-analysis/02-requirements-breakdown.md`       | 3, 7 (product + architecture)                            |
