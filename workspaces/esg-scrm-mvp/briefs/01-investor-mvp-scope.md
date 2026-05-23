# Investor-Validated MVP Scope

## Source

Investor feedback call — investors narrowed focus to 4 features for initial build.

## The Four Features

### Feature 1: ESG Data Orchestration Platform

A mapping engine that takes one internal KPI and outputs it across multiple frameworks (CSRD, ISSB, GRI, TCFD). One data entry, multiple framework outputs.

**What it must do:**

- Connect to company ERP (SAP Business One, NetSuite, Xero, SAP S/4HANA)
- Pull data from existing systems
- Map one internal KPI (e.g., kWh consumed) to multiple disclosure frameworks simultaneously
- Output: structured data in CSRD, ISSB, GRI, TCFD formats

**Constraints:**

- Must work for mid-market companies (500–5,000 employees)
- Implementation must be 3–6 weeks, not 3–6 months
- Self-serve onboarding, no consultants required

### Feature 2: Supply-Chain ESG Data Collection

Automated supplier questionnaires and data feeds for Scope 3 emissions. Suppliers respond via WhatsApp/LINE/WeChat — not email portals.

**What it must do:**

- Send automated ESG questionnaires to suppliers
- Collect data via WhatsApp, LINE, and WeChat (per market)
- Also support email and web portal as fallback
- Calculate Scope 3 emissions from collected supplier data

**Constraints:**

- Mid-market suppliers typically have no dedicated ESG staff
- Must work on mobile-first (suppliers checking WhatsApp, not email)
- Localization required: Bengali (Bangladesh), Vietnamese, Thai, Hindi, Indonesian

### Feature 3: Assurance-Ready Evidence Vault

Full audit trail with data lineage. Every number tagged with source, methodology, and confidence level. Big 4 auditors can verify without manual evidence gathering.

**What it must do:**

- Every data point tagged with: source system, extraction timestamp, methodology used, emission factor applied, confidence level (HIGH/MEDIUM/LOW)
- Full lineage chain from raw source to reported number
- Export evidence packages in auditor-accepted format
- Support Big 4 audit workflows (Deloitte, EY, PwC, KPMG)

**Constraints:**

- Evidence must survive a Big 4 audit review without manual intervention
- Confidence tagging must be consistent and defensible
- Data retention: 7 years minimum (CSRD requirement)

### Feature 4: Real-Time ESG Monitoring

Live sustainability command center connecting to existing IoT sensors and ERP systems. Real-time emissions, energy, and resource monitoring with threshold alerts.

**What it must do:**

- Read existing sensor data through ERP integration (no new hardware)
- Mid-market export manufacturers already have: smart energy meters, water flow meters, PLC-controlled production lines, building management systems
- Display live dashboard: emissions, energy, water, waste
- Threshold alerts: "Plant X exceeded daily emissions target by 15%"
- Real-time data alongside compliance data in same view

**Constraints:**

- Higher-frequency data pull than batch reporting (hourly or continuous vs quarterly)
- Alert system must be actionable, not noisy
- Works even when sensors are partial/coarse

## Target Customer

Mid-market companies (500–5,000 employees) globally, starting with Asia:

1. Bangladesh: garment factories (DBL Group, Envoy Textiles, Beximco Textiles)
2. Vietnam: textiles + electronics
3. India: pharma + auto components
4. Thailand: auto parts + food
5. Indonesia: palm oil + textiles

## Buyer

CFO / COO — not Chief Sustainability Officer. ESG is a side project handed to them by the board.

## Target Pricing

- $24–60K/year for mid-market
- $60–150K/year for enterprise divisions
- 80%+ gross margin target

## What This Brief Does NOT Cover (explicitly deferred)

- AI Copilot (investor said: focus on 4 first)
- Supplier Intelligence Graph (investor said: focus on 4 first)
- ESG ROI Engine (not in the 4, to be added later)
- Supplier network monetization (Year 2+)
- Enterprise-wide deals (stick to division-level for now)

## Success Criteria

1. Platform auto-maps 70–80% of incoming buyer questionnaires to existing ERP data
2. Supplier response rate via WhatsApp/LINE/WeChat > 60%
3. Evidence vault passes Big 4 audit review on first submission
4. Real-time monitoring dashboard live within 3–6 weeks of ERP integration
5. First customer live and using all 4 features within 60 days of contract signing
