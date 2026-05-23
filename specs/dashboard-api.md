# Dashboard API Specification

## Existing Routes

### `GET /api/dashboard/live`

Returns 6 hardcoded ESG metrics for Bangladesh Export Textiles Ltd.

**Response** (`DashboardMetrics`):

```json
{
  "metrics": {
    "energy_kwh": {
      "value": 2847320,
      "unit": "kWh",
      "confidence": "HIGH",
      "trend": "+3.2%",
      "chain_valid": true
    },
    "emissions_tco2": {
      "value": 892.4,
      "unit": "tCO2e",
      "confidence": "HIGH",
      "trend": "+1.8%",
      "chain_valid": true
    },
    "water_m3": {
      "value": 18430,
      "unit": "m3",
      "confidence": "MEDIUM",
      "trend": "+0.7%",
      "chain_valid": true
    },
    "scope3_category1": {
      "value": 4281.7,
      "unit": "tCO2e",
      "confidence": "MEDIUM",
      "trend": "+2.1%",
      "chain_valid": true
    },
    "diesel_consumed": {
      "value": 49.3,
      "unit": "tCO2e",
      "confidence": "HIGH",
      "trend": "-0.4%",
      "chain_valid": false
    },
    "scope3_category6": {
      "value": 37.0,
      "unit": "tCO2e",
      "confidence": "LOW",
      "trend": "+5.2%",
      "chain_valid": true
    }
  }
}
```

### `GET /api/dashboard/trends`

Returns 5-month trend data for energy, emissions, water.

### `GET /api/frameworks/compare/{metric_type}`

Maps a metric to CSRD, ISSB, GRI, TCFD field IDs with values and confidence.

### `GET /api/questionnaires/coverage-stats`

Returns supplier coverage statistics: total_suppliers, responding_suppliers, total_coverage, previous_coverage.

### `GET /api/questionnaires/whatsapp-preview/{supplier_id}`

Returns WhatsApp message preview for a supplier questionnaire.

### `GET /api/evidence/drilldown/{metric_type}`

Returns full evidence chain for a metric: emission factors, source system, hash chain, calculation method.

### `GET /api/reports/esg-pdf`

Returns 3-page PDF ESG report.

---

## Planned Routes — Tier 1 (Highest Priority)

### `GET /api/dashboard/operations-summary`

Returns the 5-cluster operations overview for the Dashboard tab.

**Response**:

```json
{
  "clusters": {
    "E1_energy": {
      "value": 2847320,
      "unit": "kWh",
      "confidence": "HIGH",
      "trend": "+3.2%",
      "chain_valid": true
    },
    "G6_water": {
      "value": 18430,
      "unit": "m3",
      "confidence": "MEDIUM",
      "trend": "+0.7%",
      "chain_valid": true
    },
    "E3_waste": {
      "value": 68,
      "unit": "%",
      "confidence": "MEDIUM",
      "trend": "+4.1%",
      "chain_valid": true
    },
    "S1_safety": {
      "value": 2,
      "unit": "incidents",
      "confidence": "HIGH",
      "trend": "-1",
      "chain_valid": true
    },
    "S3_gender": {
      "value": 31,
      "unit": "%",
      "confidence": "MEDIUM",
      "trend": "+2.1%",
      "chain_valid": true
    }
  }
}
```

### `GET /api/risk/summary`

Returns 4 risk scores for the RiskScoreStrip chips.

**Response**:

```json
{
  "G2_supply_chain": { "score": 78, "tier": "B", "trend": -3, "flags": 3 },
  "G3_ethics": { "score": 88, "tier": "A", "trend": 0, "flags": 2 },
  "G8_geopolitical": { "score": 31, "tier": "Low", "trend": 0, "flags": 1 },
  "G5_financial": { "score": 65, "tier": "C", "trend": 2, "flags": 1 }
}
```

### `GET /api/risk/flags`

Returns prioritized ML risk flags with severity, cluster tag, supplier, recommendation.

**Response**:

```json
{
  "flags": [
    {
      "id": "flag_001",
      "severity": "critical",
      "cluster": "G2",
      "supplier": "Bangladesh Export Textiles Ltd.",
      "title": "Labour audit overdue",
      "detail": "187 days since last Higg FEM audit",
      "recommendation": "Suspend new orders until audit completed",
      "acknowledged": false,
      "created_at": "2025-01-15T10:00:00Z"
    }
  ]
}
```

### `GET /api/suppliers/risk-ranked`

Returns suppliers sorted by G2 risk score with per-cluster scores.

**Response**:

```json
{
  "suppliers": [
    {
      "id": "sup_001",
      "name": "Bangladesh Export Textiles Ltd.",
      "country": "BD",
      "risk_tier": "D",
      "risk_score": 72,
      "clusters": { "E": 41, "S": 52, "G": 38 },
      "financial_health": "stable",
      "scope3_coverage": 61,
      "traceability": "intact"
    }
  ]
}
```

### `GET /api/suppliers/{id}/profile`

Returns full ESG profile for one supplier.

### `GET /api/scope3/categories`

Returns all 8 GHG Protocol Scope 3 categories with coverage % and tCO2e.

**Response**:

```json
{
  "categories": [
    {
      "id": "cat_1",
      "name": "Purchased Goods",
      "coverage_pct": 64,
      "respondents": 47,
      "total": 73,
      "tco2e": 4281.7
    },
    {
      "id": "cat_2",
      "name": "Capital Goods",
      "coverage_pct": 51,
      "respondents": 37,
      "total": 73,
      "tco2e": 1203.1
    },
    {
      "id": "cat_3",
      "name": "Fuel & Energy",
      "coverage_pct": 91,
      "respondents": 66,
      "total": 73,
      "tco2e": 892.4
    },
    {
      "id": "cat_4",
      "name": "Upstream Transport",
      "coverage_pct": 43,
      "respondents": 31,
      "total": 73,
      "tco2e": 612.0
    },
    {
      "id": "cat_5",
      "name": "Waste Generated",
      "coverage_pct": 38,
      "respondents": 28,
      "total": 73,
      "tco2e": 287.5
    },
    {
      "id": "cat_6",
      "name": "Business Travel",
      "coverage_pct": 100,
      "respondents": 73,
      "total": 73,
      "tco2e": 37.0
    },
    {
      "id": "cat_7",
      "name": "Employee Commuting",
      "coverage_pct": 55,
      "respondents": 40,
      "total": 73,
      "tco2e": 198.3
    },
    {
      "id": "cat_8",
      "name": "Upstream Leased",
      "coverage_pct": 22,
      "respondents": 16,
      "total": 73,
      "tco2e": 89.1
    }
  ]
}
```

---

## Planned Routes — Tier 2

### `GET /api/risk/geopolitical`

Returns country risk matrix for all Tier 1 supplier countries.

### `GET /api/risk/scorecard`

Returns 2x2 quadrant scores for Risk & Alerts tab.

### `GET /api/labour/audit-summary`

Returns labour rights KPIs: % suppliers with critical non-compliances, % workers covered by collective bargaining, CAP closure time.

### `GET /api/workforce/safety`

Returns LTIFR, TRIR, safety training hours, absenteeism rates.

### `GET /api/water/by-source`

Returns water withdrawal breakdown: municipal, groundwater, surface, recycled.

### `GET /api/waste/circularity`

Returns production waste metrics: kg waste per unit, % reused/recycled, take-back volumes.

---

## Planned Routes — Tier 3

### `GET /api/governance/board`

Returns board composition, ESG committee existence, % executive pay linked to ESG.

### `GET /api/ethics/incidents`

Returns ethics KPIs: % employees trained on CoC, # substantiated incidents, resolution time.

### `GET /api/traceability/certifications`

Returns chain-of-custody scores per supplier certification.

### `GET /api/suppliers/financial-health`

Returns supplier financial distress indicators.

### `GET /api/fibre/mix`

Returns fibre type breakdown, certification coverage.
