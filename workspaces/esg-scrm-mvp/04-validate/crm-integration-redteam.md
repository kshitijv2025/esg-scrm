# CRM Integration Readiness Red Team

**Date**: 2026-05-17
**Trigger**: Investor question — "How will you integrate this with the CRM of your customers?"
**Verdict**: Zero CRM integration capability today. The investor's question is legitimate. The existing ERP connector architecture is a structurally sound starting point. The minimum viable answer is a credible architecture sketch, not a working connector.

**Codebase audit update (2026-05-17)**: The product has zero data export capability of any kind — not even CSV export. All API responses serve hardcoded demonstration data. The ETL pipeline writes to SQLite but no API route reads from it. The SAP B1 adapter runs in `_demo_mode = True`. CRM integration is entirely greenfield development, building on top of the (not yet production) data pipeline.

---

## 1. CRM Systems By Market

| Market     | Primary CRM                    | Secondary              | Reality                                                             |
| ---------- | ------------------------------ | ---------------------- | ------------------------------------------------------------------- |
| Bangladesh | None (spreadsheets + email)    | Zoho CRM, local        | Very low CRM adoption. Procurement in ERP or paper.                 |
| Vietnam    | Zoho CRM, Salesforce (MNC)     | HubSpot, local         | Manufacturing subsidiaries of global brands use Salesforce.         |
| India      | Zoho CRM (dominant mid-market) | Salesforce, Freshsales | Zoho has 60M+ users in India. Freshworks is Chennai-based.          |
| Thailand   | Salesforce, Zoho CRM, HubSpot  | LINE-integrated tools  | LINE is dominant messaging; some CRM integrates with LINE Official. |
| Indonesia  | Salesforce, Zoho CRM           | Local systems          | Salesforce strong via MNC subsidiaries.                             |

**Critical finding**: No single dominant CRM. The majority of Bangladesh garment factories (anchor customers) do not use a CRM at all. Supplier relationships managed through WhatsApp, spreadsheets, and personal relationships.

---

## 2. Data Flow: ESG Platform → CRM

| ESG Data Point                                | CRM Field                    | Business Value                           | Priority |
| --------------------------------------------- | ---------------------------- | ---------------------------------------- | -------- |
| Supplier ESG risk score (composite)           | Supplier risk rating         | Procurement sees ESG risk at a glance    | P0       |
| Compliance status (compliant/at-risk/overdue) | Status badge                 | Flags non-responsive suppliers           | P0       |
| Individual ESG ratings (E, S, G)              | Custom ESG fields            | Buyer filters by category                | P0       |
| Scope 3 contribution (tCO2e)                  | Emissions field per supplier | Finance sees carbon cost per supplier    | P1       |
| Questionnaire response rate                   | Engagement score             | Supplier manager tracks engagement       | P1       |
| Confidence level of supplier data             | Data quality indicator       | Buyer knows which data is reliable       | P1       |
| Next audit deadline                           | Calendar event               | Operations prepares for upcoming audit   | P2       |
| ESG trend (improving/stable/declining)        | Trend arrow                  | Identifies deteriorating suppliers early | P2       |

## 3. Data Flow: CRM → ESG Platform

| CRM Data                                   | ESG Platform Use                                      | Priority |
| ------------------------------------------ | ----------------------------------------------------- | -------- |
| Supplier contact info (name, email, phone) | Pre-populate Supplier entity                          | P0       |
| Contract value / annual spend              | Spend-based Scope 3 estimation (fallback per Spec 02) | P0       |
| Contract renewal dates                     | Prioritize questionnaire timing                       | P1       |
| Supplier tier classification               | Map to ESG tier (tier1/tier2/tier3)                   | P1       |
| Supplier country / region                  | Localization and emission factor selection            | P1       |
| Relationship owner / account manager       | Route ESG alerts to correct internal contact          | P2       |

**Observation**: The Supplier entity already exists in the data model. CRM integration is primarily a sync mechanism to populate this existing entity — not new data architecture.

---

## 4. Recommended Phased Approach

| Phase | Approach                          | Timeline  | Value                                                 |
| ----- | --------------------------------- | --------- | ----------------------------------------------------- |
| 1     | CSV export of supplier ESG scores | 1–2 days  | Customer can load ESG data into any system            |
| 2     | Webhook + Zapier/Make template    | 3–5 days  | Near-real-time sync for customers using iPaaS         |
| 3     | Zoho CRM native connector         | 2–3 weeks | Native integration for largest mid-market CRM (India) |
| 4     | Salesforce native connector       | 3–4 weeks | Enterprise buyers                                     |
| 5     | HubSpot native connector          | 2–3 weeks | Vietnam/Thailand market expansion                     |

---

## 5. Investor Pitch Answer (60 seconds)

"We integrate with customer CRM systems in three ways, depending on their sophistication. For customers without a CRM — which is the majority of our Bangladesh and Indonesia market — our platform IS their supplier management system. For customers using Zoho or Salesforce — common in India and Vietnam — we provide direct API connectors that sync ESG risk scores, compliance status, and Scope 3 data into the supplier record. For any other system, we provide webhook endpoints and pre-built Zapier templates for near-real-time sync. We ship CSV export from day one, so no customer is blocked."

---

## 6. Gaps

| Gap                                       | Severity | Description                                                                                                               |
| ----------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------- |
| No CRM Connector architecture             | CRITICAL | Integration.type enum has no CRM types. No CRMConnector class. No bidirectional sync.                                     |
| No Webhook infrastructure                 | HIGH     | All data flows are inbound. No outbound push mechanism, payload definitions, or retry logic.                              |
| No SupplierESGScore composite             | HIGH     | Platform computes individual DataPoints but has no aggregated "ESG risk score" per supplier.                              |
| No bidirectional sync conflict resolution | MEDIUM   | No mechanism for data from two sources (ERP + CRM) that might conflict.                                                   |
| No public API for CRM inbound data        | MEDIUM   | No endpoint for external systems to push supplier data in.                                                                |
| No CSV export of supplier ESG data        | MEDIUM   | Evidence Vault exports audit packages, but no CSV of supplier-level ESG scores.                                           |
| No onboarding data flow from CRM          | LOW      | No "import suppliers from CRM" step in onboarding wizard.                                                                 |
| SAP B1 vendor module as de facto CRM      | DESIGN   | Bangladesh factories use SAP B1's vendor management module as CRM — should be primary integration path for anchor market. |

---

## 7. Risk Register

| Risk                                      | Likelihood | Impact | Mitigation                                                       |
| ----------------------------------------- | ---------- | ------ | ---------------------------------------------------------------- |
| Investor sees CRM absence as platform gap | High       | Medium | Phased roadmap answer ready. CSV export ships Phase 1.           |
| Customer asks for Salesforce in month 1   | Medium     | Medium | Zapier/Make template handles without native connector.           |
| Bangladesh customers have no CRM          | High       | Low    | Advantage — ESG platform becomes the supplier management system. |
| CRM sync creates duplicate suppliers      | Medium     | High   | Deduplication on name + country + industry. Upsert semantics.    |
| ESG score in CRM is stale                 | Medium     | Medium | Define SLA for score refresh. Display "last updated" timestamp.  |

---

## 8. Documents Affected

| Document                                                   | Change Required                              |
| ---------------------------------------------------------- | -------------------------------------------- |
| `specs/05-data-model.md` — Integration entity              | Add CRM types to enum                        |
| `specs/05-data-model.md` — Supplier entity                 | Add `crm_external_id` field                  |
| `specs/01-data-orchestration.md` — Connector architecture  | Define CRMConnector parallel to ERPConnector |
| `specs/02-supplier-collection.md` — Questionnaire dispatch | CRM as supplier data source                  |
| `01-analysis/07-business-model-replicability.md` — Moat    | Add CRM sync as retention mechanism          |

**Inconsistencies found:**

1. `specs/02-supplier-collection.md`'s `get_supplier_spend_from_erp()` assumes ERP is only spend source. CRM contract values are an alternative.
2. Supplier entity carries messaging IDs (whatsapp_number, line_id, wechat_id) but no CRM external ID.
3. Competitive analysis positions "ERP-agnostic" but does not extend to "CRM-agnostic."
