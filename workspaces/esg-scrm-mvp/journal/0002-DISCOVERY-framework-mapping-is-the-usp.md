# DISCOVERY: Framework mapping engine is the USP — but covers only 4 metrics

**Date**: 2026-05-07

## What was found

The existing `FrameworkCompare` component (App.jsx:579) and `/frameworks/compare/{metric}` API are the platform's core differentiator — the ability to enter data once and map it simultaneously to CSRD, ISSB, GRI, TCFD, and SASB. This is the structural moat vs. Sweep and EcoVadis.

**But**: it currently maps only 4 metrics (energy_kwh, scope3_category1, diesel_consumed, scope3_category6). The 9 clusters + 5 gaps = 14 clusters that need framework mapping are mostly unmapped.

## Why it matters

Expanding the framework mapping engine is a higher-ROI feature than adding new metric panels. Every new metric that feeds the existing framework comparison table immediately becomes a multi-framework disclosure — the demo shows the differentiating value of the platform without requiring a new visualization.

## Where to verify

- `src/api/routes/frameworks.py` — `FRAMEWORK_OUTPUTS` dict with only 4 metric keys
- `App.jsx:579` — `FrameworkCompare` component with hardcoded metric tabs
- `specs/framework-mapping.md` — planned mappings for all 14 clusters

## Implication

The 5-tab architecture recommended by the uiux-designer is sound, but the **highest-leverage implementation step** is not building new panels — it is expanding the framework comparison table to cover all 14 clusters. Every cluster added to the dropdown automatically becomes investor-ready disclosure material.
