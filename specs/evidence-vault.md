# Evidence Vault Specification

## Overview

The Assurance-Ready Evidence Vault provides a complete, tamper-evident audit trail from raw data source to reported ESG metric. Every number in a compliance report traces back through a hash chain to its source, with methodology and emission factor citations.

## Hash Chain Architecture

### Chain Structure

Each evidence entry links to the previous entry via SHA-256 hash, creating a tamper-evident chain:

```
Entry 1: hash_current = SHA-256(raw_value + source + timestamp + "GENESIS")
Entry 2: hash_current = SHA-256(raw_value + source + timestamp + Entry1.hash_current)
Entry N: hash_current = SHA-256(raw_value + source + timestamp + Entry[N-1].hash_current)
```

### Chain Integrity Verification

`GET /api/evidence/verify/{metric_type}`:

1. Loads all chain entries for the metric, ordered by recorded_at
2. Recomputes each hash_current from entry data + previous hash
3. Compares computed hash against stored hash
4. Returns: `{metric_type, chain_length, integrity: "VALID"|"BROKEN", broken_at: null|data_point_id}`

A broken chain indicates data was modified after recording — the system never modifies entries in place.

## Per-Metric Evidence

### What Gets Recorded

Every metric uploaded or ingested creates an evidence chain entry with:

| Field                    | Source                         | Purpose                   |
| ------------------------ | ------------------------------ | ------------------------- |
| `source_record_id`       | DB primary key `id`            | Stable source record ref  |
| `source_system`          | DB `source_system`             | Where the data came from  |
| `value`                  | DB `value` (calculated)        | Reported metric value     |
| `emission_factor_source` | Joined from `emission_factors` | Factor source citation    |
| `emission_factor_year`   | Joined from `emission_factors` | Factor year               |
| `emission_factor_value`  | Joined from `emission_factors` | Factor value              |
| `emission_factor_unit`   | Joined from `emission_factors` | Factor unit               |
| `emission_factor_table`  | Joined from `emission_factors` | Factor table name         |
| `calculation_method`     | DB `methodology`               | How raw became calculated |
| `confidence`             | Computed dynamically           | HIGH/MEDIUM/LOW           |
| `confidence_score`       | Computed 0.0-1.0               | Numeric confidence        |
| `confidence_reasons`     | Computed [str]                 | Scoring rationale         |
| `previous_hash`          | DB `prev_hash`                 | SHA-256 chain link        |
| `hash`                   | DB `hash`                      | SHA-256 integrity proof   |

### Confidence Scoring

| Level  | Criteria                                                                    | Audit implication                            |
| ------ | --------------------------------------------------------------------------- | -------------------------------------------- |
| HIGH   | Actual meter reading + verified emission factor + recent data (< 30 days)   | Auditor accepts without further verification |
| MEDIUM | Estimated from spend/production + standard emission factor + data < 90 days | Auditor may request supporting documents     |
| LOW    | Extrapolated or incomplete + generic emission factor + data > 90 days       | Auditor will request alternative evidence    |

Confidence is computed from:

1. **Source reliability**: mqtt/sap_b1 (HIGH) > manual (LOW)
2. **Data recency**: < 30 days (no penalty) > 30-90 days (-1 level) > 90+ days (-2 levels)
3. **Emission factor specificity**: region-specific (no penalty) > global default (-1 level)

## Data Lineage

### Lineage DAG

Derived metrics trace back through calculation steps:

```
Scope 3 Total (calculated)
  ├── Scope 3 Supplier A (from questionnaire response)
  │   ├── Energy consumption (supplier reported: 12,000 kWh)
  │   └── × Bangladesh grid factor (0.67 tCO2e/MWh) = 8.04 tCO2e
  ├── Scope 3 Supplier B (from questionnaire response)
  │   ├── Annual spend ($2.4M)
  │   └── × Spend-based factor (0.94 tCO2e/$1000) = 2,256 tCO2e
  └── Scope 3 Extrapolation (uncovered suppliers)
      └── Average of responding suppliers × number of non-responding suppliers
```

Each node in the DAG is an evidence chain entry. The lineage is stored as parent_id references in the evidence_chain table.

## Auditor Access

### Read-Only Auditor Role

Auditors receive a special access link (not a user account) that grants read-only access to one organization's evidence vault for a specified period.

### Evidence Export

`GET /api/evidence/export?period={start}-{end}&framework={gri}`

Generates a ZIP package containing:

1. **evidence_summary.csv**: All metrics with source, confidence, hash chain status
2. **raw_data/**: Original CSV uploads and MQTT readings for the period
3. **methodology.pdf**: Calculation approach, emission factor sources, confidence methodology
4. **integrity_report.pdf**: Hash chain verification results for every metric in the period
5. **framework_mapping.csv**: Which metrics map to which framework fields

### Evidence Drilldown

`GET /api/evidence/drilldown/{metric_type}`:

Returns full evidence chain for one metric:

- Chain entries ordered chronologically
- Hash integrity status for each entry
- Source documents referenced
- Emission factor with source citation
- Calculation methodology
- Confidence level with justification

## PDF Compliance Report

`GET /api/reports/pdf?framework={gri|csrd|tcfd|issb}`

Generated report sections:

1. Cover page: org name, reporting period, framework
2. Emissions summary: Scope 1+2+3 with bar charts
3. Emission factor citations: source, year, region for each factor used
4. Supplier coverage: responding suppliers, spend coverage percentage, methodology for gaps
5. Methodology statement: calculation approach, data sources, limitations
6. Confidence distribution: number of metrics at each confidence level
7. Evidence chain summary: hash integrity verification results
