# ESG Dashboard Information Architecture

**Project**: ESG SCRM MVP — Bangladesh garment supplier to H&M
**Author**: uiux-designer agent
**Date**: 2026-05-07
**Status**: Design specification for implementation

---

## 1. Problem Statement

The current 3-tab dashboard covers only 4 metrics (energy, emissions, water, Scope 3 Cat 1). The ESG scope has 14 clusters that do not map cleanly onto 3 tabs. The primary user is a Bangladesh garment factory's ESG manager preparing for H&M review — not an investor. The secondary audience is an H&M sustainability analyst doing a supplier review. Both must be served without fragmenting the UX.

---

## 2. Cluster Inventory and Data Provenance

| ID  | Cluster                        | Primary owner         | Data source                         | ML decision value             |
| --- | ------------------------------ | --------------------- | ----------------------------------- | ----------------------------- |
| E1  | Energy / GHG                   | Factory ops           | SAP utility invoices                | Reduction opportunity scoring |
| E2  | Fibre mix / Biodiversity       | Procurement           | Supplier declarations               | Biodiversity risk flag        |
| E3  | Waste / Circularity            | Factory ops           | Waste manifests                     | Circularity score vs target   |
| S1  | Workforce Safety               | HR / compliance       | Incident logs, ISO 45001            | Injury rate benchmarking      |
| S2  | Supplier Labour Rights         | Supplier audit        | Questionnaire + audit records       | Labour compliance score       |
| S3  | Gender / Inclusion             | HR                    | Payroll + headcount                 | Gender parity trend           |
| G1  | ESG Governance                 | Board / management    | Policy documents, board minutes     | Governance maturity index     |
| G2  | Supply-Chain Risk / Compliance | Procurement           | Risk assessments, audit data        | Supplier risk ranking         |
| G3  | Ethics / Grievance             | Compliance            | Whistleblower channel, incidents    | Grievance resolution time     |
| G4  | Scope 3 Full                   | All tiers             | Supplier questionnaires, spend data | Scope 3 completeness scoring  |
| G5  | Supplier Financial Health      | Finance / procurement | Financial disclosures               | Supplier viability risk       |
| G6  | Water                          | Factory ops           | Municipal bills + meter reads       | Water intensity benchmarking  |
| G7  | Traceability                   | Procurement           | Purchase orders, audit trail        | Chain-of-custody score        |
| G8  | Geopolitical Risk              | Procurement / risk    | Country risk feeds                  | Exposure heat-map             |

---

## 3. Tab / Section Architecture

**Recommended structure: 5 tabs**

```
[ Dashboard ] [ Supply Chain ] [ Risk & Alerts ] [ Frameworks ] [ Engagement ]
```

### Rationale

- **Dashboard** — owned operations (E1, E3, G6, S1, S3). High-frequency, day-to-day. The ESG manager opens this every morning.
- **Supply Chain** — supply chain data (S2, G2, G4, G5, G7, G8, E2). Tier 1 and Tier 2 supplier depth. Scored, ranked, drillable.
- **Risk & Alerts** — decision-support panel (G2 active risks, G3 grievances, G8 geopolitical, G5 financial). Proactive, not historical. This is the ML "action" tab.
- **Frameworks** — disclosure and reporting (CSRD, ISSB, GRI, TCFD mapping for all 14 clusters). Remains as-is from current design.
- **Engagement** — supplier communication (WhatsApp preview + response rates). Remains as-is; rename tab label to "Engagement".

### What the 3 existing tabs become

| Old tab             | New disposition                                                                                   |
| ------------------- | ------------------------------------------------------------------------------------------------- |
| Dashboard           | Expand to 5-cluster overview panel (E1, G6, E3, S1, S3) + keep CoverageHero + 5-month trend chart |
| Frameworks          | Expand framework table to cover all 14 clusters, not just energy/emissions                        |
| Supplier Engagement | Keep as-is; rename tab label to "Engagement"                                                      |

### What is new

- **Supply Chain tab** (new) — replaces the supplier drill-down that currently lives only in CoverageHero stats
- **Risk & Alerts tab** (new) — converts the passive alert feed into an active decision panel

---

## 4. New Panels Per Cluster

### 4.1 Dashboard Tab Panels

#### Panel D1: Operations Overview Grid (replaces current 4-card grid)

**Replaces**: existing `metrics-grid` with 4 MetricCards
**Expands to**: 5 clusters: E1 (Energy), G6 (Water), E3 (Waste), S1 (Workforce Safety), S3 (Gender/Inclusion)
**Layout**: 5-column responsive grid, each cell = MetricCard
**MetricCard behavior**: unchanged; clicking opens EvidencePanel

```
+------------------+------------------+------------------+------------------+------------------+
|  Electricity     |  Water           |  Waste Diverted  |  Recordable      |  Women in        |
|  2,847,320 kWh  |  18,430 m3       |  68% recycled   |  Incidents: 2   |  Leadership: 31% |
|  [HIGH] +3.2%   |  [HIGH] +0.7%   |  [MEDIUM] +4.1% |  [HIGH] -1 inc  |  [MEDIUM] +2.1% |
+------------------+------------------+------------------+------------------+------------------+
```

**New API route**: `GET /dashboard/operations-summary` returning all 5 clusters.

#### Panel D2: CoverageHero

**Behavior**: unchanged. Stays at `/questionnaires/coverage-stats`.

#### Panel D3: 5-Month Trend Chart

**Expands to**: Plot E1 (energy), G6 (water), E3 (waste intensity) as three lines on left axis; S1 (incident rate) as a bar overlay on right axis.
**Component**: `TrendChart` — add `waste` to data series; keep SVG implementation (avoids Recharts crash).
**Layout change**: Add a second row of legend pills below header.

```
Legend:  [*] Electricity  [*] Water  [*] Waste Intensity  [====] Safety Incidents (bar)
```

#### Panel D4: Quick Risk Summary Strip (NEW)

**Location**: Below trend chart, full width.
**Content**: 4 colored chips — G2 (suppliers at risk), G3 (open grievances), G8 (geopolitical alerts), G5 (financial risk flags).
**Behavior**: Each chip is a shortcut that switches to Risk & Alerts tab and filters to that category.

```
[ 3 suppliers at risk ]  [ 2 open grievances ]  [ 1 geopolitical alert ]  [ 1 financial flag ]
```

---

### 4.2 Supply Chain Tab Panels

#### Panel SC1: Supplier Map / List

**Layout**: Split view — left sidebar = supplier list (ranked, scrollable), right = supplier detail panel.
**Supplier list rows**: supplier name, country flag, risk tier badge (A/B/C/D), top-3 cluster scores.
**Sorting**: default = G2 risk score descending; user can resort by any cluster.

```
+---------------------------+----------------------------------------+
| Bangladesh Export Text.  |  Supplier Detail: Bangladesh Export   |
| BD    [D] *****  Risk D  |  ----------------------------------  |
|                           |  Risk Score: 72 / 100  [D]           |
| Gujarat Fabricators Ltd   |  Financial Health: Stable            |
| IN    [C] ****   Risk C  |  Scope 3 Coverage: 61%               |
|                           |  Traceability: Chain Intact           |
| Mekong Garment Co.        |  ----------------------------------  |
| VN    [B] ******  Risk B |  Cluster Scores (radar):             |
|                           |  Labour Rights: 84% ******            |
| Shanghai Trim Supplier     |  Environment: 61% *****             |
| CN    [A] ******  Risk A |  Governance: 77% ******             |
+---------------------------+----------------------------------------+
```

**New API route**: `GET /suppliers/risk-ranked` — returns suppliers with per-cluster scores.

#### Panel SC2: Scope 3 Detail Panel

**Replaces**: current Scope3 metric card (which shows only Cat 1).
**Content**: All 8 GHG Protocol Scope 3 categories; each shows coverage %, response rate, tCO2e estimate.
**Layout**: Horizontal stacked bar per category; categories color-coded by coverage rate (green >80%, amber 50-80%, red <50%).

```
Scope 3 Categories
Cat 1 (Purchased goods)  ████████████████████░░░░░░░  64%  47/73 suppliers  4,282 tCO2e
Cat 2 (Capital goods)   ████████████████░░░░░░░░░░  51%  37/73 suppliers  1,203 tCO2e
Cat 3 (Fuel/energy)     ██████████████████████████  91%  66/73 suppliers    892 tCO2e
...
```

**New API route**: `GET /scope3/categories` — returns all 8 categories with coverage and tCO2e.

#### Panel SC3: Geopolitical Risk Heat Map (NEW)

**Content**: Country-level risk for all Tier 1 supplier countries; color cells by G8 risk score.
**Layout**: Small matrix — rows = countries, columns = risk dimensions (political stability, trade exposure, currency).
**ML output**: G8 geopolitical risk score per country.

```
Country Risk Matrix
                Political  Trade    Currency  Overall
                Stability  Exposure  Volatility  Score
Bangladesh       Medium    High     Medium     62
India            Low      Medium   Low       28
Vietnam          Low      Medium   Low       31
China            Medium   Very High Low       55
```

---

### 4.3 Risk & Alerts Tab Panels

#### Panel R1: Risk Scorecard

**Layout**: 2x2 grid — G2 (supply chain compliance), G5 (supplier financial health), G8 (geopolitical), G3 (ethics/grievance).
**Content per cell**: Current score, trend arrow, # of active flags, top concern.

```
+------------------+------------------+
|  Supply Chain    |  Financial       |
|  Compliance      |  Health          |
|  78/100 [B]     |  65/100 [C]     |
|  3 suppliers    |  1 flag          |
|  at risk        |  (elevated D/E) |
+------------------+------------------+
|  Geopolitical   |  Grievances      |
|  Exposure       |  & Ethics        |
|  31/100 [Low]  |  88/100 [Good]  |
|  1 alert       |  2 open / 18 resolved|
+------------------+------------------+
```

#### Panel R2: Risk Flags Feed

**Replaces**: current passive `/dashboard/alerts` endpoint display.
**Content**: Prioritized list of ML-flagged risks — each flag shows severity (Critical/Warning/Info), cluster tag, supplier, recommendation.
**Behavior**: Acknowledge button per flag (POST to `/alerts/{id}/acknowledge`); acknowledged flags move to "addressed" section.
**ML output**: risk prioritization score combining likelihood x impact x cluster weight.

```
CRITICAL  [G2] Bangladesh Export Textiles -- labour audit overdue (187 days)
          Recommendation: Suspend new orders until audit completed
          [View Audit]  [Acknowledge]

WARNING   [G5] Gujarat Fabricators Ltd -- D/E rated financial statement
          Recommendation: Request updated financials within 30 days
          [View Profile]  [Acknowledge]

INFO      [G8] Vietnam -- currency devaluation risk elevated
          Recommendation: Review hedging coverage for VND exposure
          [View Country Profile]  [Acknowledge]
```

**New API route**: `GET /risk/flags` — returns prioritized ML risk flags with recommendation text.

#### Panel R3: Scope 3 Completeness Meter (NEW)

**Content**: Overall Scope 3 coverage across all 8 categories; per-category breakdown with missing suppliers list.
**Layout**: Donut chart showing 64% overall; below it, category list with coverage bars.
**ML output**: G4 Scope 3 completeness score; identifies which suppliers are missing Cat 1, Cat 2, etc.

---

### 4.4 Frameworks Tab Changes

#### Panel F1: Framework Comparison Table

**Expands to**: all 14 clusters, not just energy/emissions.
**Layout change**: Dropdown to select cluster; table shows CSRD / ISSB / GRI / TCFD / SASB field mappings for that cluster.
**Behavior**: clicking a framework name opens a side panel with that framework's full disclosure requirements for that cluster.

```
Cluster: [Workforce Safety (S1)          v]

Framework   Field ID         Unit       Confidence   Notes
CSRD        S1-3            rate/200k  HIGH        LTIR calculation
ISSB        S2-a            ratio      HIGH        Lost time injury rate
GRI         403-9           rate       MEDIUM      Requires ISO 45001 cert
TCFD        C1-2            narrative  LOW         Qualitative
SASB        SV-ES-320a.1    rate       MEDIUM      RTW rate
```

**Existing route**: `GET /frameworks/compare/{metric}` — extend to accept cluster ID.

---

### 4.5 Engagement Tab

**No changes** — WhatsAppBusinessPreview stays as-is.

---

## 5. Shared Panels — Where Clusters Can Consolidate

| Shared Panel           | Clusters merged                                   | Rationale                                                                                                    |
| ---------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Resource Efficiency    | E1 (Energy) + G6 (Water) + E3 (Waste)             | All three are factory utility/consumption metrics; share a "consumption vs. intensity" visualization pattern |
| Workforce Overview     | S1 (Safety) + S3 (Gender)                         | Both live in HR data; can share a workforce summary header with HR-system attribution                        |
| Supplier ESG Profile   | S2 (Labour) + G2 (Compliance) + G7 (Traceability) | A supplier's ESG score spans all three; a single "Supplier ESG Card" shows all three                         |
| Supplier Risk Overview | G5 (Financial) + G8 (Geopolitical)                | Both are supplier risk inputs; can share a "Supplier Risk Overview" panel                                    |

---

## 6. ML / Decision-Making Value Ranking

Clusters ranked by decision-useful ML output for the target user (Bangladesh garment ESG manager preparing for H&M review):

| Rank | Cluster                      | ML Output                                      | Decision action triggered                           |
| ---- | ---------------------------- | ---------------------------------------------- | --------------------------------------------------- |
| 1    | G2 Supply-Chain Risk         | Supplier risk ranking A/B/C/D                  | Which suppliers to audit next; which to flag to H&M |
| 2    | G4 Scope 3 Full              | Completeness scoring per cat                   | Which categories are below H&M's 80% threshold      |
| 3    | G3 Ethics/Grievance          | Grievance resolution time, open/resolved ratio | Whether to escalate to H&M's compliance team        |
| 4    | S2 Supplier Labour Rights    | Labour compliance score per supplier           | Pre-audit self-assessment before H&M audit          |
| 5    | E1 Energy/GHG                | Reduction opportunity scoring                  | Where to invest in efficiency                       |
| 6    | G5 Supplier Financial Health | Viability risk flags                           | Whether to diversify away from at-risk supplier     |
| 7    | G8 Geopolitical              | Country exposure heat-map                      | Cross-tier concentration risk                       |
| 8    | S1 Workforce Safety          | Injury rate benchmarking vs. sector avg        | HR intervention priority                            |
| 9    | G1 ESG Governance            | Maturity index                                 | Gap analysis vs. H&M's governance expectations      |
| 10   | G6 Water                     | Water intensity benchmarking                   | Efficiency investment                               |
| 11   | S3 Gender/Inclusion          | Gender parity trend                            | HR reporting, DEI disclosures                       |
| 12   | E3 Waste/Circularity         | Circularity score                              | Circularity target reporting                        |
| 13   | G7 Traceability              | Chain-of-custody score                         | Which suppliers need audit before next order        |
| 14   | E2 Fibre/Biodiversity        | Biodiversity risk flag                         | Procurement decision for next season's materials    |

---

## 7. Wireframe — Key New Panels

### Wireframe: Risk & Alerts Tab (R1 + R2)

```
+-----------------------------------------------------------------------+
|  Risk & Alerts                          Last updated: 2 min ago  [R]  |
+-----------------------------------------------------------------------+
|                                                                       |
|  +-------------------+  +-------------------+                       |
|  | SUPPLY CHAIN     |  | FINANCIAL HEALTH  |                       |
|  | COMPLIANCE  [B]  |  |  [C]              |                       |
|  | 78 / 100         |  | 65 / 100          |                       |
|  | Trend: -3 v       |  | Trend: +2 ^        |                       |
|  | 3 suppliers      |  | 1 flag            |                       |
|  | [View all ->]    |  | [View flag ->]    |                       |
|  +-------------------+  +-------------------+                       |
|                                                                       |
|  +-------------------+  +-------------------+                       |
|  | GEOPOLITICAL     |  | GRIEVANCES        |                       |
|  | EXPOSURE  [Low] |  | & ETHICS  [Good]  |                       |
|  | 31 / 100         |  | 88 / 100          |                       |
|  | 1 active alert   |  | 2 open / 18 closed |                       |
|  | [View map ->]   |  | [View all ->]     |                       |
|  +-------------------+  +-------------------+                       |
|                                                                       |
+-----------------------------------------------------------------------+
|  PRIORITISED RISK FLAGS                                              |
+-----------------------------------------------------------------------+
|  [CRITICAL] Labour audit overdue -- Bangladesh Export Textiles        |
|             187 days since last Higg FEM audit                       |
|             Recommendation: Suspend orders until audit complete        |
|             [View Audit]  [Acknowledge]                              |
|                                                                       |
|  [WARNING]   Financial distress signal -- Gujarat Fabricators Ltd      |
|             D/E ratio above 3.0 threshold                            |
|             Recommendation: Request certified financials              |
|             [View Profile]  [Acknowledge]                            |
|                                                                       |
|  [INFO]      Currency exposure -- Vietnam (VND) devaluation risk       |
|             Recommendation: Review hedging coverage                   |
|             [View Country]  [Acknowledge]                            |
|                                                                       |
+-----------------------------------------------------------------------+
```

### Wireframe: Supply Chain Tab (SC1 — Supplier List + Detail)

```
+---------------------------------------------------------------------+
|  Supply Chain           [73 suppliers]  [Sort: Risk v]  [Filter v]   |
+---------------------------------------------------------------------+
|                                                                     |
|  SUPPLIER             COUNTRY   RISK    SCORES (E / S / G)          |
|  --------------------+---------+--------+-----------------           |
|  > Bangladesh Export  | BD      | [D]    | 41 / 52 / 38  [View ->] |
|    Textiles           |         |        |                    |
|  > Gujarat Fab. Ltd  | IN      | [C]    | 58 / 61 / 55  [View ->] |
|  > Mekong Garment Co | VN      | [B]    | 72 / 79 / 68  [View ->] |
|  > Shanghai Trim     | CN      | [A]    | 85 / 81 / 82  [View ->] |
|    Supplier          |         |        |                    |
|  o Delta Woven Mills | PK      | [B]    | 70 / 74 / 61  [View ->] |
|  o Nile Cotton Co   | EG      | [C]    | 62 / 58 / 59  [View ->] |
|  ...                 |         |        |                    |
|                                                                     |
|  +---------------------------------------------------------------+  |
|  | SUPPLIER PROFILE: Bangladesh Export Textiles                  |  |
|  | --------------------------------------------------------------|  |
|  | Overall Risk Score    72 / 100  [D]   3 active flags       |  |
|  | Financial Health      Stable         D/E ratio: 1.8         |  |
|  | Scope 3 Coverage      61%            28/73 suppliers        |  |
|  | Traceability          Chain Intact   Last audit: 2024-Q3    |  |
|  |                                                               |  |
|  | CLUSTER SCORES                                                  |  |
|  | Labour Rights [S2]   ████████████████░░░░░░  84%              |  |
|  | Environment [E]      ██████████████░░░░░░░░░  61%              |  |
|  | Governance [G]       ████████████████░░░░░░  77%              |  |
|  | Safety [S1]          ████████████████████░░░  91%              |  |
|  | Gender [S3]          ██████████░░░░░░░░░░░░  48% [WARNING]   |  |
|  |                                                               |  |
|  | RECOMMENDATIONS (ML-generated)                               |  |
|  | 1. Commission Higg FEM audit before Q2 H&M review           |  |
|  | 2. Request gender parity plan -- leadership at 31% vs 40% tgt|  |
|  | 3. Improve Cat 1 Scope 3 data for 12 non-reporting sub-supp |  |
|  +---------------------------------------------------------------+  |
+---------------------------------------------------------------------+
```

---

## 8. Component Naming (App.jsx Additions)

### New Components to Create

| Component                  | Purpose                                    | Data source                         |
| -------------------------- | ------------------------------------------ | ----------------------------------- |
| `OperationsGrid`           | Replaces metrics-grid; 5-cluster cards     | `GET /dashboard/operations-summary` |
| `RiskScoreStrip`           | Quick risk summary chips below trend chart | `GET /risk/summary`                 |
| `SupplierMap`              | Left sidebar of Supply Chain tab           | `GET /suppliers/risk-ranked`        |
| `SupplierProfilePanel`     | Right detail panel of Supply Chain tab     | `GET /suppliers/{id}/profile`       |
| `Scope3DetailPanel`        | All 8 Scope 3 categories                   | `GET /scope3/categories`            |
| `GeopoliticalHeatmap`      | Country risk matrix                        | `GET /risk/geopolitical`            |
| `RiskScorecard`            | 2x2 risk quadrant on Risk tab              | `GET /risk/scorecard`               |
| `RiskFlagsFeed`            | Prioritized risk flags on Risk tab         | `GET /risk/flags`                   |
| `Scope3CompletenessMeter`  | Donut + category bars                      | `GET /scope3/completeness`          |
| `FrameworkClusterDropdown` | Expand FrameworkCompare to all clusters    | `GET /frameworks/compare/{cluster}` |

### Existing Components to Modify

| Component                 | Change                                                           |
| ------------------------- | ---------------------------------------------------------------- |
| `TrendChart`              | Accept `waste` data series; add bar-overlay for safety incidents |
| `FrameworkCompare`        | Replace `metric` dropdown with cluster ID; add cluster labels    |
| `WhatsAppBusinessPreview` | No changes                                                       |
| `CoverageHero`            | No changes                                                       |

---

## 9. New API Routes Required

| Route                           | Method | Returns                                               | Used by                  |
| ------------------------------- | ------ | ----------------------------------------------------- | ------------------------ |
| `/dashboard/operations-summary` | GET    | E1, G6, E3, S1, S3 metrics                            | OperationsGrid           |
| `/risk/summary`                 | GET    | 4 risk scores (G2/G5/G8/G3)                           | RiskScoreStrip           |
| `/suppliers/risk-ranked`        | GET    | Suppliers sorted by G2 score, with per-cluster scores | SupplierMap              |
| `/suppliers/{id}/profile`       | GET    | Full supplier ESG profile for one supplier            | SupplierProfilePanel     |
| `/scope3/categories`            | GET    | All 8 Scope 3 categories with coverage and tCO2e      | Scope3DetailPanel        |
| `/risk/geopolitical`            | GET    | Country risk matrix                                   | GeopoliticalHeatmap      |
| `/risk/scorecard`               | GET    | 2x2 quadrant scores                                   | RiskScorecard            |
| `/risk/flags`                   | GET    | Prioritized ML risk flags with recommendations        | RiskFlagsFeed            |
| `/scope3/completeness`          | GET    | Overall completeness % + per-category breakdown       | Scope3CompletenessMeter  |
| `/frameworks/compare/{cluster}` | GET    | Framework mapping for given cluster                   | FrameworkClusterDropdown |

---

## 10. Implementation Priority

**Phase 1 (MVP — current sprint)**:

1. Expand Dashboard tab: add OperationsGrid (E1, G6, E3, S1, S3) + RiskScoreStrip
2. Expand TrendChart to include waste series
3. Add Risk & Alerts tab with RiskScorecard + RiskFlagsFeed

**Phase 2 (Next sprint)**: 4. Add Supply Chain tab with SupplierMap + SupplierProfilePanel 5. Add Scope3DetailPanel (all 8 categories)

**Phase 3**: 6. Add GeopoliticalHeatmap + Scope3CompletenessMeter 7. Expand FrameworkCompare to all 14 clusters 8. Add ML recommendation text to supplier profiles

---

## 11. Design Decisions Requiring User Input

1. **Who is the primary user for the Risk & Alerts tab?** If H&M's analyst uses the same dashboard as the supplier's ESG manager, the flag recommendations should be calibrated differently (H&M wants to see sourcing risk; supplier wants to see what to fix). Current design assumes shared view with role-based visibility on flag severity.

2. **How should G1 ESG Governance appear?** Governance data (board composition, policy documents) is qualitative and document-based — it does not fit a metric card. Should it appear as a document checklist panel on the Dashboard tab, or as a separate Governance tab?

3. **Water (G6) — operational data or supply-chain data?** Currently classified as a factory ops metric (Dashboard tab). But for textile suppliers, water risk in the supply chain (Tier 2 cotton farming) is a major investor concern. Should the dashboard show both the factory's water consumption AND the supply-chain water risk?

4. **Traceability (G7) — how granular?** Full chain-of-custody from cotton field to finished garment requires data the supplier may not have. What is the minimum viable traceability score — supplier-level (current) or sub-supplier-level?
