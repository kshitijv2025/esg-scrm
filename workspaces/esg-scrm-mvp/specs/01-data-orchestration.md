# Spec 01: ESG Data Orchestration Platform

## What This Module Does

Connects to company ERP and HRIS systems, extracts raw operational data, transforms it into framework-compliant ESG disclosures across CSRD, ISSB, GRI, and TCFD.

## Core Architecture

```
ERP/Hris System
     ↓
Connector Layer (per-system adapters)
     ↓
Normalization Engine (raw → canonical ESG entities)
     ↓
Framework Mapping Engine (canonical → CSRD / ISSB / GRI / TCFD)
     ↓
Output: Framework-Specific Disclosure Packages
```

## Integration Architecture

### Connector Interface

Every ERP connector implements this interface:

```python
class ERPConnector(ABC):
    organization_id: UUID
    credentials: EncryptedBlob  # Never logged, never in memory as plain text

    async def test_connection() → ConnectionStatus:
        """Verify credentials and API access. Returns status + error message if failed."""

    async def extract_utility_expenses(start_date, end_date) → list[UtilityRecord]:
        """Extract utility invoices: electricity, gas, water, waste."""

    async def extract_procurement_spend(category_codes, start_date, end_date) → list[SpendRecord]:
        """Extract purchase orders / invoices by spend category."""

    async def extract_production_volume(product_codes, start_date, end_date) → list[ProductionRecord]:
        """Extract units produced, raw material consumption."""

    async def extract_employee_data() → EmployeeData:
        """Headcount, turnover, compensation bands (anonymized)."""

    async def extract_asset_register() → AssetRegister:
        """Equipment list for Scope 1 calculations (generators, fleet, refrigerants)."""
```

### Supported Connectors (MVP Scope)

| Connector                 | Priority | Difficulty | Notes                                                                                   |
| ------------------------- | -------- | ---------- | --------------------------------------------------------------------------------------- |
| **SAP Business One**      | P0       | HARD       | REST API via Service Layer. OAuth2. Company most likely to have it.                     |
| **NetSuite**              | P0       | MODERATE   | SuiteQL REST API. OAuth2. Well-documented.                                              |
| **Xero**                  | P0       | SIMPLE     | OAuth2. Excellent API docs. First integration to build.                                 |
| **SAP S/4HANA**           | P1       | HARD       | Direct SAP API. Requires SAP consultant access. Deep integration.                       |
| **Oracle**                | P1       | HARD       | REST API. OAuth2. Less common in mid-market.                                            |
| **Workday**               | P1       | MODERATE   | REST API. OAuth2. Employee data.                                                        |
| **BambooHR**              | P2       | SIMPLE     | REST API. OAuth2. Quick to implement.                                                   |
| **ADP**                   | P2       | MODERATE   | REST API. Payroll + headcount.                                                          |
| **Local HRIS per market** | P2       | HARD       | India (Zoho People), Vietnam (MISA), Thailand (Pandadoc) — each is a separate connector |

### Xero Connector (First Build — Reference Implementation)

Why Xero first:

1. OAuth2 flow is straightforward
2. Excellent API documentation
3. Sandbox environment available
4. Represents SME data model well (utility invoices, spend categories, production)
5. Fastest path to a working end-to-end demo

Xero specific notes:

- Use `/Invoices` for procurement spend
- Use `/Contacts` for supplier list
- Use `/BankTransactions` for utility payments (electricity, water)
- Rate limit: 60 calls/minute standard, 1000 calls/minute with increased limit
- Pagination: 100 records per page default, 1000 max

## Normalization Engine

Raw ERP data → canonical ESG entities.

### Supported Mappings

| ERP Data Type             | Canonical Entity | Metric Type              |
| ------------------------- | ---------------- | ------------------------ |
| Electricity invoice (kWh) | UtilityRecord    | energy_kwh               |
| Diesel purchase (litres)  | FuelPurchase     | emissions_tco2 (Scope 1) |
| Water bill (m³)           | UtilityRecord    | water_m3                 |
| Waste disposal (kg)       | WasteRecord      | waste_kg                 |
| Procurement invoice ($)   | SpendRecord      | scope3_category_1        |
| Employee headcount        | EmployeeData     | scope2_headcount         |
| Fleet fuel card           | FuelPurchase     | scope1_fleet             |

### Normalization Rules

```python
# Electricity → energy_kwh (direct measurement, HIGH confidence)
raw: {utility: "electricity", kwh: 1200000, period: "Q1 2024"}
canonical: DataPoint {
    metric_type: "energy_kwh",
    value: 1200000,
    calculation_method: "direct_measurement",
    confidence: "HIGH",
    source: "Xero BankTransaction"
}

# Procurement invoice → scope3_category_1 (spend-based, LOW confidence)
raw: {supplier: "Gujarat Traders", amount: 1200000, category: "raw_cotton"}
canonical: DataPoint {
    metric_type: "scope3_category_1",
    value: 1200000 * emission_factor.cotton_kg_co2_per_usd,  # LOW confidence
    calculation_method: "spend_based",
    confidence: "LOW",
    source: "Xero Invoice"
}
```

## Framework Mapping Engine

Canonical entities → framework-specific disclosures.

### CSRD Mapping

CSRD (Corporate Sustainability Reporting Directive) uses European Sustainability Reporting Standards (ESRS).

Key disclosures for manufacturing:

- **ESRS E1**: Climate change — GHG emissions (Scope 1, 2, 3)
- **ESRS E2**: Pollution — water, waste
- **ESRS E3**: Water and marine resources
- **ESRS S1**: Own workforce — employment, turnover, compensation
- **ESRS S2**: Workers in value chain — supplier labor practices
- **ESRS G1**: Business conduct — anti-corruption, supplier ESG compliance

Mapping rules:

```python
# CSRD requires GHG Protocol methodology
# All emissions must use: 100-year GWP from IPCC AR6
# Scope 2 must report both: location-based + market-based
```

### ISSB Mapping (Sustainability-Related Financial Disclosures)

IFRS S1 + S2:

- Climate-related risks and opportunities
- Scope 1 + 2 mandatory, Scope 3 if material
- Requires scenario analysis for physical risks

### GRI Mapping

GRI Universal Standards 2021:

- GRI 302: Energy
- GRI 303: Water and effluents
- GRI 305: Emissions
- GRI 306: Waste
- GRI 405: Diversity and equal opportunity

### TCFD Mapping

Four pillars:

1. Governance — board oversight
2. Strategy — climate risks and opportunities
3. Risk management — identification and assessment
4. Metrics and targets — Scope 1/2/3 emissions, targets

### Mapping Matrix

```
Canonical Entity → CSRD → ISSB → GRI → TCFD

energy_kwh → ESRS E1 §48 → IFRS S2 §21 → GRI 302-1 → TCFD Metrics §C
emissions_tco2 (scope1) → ESRS E1 §49 → IFRS S2 §22 → GRI 305-1 → TCFD Metrics §C
emissions_tco2 (scope2) → ESRS E1 §49 → IFRS S2 §22 → GRI 305-2 → TCFD Metrics §C
emissions_tco2 (scope3) → ESRS E1 §50 → IFRS S2 §23 → GRI 305-3 → TCFD Metrics §C
water_m3 → ESRS E3 §14 → IFRS S2 §28 → GRI 303-3 → TCFD Metrics §C
waste_kg → ESRS E5 §17 → — → GRI 306-3 → —
employee_headcount → ESRS S1 §5 → — → GRI 2-7 → TCFD Governance
```

## Output: Disclosure Package

Each framework output is a structured package:

```python
class DisclosurePackage:
    framework: ENUM(CSRD, ISSB, GRI, TCFD)
    reporting_period: (start_date, end_date)
    organization_id: UUID
    data_points: DataPoint[]
    generated_at: timestamp
    confidence_summary: {
        HIGH_pct: float,
        MEDIUM_pct: float,
        LOW_pct: float
    }
    gaps: Gap[]  # fields required but no data available
```

## The 70-80% Auto-Mapping Claim

The target is that 70-80% of a buyer questionnaire's data requirements can be auto-filled from existing ERP data without manual data entry.

What this means in practice for a garment factory:

- Energy (electricity): 100% auto-mapped from utility bills → HIGH confidence
- Water: 80% auto-mapped from utility bills + ETP records → HIGH/MEDIUM
- Waste: 60% auto-mapped from disposal records → MEDIUM
- Scope 3 Category 1 (purchased goods): 40% auto-mapped from spend data → LOW
- Supplier labor data: 0% auto-mapped → requires Feature 2

The 20-30% gap is where the ESG co-founder's knowledge adds value — knowing how to estimate the gaps using industry benchmarks.

## Brief Traceability

| Brief Requirement                                                        | Spec Section                                         |
| ------------------------------------------------------------------------ | ---------------------------------------------------- |
| "Connect to company ERP (SAP Business One, NetSuite, Xero, SAP S/4HANA)" | Integration Architecture, Supported Connectors table |
| "One internal KPI → multiple frameworks"                                 | Framework Mapping Engine                             |
| "One data entry, multiple framework outputs"                             | Output: DisclosurePackage                            |
| "Implementation 3–6 weeks, not 3–6 months"                               | Xero Connector (first build), Self-Serve Onboarding  |
| "Self-serve onboarding, no consultants"                                  | Self-Serve Onboarding section                        |
| "70–80% auto-mapped from existing ERP data"                              | The 70-80% Auto-Mapping Claim                        |
| "Mid-market companies (500–5,000 employees)"                             | Organization entity, Connector priority              |
