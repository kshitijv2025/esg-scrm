# Framework Mapping Specification

## Overview

The framework mapping engine is the platform's core USP: one internal KPI, mapped to multiple disclosure frameworks simultaneously. This spec covers how metrics are mapped and how the comparison table works.

## Supported Frameworks

| Framework      | Full Name                                                                                  | Disclosure Type    |
| -------------- | ------------------------------------------------------------------------------------------ | ------------------ |
| CSRD / ESRS    | Corporate Sustainability Reporting Directive / European Sustainability Reporting Standards | Regulatory (EU)    |
| ISSB / IFRS S2 | International Sustainability Standards Board / IFRS S2 Climate                             | Voluntary (global) |
| GRI            | Global Reporting Initiative                                                                | Voluntary (global) |
| TCFD           | Task Force on Climate-related Financial Disclosures                                        | Voluntary (global) |
| SASB           | Sustainability Accounting Standards Board                                                  | Voluntary (US)     |

## Existing Mappings

### Energy (E1) — `energy_kwh`

| Framework    | Field ID | Unit | Value     |
| ------------ | -------- | ---- | --------- |
| CSRD ESRS E1 | E1-1     | kWh  | 2,847,320 |
| ISSB IFRS S2 | S2-a     | kWh  | 2,847,320 |
| GRI 302-1    | 302-1-a  | kWh  | 2,847,320 |
| TCFD Metrics | C1.2     | kWh  | 2,847,320 |

### Scope 2 Emissions — `emissions_tco2`

| Framework    | Field ID | Unit  | Value |
| ------------ | -------- | ----- | ----- |
| CSRD ESRS E1 | E1-4     | tCO2e | 892.4 |
| ISSB IFRS S2 | S2-b     | tCO2e | 892.4 |
| GRI 305-1    | 305-1    | tCO2e | 892.4 |
| TCFD Metrics | C1.1     | tCO2e | 892.4 |

### Scope 3 Cat 1 — `scope3_category1`

| Framework    | Field ID | Unit  | Value   |
| ------------ | -------- | ----- | ------- |
| CSRD ESRS E1 | E1-6     | tCO2e | 4,281.7 |
| ISSB IFRS S2 | S2-c     | tCO2e | 4,281.7 |
| GRI 305-3    | 305-3    | tCO2e | 4,281.7 |
| TCFD Metrics | C1.3     | tCO2e | 4,281.7 |

### Scope 3 Cat 6 — `scope3_category6`

| Framework    | Field ID | Unit  | Value |
| ------------ | -------- | ----- | ----- |
| CSRD ESRS E1 | E1-6     | tCO2e | 37.0  |
| GRI 305-3    | 305-3    | tCO2e | 37.0  |

### Diesel (Scope 1) — `diesel_consumed`

| Framework            | Field ID | Unit  | Value |
| -------------------- | -------- | ----- | ----- |
| CSRD ESRS E1         | E1-2     | tCO2e | 49.3  |
| GHG Protocol Scope 1 | 1-A      | tCO2e | 49.3  |
| GRI 305-1            | 305-1    | tCO2e | 49.3  |

---

## Planned Mappings (14 clusters)

### Scope 3 All Categories (G4)

| Category                 | CSRD ESRS E1 | GHG Protocol | ISSB S2 | GRI   |
| ------------------------ | ------------ | ------------ | ------- | ----- |
| Cat 1 Purchased Goods    | E1-6         | 1.1          | S2-c    | 305-3 |
| Cat 2 Capital Goods      | E1-7         | 1.2          | S2-d    | 305-3 |
| Cat 3 Fuel & Energy      | E1-3         | 1.3          | S2-e    | 305-3 |
| Cat 4 Upstream Transport | E1-8         | 1.4          | S2-f    | 305-3 |
| Cat 5 Waste Generated    | E1-9         | 1.5          | S2-g    | 305-3 |
| Cat 6 Business Travel    | E1-6         | 1.6          | S2-c    | 305-3 |
| Cat 7 Employee Commuting | E1-10        | 1.7          | S2-h    | 305-3 |
| Cat 8 Upstream Leased    | E1-11        | 1.8          | S2-i    | 305-3 |

### Water (G6) — `water_m3`

| Framework    | Field ID | Unit |
| ------------ | -------- | ---- |
| CSRD ESRS E3 | E3-1     | m³   |
| GRI 303-3    | 303-3    | m³   |
| ISSB IFRS S2 | S2-j     | m³   |

### Waste (E3)

| Framework    | Field ID | Unit   |
| ------------ | -------- | ------ |
| CSRD ESRS E5 | E5-1     | tonnes |
| GRI 306-3    | 306-3    | tonnes |

### Workforce Safety (S1) — LTIFR

| Framework    | Field ID | Unit              |
| ------------ | -------- | ----------------- |
| CSRD ESRS S1 | S1-3     | rate per 1M hours |
| GRI 403-9    | 403-9    | rate              |
| ISSB IFRS S2 | S2-k     | rate              |

### Gender (S3) — % women in leadership

| Framework    | Field ID | Unit |
| ------------ | -------- | ---- |
| CSRD ESRS S1 | S1-5     | %    |
| GRI 405-1    | 405-1    | %    |

### Governance (G1) — % board with ESG expertise

| Framework    | Field ID | Unit |
| ------------ | -------- | ---- |
| CSRD ESRS G1 | G1-1     | %    |
| ISSB S1      | S1-a     | %    |

---

## FrameworkCompare Component Behavior

1. User selects a cluster from the dropdown (e.g., "Workforce Safety (S1)")
2. API returns all framework mappings for that cluster
3. Table shows: Framework, Field ID, Unit, Value, Confidence, Notes
4. Confidence column uses color coding: HIGH=green, MEDIUM=amber, LOW=red
5. Clicking a framework row opens a side panel with that framework's full disclosure requirements

---

## Emission Factor Sources

| Factor                          | Source                     | Year |
| ------------------------------- | -------------------------- | ---- |
| Bangladesh grid emission factor | IEA Emissions Factors 2023 | 2023 |
| Diesel emission factor          | GHG Protocol               | 2022 |
| EEIO factors for supplier spend | EXIOBASE                   | 2019 |
| Flight emission factors         | DEFRA                      | 2023 |
| Hotel emission factors          | GHG Protocol               | 2023 |
