# ESG SCRM — CRM Integration Strategy

**For**: Investor Business Plan
**Date**: 2026-05-17

---

## The Challenge

Mid-market buyers manage supplier relationships across multiple systems. ESG risk data that lives only in a standalone platform creates duplicate data entry — the exact problem the product is designed to eliminate. Customers need ESG intelligence inside the tools they already use to manage suppliers.

**Current product state (as of 2026-05-17)**: The prototype has no data export or integration capability whatsoever. All API responses serve hardcoded demonstration data. Even CSV export — the simplest integration path — does not exist yet. The phased rollout below represents new development, not existing features.

## Market Reality

| Market     | CRM Landscape                              | Key Insight                                                                 |
| ---------- | ------------------------------------------ | --------------------------------------------------------------------------- |
| Bangladesh | Majority have no CRM                       | Supplier management via WhatsApp, spreadsheets, ERP vendor modules          |
| Vietnam    | Zoho CRM + Salesforce (MNC subsidiaries)   | Manufacturing subsidiaries of global brands use parent company's Salesforce |
| India      | Zoho CRM (dominant mid-market), Freshsales | Zoho has 60M+ users in India; Freshworks is Chennai-based                   |
| Thailand   | Salesforce, Zoho, HubSpot                  | LINE-integrated CRM tools emerging                                          |
| Indonesia  | Salesforce, Zoho                           | Salesforce strong via MNC subsidiaries                                      |

**Key finding**: There is no single dominant CRM across our target markets. The anchor customer (Bangladesh garment factories) largely operates without a CRM. This is an advantage — our platform becomes their supplier ESG management system.

## Integration Architecture

We use the same connector pattern already built for ERP integrations (SAP Business One, NetSuite, Xero). The `ERPConnector` abstract class in our data orchestration layer is extended to a `CRMConnector` with bidirectional sync capabilities.

**Note**: The ERP connector architecture exists in the codebase but currently runs in demo mode. The SAP B1 adapter (`_demo_mode = True`) reads from a static CSV file rather than a live ERP system. CRM connector development will proceed in parallel with production ERP integration.

### Data Flow: ESG Platform → CRM

| Data Point                   | CRM Field                      | Why It Matters                                          |
| ---------------------------- | ------------------------------ | ------------------------------------------------------- |
| Supplier ESG risk score      | Risk rating on supplier record | Procurement sees ESG risk during sourcing decisions     |
| Compliance status            | Status badge                   | Flags suppliers who haven't responded to questionnaires |
| E/S/G individual scores      | Custom fields                  | Buyers filter suppliers by ESG category                 |
| Scope 3 contribution (tCO2e) | Emissions field                | Finance tracks carbon cost per supplier                 |
| Questionnaire response rate  | Engagement score               | Supplier relationship manager tracks engagement         |
| Next audit deadline          | Calendar event                 | Operations prepares for upcoming audits                 |
| ESG trend indicator          | Trend arrow                    | Identifies deteriorating suppliers before crisis        |

### Data Flow: CRM → ESG Platform

| CRM Data                      | How We Use It                                                        |
| ----------------------------- | -------------------------------------------------------------------- |
| Supplier contact info         | Pre-populates Supplier entity — zero manual entry during onboarding  |
| Contract value / annual spend | Spend-based Scope 3 estimation when direct supplier data unavailable |
| Contract renewal dates        | Prioritizes questionnaire timing around contract cycles              |
| Supplier tier classification  | Maps to ESG monitoring tier (determines questionnaire frequency)     |
| Account manager               | Routes ESG alerts to the right internal contact                      |

## Phased Rollout

| Phase                             | What Ships                                                 | Timeline    | Customer Impact                                     |
| --------------------------------- | ---------------------------------------------------------- | ----------- | --------------------------------------------------- |
| **1. CSV Export**                 | One-click CSV of supplier ESG scores                       | Week 1      | Every customer can load ESG data into any system    |
| **2. Webhook + Zapier Templates** | Real-time webhook events + pre-built Zapier/Make templates | Weeks 2–3   | Near-real-time sync for 5,000+ apps via iPaaS       |
| **3. Zoho CRM Connector**         | Native bidirectional sync                                  | Weeks 4–6   | Covers largest mid-market CRM (India anchor market) |
| **4. Salesforce Connector**       | Native bidirectional sync                                  | Weeks 7–10  | Enterprise buyers and MNC subsidiaries              |
| **5. HubSpot Connector**          | Native bidirectional sync                                  | Weeks 11–13 | Vietnam/Thailand market expansion                   |

## For Customers Without a CRM

For the majority of our Bangladesh and Indonesia customers who have no CRM — our platform IS their supplier management system. The supplier directory, ESG scores, communication history (WhatsApp), and compliance timeline are all in one place. This is not a gap; it is a feature.

## Investor Answer (When Asked)

> "We integrate with customer CRM systems in three ways. For customers without a CRM — the majority of our Bangladesh and Indonesia market — our platform is their supplier management system. For customers using Zoho or Salesforce — common in India and Vietnam — we provide direct API connectors that sync ESG risk scores and Scope 3 data into the supplier record. For any other system, we provide webhook endpoints and pre-built Zapier templates for real-time sync. CSV export ships from day one."

## Why This Deepens Our Moat

CRM integration makes the ESG platform part of the customer's daily workflow rather than a standalone tool. Once a procurement team sees ESG risk scores inside their CRM supplier records, and once historical Scope 3 data accumulates in the platform, switching to a competitor means losing that embedded intelligence. The CRM integration converts our product from "another reporting tool" into "part of the supplier management infrastructure" — significantly raising switching costs.

## Technical Risks and Mitigations

| Risk                                       | Mitigation                                                                                          |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| CRM sync creates duplicate suppliers       | Deduplication on name + country + industry. Upsert semantics.                                       |
| ESG score in CRM is stale                  | Define SLA for score refresh (daily for webhook, weekly for CSV). Display "last updated" timestamp. |
| Customer asks for Salesforce in month 1    | Zapier/Make template handles this immediately without native connector.                             |
| Multiple CRM systems across target markets | Phased rollout prioritizes by market penetration (Zoho first for India, then Salesforce).           |
