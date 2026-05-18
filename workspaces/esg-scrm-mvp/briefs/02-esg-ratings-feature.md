# ESG Ratings Feature — New Feature Brief

> **Status: Deferred** (2026-05-07) — Removed from current sprint. No backend endpoint exists and client-side derivation requires a validated scoring methodology before UI is meaningful. Re-evaluate after backend scoring engine is built.

## Source

Dashboard feature request — add an ESG Ratings panel to the existing investor demo.

## What is being asked

Add an ESG Ratings display panel to the dashboard showing:

- An overall ESG letter grade (AAA to CCC, like MSCI)
- A breakdown by E, S, and G with individual scores
- The provider name (simulate EcoVadis-style 0-100 percentile scoring)
- Peer comparison (position relative to industry average)
- Key drivers / risk flags that explain the rating

## The ask in the user's own words

"ESG ratings are calculated by turning company data into scores for environmental, social, and governance factors, then combining those scores using a provider's own methodology. The exact formula differs by provider, but most weigh material issues more heavily, adjust for industry peer comparisons, and use company disclosures plus external data sources."

"MSCI rates companies on a seven-point scale from AAA to CCC based on industry-relative ESG risk management. It starts by selecting the most relevant environmental and social 'key issues' for the company's industry, then scores exposure to those risks and the quality of management controls, and finally normalizes the result against industry peers to produce the final letter rating."

"Sustainalytics focuses on unmanaged ESG risk, meaning the amount of ESG risk a company is exposed to after accounting for management actions."

## Design intent

- Provider: EcoVadis-style (0–100 score → Bronze/Silver/Gold/Platinum)
- Secondary rating: MSCI-style (AAA to CCC) for E and S separately
- Tertiary: Governance score 0–10
- Peer benchmark: garment manufacturing industry (Bangladesh context)
- Visual: gauge chart or radial breakdown, letter grades prominent
- Clicking a category shows: key issue scores, peer percentile, trend vs prior year

## Constraints

- Must fit within existing demo aesthetic (dark theme, green accent)
- Uses existing demo data (energy, emissions, water, Scope 3, supplier coverage)
- No new backend data required — compute scores from existing METRICS + evidence data
- Must feel credible to an investor reviewing the demo

## What's in scope for this analysis

1. Rating methodology design (what inputs, what weights, what output)
2. How the panel looks and behaves in the dashboard
3. What data it needs from the existing backend
4. How it ties into the existing 3-tab layout
5. Whether this belongs in the demo at all (or is it a distraction?)
