# Data Model — ESG+SCRM MVP

## Core Entities

### Organization

```
Organization {
  id: UUID (primary key)
  name: string
  type: ENUM(mid_market, enterprise_division)
  employee_count: int
  industry: string (matched to GHG Protocol categories)
  primary_buyer: string (e.g., "H&M", "Zara", "Primark")
  created_at: timestamp
  updated_at: timestamp
}
```

### Integration (ERP/Hris Connection)

```
Integration {
  id: UUID (primary key)
  organization_id: FK → Organization
  type: ENUM(sap_s4hana, sap_business_one, oracle, netsuite, xero, workday, bamboo_hr, adp, personio, local_hris)
  status: ENUM(pending, connected, error, disconnected)
  last_sync_at: timestamp
  credentials_encrypted: blob (AES-256 encrypted, never logged)
  config: JSON (per-integration configuration)
  created_at: timestamp
}
```

### DataPoint (Every emission/energy/water number reported)

```
DataPoint {
  id: UUID (primary key)
  organization_id: FK → Organization
  integration_id: FK → Integration (nullable — may be manually entered)

  # Source identification
  source_system: string (e.g., "SAP Business One", "Manual Entry", "WhatsApp Supplier Response")
  source_record_id: string (internal ID from source system)
  extraction_timestamp: timestamp

  # The actual value
  metric_type: ENUM(energy_kwh, emissions_tco2, water_m3, waste_kg, scope1, scope2, scope3_category_1...9)
  value: decimal
  unit: string (e.g., "kWh", "tCO2e", "m³")

  # Methodology
  calculation_method: ENUM(direct_measurement, activity_based, spend_based)
  emission_factor_source: string (e.g., "DEFRA 2024", "GHG Protocol", "IEA 2023")
  emission_factor_value: decimal
  confidence: ENUM(HIGH, MEDIUM, LOW)

  # Lineage
  upstream_data_points: FK[] → DataPoint (for derived calculations)

  # Audit
  reported_in_frameworks: ENUM[] (CSRD, ISSB, GRI, TCFD)
  reported_at: timestamp
  reported_by: FK → User
  version: int (increments on update)
}
```

### SupplierQuestionnaire

```
SupplierQuestionnaire {
  id: UUID (primary key)
  organization_id: FK → Organization (the buyer who sent it)
  supplier_id: FK → Supplier
  buyer_questionnaire_template: FK → QuestionnaireTemplate
  status: ENUM(draft, sent, partially_responded, fully_responded, validated, archived)
  sent_at: timestamp
  due_at: timestamp
  channel: ENUM(whatsapp, line, wechat, email, portal)
  language: string (ISO 639-1)
  created_at: timestamp
}
```

### SupplierResponse

```
SupplierResponse {
  id: UUID (primary key)
  questionnaire_id: FK → SupplierQuestionnaire
  question_id: FK → QuestionnaireQuestion
  response_value: string
  confidence: ENUM(HIGH, MEDIUM, LOW)
  submitted_via: ENUM(whatsapp, line, wechat, email, portal)
  submitted_at: timestamp
  validated: boolean
  validated_by: FK → User
}
```

### Supplier

```
Supplier {
  id: UUID (primary key)
  organization_id: FK → Organization (the buyer)
  name: string
  country: string (ISO 3166-1 alpha-2)
  industry: string
  tier: ENUM(tier1, tier2, tier3)
  relationship_status: ENUM(active, inactive, blocked)
  whatsapp_number: string (E.164 format)
  line_id: string
  wechat_id: string
  preferred_channel: ENUM(whatsapp, line, wechat, email)
  created_at: timestamp
}
```

### QuestionnaireTemplate

```
QuestionnaireTemplate {
  id: UUID (primary key)
  name: string (e.g., "H&M ESG Questionnaire 2024")
  buyer: string (e.g., "H&M")
  framework_mapping: JSON { question_id → [csrd_field, gri_field, tcfd_field] }
  version: string
  questions: FK[] → QuestionnaireQuestion
  created_at: timestamp
}
```

### QuestionnaireQuestion

```
QuestionnaireQuestion {
  id: UUID (primary key)
  template_id: FK → QuestionnaireTemplate
  question_number: int
  question_text: string
  response_type: ENUM(text, number, file_upload, yes_no, multi_choice)
  required: boolean
  mapped_data_points: FK[] → DataPoint
  help_text: string
}
```

### EvidenceRecord (Audit trail for Evidence Vault)

```
EvidenceRecord {
  id: UUID (primary key)
  data_point_id: FK → DataPoint
  organization_id: FK → Organization

  # What was the state at time of evidence creation
  value: decimal
  unit: string
  methodology: string
  confidence: ENUM(HIGH, MEDIUM, LOW)

  # Evidence chain
  evidence_type: ENUM(api_extraction, manual_entry, supplier_response, sensor_reading, calculation)
  raw_source_reference: string (file path, API response ID, message ID)
  cryptographic_hash: string (SHA-256 of raw source + value + timestamp)
  previous_hash: string (hash of prior EvidenceRecord for chain integrity)
  chain_valid: boolean

  # Retention
  reported_at: timestamp
  reported_by: FK → User
  retained_until: timestamp (created_at + 7 years)
  retention_policy: ENUM(csrd_7yr, unlimited)
}
```

### ThresholdAlert

```
ThresholdAlert {
  id: UUID (primary key)
  organization_id: FK → Organization
  metric_type: ENUM(energy_kwh, emissions_tco2, water_m3)
  threshold_value: decimal
  threshold_unit: string
  comparison: ENUM(gt, lt, gte, lte, eq)
  window: ENUM(hourly, daily, weekly)
  action: ENUM(email, whatsapp, dashboard_badge, all)
  recipient_emails: string[]
  recipient_whatsapp: string
  active: boolean
  created_at: timestamp
}
```

### AlertEvent

```
AlertEvent {
  id: UUID (primary key)
  alert_id: FK → ThresholdAlert
  triggered_at: timestamp
  actual_value: decimal
  actual_unit: string
  notification_sent: boolean
  acknowledged: boolean
  acknowledged_by: FK → User
  acknowledged_at: timestamp
}
```

## Emission Factor Database

Embedded emission factors (read-only, versioned snapshots):

| Source       | Use Case                      | Update Frequency |
| ------------ | ----------------------------- | ---------------- |
| GHG Protocol | Scope 1/2/3 category defaults | Annual           |
| DEFRA        | UK grid factors, transport    | Annual           |
| IEA          | Grid factors by country       | Annual           |
| EPA          | US-specific factors           | Annual           |
| IPCC         | Global warming potentials     | Periodic         |
| Ecoinvent    | Life cycle assessment         | Periodic         |

Factors are stored as:

```
EmissionFactor {
  id: UUID
  factor_group: string (e.g., "grid_electricity_vietnam_2023")
  source: string
  year: int
  value: decimal
  unit: string
  applies_to: string (country code, industry code, or "global")
  confidence: ENUM(HIGH, MEDIUM, LOW)
  valid_from: date
  valid_to: date (nullable = no expiry)
}
```

## Confidence Taxonomy

| Confidence | Definition                                         | When to Use                                                                               |
| ---------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| **HIGH**   | Direct measurement from calibrated instrumentation | Utility bills with meter readings, direct sensor data, invoices                           |
| **MEDIUM** | Activity data × published emission factor          | Calculated from production volume × industry factor, spend-based with reliable spend data |
| **LOW**    | Spend-based estimate, industry average             | Supplier not responding, approximate spend categories, no direct measurement              |

**Rules:**

1. Confidence level is set at DataPoint creation, not adjustable by user
2. When two DataPoints of different confidence combine (e.g., Scope 3 calculation), the result takes the lower confidence
3. Every reported number displays its confidence badge in all dashboards and exports
4. HIGH confidence data cannot be overridden by MEDIUM or LOW in the same report

## Data Retention Policy

| Data Type              | Retention                | Rationale               |
| ---------------------- | ------------------------ | ----------------------- |
| EvidenceRecord         | 7 years from report date | CSRD requirement        |
| DataPoint (historical) | 7 years                  | CSRD audit trail        |
| DataPoint (current)    | Indefinite               | Business value          |
| SupplierResponse       | 7 years                  | CSRD + potential legal  |
| Integration logs       | 3 years                  | Security audit          |
| AlertEvent             | 2 years                  | Operational improvement |
| Session logs           | 1 year                   | Security                |

**Tamper-evident storage:** EvidenceRecord chain uses SHA-256 hash chain. Any modification to a historical record breaks the chain and is detectable. Annual hash verification job compares current hashes against stored previous_hashes.

## Brief Traceability

| Brief Requirement                                                | Spec Section                                            |
| ---------------------------------------------------------------- | ------------------------------------------------------- |
| "Every number tagged with source, methodology, confidence level" | DataPoint entity, Confidence Taxonomy                   |
| "Full audit trail with data lineage"                             | EvidenceRecord entity, DataPoint.upstream_data_points   |
| "Big 4 auditors can verify"                                      | EvidenceRecord.evidence_type, cryptographic_hash chain  |
| "7-year data retention"                                          | Data Retention Policy section                           |
| "Confidence level HIGH/MEDIUM/LOW"                               | Confidence Taxonomy                                     |
| "Every data point tagged with source system"                     | DataPoint.source_system, DataPoint.extraction_timestamp |
