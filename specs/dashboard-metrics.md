# ESG Metrics Specification

## Metric Data Model

Every metric follows this schema:

```typescript
interface ESGMetric {
  value: number;
  unit: string;
  confidence: "HIGH" | "MEDIUM" | "LOW";
  trend: string; // e.g. "+3.2%" or "-1 incident"
  chain_valid: boolean; // SHA-256 hash chain integrity
  data_point_id: string; // unique identifier
  source_system: string; // e.g. "SAP Business One", "Higg FEM"
  calculation_method: string;
  emission_factor_source?: string;
  emission_factor_year?: number;
  emission_factor_table?: string;
  emission_factor_value?: number;
  emission_factor_unit?: string;
  reported_in_frameworks: string[];
}
```

## Confidence Tiers

| Confidence | Definition                                        | Example                                                                     |
| ---------- | ------------------------------------------------- | --------------------------------------------------------------------------- |
| HIGH       | Metered/utility-billed data, third-party verified | Electricity (kWh from utility bills), diesel (fuel meter)                   |
| MEDIUM     | Calculated from metered inputs × emission factors | Emissions (kWh × grid factor), Scope 3 Cat 1 (supplier declarations × EEIO) |
| LOW        | Self-reported, unaudited, or extrapolated         | Scope 3 Cat 6 (business travel from expense reports), survey responses      |

## Evidence Chain

Every metric carries a SHA-256 hash chain:

1. Each record's hash = SHA-256(data_point_id + value + timestamp + previous_hash)
2. Previous record's hash embedded in current record
3. `chain_valid: false` means record was altered post-submission
4. Genesis record has `previous_hash = "genesis"`

---

## Existing Metrics

### Energy (E1)

- **Field**: `energy_kwh`
- **Source**: SAP Business One utility invoices / smart meter reads
- **Calculation**: Sum of electricity consumed (kWh) per billing period
- **Confidence**: HIGH (metered utility data)
- **Reported in**: CSRD ESRS E1, ISSB IFRS S2, GRI 302-1, TCFD Metrics

### Emissions — Scope 1 (E1)

- **Field**: `diesel_consumed`
- **Source**: Fuel purchase records / diesel generator meter
- **Calculation**: Diesel litres × diesel emission factor (2.68 kgCO2/litre)
- **Confidence**: HIGH (metered fuel)
- **Reported in**: CSRD ESRS E1, GHG Protocol Scope 1
- **Note**: `chain_valid: false` is a deliberate demo state showing tampering detection

### Emissions — Scope 2 (E1)

- **Field**: `emissions_tco2`
- **Source**: Calculated from electricity consumption × grid emission factor
- **Calculation**: `energy_kwh × grid_emission_factor (kgCO2/kWh)`
- **Grid factor**: IEA 2023 emission factors for Bangladesh grid (0.52 kgCO2/kWh)
- **Confidence**: HIGH (based on metered energy × official factor)
- **Reported in**: CSRD ESRS E1, ISSB IFRS S2, GRI 305-1

### Water (G6)

- **Field**: `water_m3`
- **Source**: Municipal water meter readings
- **Calculation**: Sum of water withdrawn (m³) per billing period
- **Confidence**: MEDIUM (metered but no withdrawal source breakdown)
- **Reported in**: GRI 303-3, CSRD ESRS E3
- **Note**: Needs expansion to include water stress mapping and wastewater discharge

### Scope 3 Cat 1 — Purchased Goods (G4)

- **Field**: `scope3_category1`
- **Source**: Supplier questionnaire responses via WhatsApp
- **Calculation**: Supplier spend × EEIO emission factor (kgCO2/$)
- **Confidence**: MEDIUM (supplier self-reported, not third-party verified)
- **Reported in**: CSRD ESRS E1, GHG Protocol Scope 3 Cat 1, ISSB IFRS S2

### Scope 3 Cat 6 — Business Travel (G4)

- **Field**: `scope3_category6`
- **Source**: Expense management system / travel agency reports
- **Calculation**: Air miles × flight emission factor + hotel nights × hotel factor
- **Confidence**: LOW (expense data, not flight-specific)
- **Reported in**: GHG Protocol Scope 3 Cat 6

---

## Planned Metrics

### Waste & Circularity (E3)

- **Field**: `waste_kg_per_unit`, `pct_recycled`
- **Source**: Waste manifests, cutting logs, off-spec goods records
- **Calculation**: Total waste kg / units produced; recycled kg / total waste kg
- **Confidence**: MEDIUM
- **Reported in**: GRI 306-3, CSRD ESRS E5

### Workforce Safety (S1)

- **Fields**: `ltifr`, `trir`, `safety_training_hours`, `absenteeism_rate`
- **Source**: Factory EHS logs, HRIS incident records
- **LTIFR formula**: (Number of lost-time injuries × 1,000,000) / Total hours worked
- **Confidence**: HIGH (incident records)
- **Reported in**: GRI 403-9, CSRD ESRS S1

### Gender & Inclusion (S3)

- **Fields**: `pct_women_leadership`, `pct_women_board`, `promotion_rate_by_gender`, `attrition_rate_by_gender`
- **Source**: HRIS payroll system
- **Confidence**: HIGH (HRIS data)
- **Reported in**: GRI 405-1, CSRD ESRS S1

### Labour Rights (S2)

- **Fields**: `pct_critical_noncompliances`, `pct_collective_bargaining`, `cap_closure_days`, `pct_high_risk_volume`
- **Source**: Supplier audit records, CAP tracking system
- **Confidence**: MEDIUM (audit-based, not continuous)
- **Reported in**: GRI 407-1, CSRD ESRS S2

### Supplier Financial Health (G5)

- **Fields**: `supplier_credit_score`, `debt_equity_ratio`, `payment_history_score`
- **Source**: Financial data providers (D&B, Bureau van Dijk), payment records
- **Confidence**: MEDIUM (third-party provided, not audited)
- **Note**: Requires data provider integration

### Geopolitical Risk (G8)

- **Field**: `country_risk_score` per supplier country
- **Source**: World Bank governance indicators, INFORM climate risk index, custom geopolitical risk model
- **Calculation**: Weighted composite of political stability, trade exposure, currency volatility
- **Confidence**: MEDIUM (index-based, not supplier-specific)
- **Note**: Aggregated at country level, not supplier level

### Water Stress (G6)

- **Fields**: `water_withdrawal_by_source`, `pct_recycled_water`, `wastewater_discharge`
- **Source**: Municipal bills + meter reads + wastewater meter
- **Reported in**: GRI 303-1, CSRD ESRS E3

### Fibre Mix (E2)

- **Fields**: `pct_cotton`, `pct_polyester`, `pct_certified_organic`, `land_use_risk_score`
- **Source**: PLM/BOM system, supplier fibre declarations
- **Confidence**: MEDIUM (self-reported by supplier)
- **Reported in**: GRI 308-2, CSRD deforestation regulation

### Traceability Score (G7)

- **Field**: `chain_of_custody_score` per supplier
- **Source**: Purchase orders, mill visits, certification body verification APIs (Textile Exchange, GOTS)
- **Confidence**: MEDIUM (certification-based, not continuous)
- **Note**: Different from the hash-chain evidence panel — this is supplier certification authenticity, not data integrity

### Ethics & Grievance (G3)

- **Fields**: `pct_coc_trained`, `substantiated_incidents`, `pct_resolved_within_30d`
- **Source**: Learning management system (LMS) for training, HR case management for grievances
- **Confidence**: MEDIUM (internal systems)
- **Reported in**: GRI 205-2, CSRD ESRS G1
