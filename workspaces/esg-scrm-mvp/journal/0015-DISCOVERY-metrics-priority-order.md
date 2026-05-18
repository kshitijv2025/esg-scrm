---
name: discovery-metrics-priority-order
description: Top 10 metrics prioritized for operations homepage — supply chain coverage first
type: DISCOVERY
date: 2026-05-07
created_at: 2026-05-07T00:00:00Z
author: agent
session_id: esg-scrm-mvp
session_turn: 2
project: esg-scrm-mvp
topic: dashboard metrics priority
phase: analyze
tags: [metrics, priority, ux, operations-tab]
---

# DISCOVERY: Top 10 metrics for operations homepage, priority ordered

## Decision

Summary strip (4 KPIs) above the existing 6 metric cards. No existing metrics removed.

## Priority hierarchy

### Row 0 — Summary Strip (new)
1. **Supply Chain Coverage %** — leading indicator for Scope 3 data quality (coverage drives everything else)
2. **Active Risk Flags** — COO action trigger; count of open risks needing attention
3. **Scope 3 Completeness %** — what % of Scope 3 categories have supplier responses
4. **Total CO2e (All Scopes)** — derived client-side: emissions + scope3_cat1 + diesel + business_travel

### Rows 1–2 — Operational Metrics (existing 6, unchanged)
5. Electricity (Scope 2) | 6. Total Emissions (Scope 1+2) | 7. Water Withdrawal
8. Purchased Goods (Scope 3) | 9. Diesel Combustion (Scope 1) | 10. Business Travel (Scope 3)

## Key finding: CFO/COO buyer hierarchy

The buyer opens the dashboard to answer, in order:
1. "Is my supply chain data complete?" → Coverage %
2. "Do I have any fires to put out?" → Risk Flags
3. "How much of Scope 3 do I know?" → Scope 3 Completeness
4. "What is my total carbon?" → Total CO2e

The 6 operational metrics are the drill-down evidence. They are secondary to the summary strip.

## Implementation
- `SummaryStrip` component added to App.jsx
- Dashboard `useEffect` extended to fetch `/risk/summary` + `/scope3/completeness`
- Total CO2e derived client-side from existing metrics data
- CSS: `.summary-strip` grid, responsive at 900px and 600px breakpoints
