# Dashboard Tabs & Panels Specification

## Tab Structure

```
[ Dashboard ] [ Supply Chain ] [ Risk & Alerts ] [ Frameworks ] [ Engagement ]
```

---

## Tab 1: Dashboard

**Purpose**: Day-to-day operations overview. The ESG manager opens this every morning.

### Panel: Operations Overview Grid (D1)

- **Replaces**: existing 4-card metrics grid
- **Clusters**: E1 (Energy), G6 (Water), E3 (Waste), S1 (Safety), S3 (Gender)
- **Layout**: 5-column responsive grid of MetricCards
- **Behavior**: clicking any card opens EvidencePanel
- **Data**: `GET /api/dashboard/operations-summary`

### Panel: Coverage Hero (D2)

- **Unchanged**: supplier coverage bar, % responding, delta
- **Data**: `GET /api/questionnaires/coverage-stats`

### Panel: 5-Month Trend Chart (D3)

- **Expands**: adds waste data series to existing energy/emissions/water chart
- **Left axis**: E1 (energy kWh), G6 (water m³), E3 (waste intensity)
- **Right axis**: S1 (incident rate as bars)
- **Implementation**: SVG polyline chart (not Recharts — avoids crash per existing App.jsx pattern)
- **Data**: `GET /api/dashboard/trends`

### Panel: Risk Score Strip (D4) [NEW]

- **Location**: below trend chart, full width
- **Content**: 4 chips — G2 suppliers at risk, G3 grievances, G8 geopolitical, G5 financial
- **Behavior**: clicking a chip navigates to Risk & Alerts tab with that filter active
- **Data**: `GET /api/risk/summary`

---

## Tab 2: Supply Chain [NEW]

**Purpose**: Tier 1 + Tier 2 supplier depth. Scored, ranked, drillable.

### Panel: Supplier List (SC1)

- **Layout**: left sidebar, scrollable supplier rows
- **Columns**: supplier name, country flag, risk tier badge (A/B/C/D), E/S/G scores
- **Default sort**: risk score descending
- **Data**: `GET /api/suppliers/risk-ranked`

### Panel: Supplier Profile Panel (SC2)

- **Layout**: right detail panel, appears when a supplier row is selected
- **Content**: overall risk score, financial health, scope3 coverage, traceability status
- **Cluster scores**: horizontal bars for Labour Rights, Environment, Governance, Safety, Gender
- **ML Recommendations**: 3 bulleted, ML-generated action items
- **Data**: `GET /api/suppliers/{id}/profile`

### Panel: Scope 3 Detail (SC3)

- **Replaces**: current Scope3 MetricCard (which shows only Cat 1)
- **Content**: all 8 GHG Protocol Scope 3 categories
- **Layout**: horizontal bar per category, color-coded by coverage %
- **Data**: `GET /api/scope3/categories`

### Panel: Geopolitical Risk Heat Map (SC4) [NEW]

- **Content**: country-level risk for all Tier 1 supplier countries
- **Layout**: matrix — rows = countries, columns = political stability, trade exposure, currency volatility, overall score
- **Data**: `GET /api/risk/geopolitical`

---

## Tab 3: Risk & Alerts [NEW]

**Purpose**: Proactive decision support. The ML "action" tab.

### Panel: Risk Scorecard (R1)

- **Layout**: 2x2 grid
- **Quadrants**: G2 (supply chain compliance), G5 (financial health), G8 (geopolitical), G3 (ethics/grievance)
- **Per cell**: score out of 100, tier badge, trend arrow, # of active flags
- **Data**: `GET /api/risk/scorecard`

### Panel: Risk Flags Feed (R2)

- **Replaces**: passive `/dashboard/alerts` display
- **Content**: prioritized list of ML-flagged risks
- **Per flag**: severity badge (CRITICAL/WARNING/INFO), cluster tag, supplier, title, detail, recommendation, acknowledge button
- **Behavior**: acknowledge button POSTs to `POST /api/risk/flags/{id}/acknowledge`; flag moves to "addressed" section
- **ML output**: risk prioritization score = likelihood × impact × cluster_weight
- **Data**: `GET /api/risk/flags`

### Panel: Scope 3 Completeness Meter (R3) [NEW]

- **Layout**: donut chart showing overall Scope 3 coverage %; below it, category bars
- **Data**: `GET /api/scope3/completeness`

---

## Tab 4: Frameworks

**Purpose**: Disclosure and reporting. Multi-framework mapping engine.

### Panel: Framework Comparison Table (F1)

- **Current**: dropdown for 4 metrics (energy_kwh, scope3_cat1, diesel, scope3_cat6)
- **Expands**: dropdown for all 14 clusters (E1, E2, E3, S1, S2, S3, G1, G2, G3, G4, G5, G6, G7, G8)
- **Per cluster**: rows showing CSRD, ISSB, GRI, TCFD, SASB field mappings with field ID, unit, confidence, notes
- **Behavior**: clicking a framework row opens a side panel with that framework's full disclosure requirements
- **Data**: `GET /api/frameworks/compare/{cluster}`

---

## Tab 5: Engagement

**Purpose**: Supplier communication. No changes from current design.

### Panel: WhatsApp Business Preview (E1)

- **Unchanged**: `WhatsAppBusinessPreview` component from current App.jsx
- **Data**: `GET /api/questionnaires/whatsapp-preview/{supplier_id}`

---

## Component Summary

| Component                  | File    | Tab           | New?                      |
| -------------------------- | ------- | ------------- | ------------------------- |
| `OperationsGrid`           | App.jsx | Dashboard     | YES                       |
| `RiskScoreStrip`           | App.jsx | Dashboard     | YES                       |
| `SupplierMap`              | App.jsx | Supply Chain  | YES                       |
| `SupplierProfilePanel`     | App.jsx | Supply Chain  | YES                       |
| `Scope3DetailPanel`        | App.jsx | Supply Chain  | YES                       |
| `GeopoliticalHeatmap`      | App.jsx | Supply Chain  | YES                       |
| `RiskScorecard`            | App.jsx | Risk & Alerts | YES                       |
| `RiskFlagsFeed`            | App.jsx | Risk & Alerts | YES                       |
| `Scope3CompletenessMeter`  | App.jsx | Risk & Alerts | YES                       |
| `FrameworkClusterDropdown` | App.jsx | Frameworks    | YES                       |
| `TrendChart`               | App.jsx | Dashboard     | MODIFY — add waste series |
| `FrameworkCompare`         | App.jsx | Frameworks    | MODIFY — cluster dropdown |
| `WhatsAppBusinessPreview`  | App.jsx | Engagement    | unchanged                 |
| `CoverageHero`             | App.jsx | Dashboard     | unchanged                 |
| `MetricCard`               | App.jsx | Dashboard     | unchanged                 |
| `EvidencePanel`            | App.jsx | Dashboard     | unchanged                 |
