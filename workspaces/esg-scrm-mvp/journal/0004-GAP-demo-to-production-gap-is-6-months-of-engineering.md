# GAP: Demo-to-Production Gap is 6 Months of Engineering

**Date**: 2026-05-07

## Finding

The codebase is a polished demo with 0 production infrastructure. Every API returns in-memory dicts. No database, no connectors, no MQTT client, no WhatsApp integration. Converting this demo to a paying customer environment requires rebuilding the entire backend.

## What Exists vs. What's Needed

| Layer               | Exists                                    | Needed                                 |
| ------------------- | ----------------------------------------- | -------------------------------------- |
| Frontend UI         | 3-tab React app, dark theme, metric cards | 5-tab layout, all panels               |
| Backend API         | 7 FastAPI routes, hardcoded dicts         | Real endpoints with DB + connectors    |
| Database            | None                                      | PostgreSQL + DataFlow ORM              |
| Factory integration | None                                      | MQTT consumer, ERP adapters            |
| WhatsApp            | Static preview text                       | Business API integration + AI parser   |
| External APIs       | None                                      | D&B, World Bank, WRI Aqueduct          |
| Framework mapping   | 4 hardcoded metric keys                   | 14 cluster mappings + real computation |
| Risk engine         | None                                      | ML flag generation + priority scoring  |
| Evidence vault      | Theatrical SHA-256 display                | Real hash computation                  |

## Implication

The demo is a sales tool. It cannot become the product without a full backend rebuild. A technical buyer doing due diligence will identify this gap within 10 minutes.

## What to Do Before Investor Demos with Technical Buyers

1. Build `GET /api/dashboard/operations-summary` — real 5-cluster data from a real CSV/DB
2. Wire one real data source (SAP B1 mock or CSV loader) to prove the integration concept
3. Implement one real SHA-256 hash chain for a single metric
4. Add `src/connectors/` implementations (even a mock MQTT client counts as proof of concept)

The demo's visual polish is a strength — don't abandon it. Add one real data path underneath to make the demo credible under technical scrutiny.
