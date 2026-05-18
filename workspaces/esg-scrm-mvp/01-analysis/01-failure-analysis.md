# Failure Analysis: ESG SCRM MVP — 4 Features

## Executive Summary

Four investor-validated features with aggressive constraints: 3–6 week implementation, self-serve onboarding, mobile-first supplier engagement across 5 Asian markets, and a Big 4 audit guarantee. The critical path runs through Feature 1 (ERP integration) and Feature 3 (evidence vault confidence tagging). Feature 2's WhatsApp/LINE/WeChat multi-channel routing is the highest external-dependency risk. Feature 4's real-time IoT ingestion will silently produce misleading data when sensors are coarse or intermittent — this is the failure that cascades across all four features because every feature depends on data quality.

**Complexity: MODERATE**
The technical surface is not exotic — REST APIs, message queues, time-series databases — but the integration breadth (4 ERP systems, 3 chat platforms, IoT protocols) creates a combinatorial explosion of pairwise failure modes that only manifest in production.

---

## Feature 1: ESG Data Orchestration Platform

### Top 3 Failure Modes

**FM-1.1: SAP Business One API rate-limits destroy the 3–6 week implementation timeline**

SAP Business One exposes data via the Service Layer (REST/SAPUI5). It has no bulk extraction endpoint. The maximum extraction rate is approximately 1 request per second with pagination limits of 1,000 records per page. A mid-market company with 10,000 line items, 3,000 journal entries, and 500 inventory batches requires a minimum of 13.5 hours of continuous polling at 1 req/s. This is not a performance problem — it is a feasibility problem for the stated implementation timeline, because the ERP connector cannot be built, tested, and validated in 6 weeks if every customer requires half a day of data extraction.

The mitigation is to build a differential sync engine (only extract changed records since last sync), but this requires the SAP B1 audit log to be accessible and reliable — it frequently is not in mid-market deployments where consultants have disabled it to reduce storage costs. If audit logging is disabled, the connector falls back to full-table polling, which hits the rate limit on every subsequent sync.

**FM-1.2: KPI-to-framework mapping produces wrong outputs for non-linear KPIs**

Carbon footprint calculations (the most common ESG KPI) require conversion factors that vary by geography, by fuel type, by combustion efficiency, and by Scope 3 category. A kWh consumed at a Bangladesh garment factory cannot be mapped to CSRD without knowing: grid emission factor for Bangladesh's national grid (varies year-to-year), whether the factory has rooftop solar (self-generation reduces grid consumption), and whether the factory purchases RECs. If the mapping engine simply multiplies kWh by a generic emission factor, the CSRD output will be wrong and the Evidence Vault will faithfully record the wrong number with HIGH confidence.

The brief states "one data entry, multiple framework outputs." The mapping engine must be a proper transformation engine with a methodology database — not a lookup table. Building a methodology database for 4 frameworks with 50+ KPIs each is a 6-month effort, not a 3-week effort.

**FM-1.3: NetSuite and Xero data models are incompatible with Scope 3 accounting requirements**

NetSuite and Xero are general-ledger systems. They record financial transactions, not physical flows. Scope 3 emissions require tracking: purchased goods and services (physical weight/volume of inputs), business travel (flight segments, hotel nights), employee commuting (headcount by distance bracket), upstream transportation (freight ton-kilometers). None of these map directly from a chart of accounts. The integration will require a shadow data model — a translation layer between financial records and physical quantities — that must be built and maintained per-customer. "Self-serve onboarding, no consultants" is only achievable if this shadow model is pre-built for common industry verticals. If it is not, every new customer requires a consulting engagement to define their own mapping.

### Technical Risks (6+ Month Delay)

**TR-1.1: CSRD taxonomy is not stable — European Sustainability Reporting Standards (ESRS) are still being finalized**

CSRD entered force in January 2023 but the underlying ESRS standards are being updated. The most recent update (ESRS 2.4) changed the emission factor tables for Scope 3 Category 1 (purchased goods). A KPI mapping engine built against the current ESRS taxonomy will require rework every time the EU updates the standards, which happened twice in 2024. The risk is not implementation delay — it is that the delivered product produces outputs that are non-compliant by the time the customer submits their first report.

**TR-1.2: Multi-framework KPI normalization requires a semantic layer that does not exist**

GRI, ISSB, TCFD, and CSRD do not use the same KPI definitions. "Energy consumption" in GRI includes renewable energy with no conversion factor; CSRD requires gross energy consumption disaggregated by energy source. "Water withdrawal" in GRI is total volume; CSRD requires freshwater/non-freshwater distinction by source. Building a semantic normalization layer across 4 frameworks with 200+ distinct data points requires deep domain expertise in each framework plus a data modeling discipline that is not available in a 3–6 week build.

### External Dependencies

- SAP Business One Service Layer access (requires customer to enable and expose the Service Layer — many mid-market customers have it disabled)
- NetSuite token-based authentication (requires NetSuite admin to generate tokens — approval processes vary by customer)
- Xero API rate limits (5,000 requests/day on standard tier — insufficient for full extraction, upgrade required)
- ESRS/GRI/ISSB/TCFD standard version tracking (requires ongoing maintenance contract with a standardsbody or third-party data provider)

### Single Hardest Problem

**The semantic translation layer between financial ledgers and physical ESG quantities.** Every framework requires physical quantities (kg CO2e, kWh, m3 water) but the source systems contain financial quantities (USD, transactions). The translation requires emission factors, conversion coefficients, and physical intensity ratios that must come from authoritative sources (DEFRA, EPA, IEA, GHG Protocol) and must be kept current. This is not a software engineering problem — it is a domain knowledge problem that cannot be solved by writing code faster.

---

## Feature 2: Supply-Chain ESG Data Collection

### Top 3 Failure Modes

**FM-2.1: WhatsApp Business API rate limits make supplier response tracking unreliable**

WhatsApp Business Platform (Meta's official API) enforces rate limits at the phone number level: 250 outgoing messages per 24 hours per phone number, with burst limits of 20 messages per minute. A supplier ESG program with 200 suppliers, each requiring 5 questionnaire rounds per year, generates 1,000 outgoing messages per year per supplier — 200,000 messages total. This is within Meta's enterprise tier limits, but the per-minute burst limit of 20 means a questionnaire distribution to 200 suppliers simultaneously will trigger Meta's spam detection, resulting in the business account being temporarily banned.

The mitigation — throttling message send rates — means suppliers receive questionnaires spread over 10 minutes rather than instantly. Mid-market suppliers, who check WhatsApp infrequently, may not see the message before it scrolls out of view. The >60% response rate target (Success Criterion 2) becomes infeasible if messages arrive outside suppliers' active hours or if Meta's spam filter treats bulk questionnaire sends as abuse.

**FM-2.2: LINE and WeChat require local entity registration and government approval respectively**

LINE Corporation is a Japanese company. Business API access for corporate accounts requires the business to be registered in a country where LINE operates. For Bangladesh-based garment factory suppliers: LINE has limited market penetration in Bangladesh (dominated by Facebook Messenger and local apps like Pathao). For WeChat: WeChat Work (the enterprise version) requires a Chinese business license and government registration. Mid-market suppliers in Vietnam, India, and Indonesia may be on WeChat for consumer use, but WeChat Work for business verification requires Chinese entity sponsorship — which a Bangladesh garment factory does not have and cannot obtain.

The brief's promise of "WhatsApp/LINE/WeChat per market" (Bangladesh → WhatsApp, Vietnam → LINE, India → WhatsApp, Thailand → LINE, Indonesia → WhatsApp) is a reasonable market split, but LINE is not viable in Bangladesh regardless of what the brief says. This requires a factual correction.

**FM-2.3: Scope 3 emissions calculations require supplier-specific emission factors that suppliers cannot provide**

A supplier in Bangladesh's garment industry cannot tell you their grid emission factor, their natural gas combustion efficiency, or their Scope 3 upstream transportation fuel consumption. They do not have this data. Asking suppliers to self-report Scope 3 Category 1 (purchased goods and services) emissions requires them to know: the emission factor of fabric they purchased (which depends on fiber type, dyeing process, and energy source of the mill), the emission factor of buttons and zippers (which requires knowing the zinc mining region and electricity grid), and the transportation mode for each input. The questionnaire will return answers in the format "we try to use recycled materials" — which cannot be converted to kg CO2e without making assumptions that will not survive a Big 4 audit.

### Technical Risks (6+ Month Delay)

**TR-2.1: Multi-language NLP parsing of free-text WhatsApp responses at scale**

The brief requires questionnaires in Bengali, Vietnamese, Thai, Hindi, and Indonesian. Suppliers will respond in mixed language (Benglish, Vietlish, Hinglish) with free text, voice notes (which require transcription), and images of documents (which require OCR). Building a NLP pipeline that handles code-mixed text in 5 languages with no training data is a 12-month effort. The alternative — structured multiple-choice questionnaires — reduces response quality (suppliers click random answers to complete the form) but is the only path to >60% response rate.

**TR-2.2: Scope 3 calculation methodology disagreement between frameworks**

CSRD requires Scope 3 calculation using the GHG Protocol Value Chain Standard. GRI allows the CDP questionnaire methodology. ISSB (IFRS S2) requires climate-related scenario analysis for Scope 3 Category 11 (use of sold products). The same supplier dataset can produce different Scope 3 totals depending on which methodology is applied. If the platform calculates Scope 3 using one methodology and the customer's auditor applies another, the evidence vault will show a HIGH-confidence number that is disputed on audit.

### External Dependencies

- WhatsApp Business Platform API approval (requires Meta business verification — 2–6 week approval process, not self-serve)
- LINE Business Connect partner status (requires partnership with a LINE authorized reseller in each market)
- WeChat Work enterprise account (requires Chinese business entity — not available to non-Chinese companies)
- Third-party emission factor databases (DEFRA, EPA, IEA — commercial licenses required for commercial use)

### Single Hardest Problem

**Collecting defensible Scope 3 supplier data from suppliers with no ESG infrastructure.** The entire supplier data collection program assumes suppliers can provide primary data (meter reads, fuel receipts, procurement records). In practice, mid-market suppliers in Bangladesh, Vietnam, and India have no ESG data collection infrastructure. The platform will receive estimated data or no data, and the Scope 3 calculation will be built on spend-based proxies (EEIO factors), which are explicitly rejected by CSRD's additionality requirements. This is not a technical failure — it is a domain assumption that the brief does not examine.

---

## Feature 3: Assurance-Ready Evidence Vault

### Top 3 Failure Modes

**FM-3.1: Confidence scoring is subjective and will not survive auditor challenge**

The brief requires every data point tagged with confidence level HIGH/MEDIUM/LOW. In practice, confidence levels are determined by: data source (meter > estimated > spend-based), temporal proximity (actual meter read at time of reporting > annual average), and methodology consistency (same method used every period > method changed mid-year). A data scientist building the confidence engine will encode rules like "if source = ERP system and extraction timestamp within 24 hours, HIGH." But the Big 4 auditor's own methodology guidelines (Deloitte's ESG Assurance Methodology, EY's Climate Change Assurance) define confidence differently — they use "limited assurance" vs "reasonable assurance" which are audit engagement types, not data quality classifications.

When the auditor asks "why is this electricity consumption tagged HIGH confidence?" and the answer is "because it came from the ERP," the auditor will respond: "that tells me the source system, not whether the underlying meter was calibrated, whether the reading was transcribed correctly, or whether the meter covers all consumption points." The evidence vault will be technically complete but substantively useless for audit.

**FM-3.2: Data lineage chain breaks at the third-party emission factor boundary**

Emission factors are external lookups (DEFRA 2024, EPA eGRID 2023). The evidence vault records: "kWh × 0.000476 tonnes CO2e/kWh (source: DEFRA 2024, Table 1, row 47)." This looks like a complete lineage chain. It is not, because:

1. DEFRA's factors are themselves based on an average grid mix that may not reflect the factory's actual grid region in Bangladesh (the national average vs the Dhaka grid region vs the specific industrial zone)
2. The factor has a measurement uncertainty band (typically ±5–10%) that is not recorded
3. The factor is applied to an electricity meter reading that was itself estimated if the meter was read quarterly rather than hourly

The complete lineage chain would require tracing the emission factor back to its underlying study, which DEFRA does not publish. The vault will have a 7-year data retention record but incomplete lineage for every third-party emission factor lookup — and auditors know this.

**FM-3.3: CSRD's 7-year retention requirement conflicts with ERP data retention policies**

CSRD requires 7 years of data retention. Mid-market companies on Xero (SMB-focused) have data retention policies that are governed by Xero's own data retention terms, not by CSRD. If the company cancels its Xero subscription, their historical financial data may become inaccessible or archived in a format the platform cannot re-extract. The evidence vault will have records for years 1–3, then a gap for years 4–7 — which is a CSRD compliance failure, not a platform failure, but the customer will blame the platform.

### Technical Risks (6+ Month Delay)

**TR-3.1: Structured data extraction from unstructured ERP systems**

SAP B1 and NetSuite store ESG-relevant data across hundreds of tables with non-standard naming. Energy consumption may be in utility bill line items (utility_type = 'electricity', amount = kwh_value), or it may be in production machine PLC logs (machine_id, run_hours, power_draw_kw), or it may be estimated from production volume (units_produced × energy_per_unit). The evidence vault must record which extraction method was used for each data point. Building a reliable automated extraction method classifier across 4 ERP systems is a 6–9 month effort.

**TR-3.2: Audit evidence package format standardization**

Deloitte, EY, PwC, and KPMG each have proprietary evidence request templates. EY uses the "Assurance Evidence File (AEF)" format, PwC uses "Sustainability Data Extract (SDE)," Deloitte uses "Climate Change and Sustainability Assurance (CCSA) workpapers." Building export adapters for 4 audit firm formats requires legal review of each format's specification, and all 4 specifications are proprietary and change annually.

### External Dependencies

- Audit firm proprietary evidence formats (EyeforESG, AAF 1/06, ISAE 3000 — versions change annually)
- Emission factor database subscriptions (DEFRA, EPA — commercial licenses required)
- ERP vendor data export APIs (varies by version, sometimes changes without notice)

### Single Hardest Problem

**Defining confidence in a way that is both machine-computable and auditor-defensible.** Confidence must be: (a) calculable from observable attributes of the data point without human judgment, (b) consistent across the platform so two auditors reviewing the same data point get the same confidence label, and (c) mapped to the auditor's own assurance standards. This requires a joint design process with each of the Big 4 that does not exist today — each firm has different internal guidelines and is not willing to co-design a vendor's confidence taxonomy.

---

## Feature 4: Real-Time ESG Monitoring

### Top 3 Failure Modes

**FM-4.1: Coarse sensor granularity produces misleading real-time alerts**

The brief states "mid-market export manufacturers already have: smart energy meters, water flow meters, PLC-controlled production lines, building management systems." This is technically true but misleading. A mid-market garment factory typically has: one electricity meter for the entire facility (not per production line), one water meter for the entire facility (not per process), and PLC logs that record production counts but not energy consumption per unit. Real-time monitoring with this sensor topology produces a single facility-level kWh number that updates daily (from the utility bill) or hourly (from the smart meter). It cannot produce "Plant X exceeded daily emissions target by 15%" because there is no "Plant X" sensor — there is one meter for the whole site.

The alert system will fire on the facility-level number, which means any overage is a facility-wide overage with no actionable remediation. The operations team receives: "Facility exceeded daily energy target by 15%" — they have no way to identify which production line, which shift, or which process caused the overage.

**FM-4.2: Continuous data ingestion requires a time-series database and a 24/7 monitoring infrastructure the buyer has not budgeted for**

Real-time monitoring at hourly or continuous frequency generates: 8,760 data points/year per sensor for hourly, 525,600 data points/year per sensor for 1-minute intervals. A mid-market factory with 20 sensors (energy, water, gas, waste, 5 production lines × 4 metrics) generates 10.5 million data points per year. Storing and querying this data requires a time-series database (TimescaleDB, InfluxDB, or equivalent), a real-time stream processor (Apache Kafka or equivalent), and a dashboard with <5-second latency on refresh.

The brief does not budget for this infrastructure. The platform's pricing ($24–60K/year) does not include infrastructure costs. If the platform is deployed as SaaS, the platform absorbs the infrastructure cost and erodes the 80% gross margin target. If deployed on-premise, the customer must provision and maintain this infrastructure — which they have not done and which requires IT staff they do not have.

**FM-4.3: Threshold alert noise will cause alert fatigue within 30 days of go-live**

Environmental monitoring generates anomalous readings: a water flow meter reading 0.001 m3/hour for 10 minutes (air bubble in the pipe, not a leak), an electricity meter reading double the baseline for 5 minutes (air conditioning cycling on, not an anomaly), a PLC reporting negative production counts (sensor reset). An uncalibrated alert system will generate 10–50 alerts per day per plant. After 2 weeks, the operations team will have muted the alerts or stopped checking the dashboard. The real-time monitoring feature will be technically live and producing data that nobody trusts.

### Technical Risks (6+ Month Delay)

**TR-4.1: ERP-to-sensor data synchronization across time zones**

A Bangladesh garment factory operating on Bangladesh Standard Time (BST, UTC+6) with an ERP running on a US-based server (UTC-8) generates sensor data timestamps in BST that must be aligned with ERP financial data timestamps in UTC. The platform must perform timezone-aware aggregation: "daily energy consumption" requires defining when "day" starts (06:00 BST = 00:00 UTC previous day). If this is not handled correctly, the daily energy total will be split across two calendar days in the ERP, producing a mismatch between the evidence vault's reported consumption and the ERP's reported consumption.

**TR-4.2: SCADA/ICS protocol security for OT network integration**

Building management systems (BMS) and PLCs in manufacturing facilities use OT protocols: BACnet, Modbus, Profinet. These protocols were designed for closed industrial networks and have no authentication by default. Connecting the platform to the OT network requires network segmentation (putting the BMS on a VLAN isolated from the corporate IT network and the platform), which requires coordination with the customer's IT department and OT vendor — typically a 6–8 week engagement for a single site, not a self-serve configuration.

### External Dependencies

- Customer OT network infrastructure (BACnet/Modbus/Profinet compatibility — varies by site)
- ERP real-time data APIs (SAP S/4HANA has a real-time API; SAP Business One does not)
- Alert recipient mobile numbers and notification preferences (requires GDPR/PDPA consent collection)
- Cellular network coverage at factory sites (Bangladesh industrial zones have intermittent connectivity)

### Single Hardest Problem

**Deriving meaningful per-process emissions from facility-level sensor data.** The business value of real-time monitoring is not "facility total is X" — it is "which process is driving the overage." Achieving this requires either: (a) installing per-process sensors (cost-prohibitive, 6-month lead time), or (b) inferring per-process consumption from proxy signals (production counts, run hours, machine power draw models). The inference approach requires factory-specific ML models that must be trained on each customer's data, which contradicts the self-serve onboarding requirement.

---

## Cross-Cutting Risks

### Risk 1: The 3–6 Week Implementation Timeline Is Built on the Assumption That All 4 ERP Connectors Are Pre-Built

The implementation timeline assumes self-serve onboarding with no consultants. This is only achievable if all 4 ERP connectors (SAP B1, NetSuite, Xero, SAP S/4HANA) are pre-built, tested, and documented. In practice:

- SAP B1 Service Layer API is different in every minor version (9.0, 9.1, 9.2, 9.3) — one connector does not fit all
- NetSuite has 3 REST API versions in common use (2021.1, 2022.1, 2023.1) with different response schemas
- Xero's API requires OAuth 2.0 token refresh management and has different rate limit tiers (5K/day standard, 60K/day premium)

Building and maintaining 4 ERP connectors across 3 API versions each = 12 integration surfaces. Each integration surface has its own failure modes described above. The 3–6 week timeline assumes all 12 surfaces work reliably on the first try for every customer. This assumption does not survive contact with production.

### Risk 2: Supplier Data Quality Determines Scope 3 Accuracy, Which Determines Evidence Vault Confidence

The Evidence Vault's confidence tagging is only as strong as its weakest input. If Feature 2 (supplier questionnaires) returns spend-based Scope 3 estimates rather than primary data, the Evidence Vault will tag every Scope 3 data point as MEDIUM or LOW confidence — not because of a platform defect, but because the underlying data is a proxy. This propagates into the monitoring dashboard (Feature 4): if the real-time sensor data is facility-level and the Scope 3 data is spend-based, the dashboard's "emissions intensity" calculation (total emissions / production volume) will be misleading.

### Risk 3: The Single Failure That Cascades Across All 4 Features

**The data quality assumption failure.**

All 4 features assume: (a) the customer has ESG-relevant data in their ERP, (b) the data is digitally accessible via API, (c) the data is of sufficient quality to map to ESG frameworks. None of these assumptions are validated at sales time. A Bangladesh garment factory's SAP B1 system may contain electricity costs (financial), not electricity consumption (kWh). The Chart of Accounts maps "utility expense" to "cost center X" but the utility bills are PDF invoices processed by an accountant and entered as journal entries — the kWh value is not in the ERP at all.

When this failure occurs:

- Feature 1 cannot map kWh because kWh is not in the ERP → no framework outputs
- Feature 2 asks suppliers for primary data because the ERP didn't have it → supplier response quality degrades
- Feature 3 has no reliable source for the evidence vault → confidence tags are all LOW
- Feature 4 connects to sensors that the ERP doesn't validate → real-time data is disconnected from reported data

The cascading failure is: **the platform is live, data is flowing, but every number is wrong because the fundamental data model (financial ledger ≠ physical flows) was never corrected.** This is not a technical failure — it is a consulting failure that no software can fix.

### Risk 4: CSRD Regulatory Deadline Is 2025–2026, But the Platform Cannot Be Validated in Time

CSRD phasing: large public interest entities (500+ employees) in the EU must comply from fiscal year 2025 (reports published in 2026). The first cohort of CSRD obligors is already in their reporting cycle. The platform is not yet built. If the MVP takes 6 months to build and validate with one lighthouse customer, the first validated deployment is mid-2026 — after the first CSRD reports are already due. The market window for "CSRD compliance for mid-market Asia exporters" is narrower than the brief implies.

---

## Recommendations

1. **Validate the data model assumption before building anything.** Spend 2 weeks with one lighthouse customer (DBL Group) auditing their SAP B1 system to confirm that kWh, water m3, and waste kg are digitally accessible — not PDF invoices. If they are not, the entire platform architecture must change.

2. **Build the SAP B1 connector first and make it the hardest.** It has the most complex API, the highest customer concentration in the target market (Bangladesh garment sector), and the most failure modes. If the SAP B1 connector works, the others are incremental.

3. **Define confidence as a fixed taxonomy agreed with one auditor before building.** Approach one Big 4 firm (Deloitte has the most published ESG assurance methodology) and ask them to co-design the confidence taxonomy. Do not build it alone and show it to auditors afterward — the rework will be 6 months.

4. **Build the supplier questionnaire as structured multiple-choice, not free-text.** Free-text NLP is a 12-month research problem. Multiple-choice with industry-specific options (fabric type, energy source, transportation mode) is a 6-week build and will produce data that can actually be converted to kg CO2e.

5. **For real-time monitoring, start at daily granularity, not hourly.** The sensors do not support hourly. Daily reconciliation is achievable in 3 weeks. "Real-time" should ship as "same-day" with a roadmap to hourly as sensor density increases per customer site.
