# Spec 03: Assurance-Ready Evidence Vault

## What This Module Does

Every data point in the system carries a complete audit trail — source, methodology, confidence, and cryptographic integrity — so Big 4 auditors can verify ESG reports without manual evidence gathering.

## The Audit Problem

Today: A mid-market company submits an ESG report to H&M. H&M's auditor asks: "Prove that 864 tonnes CO2 from electricity is accurate." The company spends 3 weeks manually gathering utility bills, screenshots of SAP, and a consultant's calculation notes.

With Evidence Vault: The auditor opens the evidence package, sees the exact DataPoint, drills into the source record (Xero invoice #INV-2024-Q1-0042), sees the emission factor applied (IEA 2023 Vietnam grid factor: 0.72 kg CO2/kWh), and sees the chain of custody from extraction → calculation → reported number. Total time: 10 minutes.

## Evidence Record Structure

Every DataPoint generates an EvidenceRecord when it is included in a reported disclosure:

```python
class EvidenceRecord:
    id: UUID
    data_point_id: UUID
    organization_id: UUID

    # The reported value
    value: Decimal
    unit: str
    metric_type: str

    # The chain of custody
    evidence_type: ENUM(
        api_extraction,      # Pulled from ERP via API
        manual_entry,        # User entered manually
        supplier_response,   # From supplier questionnaire
        sensor_reading,      # From IoT/meter
        calculation         # Derived from other DataPoints
    )
    raw_source_reference: str   # API response ID, file path, message ID
    raw_source_hash: str      # SHA-256 of raw source at extraction time

    # Calculation trail (if derived)
    calculation_inputs: list[DataPoint]  # Upstream DataPoints used
    calculation_formula: str            # Human-readable formula
    calculation_result: Decimal

    # Confidence
    confidence: ENUM(HIGH, MEDIUM, LOW)
    confidence_rationale: str           # Why this confidence level

    # Cryptographic integrity
    cryptographic_hash: str              # SHA-256(data_point_id + value + methodology + timestamp)
    previous_hash: str                   # Hash of prior EvidenceRecord (chain)
    chain_valid: bool                    # Computed at verification time

    # Audit metadata
    included_in_report: UUID             # Which DisclosureReport this appeared in
    reported_at: datetime
    reported_by: UUID
    retained_until: datetime              # created_at + 7 years (CSRD)

    # Retention policy
    retention_policy: ENUM(csrd_7yr, unlimited)
```

## The Confidence Tagging System

### Confidence Rules (Invariant — cannot be overridden by user)

| Source                           | Calculation Method | Confidence                                        |
| -------------------------------- | ------------------ | ------------------------------------------------- |
| Utility bill / invoice (kWh, m³) | Direct measurement | **HIGH**                                          |
| Meter / sensor (calibrated)      | Direct measurement | **HIGH**                                          |
| Activity data × published factor | Activity-based     | **MEDIUM**                                        |
| Spend data × industry factor     | Spend-based        | **LOW**                                           |
| Industry benchmark               | Spend-based        | **LOW**                                           |
| Supplier self-reported           | Activity-based     | **MEDIUM** (if verified), **LOW** (if unverified) |
| Estimate / interpolation         | —                  | **LOW**                                           |

### Confidence Aggregation

When DataPoints combine (e.g., Scope 3 = sum of all supplier emissions):

```
Resultant Confidence = MIN(all input confidences)

Scope3 = sum([
    Supplier_A: HIGH,    ← verified energy bill
    Supplier_B: MEDIUM,  ← activity-based from production
    Supplier_C: LOW     ← spend-based estimate
])
→ Scope3 Overall Confidence = LOW
```

This is displayed as: "Scope 3 total: 2,051 tCO2e (± MEDIUM-LOW confidence)"

### What Triggers HIGH Confidence Downgrade

Confidence downgrades to MEDIUM when:

- Source data was manually adjusted (e.g., invoice amount corrected)
- Unit conversion was required (e.g., gallons → m³)
- Data came from supplier portal (self-reported, unverified)

Confidence downgrades to LOW when:

- Supplier did not respond (spend-based estimate used)
- Data is > 2 years old
- Source system had known data quality issues

## Audit Trail Data Lineage

### Lineage Graph

Every DataPoint tracks its full ancestry:

```
DisclosureReport (CSRD Q1 2024)
    ↓
DataPoint: emissions_tco2 = 864 (Scope 2)
    ↓ upstream
Integration: Xero BankTransaction #INV-2024-Q1-0042
    extraction_timestamp: 2024-03-31T23:59:59Z
    raw_source_hash: sha256(Xero response payload)
    ↓
EmissionFactor: IEA 2023 Vietnam grid factor
    factor_value: 0.72 kg CO2/kWh
    source: IEA World Energy Balances 2023
    confidence: HIGH (published by government)
    ↓
Calculation: 1,200,000 kWh × 0.72 kg CO2/kWh = 864,000 kg CO2 = 864 tCO2
    calculation_method: activity_based
```

The lineage is displayed as a navigable tree in the audit view.

### Upstream Data Points

```python
@dataclass
class LineageNode:
    id: UUID
    metric_type: str
    value: Decimal
    unit: str
    source: str
    extraction_timestamp: datetime
    confidence: ConfidenceLevel
    children: list[LineageNode]  # Recursive for derived calculations
```

## Cryptographic Integrity Chain

### Hash Chain

```
EvidenceRecord[1] → hash(data_point_id + value + methodology + timestamp + prev_hash)
EvidenceRecord[2] → hash(data_point_id + value + methodology + timestamp + EvidenceRecord[1].hash)
EvidenceRecord[3] → hash(data_point_id + value + methodology + timestamp + EvidenceRecord[2].hash)
...
```

### Verification Job

Weekly job: For each EvidenceRecord, recompute SHA-256 and compare to stored `cryptographic_hash`. If mismatch → `chain_valid = False` → alert triggered.

### What This Prevents

- Tampering with a historical value after reporting
- Silent modification of a utility invoice number
- Backdating data extractions
- "I forgot to change the number in my report" fraud

What it does NOT prevent:

- Modifying raw source data before extraction (mitigated by `raw_source_hash` at extraction time)
- Breaking the chain (detectable, but the break itself is visible)

## Audit Evidence Package

When a report is submitted or an auditor requests evidence:

```python
class AuditEvidencePackage:
    report_id: UUID
    disclosure_framework: ENUM(CSRD, ISSB, GRI, TCFD)
    reporting_period: (date, date)
    organization: Organization

    # All evidence for this report
    evidence_records: list[EvidenceRecord]

    # Summary statistics
    confidence_summary: {
        HIGH: {count: int, tCO2e: Decimal},
        MEDIUM: {count: int, tCO2e: Decimal},
        LOW: {count: int, tCO2e: Decimal}
    }

    # Gaps (data not available)
    gaps: list[Gap]

    # Chain verification result
    chain_verified: bool
    chain_verification_date: datetime

    # Metadata
    generated_at: datetime
    generated_by: UUID
    package_hash: str  # SHA-256 of entire package for tamper evidence
```

### Package Export Formats

| Format                | Use Case                               |
| --------------------- | -------------------------------------- |
| PDF (human-readable)  | Auditor review, regulatory submission  |
| ZIP (JSON + raw data) | Data auditor import, forensic analysis |
| XLSX (structured)     | Internal review, gap analysis          |

## Big 4 Auditor Workflow Integration

### What Auditors Need

| Auditor Need                                  | How We Satisfy It                                                 |
| --------------------------------------------- | ----------------------------------------------------------------- |
| "Show me the source of this number"           | Drill-down from DataPoint → EvidenceRecord → raw_source_reference |
| "Prove this wasn't modified after reporting"  | Hash chain verification + raw_source_hash at extraction           |
| "What's the emission factor you used?"        | emission_factor_source + emission_factor_value in EvidenceRecord  |
| "How confident are you in this number?"       | Confidence badge (HIGH/MEDIUM/LOW) + confidence_rationale         |
| "What happens if a supplier doesn't respond?" | LOW confidence flag, fallback methodology documented              |
| "Can you give me raw data exports?"           | ZIP export with JSON + raw API responses                          |

### Auditor Access Model

- Auditors get read-only access to the Evidence Vault via a dedicated "Auditor Portal"
- No write access — auditors can view and export but not modify
- Auditor access is time-limited (access expires after audit completion)
- All auditor access is logged (who viewed what, when)

## Brief Traceability

| Brief Requirement                                                | Spec Section                                                              |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------- |
| "Every number tagged with source, methodology, confidence level" | EvidenceRecord structure, Confidence Tagging System                       |
| "Full audit trail with data lineage"                             | Audit Trail Data Lineage, Lineage Graph                                   |
| "Big 4 auditors can verify without manual evidence gathering"    | Audit Evidence Package, Big 4 Auditor Workflow Integration                |
| "7-year data retention"                                          | EvidenceRecord.retained_until, Data Retention Policy (spec 05-data-model) |
| "Confidence level HIGH/MEDIUM/LOW"                               | Confidence Tagging System table                                           |
| "Tamper-evident storage"                                         | Cryptographic Integrity Chain                                             |
| "Cryptographic hash chain"                                       | Hash Chain section                                                        |
| "Auditor portal (read-only, time-limited)"                       | Auditor Access Model                                                      |
