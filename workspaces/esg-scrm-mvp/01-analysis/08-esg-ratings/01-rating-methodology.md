# ESG Ratings — Methodology Analysis

## What ESG Ratings Actually Measure

ESG ratings are not absolute "good/bad" scores. They measure **relative risk exposure** and **management quality** within an industry peer group. Two identical companies in different industries get very different ratings because material issues differ.

### The Four-Step Process (per providers)

1. **Collect data** — company disclosures, supplier questionnaires, IoT sensors, ERP
2. **Identify material issues** — which E, S, G factors are most relevant for the company's industry (e.g., water is critical for textiles, not for software)
3. **Score performance** — rate the company on each material issue (quantitative indicators + qualitative judgment)
4. **Aggregate** — combine into one score using provider-specific weights and normalization

### Provider Comparison

| Provider          | Scale            | Approach                              | Key Distinction                             |
| ----------------- | ---------------- | ------------------------------------- | ------------------------------------------- |
| MSCI              | AAA to CCC       | Risk management relative to peers     | Industry-relative; governance separate 0-10 |
| EcoVadis          | 0-100 percentile | Unmanaged risk minus managed controls | Bronze/Silver/Gold/Platinum bands           |
| Sustainalytics    | 0-100 risk score | Unmanaged ESG risk after controls     | Lower = better; peer-ranked                 |
| ISSB/TCFD-aligned | 0-100            | Alignment with disclosure standards   | Binary readiness + depth scoring            |

---

## Rating Methodology for Demo

We simulate **EcoVadis-style** as primary (0-100 score → 4 bands) plus **MSCI-style** for E/S sub-scores (AAA to CCC).

### Inputs Available in Demo

From existing METRICS + EVIDENCE_CHAIN:

| Metric                               | Type          | Material Issue                    | Score Contribution     |
| ------------------------------------ | ------------- | --------------------------------- | ---------------------- |
| energy_kwh                           | Environmental | Energy efficiency / Climate       | E score                |
| emissions_tco2                       | Environmental | GHG emissions                     | E score                |
| water_m3                             | Environmental | Water stewardship                 | E score                |
| diesel_consumed                      | Environmental | Scope 1 direct emissions          | E score                |
| scope3_category1                     | Social        | Supply chain emissions            | S score (supply chain) |
| scope3_category6                     | Social        | Business travel                   | S score                |
| chain_valid (all True except diesel) | Governance    | Data integrity / evidence quality | G score                |

### What We Don't Have (would need in production)

These are the gaps between demo and real rating:

| Missing                    | Impact                    | How to Source               |
| -------------------------- | ------------------------- | --------------------------- |
| Board governance data      | Cannot score G accurately | Company disclosures / D&B   |
| Controversy history        | MSCI deducts heavily      | RepRisk, news feeds         |
| Policy quality (0-5 scale) | Qualitative E/S input     | Analyst assessment          |
| Peer group data            | Peer benchmarking         | Industry databases          |
| Supplier audit results     | S score for supply chain  | Social audit reports        |
| Injury rates, turnover     | S score inputs            | HR systems / worker surveys |
| Tax transparency           | G score input             | Company reports             |

### Demo Scoring Approach

**Environmental Score (E): 0-100**

- Energy efficiency: kWh per unit of production (or just absolute kWh normalized)
- Emissions intensity: tCO2e per revenue or production unit
- Water intensity: m³ per production unit
- Renewable share: % of energy from solar (from supplier data)
- Diesel dependence: Scope 1 as % of total emissions
- Data quality bonus: +5 if all hash chains intact

**Social Score (S): 0-100**

- Scope 3 Cat 1 coverage: % suppliers reporting (47/73 = 64%)
- Data quality: chain_valid on scope3_category1
- Trend trajectory: improving vs deteriorating

**Governance Score (G): 0-100**

- Hash chain integrity: % metrics with intact chain (5/6 = 83%)
- Evidence completeness: % metrics with full audit trail
- Chain broken penalty: diesel chain broken → -10 points

**Overall Score:**
Weighted average: E 40% + S 35% + G 25% = composite 0-100

**Band Assignment:**

- Platinum: 75-100
- Gold: 65-74
- Silver: 50-64
- Bronze: 35-49
- Basic: 0-34

---

## Peer Benchmark Context

**Industry: Garment manufacturing / Textiles (Bangladesh)**

Global peer benchmarks for textile manufacturers:

- EcoVadis average for textiles: ~45 (below average)
- Top performers (H&M suppliers): ~70+
- Bangladesh industry avg: ~38-42 (water + energy intensive)

Our demo scores aim for: **Silver 62/100** (realistic for mid-market Bangladesh supplier with partial coverage)

---

## EcoVadis vs MSCI Mapping

| EcoVadis (0-100) | Band     | MSCI Equivalent |
| ---------------- | -------- | --------------- |
| 75-100           | Platinum | AA              |
| 65-74            | Gold     | A               |
| 50-64            | Silver   | BBB             |
| 35-49            | Bronze   | BB              |
| 0-34             | Basic    | B / CCC         |
