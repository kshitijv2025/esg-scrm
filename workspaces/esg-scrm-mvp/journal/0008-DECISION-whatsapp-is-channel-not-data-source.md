# DECISION: WhatsApp is supplier engagement channel, not primary data source

## What

VC raised WhatsApp platform dependency risk: what if Meta restricts Business API access in Bangladesh (they've restricted Facebook before)?

## Resolution

WhatsApp is the _supplier engagement layer_ for filling gaps, not the primary data source. Primary data comes from:

1. ERP API connectors (SAP B1, NetSuite, Xero) — primary data pipeline
2. IoT sensors via ERP integration — real-time monitoring data
3. WhatsApp questionnaires — supplier data for Scope 3 Category 1 where API data doesn't exist

If WhatsApp disappears tomorrow: primary data pipeline (ERP connectors) continues. Only the supplier questionnaire gap-fill is disrupted.

## Why This Matters

This reframes the WhatsApp risk from "existential threat to the business" to "risk to supplier response rate for Scope 3 data." The fallback is not "we go out of business" — it's "we use email + web portal for supplier collection with lower response rates."

## Mitigation

- Multi-channel: WhatsApp + LINE + email + web portal all supported from day 1
- ERP API as primary pipeline: even if WhatsApp is disrupted, core data flows continue
- Coverage tracking (not response rate): measure procurement spend coverage, not response rate percentage

## Source

VC red team Round 1 — platform dependency concern

## Action

Update specs/02-supplier-collection.md to clarify WhatsApp's role as one channel among four.
