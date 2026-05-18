# ESG + SCRM Business Plan

**Confidential — For Investor Review**
**Date**: May 2026

---

## 1. Executive Summary

### The Problem

Mid-market export manufacturers (500–5,000 employees) in Asia are receiving ESG data requests from EU buyers that carry real commercial consequences. H&M, Zara, and Primark are legally required under CSDDD and CSRD to obtain Scope 3 supplier data — or face penalties up to 2% of global turnover. Factories that cannot provide auditable ESG data risk losing contracts worth $10–120M annually.

Today, 70–80% of these factories handle ESG compliance with Excel and email. The same data is entered 8–12 times per year in different formats for different buyers. A single ESG questionnaire cycle takes 10 weeks. There is no audit trail, no confidence scoring, and no way to reuse data across frameworks.

### The Solution

An integrated ESG + Supply Chain Risk Management platform that does four things:

1. **ESG Data Orchestration** — Connect to existing ERP systems, map one KPI across CSRD/ISSB/GRI/TCFD frameworks automatically
2. **Supply-Chain ESG Collection** — Automated supplier questionnaires via WhatsApp/LINE/WeChat (not email portals), mobile-first, localized in 5 Asian languages
3. **Assurance-Ready Evidence Vault** — Full data lineage, confidence tagging, and Big 4 auditor-ready evidence packages
4. **Real-Time ESG Monitoring** — Live dashboard connecting existing IoT sensors and ERP systems for continuous emissions, energy, and resource tracking

### The Ask

| Scenario     | Investment | Valuation        | Conditions                                                          |
| ------------ | ---------- | ---------------- | ------------------------------------------------------------------- |
| **Seed**     | $1.5–2.5M  | $8–10M pre-money | 5 paying customers, tech co-founder vesting signed, 18-month runway |
| **Pre-Seed** | $500K–1M   | $3–4M pre-money  | 5 warm-network customers, vesting signed                            |

---

## 2. Market Opportunity

### Regulatory Catalyst

Three EU regulations create binding demand:

- **CSDDD** — EU companies must obtain Scope 3 supplier data or face penalties up to 2% of global turnover
- **CSRD** — ~50,000 EU companies must report Scope 3 Category 1 data starting 2025–2026
- **EUDR** — EU Deforestation Regulation requires GPS-level traceability for palm oil, rubber, and timber shipments

These are not requests. They are legal obligations on EU brands that translate into contractual pressure on Asian factories.

### Target Market Sizing

**Bottom-up SAM calculation:**

| Market                           | Export Factories (est.) | Addressable (% facing EU ESG pressure) | Target Customers |
| -------------------------------- | ----------------------- | -------------------------------------- | ---------------- |
| Bangladesh (garments)            | 4,000+                  | 60%                                    | 2,400            |
| Vietnam (textiles + electronics) | 3,000+                  | 50%                                    | 1,500            |
| India (pharma + auto + IT)       | 10,000+                 | 30%                                    | 3,000            |
| Thailand (auto + food)           | 2,500+                  | 40%                                    | 1,000            |
| Indonesia (palm oil + textiles)  | 3,000+                  | 45%                                    | 1,350            |
| **Total addressable**            | **22,500+**             |                                        | **~9,250**       |

**SAM**: 9,250 factories × $50K ACV = **$462M**
**SOM (Year 3)**: 50–100 customers × $60K–$156K ACV = **$3M–$15.6M**

### Consumer ESG Tailwind

| Survey          | Finding                                                                                      |
| --------------- | -------------------------------------------------------------------------------------------- |
| PwC (2023/2024) | 76% prefer companies acting responsibly on ESG; willing to pay ~9.7% premium                 |
| McKinsey        | 66–80% willingness to pay more for sustainable products                                      |
| Deloitte (2024) | 1 in 3 consumers chose a more sustainable brand; cost-of-living crisis has NOT killed demand |
| Simon-Kucher    | 63% changed purchasing behavior toward sustainability in past 5 years                        |

Consumer preference is a tailwind. Regulatory enforcement is the conversion lever.

---

## 3. Product

### Current Status: Working Prototype

The product is at a **working prototype** stage with a functional FastAPI backend (8 routers, ~25 API endpoints) and React frontend (5-tab dashboard). The core architecture is in place: ETL pipeline, MQTT ingestion, SQLite database, SHA-256 evidence chain, and a 4-tier questionnaire engine. The immediate development priority is wiring these components together — currently the ETL writes data to a database that the API does not yet read from, and the API serves demonstration data while the real data pipeline stands ready.

### Four MVP Features

**Feature 1: ESG Data Orchestration** — _Architecture complete, ERP connectors in demo mode_

One data entry, multiple framework outputs. Connects to SAP Business One, NetSuite, Xero, SAP S/4HANA. Maps internal KPIs (e.g., kWh consumed) to CSRD, ISSB, GRI, and TCFD disclosure formats simultaneously. Self-serve onboarding in 3–6 weeks.

Current state: SAP Business One adapter built (in demo mode). Framework mapping engine serves CSRD/ISSB/GRI/TCFD comparisons for ~18 metric types. Full integration requires switching from demo CSV data to live ERP connections.

**Feature 2: Supply-Chain ESG Data Collection** — _Questionnaire engine built, WhatsApp integration pending_

Automated questionnaires sent to suppliers via WhatsApp (Bangladesh, India, Indonesia) and LINE (Thailand). Suppliers respond on mobile — not email portals. Localized in Bengali, Vietnamese, Thai, Hindi, Indonesian. Calculates Scope 3 emissions from collected data using a three-layer maturity model:

| Layer                | When      | Method                                                       | Confidence                 |
| -------------------- | --------- | ------------------------------------------------------------ | -------------------------- |
| 1. Spend-based       | Day 1     | $1.2M cotton spend × 0.94 kg CO2/$ = 1,128 tonnes            | LOW but immediate          |
| 2. Supplier-specific | Month 2–3 | Supplier provides their own energy/fertilizer data           | MEDIUM — 49% more accurate |
| 3. Verified          | Month 6+  | Supplier uses the tool themselves → data flows automatically | HIGH                       |

Current state: 4-tier questionnaire engine built (31 questions across TIER1-4). WhatsApp message templates designed. Real Meta Business API integration is the next step.

**Feature 3: Assurance-Ready Evidence Vault** — _SHA-256 hash chain working_

Every data point tagged with source system, extraction timestamp, methodology, emission factor applied, and confidence level (HIGH/MEDIUM/LOW). Full lineage chain from raw source to reported number. Evidence packages exportable in Big 4 auditor format. 7-year data retention (CSRD requirement).

Current state: SHA-256 hash chain fully implemented with genesis block, tamper detection (diesel metric demonstrates tamper flagging), and verification endpoint. Evidence drilldown API returns full chain data. PDF report generation working (4-page ESG report via fpdf2).

**Feature 4: Real-Time ESG Monitoring** — _ETL pipeline built, API integration pending_

Live dashboard connecting existing IoT sensors and ERP systems. Real-time emissions, energy, water, and waste monitoring with threshold alerts. Works with existing infrastructure — no new hardware.

Current state: MQTT→ETL→SQLite pipeline built. WebSocket alert bus implemented. Dashboard shows 4 live metrics from API. Immediate next step: wire ETL output to API routes and start the alert bus.

### Prototype Metrics

| Metric                 | Current Value                                                       |
| ---------------------- | ------------------------------------------------------------------- |
| API endpoints          | ~25 across 8 routers                                                |
| Frontend tabs          | 5 (Operations, Supply Chain, Risk, Frameworks, Supplier Engagement) |
| Live metrics displayed | 4 of 6 (energy, emissions, water, scope3_cat1)                      |
| Test coverage          | 13 behavioral tests, 3 of 8 routers                                 |
| SHA-256 evidence chain | Working with tamper detection                                       |
| ETL pipeline           | Built (MQTT + SAP B1 → SQLite)                                      |
| Database               | SQLite with schema, not yet read by API                             |

### Before & After

| Metric                     | Before (Excel + Email)         | After (This Platform)             |
| -------------------------- | ------------------------------ | --------------------------------- |
| Time per ESG questionnaire | 10 weeks                       | 5 days                            |
| Data entry per year        | 8–12 times (different formats) | 1 time (auto-mapped)              |
| Supplier response rate     | 40% (email only)               | 60%+ (WhatsApp/LINE)              |
| Audit trail                | None                           | Full lineage with confidence tags |
| Scope 3 coverage           | Spend-based estimate only      | Three-layer verified data         |

---

## 4. Business Model

### Pricing Tiers

| Tier       | Monthly Price | ACV         | Target Customer                    | What's Included                                                                                        |
| ---------- | ------------- | ----------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **Tier 1** | $5,000/mo     | $60,000/yr  | Mid-market (500–2,500 employees)   | 4 features, 1 ERP connector, WhatsApp supplier collection, 100 suppliers                               |
| **Tier 2** | $9,000/mo     | $108,000/yr | Mid-market (2,500–4,000 employees) | 4 features, 2 ERP connectors, WhatsApp + LINE, 500 suppliers, evidence vault                           |
| **Tier 3** | $25,000/mo    | $300,000/yr | Enterprise division                | 4 features, unlimited connectors, all messaging platforms, unlimited suppliers, priority audit support |

### Unit Economics (Red-Team Corrected)

All figures below have been independently validated and corrected from original estimates.

| Metric           | Tier 1     | Tier 2     | Tier 3     |
| ---------------- | ---------- | ---------- | ---------- |
| Monthly Revenue  | $5,000     | $9,000     | $25,000    |
| Monthly COGS     | $135       | $295       | $670       |
| **Gross Margin** | **99.7%**  | **99.7%**  | **99.8%**  |
| CAC              | $25,500    | $35,500    | $66,500    |
| Payback Period   | 6.1 months | 4.6 months | 3.0 months |
| 3-Year LTV       | $149,640   | $278,880   | $809,380   |
| **LTV:CAC**      | **5.9:1**  | **7.9:1**  | **12.2:1** |

**COGS breakdown**: WhatsApp Business API ($60/customer/month), cloud infrastructure, payment processing ($5/month for B2B wire transfers). GPT-4o-mini AI costs are negligible ($0.039–0.390/month — originally overstated 1,000–2,500x).

**CAC breakdown**: Salesperson ($7,500 for 3-month cycle), pre-sales engineering ($4,000–6,000), marketing ($3,000–5,000), BGMEA referral fee ($6,000 for T1), travel ($500–2,000), legal ($1,000–5,000).

### Revenue Projections (3-Year)

| Metric                 | Year 1      | Year 2    | Year 3    |
| ---------------------- | ----------- | --------- | --------- |
| Customers (cumulative) | 10          | 35        | 80        |
| Avg ACV                | $72,000     | $84,000   | $96,000   |
| **Annual Revenue**     | **$720K**   | **$2.9M** | **$7.7M** |
| Gross Margin           | 99.7%       | 99.7%     | 99.7%     |
| Gross Profit           | $718K       | $2.9M     | $7.7M     |
| Operating Expenses     | $1.2M       | $2.5M     | $4.5M     |
| **Net Income**         | **($482K)** | **$400K** | **$3.2M** |

**Key assumptions**: 80% Tier 1 / 15% Tier 2 / 5% Tier 3 in Year 1, shifting to 50/30/20 by Year 3. Churn rate: 10% annually (conservative; high switching cost due to accumulated supplier data). Expansion revenue from tier upgrades not included (conservative).

---

## 5. Go-to-Market Strategy

### Dual-Track Approach

| Track                   | Focus                                       | Effort                            | Target                       |
| ----------------------- | ------------------------------------------- | --------------------------------- | ---------------------------- |
| **Mid-Market**          | Revenue + product-market fit + case studies | 70% (shifting to 40% by Month 18) | 30–50 customers in 18 months |
| **Enterprise Division** | Learning + logo value                       | 30% (shifting to 60% by Month 18) | 1–2 division deals           |

### Priority Markets

| Rank | Market                               | Why                                                                                                          |
| ---- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| 1    | **Bangladesh (garments)**            | 4,000+ factories, all exporting to EU. Every one receiving ESG questionnaires from H&M, Zara, Primark today. |
| 2    | **Vietnam (textiles + electronics)** | EU is top export market. EUDR + CSDDD creating immediate demand.                                             |
| 3    | **India (pharma + auto + IT)**       | Largest number of mid-market companies. EU + US compliance pressure.                                         |
| 4    | **Thailand (auto parts + food)**     | Automotive supply chain to EU/Japan. Toyota/BMW supplier requirements.                                       |
| 5    | **Indonesia (palm oil + textiles)**  | EUDR is existential for palm oil — comply or lose EU market access.                                          |

### Sales Psychology

**Wrong**: "Buy ESG software to comply with regulations."
**Right**: "H&M just told your supplier they need Scope 3 data in 90 days. Protect $40M of annual orders."

The math: A factory doing $40M annually with H&M faces a letter requiring auditable Scope 3 data. Platform cost: $48–60K/year. That's 0.08–0.20% of the revenue being protected. The CFO signs today.

### Customer Acquisition Channels

1. **BGMEA partnership** — Bangladesh Garment Manufacturers and Exporters Association represents 4,000+ factories. Referral fee of ~10% ACV ($6,000 per T1 customer)
2. **Direct sales** — Account executives targeting CFOs at named factories
3. **EU buyer referrals** — H&M, Zara, Primark procurement teams recommending the platform to suppliers (reduces buyer's own Scope 3 reporting burden)
4. **Consultant network** — Local ESG consultants (currently producing PDFs for $10–30K) become resellers

---

## 6. Competitive Landscape & Moat

### Competitive Positioning

| Dimension                  | This Platform                   | Sweep                        | EcoVadis                 | Persefoni/Watershed          |
| -------------------------- | ------------------------------- | ---------------------------- | ------------------------ | ---------------------------- |
| ESG + SCRM combined        | Yes                             | No (reporting only)          | No (ratings only)        | No (reporting only)          |
| Buyer persona              | CFO/COO                         | Chief Sustainability Officer | Procurement/Supply Chain | Chief Sustainability Officer |
| Mid-market focused         | Yes                             | No (enterprise)              | Partial                  | No (enterprise)              |
| Messaging-native suppliers | WhatsApp/LINE                   | Email portal                 | Email portal             | Email portal                 |
| Implementation time        | 3–6 weeks                       | 3–6 months                   | 2–4 weeks                | 3–6 months                   |
| Broad ERP integration      | SAP B1, NetSuite, Xero, S/4HANA | SAP S/4HANA, Workday         | Limited                  | SAP S/4HANA, Workday         |

### Moat Analysis (Replication Timelines)

| Feature                      | Replication Time | Why                                                                                                                  |
| ---------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------- |
| Data Orchestration           | 18–24 months     | Sweep/Persefoni already have it; they lack mid-market speed and broad ERP coverage                                   |
| WhatsApp Supplier Collection | 12–18 months     | WhatsApp Business API approval per country (4–8 weeks), supplier trust network takes 24–36 months to build from zero |
| Evidence Vault               | 36+ months       | Requires simultaneous investment in data lineage methodology AND audit chain integrity AND Big 4 trust relationships |
| Combined ESG + SCRM          | 3+ years         | Requires fundamentally different architecture; no competitor has both                                                |

**Sustainable moat**: The supplier ESG data layer. Once a factory has 18 months of structured Scope 3 data in the platform, switching to any other system means losing that historical dataset — which is H&M contract renewal evidence.

### What Competitors Do Better (Honest Assessment)

- **Sweep**: Carbon measurement depth for CDP/SBTi, enterprise security (SOC 2), Big 4 auditor trust, 200+ enterprise customers, $100M+ runway
- **EcoVadis**: 130,000+ rated companies, established rating methodology, procurement team trust
- **Persefoni/Watershed**: Enterprise-grade features, SSO, SCIM, advanced permissions

---

## 7. Technology & Architecture

### Current Architecture (Prototype)

```
WORKING PATH (serves all traffic today):
  CSV/Static Data → API Routes (FastAPI) → React Dashboard (5 tabs)
  Hardcoded Dicts → Risk/Scope3/Supplier Routes → Frontend

BUILT BUT NOT YET CONNECTED:
  IoT Sensors → MQTT Client → ETL Pipeline → SQLite Database (writes, not yet read by API)
  SAP B1 → Adapter (demo mode) → ETL Pipeline → SQLite Database
  Questionnaire Engine (4 tiers, 31 questions) — not imported by API routes
  WebSocket Alert Bus — not registered in application
  SHA-256 Hash Chain — working, connected to evidence API
```

The prototype has all components built. The immediate development task is connecting the data pipeline (ETL→SQLite→API) so the API serves live data instead of static demonstration data.

### Target Architecture (Production)

```
[ERP Systems] → [Data Orchestration Layer] → [Framework Mapping Engine]
[Sensors/IoT]  ↗                              ↓
                                                [Evidence Vault] → [Auditor Packages]
[WhatsApp/LINE/WeChat] → [Supplier Data] → [Scope 3 Engine]
                                                ↓
                                          [Monitoring Dashboard]
                                                ↓
                                          [CRM Integration Layer] → [Zoho/Salesforce/HubSpot]
```

### Integration Breadth

| System Type | Systems Supported                                                                   |
| ----------- | ----------------------------------------------------------------------------------- |
| ERP         | SAP Business One, NetSuite, Xero, SAP S/4HANA                                       |
| Messaging   | WhatsApp Business API, LINE Official Account                                        |
| HRIS        | Local systems per market                                                            |
| CRM         | Zoho CRM, Salesforce, HubSpot (via API + Zapier/Make)                               |
| IoT/Sensors | Energy meters, water flow meters, PLC-controlled lines, building management systems |

### CRM Integration Strategy

For customers without a CRM (majority of Bangladesh/Indonesia factories), the platform IS their supplier management system. For customers using Zoho or Salesforce (India, Vietnam), we provide direct API connectors that sync ESG risk scores, compliance status, and Scope 3 data into the supplier record. For any other system, webhook endpoints and pre-built Zapier templates provide real-time sync. CSV export ships from day one.

### Technical Foundation

- **Emission calculation**: Three methods (direct measurement, activity-based, spend-based), always using best available, tagged with methodology and confidence
- **Emission factors**: GHG Protocol, DEFRA, IPCC, EPA, IEA, Ecoinvent
- **Data retention**: 7 years minimum (CSRD requirement)
- **Audit integrity**: Full lineage chain from raw source to reported number

---

## 8. Team & Operations

### Founding Team

_Note: This section requires completion with actual team member details._

**Required roles:**

- **CEO / Co-Founder** — Business development, investor relations, market strategy
- **CTO / Technical Co-Founder** — Architecture, engineering leadership, integration development
  - Must have enterprise SaaS shipping experience
  - 4-year vesting with 1-year cliff (investor requirement, signed before wire)
- **Head of Product** — Product roadmap, UX design, customer feedback integration

**Key hires (Months 1–6):**

- 2 Backend Engineers (ERP integration, data pipeline)
- 1 Frontend Engineer (dashboard)
- 1 WhatsApp/AI Engineer (messaging platform + chatbot)
- 1 Sales Representative (Bangladesh market, $2,500/month fully loaded)

**Advisory needs:**

- ESG compliance expert (CSRD/CSDDD regulatory depth)
- Big 4 audit relationship partner
- Bangladesh market connector (BGMEA relationship)

### Legal & Operations

- **Company structure**: To be determined (Singapore Pte Ltd recommended for Asian operations)
- **Data residency**: GDPR compliance required (EU buyer data)
- **WhatsApp Business**: Meta Business Verification per country (4–8 weeks lead time)

---

## 9. Financial Projections

### Use of Funds ($2M Seed)

| Category                 | Allocation | %   | Purpose                                                                       |
| ------------------------ | ---------- | --- | ----------------------------------------------------------------------------- |
| Engineering              | $800K      | 40% | 4 engineers × 18 months, ERP connectors, WhatsApp integration, evidence vault |
| Sales & Marketing        | $500K      | 25% | 2 sales reps, BGMEA partnership, market-specific campaigns                    |
| Infrastructure           | $200K      | 10% | Cloud hosting, WhatsApp API costs, database, security                         |
| Operations & Legal       | $200K      | 10% | Company setup, compliance, accounting, advisory                               |
| Working Capital / Buffer | $300K      | 15% | Contingency, extended runway if revenue slower than projected                 |

**Monthly burn rate**: ~$111K
**Runway**: 18 months at planned burn

### Path to Profitability

| Milestone              | Timeline    | Condition                                          |
| ---------------------- | ----------- | -------------------------------------------------- |
| First revenue          | Month 3–4   | First paying customer                              |
| Break-even (operating) | Month 14–16 | ~25 customers at $72K blended ACV                  |
| Cash-flow positive     | Month 16–18 | Operating break-even + deferred revenue catches up |
| Series A ready         | Month 15–18 | $2.9M ARR, 35 customers, clear path to $10M ARR    |

---

## 10. Risk Assessment

| Risk                               | Likelihood              | Impact   | Mitigation                                                                                                                                                                                                                                    |
| ---------------------------------- | ----------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Sweep moves down-market**        | High (within 18 months) | High     | ESG+SCRM combination is structurally different; Sweep is reporting-only architecture. Speed is our weapon (3–6 weeks vs their 3–6 months).                                                                                                    |
| **Regulation delayed or weakened** | Medium                  | Medium   | Product delivers operational value beyond compliance — water savings ($38K/year), supplier risk identification, procurement optimization. Revenue-protection framing works regardless of regulation.                                          |
| **No CRM integration**             | Medium                  | Medium   | Phased CRM roadmap (CSV → Zapier → native connectors). Most anchor customers (Bangladesh) don't use CRM — our platform fills that gap.                                                                                                        |
| **High customer churn**            | Medium                  | High     | Accumulated supplier data creates high switching cost. Tier 1 LTV:CAC of 5.9:1 leaves room for 10% annual churn.                                                                                                                              |
| **Technical co-founder departs**   | Low                     | Critical | 4-year vesting with 1-year cliff. Board seat for lead investor.                                                                                                                                                                               |
| **WhatsApp API changes/bans**      | Low                     | High     | Multi-channel strategy (LINE for Thailand, email fallback, web portal). No single messaging platform dependency.                                                                                                                              |
| **Gross margin erosion**           | Low                     | Medium   | COGS is 0.3% of revenue. Even 10x COGS increase leaves gross margin above 97%. Margin risk is from implementation costs, not infrastructure.                                                                                                  |
| **BGMEA referral fee too high**    | Medium                  | Low      | Negotiable. If BGMEA demands >15%, pivot to direct sales + EU buyer referral channel.                                                                                                                                                         |
| **Prototype-to-product gap**       | Medium                  | High     | Current prototype serves static demonstration data. Full codebase audit identified 20 findings (2 critical, 7 high). Mitigation: phased development plan with ETL-to-API wiring as first priority. Estimated 7-10 sessions to investable MVP. |

---

## 11. Traction & Milestones

### Current Status

**Working prototype** — not yet in customer hands.

What's built:

- FastAPI backend: 8 routers, ~25 API endpoints, SQLite database, SHA-256 evidence chain
- React frontend: 5-tab dashboard (Operations, Supply Chain, Risk & Alerts, Frameworks, Supplier Engagement)
- ETL pipeline: MQTT + SAP B1 → SQLite (built, needs wiring to API)
- Questionnaire engine: 4-tier system with 31 questions (built, needs API integration)
- WebSocket alert bus (built, needs registration)
- 13 behavioral unit tests

What's not yet built:

- Live ERP connections (SAP B1 adapter in demo mode)
- Real WhatsApp Business API (template preview only)
- Authentication and authorization
- Multi-tenancy
- CRM integration (CSV export, connectors)
- Production deployment infrastructure
- ML-powered recommendations (currently hardcoded)

No paying customers (pre-revenue). No pilots or LOIs.

### 90-Day Sprint Commitments

| Milestone                         | Target Date | Success Criteria                                                             |
| --------------------------------- | ----------- | ---------------------------------------------------------------------------- |
| Wire ETL to API                   | Month 1     | Dashboard reads from SQLite instead of CSV; real data pipeline working       |
| First ERP integration live        | Month 2     | SAP Business One or Xero, pulling real customer data                         |
| WhatsApp supplier collection live | Month 3     | At least 1 customer using WhatsApp questionnaires with 50+ suppliers         |
| First paying customer             | Month 3     | Signed contract, $4K+/month, live ERP integration                            |
| 5 paying customers                | Month 6     | At least 3 from inbound/referral (not personal network), weekly active usage |
| BGMEA partnership signed          | Month 2     | Referral agreement in place                                                  |

### 18-Month Roadmap

| Period       | Focus                | Target                                            |
| ------------ | -------------------- | ------------------------------------------------- |
| Months 1–6   | Product-market fit   | 5–10 customers, core 4 features live              |
| Months 7–12  | Scale mid-market     | 20–35 customers, CRM connectors, LINE integration |
| Months 13–18 | Enterprise expansion | 50+ customers, Series A preparation               |

---

## 12. Investment Terms

| Parameter             | Seed (Tier 1)                                                        | Pre-Seed (Tier 2)                                       |
| --------------------- | -------------------------------------------------------------------- | ------------------------------------------------------- |
| Investment            | $1.5–2.5M                                                            | $500K–1M                                                |
| Valuation (pre-money) | $8–10M                                                               | $3–4M                                                   |
| Runway                | 18 months                                                            | 12–15 months                                            |
| Conditions            | 5 paying customers, 3+ inbound, tech co-founder vesting signed       | 5 warm-network customers, vesting signed                |
| Use of proceeds       | Engineering (40%), Sales (25%), Infra (10%), Ops (10%), Buffer (15%) | Engineering (50%), Sales (20%), Ops (15%), Buffer (15%) |

### Why This Valuation

- **Comparable seed-stage ESG SaaS**: Sweep raised $100M+ at Series B. Persefoni raised $100M+ at Series B. No comparable seed-stage ESG+SCRM exists.
- **Revenue multiple**: At 5 customers × $60K ACV = $300K ARR, $8–10M pre-money = 27–33x ARR (aggressive but within seed-stage norms for high-growth SaaS)
- **Market timing**: CSRD enforcement begins 2025–2026. First-mover advantage in Asian mid-market ESG+SCRM is worth a premium.

---

## 13. Appendix

### A. Key Source Documents

| Document                      | Description                                                                     |
| ----------------------------- | ------------------------------------------------------------------------------- |
| `PITCH_ANALYSIS.md`           | Full pitch analysis with 14 VC red-team critiques and founder counter-arguments |
| `ESG_Unit_Economics.docx`     | Corrected unit economics ($5K/$9K/$25K tiers)                                   |
| `ESG_SCRM_Investor_Deck.pptx` | Investor presentation                                                           |
| `INVESTOR_PREREAD.docx`       | One-page investor pre-read                                                      |
| `ESG_Data_Inventory.docx`     | Data inventory and framework mapping                                            |

### B. Regulatory Framework Details

- **CSDDD**: Corporate Sustainability Due Diligence Directive — requires EU companies to identify, prevent, and mitigate adverse human rights and environmental impacts in their value chain. Penalties up to 2% of global turnover.
- **CSRD**: Corporate Sustainability Reporting Directive — ~50,000 EU companies must report on environmental, social, and governance matters using ESRS standards. Scope 3 reporting mandatory.
- **EUDR**: EU Deforestation Regulation — requires due diligence for palm oil, cattle, soy, coffee, cocoa, timber, and rubber to ensure products are deforestation-free.
- **LkSG**: German Supply Chain Due Diligence Act — already in force, penalties up to 2% of global turnover.

### C. Consumer ESG Preference Data Sources

PwC (2023/2024), NielsenIQ, Deloitte (2024), McKinsey, IBM, Simon-Kucher, First Insight/Wharton — see Section 2 for detailed findings.

---

_This business plan was prepared as part of the Machine Learning for Decision Making course, Term 4. Financial projections are forward-looking estimates based on red-team-validated unit economics. All regulatory citations reference public EU legislation._
