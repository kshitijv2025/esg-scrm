# GAP: Core architecture assumption may be false for Bangladesh

## What

The system assumes ESG-relevant physical quantities (kWh, m³ water) exist digitally in the customer's ERP. In Bangladesh garment factories, utility bills are PDFs processed by accountants. kWh is not digitally accessible.

## Detail

Failure analyst found: SAP Business One in Bangladesh runs on-premise on shared servers, often without the Service Layer exposed. "Connect to SAP B1" means consultant-led middleware deployment. The rate limit (1 req/s, no bulk endpoint) makes full extraction infeasible for companies with >10K records.

Value auditor found: "Connect to SAP Business One" requires a local IT vendor in Dhaka who takes 2 weeks to respond to tickets.

Critical path implication: If kWh is not digitally accessible in the lighthouse customer's ERP, the entire architecture must change — and the 60-day go-live target becomes impossible.

## Implication

**Before writing any code: audit one lighthouse customer's SAP B1 system for 2 weeks.** If kWh isn't digitally accessible, either (a) change the MVP to CSV upload (slower but achievable) or (b) select a different first customer with a digital ERP.

## Source

Failure analyst FM-1.1, value auditor Bangladesh CFO red flags
