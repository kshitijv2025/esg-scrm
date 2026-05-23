# Data Model Specification

## Entity Relationship

```
organizations 1──N users
organizations 1──N api_keys
organizations 1──N factories
organizations 1──N suppliers
organizations 1──N questionnaire_templates
organizations 1──N alert_thresholds

factories 1──N metrics
factories 1──N evidence_chain_entries

suppliers 1──N risk_flags
suppliers 1──N questionnaire_responses

metrics 1──1 evidence_chain_entries
metrics ──N emission_factors (via calculation)

questionnaire_templates 1──N questionnaire_questions
questionnaire_templates 1──N questionnaire_responses
questionnaire_questions 1──1 questionnaire_responses (per supplier)
```

## Core Tables

### `organizations`

| Column     | Type | Constraints        | Description                  |
| ---------- | ---- | ------------------ | ---------------------------- |
| id         | TEXT | PK, auto-generated | org_id used in JWT           |
| name       | TEXT | NOT NULL           | Organization display name    |
| industry   | TEXT |                    | e.g., "Garment/Textile"      |
| country    | TEXT |                    | ISO country code, e.g., "BD" |
| created_at | TEXT |                    | ISO timestamp                |

### `users`

| Column        | Type | Constraints                | Description              |
| ------------- | ---- | -------------------------- | ------------------------ |
| id            | TEXT | PK, auto-generated         | User ID in JWT sub       |
| org_id        | TEXT | FK → organizations.id      | Tenant isolation         |
| name          | TEXT | NOT NULL                   | Display name             |
| email         | TEXT | UNIQUE, NOT NULL           | Login identifier         |
| password_hash | TEXT | NOT NULL                   | SHA-256 salt$hash format |
| role          | TEXT | NOT NULL, DEFAULT 'viewer' | admin/editor/viewer      |
| created_at    | TEXT |                            | ISO timestamp            |

### `factories`

| Column     | Type | Constraints           | Description            |
| ---------- | ---- | --------------------- | ---------------------- |
| id         | TEXT | PK                    | e.g., "factory_bd_001" |
| org_id     | TEXT | FK → organizations.id | Tenant isolation       |
| name       | TEXT | NOT NULL              | Factory display name   |
| location   | TEXT |                       | City, country          |
| created_at | TEXT |                       | ISO timestamp          |

### `suppliers`

| Column           | Type | Constraints           | Description                         |
| ---------------- | ---- | --------------------- | ----------------------------------- |
| id               | TEXT | PK                    | Auto-generated                      |
| org_id           | TEXT | FK → organizations.id | Tenant isolation                    |
| name             | TEXT | NOT NULL              | Supplier name                       |
| country          | TEXT |                       | ISO country code                    |
| contact_name     | TEXT |                       | Contact person                      |
| phone            | TEXT |                       | WhatsApp number                     |
| product_category | TEXT |                       | e.g., "Dyeing", "Spinning"          |
| annual_spend_usd | REAL |                       | Used for Scope 3 coverage weighting |
| esg_score        | REAL |                       | 0-100 computed score                |
| risk_tier        | TEXT |                       | A/B/C/D                             |
| created_at       | TEXT |                       | ISO timestamp                       |

### `metrics`

| Column      | Type    | Constraints        | Description                          |
| ----------- | ------- | ------------------ | ------------------------------------ |
| id          | INTEGER | PK, auto-increment |                                      |
| factory_id  | TEXT    | FK → factories.id  | Source factory                       |
| cluster     | TEXT    | NOT NULL           | e.g., "energy", "water", "emissions" |
| value       | REAL    | NOT NULL           | Metric value                         |
| unit        | TEXT    |                    | e.g., "kWh", "m3", "tCO2e"           |
| confidence  | TEXT    |                    | HIGH/MEDIUM/LOW                      |
| source      | TEXT    |                    | "mqtt", "csv_upload", "manual"       |
| period      | TEXT    |                    | e.g., "2026-04"                      |
| recorded_at | TEXT    |                    | ISO timestamp                        |

### `risk_flags`

| Column       | Type    | Constraints       | Description                             |
| ------------ | ------- | ----------------- | --------------------------------------- |
| id           | INTEGER | PK                |                                         |
| org_id       | TEXT    |                   | Tenant isolation                        |
| supplier_id  | TEXT    | FK → suppliers.id | Affected supplier (nullable)            |
| flag_type    | TEXT    | NOT NULL          | e.g., "emissions_spike", "non_response" |
| severity     | TEXT    |                   | HIGH/MEDIUM/LOW                         |
| cluster      | TEXT    |                   | e.g., "energy", "water"                 |
| priority     | INTEGER |                   | Computed priority score                 |
| message      | TEXT    |                   | Human-readable description              |
| acknowledged | INTEGER |                   | 0=pending, 1=acknowledged               |
| created_at   | TEXT    |                   | ISO timestamp                           |

## Evidence and Compliance Tables

### `evidence_chain`

| Column             | Type    | Constraints              | Description                       |
| ------------------ | ------- | ------------------------ | --------------------------------- |
| id                 | INTEGER | PK                       |                                   |
| metric_id          | INTEGER | FK → metrics.id          | Linked metric                     |
| org_id             | TEXT    |                          | Tenant isolation                  |
| source_system      | TEXT    |                          | "csv_upload", "mqtt", "sap_b1"    |
| raw_value          | REAL    |                          | Original value before calculation |
| calculated_value   | REAL    |                          | After emission factor application |
| emission_factor_id | INTEGER | FK → emission_factors.id | Factor used in calculation        |
| methodology        | TEXT    |                          | Calculation approach description  |
| confidence         | TEXT    |                          | HIGH/MEDIUM/LOW                   |
| hash_previous      | TEXT    |                          | SHA-256 of previous chain entry   |
| hash_current       | TEXT    |                          | SHA-256 of this entry             |
| recorded_at        | TEXT    |                          | ISO timestamp                     |
| recorded_by        | TEXT    |                          | User ID who created entry         |

### `emission_factors`

| Column       | Type    | Constraints | Description                                       |
| ------------ | ------- | ----------- | ------------------------------------------------- |
| id           | INTEGER | PK          |                                                   |
| category     | TEXT    | NOT NULL    | e.g., "grid_electricity", "diesel", "natural_gas" |
| factor_value | REAL    | NOT NULL    | Emission factor value                             |
| unit         | TEXT    | NOT NULL    | e.g., "tCO2e/MWh"                                 |
| source       | TEXT    | NOT NULL    | "GHG Protocol 2024", "IPCC AR6"                   |
| region       | TEXT    |             | e.g., "Bangladesh", "Global"                      |
| year         | INTEGER |             | Source publication year                           |
| is_active    | INTEGER | DEFAULT 1   | Soft deactivate for updated factors               |

### `framework_mappings`

| Column             | Type    | Constraints | Description                              |
| ------------------ | ------- | ----------- | ---------------------------------------- |
| id                 | INTEGER | PK          |                                          |
| metric_name        | TEXT    | NOT NULL    | e.g., "energy_kwh"                       |
| framework          | TEXT    | NOT NULL    | GRI/TCFD/CSRD/ISSB                       |
| field_id           | TEXT    | NOT NULL    | e.g., "GRI 302-1"                        |
| field_name         | TEXT    |             | Human-readable field name                |
| unit               | TEXT    |             | Required output unit                     |
| calculation_method | TEXT    |             | How to convert metric to framework field |

## Supplier Engagement Tables

### `questionnaire_templates`

| Column     | Type    | Constraints  | Description                                |
| ---------- | ------- | ------------ | ------------------------------------------ |
| id         | INTEGER | PK           |                                            |
| org_id     | TEXT    |              | Tenant isolation (empty = global template) |
| name       | TEXT    | NOT NULL     | e.g., "H&M ESR - Bengali"                  |
| language   | TEXT    | DEFAULT 'en' | ISO language code                          |
| category   | TEXT    |              | environment/social/governance              |
| is_active  | INTEGER | DEFAULT 1    |                                            |
| created_at | TEXT    |              |                                            |

### `questionnaire_questions`

| Column        | Type    | Constraints                     | Description                    |
| ------------- | ------- | ------------------------------- | ------------------------------ |
| id            | INTEGER | PK                              |                                |
| template_id   | INTEGER | FK → questionnaire_templates.id |                                |
| question_text | TEXT    | NOT NULL                        | Question in specified language |
| question_type | TEXT    | NOT NULL                        | number/choice/text             |
| choices       | TEXT    |                                 | JSON array for choice type     |
| sort_order    | INTEGER |                                 | Display order                  |
| required      | INTEGER | DEFAULT 1                       |                                |

### `questionnaire_responses`

| Column         | Type    | Constraints                     | Description         |
| -------------- | ------- | ------------------------------- | ------------------- |
| id             | INTEGER | PK                              |                     |
| org_id         | TEXT    |                                 | Tenant isolation    |
| supplier_id    | TEXT    | FK → suppliers.id               | Responding supplier |
| template_id    | INTEGER | FK → questionnaire_templates.id | Template used       |
| question_id    | INTEGER | FK → questionnaire_questions.id | Question answered   |
| response_value | TEXT    |                                 | Parsed response     |
| confidence     | TEXT    |                                 | HIGH/MEDIUM/LOW     |
| received_at    | TEXT    |                                 | ISO timestamp       |
| channel        | TEXT    |                                 | whatsapp/web/manual |

## Configuration Tables

### `alert_thresholds`

| Column             | Type    | Constraints | Description             |
| ------------------ | ------- | ----------- | ----------------------- |
| id                 | INTEGER | PK          |                         |
| org_id             | TEXT    |             | Tenant isolation        |
| metric_cluster     | TEXT    | NOT NULL    | e.g., "energy", "water" |
| warning_threshold  | REAL    |             | Value for MEDIUM alert  |
| critical_threshold | REAL    |             | Value for HIGH alert    |
| unit               | TEXT    |             | e.g., "kWh/day"         |
| is_active          | INTEGER | DEFAULT 1   |                         |

## Multi-Tenancy Rules

1. All queries MUST filter by `org_id` from JWT (never from request body/params)
2. `organizations.id` is immutable after creation
3. `framework_mappings` and `emission_factors` are shared reference data (no org_id) — they apply globally
4. `questionnaire_templates` with `org_id = ''` are global templates available to all orgs
5. Seed data uses `org_id = ''` for reference data, real org_id for demo data
