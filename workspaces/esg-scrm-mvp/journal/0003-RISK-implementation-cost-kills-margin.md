# RISK: Implementation Cost is Incompatible With $4-5K ACV Pricing

**Date**: 2026-05-07

## Finding

At $4-5K/month ACV ($48-60K/year), gross margin target of 80% requires implementation cost below ~$10K/customer/year. Mid-market factory integrations (SAP B1, MQTT, WhatsApp) cost $15-25K per customer in professional services estimates. This means the first 10-20 customers operate at 40-60% gross margins — below SaaS industry standard — until pre-built connectors exist.

## Why

- No integration connectors exist (src/connectors/ is empty)
- Every mid-market factory has different ERP setup — no two integrations are identical
- WhatsApp Business API verification takes 2-8 weeks before any message can be sent
- 3-6 week implementation SLA from the brief cannot be met without pre-built connectors

## Implication

First cohort of customers must be priced at $6-8K/month to absorb implementation cost. Self-serve connectors for SAP Business One are the single highest-leverage investment for margin improvement.

## Financial math

| Cost element               | Per customer/year            |
| -------------------------- | ---------------------------- |
| Implementation (amortized) | $15,000                      |
| CS / support               | $5,000                       |
| Infrastructure             | $1,200                       |
| Total cost                 | $21,200                      |
| Revenue at $4K/mo          | $48,000                      |
| Gross margin               | **55.8%** (below 80% target) |

At $6K/mo with connectors: implementation drops to $3K amortized → 87% gross margin.

## Mitigation

Price first cohort at $6-8K/month explicitly as "implementation inclusive." Pre-built SAP B1 connector + WhatsApp template = the margin lever.
