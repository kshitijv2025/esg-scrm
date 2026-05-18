# DECISION: Track procurement spend coverage rate, not response rate

## What

The brief says "supplier response rate > 60%." The correct metric is coverage rate: what fraction of total procurement spend is covered by responding suppliers.

## Detail

If the 60% who respond are small suppliers (trims, packaging, logistics) while the 40% who don't respond include the large spinning mills and dye houses (60% of procurement spend), Scope 3 data is useless. The non-responding 40% represents the emissions that actually matter.

## Decision

Metrics to track:

- Response rate: number of suppliers who responded / number of suppliers contacted (secondary metric)
- Coverage rate: total procurement spend of responding suppliers / total procurement spend of all suppliers (primary metric)

Target: 60% coverage rate by spend, not 60% response rate by headcount.

Pilot validation: target the largest 3 suppliers by spend first — if they respond, coverage is high even at lower response rates.

## Source

Value auditor finding, confirmed in VC red team Round 3

## Action

Update specs/02-supplier-collection.md success criteria. Update investor pitch metrics.
