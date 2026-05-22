# DECISION: Todo Prioritization — Value-Ranked Build Order

**Date**: 2026-05-19

## Decision

61 todos organized into 4 milestones (A-D), value-ranked by CFO buyer priority rather than technical dependency order alone.

## Prioritization Rationale

1. **WhatsApp Supplier Collection** (Milestone B, 18 todos) — THE deal-closer. Journal anchor: `0001-DISCOVERY-deal-closer.md`. Value-auditor confirmed: CFO buys because H&M requires Scope 3 data and WhatsApp is how suppliers in Bangladesh actually communicate.

2. **Framework Mapping Engine** (Milestone C1, 4 todos) — Core USP. Journal anchor: `0002-DISCOVERY-framework-mapping-is-the-usp.md`. Collecting data is useless without outputting it in buyer-required format.

3. **Emission Factor Database** (Milestone A2, 5 todos) — Technical dependency that blocks both #1 and #2. Hardcoded 0.94 factor replaced with real GHG Protocol/IEA/DEFRA sourced factors.

## Trade-off

Phase A (data foundation) must complete before Phase B (WhatsApp) and Phase C (framework mapping) can return accurate numbers. But Phase A has the lowest buyer-visible value on its own. The build order respects this: A ships first (table stakes), B ships second (deal-closer), C ships third (proof), D ships last (wow factor).

## Build/Wire Separation

Every component with data flow has separate BUILD and WIRE todos. BUILD = component runs with structure and logic. WIRE = real data flows end-to-end with zero mock/hardcoded data remaining. These are NOT collapsed because a component returning hardcoded data while appearing functional is the same as a broken component.
