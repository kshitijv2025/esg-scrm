# GAP: 3-6 week constraint is onboarding time, not development time

## What

The brief says "Implementation must be 3–6 weeks, not 3–6 months." The requirements analyst confirmed this is onboarding time per customer AFTER the platform is built. Sequential critical path for initial development is 17–23 weeks.

## Detail

Feature 3 (Evidence Vault) must be built before Feature 1 (Orchestration Platform) because every DataPoint requires auditable lineage — retrofitting provenance into a deployed system is more expensive than designing it upfront.

Feature 2 (Supplier Collection) can run in parallel with Feature 1, but only after Feature 3's data model is complete.

WhatsApp Business API requires Meta Business Verification (2–8 weeks) before any messaging can be sent.

## Implication

The investor pitch should not promise "first customer live in 60 days." It should say: "Platform development takes 4–5 months. First customer onboarding takes 3–6 weeks." The 60-day promise applies to the CSV-based MVP path, not the full platform.

## Source

Requirements analyst, critical path analysis
