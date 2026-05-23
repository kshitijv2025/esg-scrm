# Requirements Breakdown — ESG SCRM MVP

## Executive Summary

Four features, three of which are genuinely hard. Feature 1 (Orchestration Platform) and Feature 3 (Evidence Vault) are architecturally complex — they involve multi-framework semantic mapping and graph-structured lineage chains respectively. Feature 2 (Supply-Chain Collection) is moderately complex but dominated by WhatsApp Business API integration and 6-language localization. Feature 4 (Real-Time Monitoring) is the simplest technically, but depends entirely on Feature 1's ERP connector layer. The critical path runs Feature 3 → Feature 1 → Feature 2/4 in sequence.

**Overall complexity: COMPLEX** — not because of any single feature, but because the cross-feature data model dependencies require the Evidence Vault to be designed before the Orchestration Platform, and the Orchestration Platform's connector architecture must be designed before Real-Time Monitoring can consume ERP data.

---

## Feature 1: ESG Data Orchestration Platform

### What it actually is

A semantic translation layer: it takes normalized internal KPI data (e.g., "kWh consumed") and produces structured outputs formatted for CSRD, ISSB, GRI, and TCFD disclosure frameworks. Each framework has different taxonomies, disclosure requirements, and data structures.

### Sub-components

| Sub-component                | Description                                                                                          | Complexity |
| ---------------------------- | ---------------------------------------------------------------------------------------------------- | ---------- |
| KPI Normalization Layer      | Canonical internal data model that maps raw ERP fields to internal KPIs                              | MODERATE   |
| Framework Mapping Engine     | Per-framework transformation rules (CSRD ESRS, ISSB IFRS S1/S2, GRI Standards, TCFD recommendations) | HARD       |
| ERP Connector Framework      | Pluggable adapter layer for SAP Business One, NetSuite, Xero, SAP S/4HANA                            | HARD       |
| Self-Serve Onboarding Wizard | Guided configuration flow — no consultants                                                           | MODERATE   |
| Output Renderer              | Generates structured payloads in each framework's schema                                             | SIMPLE     |
| KPI Taxonomy Library         | Structured definitions of common KPIs (energy, water, waste, GHG)                                    | MODERATE   |

### Complexity by sub-component

**ERP Connector Framework — HARD:** Each ERP has a distinct API surface. SAP S/4HANA uses OData APIs with SAP-specific auth (OAuth + SAML). SAP Business One uses DI Server REST APIs. NetSuite uses SuiteTalk SOAP and SuiteQL. Xero uses OAuth 2.0 with a proprietary accounting data model. Building connectors that handle authentication, pagination, error retry, and field mapping for all four in 3–6 weeks is aggressive. The 3–6 week constraint applies to total onboarding time per customer, but building the platform to support 4 ERP systems in the first release is a full engineering workstream.

**Framework Mapping Engine — HARD:** CSRD ESRS has ~100+ disclosure requirements. ISSB IFRS S1/S2 has sector-specific disclosure requirements. GRI has been evolving since 2020. TCFD has 11 recommended disclosures across 4 pillars. These frameworks overlap partially but differ in taxonomy, metric definitions, and boundary requirements. A single internal KPI maps differently across frameworks (e.g., "renewable energy %" maps to GRI 302-4, CSRD ESRS E1, TCFD Strategy). Building a rules engine for this mapping that is maintainable (frameworks update annually) and explainable (auditors ask "why did you map X to Y?") requires a structured semantic layer, not a simple lookup table.

**KPI Normalization Layer — MODERATE:** Raw ERP data is dirty. A "utility bill" in Xero has line items; in SAP S/4HANA it's a cost center posting. Normalizing across these into canonical KPIs requires resolver logic for unit conversion, date period alignment, and null/missing data handling. Medium complexity but high correctness requirements — a wrong normalization propagates into every framework output.

**Self-Serve Onboarding — MODERATE:** The wizard must guide a non-technical CFO/COO through connecting their ERP, identifying which ERP fields map to which KPIs, and validating the mapping before activation. This is a UX challenge, not a backend challenge. Building it so no consultant is required means extensive validation, help tooltips, and "did you mean" suggestions. Also requires building the connector configuration UI.

### External dependencies

- SAP Business One API credentials and sandbox environments
- NetSuite sandbox (SuiteTalk SOAP testing environment)
- Xero developer account and sandbox
- SAP S/4HANA OData sandbox (requires SAP infrastructure access)
- CSRD ESRS taxonomy (EU ESRS published, machine-readable)
- GRI Standards database (GRI has an API)
- ISSB IFRS S1/S2 standards (published by ISSB)
- TCFD framework (fully public)

### Cross-feature dependencies

- **Depends on:** Feature 3 (Evidence Vault) — every framework output must carry data lineage provenance. The Orchestration Platform cannot produce auditable outputs without the Evidence Vault's tagging infrastructure.
- **Powers:** Feature 4 (Real-Time Monitoring) — the ERP connector layer is shared. Real-Time Monitoring consumes the same connector framework, so the connector architecture must be designed for both batch and streaming contexts.

### MVP-within-MVP

**Minimal version:** One ERP (Xero — simplest OAuth 2.0 integration), one framework (CSRD ESRS — largest market urgency for EU-exposed buyers), five core KPIs (energy, water, waste, GHG Scope 1, GHG Scope 2). Output is a structured JSON payload and a PDF summary. No self-serve wizard — white-glove onboarding with a config file generated by the sales team.

**What delivers value:** A prospect can see their Xero data translated into CSRD format in a demo, demonstrating the core mapping concept. This validates the framework mapping thesis before the full multi-ERP, multi-framework investment.

---

## Feature 2: Supply-Chain ESG Data Collection

### What it actually is

A supplier engagement platform: automated questionnaires, multi-channel delivery (WhatsApp/LINE/WeChat), mobile-first UX, multi-language support, and a Scope 3 emissions calculator. The hardest parts are the messaging platform integrations and the multi-language/multi-script localization.

### Sub-components

| Sub-component                       | Description                                               | Complexity |
| ----------------------------------- | --------------------------------------------------------- | ---------- |
| WhatsApp Business API Integration   | Official WhatsApp Business Platform integration via Meta  | HARD       |
| LINE Official Account Integration   | LINE Messaging API for Thailand/Taiwan markets            | MODERATE   |
| WeChat Work Integration             | WeChat Work (WeCom) API for China                         | HARD       |
| Email Fallback Delivery             | SMTP-based questionnaire delivery                         | SIMPLE     |
| Web Portal (Supplier-Facing)        | Branded questionnaire response UI                         | MODERATE   |
| Multi-Language Questionnaire Engine | Dynamic questionnaire with 6-language support             | MODERATE   |
| Supplier Response State Machine     | Tracks: Invited → Viewed → Started → Submitted → Verified | MODERATE   |
| Scope 3 Emissions Calculator        | GHG Protocol Scope 3 calculation engine (15 categories)   | HARD       |
| Mobile-First UX                     | WhatsApp-native questionnaire experience                  | MODERATE   |
| Localization Infrastructure         | Bengali, Vietnamese, Thai, Hindi, Indonesian + RTL        | MODERATE   |

### Complexity by sub-component

**WhatsApp Business API — HARD:** The WhatsApp Business Platform is the most complex of the three messaging integrations. Key challenges:

- Business Verification: The company must be approved by Meta (takes 2–8 weeks, requires business documentation)
- Message templates: All outbound messages must use pre-approved templates. Dynamic content (questionnaire links, emission calculations) requires carefully structured template variables.
- Conversation pricing: WhatsApp charges per conversation, not per message. Cost modeling required.
- Phone number requirements: Must use WhatsApp Business phone numbers (cannot be the same as customer-facing numbers)
- The 24+1 rule: After 24 hours of silence, you can only send a template message. Interactive conversations require careful session design.

**WeChat Work Integration — HARD:** WeChat Work (WeCom) requires:

- Chinese company registration and WeCom account approval
- API access requires corporate WeChat account — not the consumer WeChat app
- Content moderation requirements for the Chinese market
- Specific privacy/data residency requirements (data must stay in China)
- Integration complexity is high regardless of SDK quality because of regulatory requirements

**LINE Integration — MODERATE:** LINE has a well-documented Messaging API with a reasonable developer experience. Key complexity is the LINE Official Account features (rich menu, quick reply) and the Thai market localization requirements.

**Scope 3 Emissions Calculator — HARD:** This is not a simple lookup. Scope 3 has 15 GHG Protocol categories, each with different calculation methodologies:

- Category 1 (Purchased goods): spend-based or EEIO-based calculations
- Category 4 (Upstream transportation): distance-based, mode-based
- Category 6 (Business travel): flight segments, hotel nights, car rentals
- Category 7 (Employee commuting): distance, mode, frequency
- Categories 8–15: even more specialized methodologies

Each supplier's response provides partial data — the calculator must handle missing data gracefully and propagate uncertainty. Also requires access to emission factor databases (DEFRA, EPA, IEA — typically updated annually).

**Multi-Language Localization — MODERATE:** Six languages including Bengali (Bangladesh, RTL-adjacent script) and Thai (complex script rendering). Each language requires:

- Questionnaire text translation (ESG terminology must be precise — "emissions" translates differently in Bengali vs English)
- Number formatting, date formatting per locale
- Currency handling (suppliers quote in local currency)
- Mobile UX adaptations (some scripts have longer word forms)

### External dependencies

- Meta WhatsApp Business Platform API (requires business verification)
- LINE Messaging API (requires LINE Official Account)
- WeChat Work / WeCom API (requires corporate WeChat account)
- GHG Protocol Scope 3 emission factors (DEFRA, EPA — publicly available but must be kept current)
- Translation services or native speaker review for 6 languages
- Twilio or MessageBird as WhatsApp Business Solution Provider (BSP) — Meta requires BSP for WhatsApp API

### Cross-feature dependencies

- **Depends on:** Feature 1 (Orchestration Platform) — the questionnaire templates need to be aligned with the KPI taxonomy. Feature 3 (Evidence Vault) — every supplier data submission must carry source/methodology tags for the evidence chain.
- **Powers:** Feature 1 (Orchestration Platform) — supplier data feeds into the multi-framework reporting. Feature 4 (Real-Time Monitoring) — supplier delivery performance metrics could feed into a monitoring dashboard.

### MVP-within-MVP

**Minimal version:** Email-only delivery (no WhatsApp/LINE/WeChat), English-only, one Scope 3 category (Category 1: Purchased Goods, spend-based calculation), web portal for supplier response. WhatsApp/LINE/WeChat add-on in Phase 2.

**What delivers value:** The email+web MVP demonstrates the full questionnaire-to-calculation flow. A supplier receives a questionnaire, submits data, and the system produces a Scope 3 emissions figure. This validates the supplier engagement model and the calculation engine before the expensive WhatsApp integration work.

---

## Feature 3: Assurance-Ready Evidence Vault

### What it actually is

An immutable audit ledger: every ESG data point is stored with its complete provenance chain, from the raw source datum through every transformation to the final reported number. The system must be able to produce an "evidence package" that a Big 4 auditor can verify without asking the company for additional documentation.

### Sub-components

| Sub-component                 | Description                                                               | Complexity |
| ----------------------------- | ------------------------------------------------------------------------- | ---------- |
| Data Point Provenance Schema  | Every record: source, timestamp, methodology, emission factor, confidence | HARD       |
| Lineage Chain Storage         | Graph database or structured JSON tree tracking transformations           | HARD       |
| Confidence Scoring Engine     | Algorithm that produces HIGH/MEDIUM/LOW with defensible rationale         | HARD       |
| Audit Evidence Exporter       | Generates auditor-accepted evidence packages (PDF, XHTML, XBRL)           | MODERATE   |
| Big 4 Audit Workflow Support  | Structured auditor review interface with verification steps               | MODERATE   |
| 7-Year Retention Architecture | Immutable storage with legal hold support                                 | MODERATE   |
| Data Immutability Layer       | Append-only storage with cryptographic integrity checks                   | MODERATE   |

### Complexity by sub-component

**Data Point Provenance Schema — HARD:** Each data point must carry:

- Source system (ERP connector ID, IoT sensor ID, supplier submission ID)
- Extraction timestamp (UTC, millisecond precision)
- Methodology used (which calculation methodology, which version)
- Emission factor applied (which factor, which source, which version, what unit)
- Confidence level (HIGH/MEDIUM/LOW)
- Raw value before transformation
- Transformation chain reference

This is not a flat schema. A Scope 2 emissions figure from Feature 1's orchestration engine might trace back through: SAP meter reading → unit conversion → grid emission factor lookup → region/year correction → reported number. The provenance schema must represent this graph, not a flat record.

**Lineage Chain Storage — HARD:** The transformation chain is a directed acyclic graph (DAG), not a linear chain. One reported number might derive from multiple source data points, each with their own sub-chains. Options:

- Graph database (Neo4j, Amazon Neptune): best for lineage traversal, but adds infrastructure
- Structured JSON in relational DB: simpler but lineage queries become complex SQL
- Purpose-built ledger (汨: blockchain-style): overkill for this use case

The choice affects query performance for the audit exporter. Auditors ask questions like "show me every input that contributed to this CSRD E1 figure" — the storage model must support these traversals efficiently.

**Confidence Scoring Engine — HARD:** "HIGH/MEDIUM/LOW" sounds simple but the algorithm must be:

- Consistent: same data quality produces same confidence across all KPIs
- Defensible: auditable rationale for every score (auditors will ask "why is this MEDIUM and not HIGH?")
- Portable: works across CSRD, ISSB, GRI, TCFD with consistent logic

Confidence factors include: data source reliability (ERP meter reading vs manual entry), temporal proximity (actual reading vs estimate), coverage (100% of sites vs sample), emission factor vintage (current year vs 3-year-old), and methodology standard (GHG Protocol vs company-defined). Building an algorithm that weights these factors consistently — and documenting the weighting — is a non-trivial task.

**7-Year Retention Architecture — MODERATE:** CSRD requires 7-year data retention. This is not just storage — it requires:

- Immutable storage (data cannot be modified, only superseded with a new record)
- Legal hold capability (certain data must be preserved during audit/enforcement proceedings)
- Storage cost planning (if a mid-market company has 10,000 sensors, 7 years of hourly readings = 10,000 × 8,760 × 7 ≈ 600M records)
- Retrieval performance (audit queries spanning 7 years must be fast)

### External dependencies

- EU CSRD regulation text (for retention requirement definition)
- Big 4 audit methodology documentation (Deloitte, EY, PwC, KPMG each have published ESG audit approaches)
- XBRL taxonomy for EU digital reporting (CSRD requires iXBRL filing)
- GHG Protocol emission factor databases (DEFRA, EPA, IEA — updated annually)
- Cryptographic hashing library (for data immutability verification)

### Cross-feature dependencies

- **Powers:** Feature 1 (Orchestration Platform) — the Evidence Vault is the backbone of the audit trail. Every framework output must be verifiable.
- **Powers:** Feature 2 (Supply-Chain Collection) — supplier submissions feed into the evidence chain.
- **Powers:** Feature 4 (Real-Time Monitoring) — sensor readings must carry provenance.
- **No dependencies on other features:** The Evidence Vault can be designed and built first. It has no inputs from Features 1, 2, or 4 — they consume its infrastructure.

### MVP-within-MVP

**Minimal version:** Linear provenance chain (not full DAG), flat JSON storage (not graph DB), PDF evidence export (not XBRL/iXBRL), HIGH/MEDIUM/LOW confidence with documented algorithm, 1-year retention (not 7-year). The architecture supports the full DAG and 7-year retention as upgrades.

**What delivers value:** A demo showing that a single ESG KPI (e.g., total GHG emissions) has a complete, auditable provenance chain — from the original utility bill line item through the framework mapping to the final CSRD disclosure figure — demonstrates the core assurance proposition to an investor.

---

## Feature 4: Real-Time ESG Monitoring

### What it actually is

A live operations dashboard: connects to existing IoT sensors and ERP systems to display real-time emissions, energy, water, and waste data. Higher-frequency data collection than batch reporting, with threshold-based alerting.

### Sub-components

| Sub-component                 | Description                                                  | Complexity |
| ----------------------------- | ------------------------------------------------------------ | ---------- |
| ERP / IoT Streaming Connector | Continuous polling or event-driven data ingestion from ERP   | MODERATE   |
| Time-Series Data Store        | High-frequency metric storage with aggregation               | MODERATE   |
| Live Dashboard UI             | Real-time display with charts, metrics, threshold indicators | MODERATE   |
| Threshold Alert Engine        | Configurable rules → notifications when limits exceeded      | SIMPLE     |
| Alert Routing System          | Delivery via email, SMS, Slack, Teams                        | SIMPLE     |
| Data Quality Monitor          | Detects anomalous sensor readings (gaps, spikes, flatlines)  | MODERATE   |

### Complexity by sub-component

**ERP / IoT Streaming Connector — MODERATE:** The brief says "no new hardware" — but mid-market export manufacturers' IoT readiness varies enormously. Some have OPC-UA servers on their production lines; others have only manual meter readings in a spreadsheet. Building a connector framework that handles:

- ERP push (NetSuite/SAP scheduled exports vs real-time)
- IoT pull (REST polling of sensor APIs, MQTT subscribers, OPC-UA)
- Coarse data (daily meter reads vs hourly sensor readings)
- Data quality gaps (sensor offline, reading of 0 that might be a failure)

This is moderate complexity but high variance — every factory is different.

**Threshold Alert Engine — SIMPLE (but the UX is not):** The engine itself is a simple rules processor: `if current_value > threshold: fire alert`. What is not simple is the alert UX:

- "Not noisy": A plant that regularly exceeds threshold at shift change generates daily alerts that become ignored
- Actionability: "Plant X exceeded daily emissions target by 15%" is informative but not actionable — who receives it, what do they do, when is it resolved?
- Alert fatigue prevention: requires alert deduplication, snooze logic, and escalation paths

**Data Quality Monitor — MODERATE:** IoT sensor data is notoriously dirty. Common failure modes:

- Flatline readings (sensor stuck at last value)
- Spikes (electrical interference, sensor malfunction)
- Gaps (sensor offline for hours or days)
- Drift (sensor reading consistently off from reality)

Building a data quality monitor that flags these failures so the system doesn't silently report bad data requires statistical process control (control charts, z-score detection) or ML-based anomaly detection. "Works even when sensors are partial/coarse" (from the brief) means the system must degrade gracefully — use daily estimates when hourly isn't available — and still produce confidence-tagged outputs.

### External dependencies

- ERP system APIs (same as Feature 1 — SAP, NetSuite, Xero, S/4HANA)
- IoT sensor vendor APIs (varies by manufacturer — no standard)
- OPC-UA server access (common in industrial manufacturing)
- MQTT broker access (if sensors publish to MQTT)
- Notification providers (Twilio SMS, SendGrid email, Slack/Teams webhooks)
- Time-series database (InfluxDB, TimescaleDB, or cloud-native equivalents)

### Cross-feature dependencies

- **Depends on:** Feature 1 (Orchestration Platform) — the ERP connector framework is shared. Real-Time Monitoring cannot consume ERP data until Feature 1's connector architecture is designed. Feature 3 (Evidence Vault) — sensor readings must carry provenance tags.
- **Powers:** None of the other features depend on Real-Time Monitoring.

### MVP-within-MVP

**Minimal version:** One data source (Xero or a single IoT sensor via REST polling), one KPI (energy consumption in kWh), simple threshold alert (email only), hourly polling, basic dashboard with current value and 24-hour trend line. No alert deduplication or escalation in MVP.

**What delivers value:** A live dashboard showing energy consumption in real-time with an alert when a configurable threshold is exceeded demonstrates the real-time monitoring concept. This is the easiest feature to demonstrate to an investor because it has the most visceral, immediate visual impact.

---

## Critical Path Analysis

### The Dependency Chain

```
Feature 3 (Evidence Vault)
        ↓
Feature 1 (Orchestration Platform)
        ↓
Feature 4 (Real-Time Monitoring)

Feature 2 (Supply-Chain Collection) can run in parallel with Feature 1 after Feature 3 is complete.
```

**Why Feature 3 first:** Every data point in the system must carry provenance. If Feature 1 and Feature 4 are built without the Evidence Vault infrastructure, they produce ESG figures without auditable lineage — which means they cannot pass a Big 4 audit review (Success Criterion 3). Retrofitting provenance into an already-deployed system is far more expensive than designing it upfront.

**Why Feature 1 before Feature 4:** Feature 4's ERP connector layer shares architecture with Feature 1. Building Feature 1's connector framework first establishes the data ingestion patterns that Feature 4's real-time streaming will extend. Feature 4 also depends on Feature 1's KPI taxonomy for the monitoring dashboard.

**Feature 2 in parallel:** Once Feature 3's provenance schema exists, Feature 2's supplier questionnaire and Scope 3 calculator can be built independently. Feature 2 has no dependencies on Feature 1 or Feature 4. It can start as soon as the Evidence Vault schema is finalized.

### Critical Path Timeline

| Phase    | Workstream                                                      | Duration  | Depends On |
| -------- | --------------------------------------------------------------- | --------- | ---------- |
| Phase 0  | Evidence Vault data model + storage architecture                | 2–3 weeks | Nothing    |
| Phase 1a | Orchestration Platform: KPI taxonomy + one ERP connector (Xero) | 3–4 weeks | Phase 0    |
| Phase 1b | Orchestration Platform: Framework mapping engine (CSRD only)    | 3–4 weeks | Phase 1a   |
| Phase 2  | Supply-Chain: questionnaire engine + email/web portal           | 3–4 weeks | Phase 0    |
| Phase 3  | Supply-Chain: Scope 3 calculator                                | 3–4 weeks | Phase 2    |
| Phase 4  | Real-Time Monitoring: connector framework + dashboard           | 3–4 weeks | Phase 1a   |
| Phase 5  | Evidence Vault: audit exporter + confidence engine              | 3–4 weeks | Phases 1–4 |

**Total sequential duration: 17–23 weeks** — well beyond the 3–6 week per-customer implementation constraint. The 3–6 week constraint is about ONBOARDING TIME PER CUSTOMER (i.e., how long it takes to connect a new customer after the platform is built), not about initial development time.

### Where parallelism helps

- Phase 2 (Supply-Chain) starts after Phase 0, in parallel with Phase 1a
- Phase 4 (Real-Time) can start after Phase 1a, in parallel with Phase 1b
- Phase 5 (Evidence Vault exporter) can be finalized after all data sources are known, parallel with other work

---

## Cross-Feature Data Model

### Shared Entities

| Entity                                         | Features That Use It |
| ---------------------------------------------- | -------------------- |
| `KPI` (canonical metric definition)            | All 4                |
| `DataSource` (ERP connector, sensor, supplier) | Features 1, 3, 4     |
| `ProvenanceRecord` (lineage chain)             | Features 1, 2, 3, 4  |
| `Supplier`                                     | Features 2, 3        |
| `EmissionFactor` (versioned factor database)   | Features 1, 2, 3     |
| `FrameworkOutput` (CSRD/ISSB/GRI/TCFD payload) | Features 1, 3        |
| `AlertRule`                                    | Feature 4            |
| `ConfidenceScore`                              | Features 1, 2, 3, 4  |

**Implication:** These entities must be designed as a unified schema. If each feature builds its own version of these entities, integration will require a migration that gets more expensive the longer it's deferred.

---

## Honest Complexity Summary

| Feature                    | Complexity    | Hardest Sub-component                               |
| -------------------------- | ------------- | --------------------------------------------------- |
| 1: Orchestration Platform  | HARD          | Multi-framework semantic mapping + 4 ERP connectors |
| 2: Supply-Chain Collection | MODERATE-HARD | WhatsApp Business API + Scope 3 calculator          |
| 3: Evidence Vault          | HARD          | Lineage DAG storage + confidence scoring algorithm  |
| 4: Real-Time Monitoring    | MODERATE      | IoT data quality monitoring + alert UX              |

**The three genuinely hard problems are:**

1. **Framework semantic mapping** (Feature 1) — maintaining a rules engine across 4 evolving disclosure frameworks with overlapping but distinct taxonomies
2. **Lineage DAG storage and query** (Feature 3) — storing and traversing complete provenance chains for arbitrary ESG calculations
3. **WhatsApp Business API integration** (Feature 2) — Meta's business verification, message template constraints, and conversation pricing model are operational complexity beyond pure engineering

The 3–6 week implementation constraint per customer does not apply to initial platform development. It applies to the ONBOARDING TIME after the platform is built. Building the platform to support 4 ERP systems, 4 frameworks, 3 messaging platforms, and 6 languages requires a full engineering investment — the constraint is a sales/onboarding claim, not a development estimate.
