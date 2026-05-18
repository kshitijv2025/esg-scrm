# MVP Build Plan — 4 Features

## Critical Path

Feature 1 (Data Orchestration) must be built first — all other features depend on its data model.

```
Feature 1: Data Orchestration
    ├── Xero Connector (first: fastest to working demo)
    ├── Normalization Engine
    └── Framework Mapping Engine
            ↓
Feature 3: Evidence Vault (depends on DataPoint model)
    ├── EvidenceRecord entity
    ├── Hash chain
    └── Audit export
            ↓
Feature 2: Supplier Collection
    ├── WhatsApp BSP integration (via Twilio/MessageBird)
    ├── Questionnaire Engine
    └── Scope3 Calculator
            ↓
Feature 4: Real-Time Monitoring
    └── Dashboard + Alert system (reuses Feature 1 connectors)
```

## Phase 1: Foundation (Month 1–2)

### Week 1–2: Core Data Model + Xero Connector

**Goal:** End-to-end working demo: connect Xero → extract utility data → map to CSRD → display disclosure package.

Tasks:

- [ ] Set up project: monorepo, FastAPI backend, React frontend, PostgreSQL
- [ ] Implement DataPoint, Organization, Integration entities
- [ ] Build Xero OAuth2 connector (test connection, extract utility invoices)
- [ ] Build Normalization Engine: Xero → DataPoint mapping
- [ ] Build Framework Mapping Engine: DataPoint → CSRD disclosure
- [ ] Basic dashboard: show DataPoints with confidence badges
- [ ] EvidenceRecord creation on DataPoint report inclusion

**Demo target:** Upload a sample Xero export, see CSRD disclosure in 5 minutes.

### Week 3–4: Second Connector + Evidence Vault

**Goal:** Two connectors working + Evidence Vault shipped.

Tasks:

- [ ] Build SAP Business One connector (or NetSuite if SAP unavailable)
- [ ] Evidence Vault: hash chain implementation
- [ ] EvidenceRecord creation for all DataPoints
- [ ] Weekly hash verification job
- [ ] Basic auditor portal (read-only, time-limited access)
- [ ] Audit export (PDF + JSON ZIP)

**Demo target:** Show an auditor "here's the evidence for this number, click to drill down."

### Week 5–8: Supplier Collection v1

**Goal:** WhatsApp supplier questionnaire working end-to-end.

Tasks:

- [ ] WhatsApp Business Account setup (via Twilio BSP)
- [ ] Messaging Gateway: WhatsApp send/receive
- [ ] Questionnaire Engine: template import, question routing
- [ ] NLUParser for response parsing
- [ ] Follow-up automation (Day 3, 7, 14)
- [ ] Scope3 Calculator from supplier responses
- [ ] LINE connector (for Thailand market)

**Demo target:** Send a 5-question WhatsApp questionnaire to a supplier, receive response, see it populate Scope 3 calculation.

## Phase 2: Real-Time + Enterprise (Month 3–4)

### Week 9–12: Real-Time Monitoring

**Goal:** Live dashboard with hourly data refresh + alert system.

Tasks:

- [ ] Hourly batch job from ERP connectors (reuse Feature 1 connectors)
- [ ] Dashboard: live counters + trend charts
- [ ] ThresholdAlert entity + evaluation engine
- [ ] Alert notification: email + dashboard badge
- [ ] WhatsApp alert notification
- [ ] Alert acknowledgment workflow

**Demo target:** Show live energy counter updating hourly, trigger a test alert.

### Week 13–16: NetSuite + SAP S/4HANA Connectors

**Goal:** Enterprise ERP integrations for division-level deals.

Tasks:

- [ ] NetSuite connector (SuiteQL API)
- [ ] SAP S/4HANA connector (if access available)
- [ ] Multi-connector management UI
- [ ] Integration health monitoring
- [ ] Credential rotation for all connectors

## Success Metrics

| Milestone                  | Target  | Measurement                                            |
| -------------------------- | ------- | ------------------------------------------------------ |
| Xero end-to-end demo       | Week 2  | Upload Xero export → CSRD disclosure in < 5 min        |
| SAP Business One live      | Week 4  | Customer sees their actual data in the platform        |
| WhatsApp questionnaire     | Week 8  | Supplier receives and responds to WhatsApp message     |
| First paying customer      | Month 3 | Signed contract, data connected                        |
| 60% supplier response rate | Month 4 | 3 of 5 suppliers responding to WhatsApp                |
| Real-time dashboard live   | Month 4 | Hourly data refresh visible on screen                  |
| Big 4 auditor acceptance   | Month 6 | Auditor reviews Evidence Vault without manual requests |

## What NOT to Build in MVP

- WeChat integration (China, deferred)
- SCADA/OPC-UA direct sensor integration (post-MVP)
- AI Copilot (Feature 7, deferred)
- Supplier Intelligence Graph (Feature 8, deferred)
- Multi-tenant architecture (single org per deployment for MVP)
- Mobile app (responsive web is sufficient)

## Technical Decisions to Make Now

| Decision          | Recommendation                               | Rationale                                                                 |
| ----------------- | -------------------------------------------- | ------------------------------------------------------------------------- |
| Backend framework | FastAPI                                      | Native async, Pydantic for data validation, good for ERP integration work |
| Frontend          | React + Tailwind                             | Fast iteration, good dashboard component libraries                        |
| Database          | PostgreSQL                                   | ACID compliance needed for Evidence Vault hash chain integrity            |
| Message queue     | Redis Streams (or SQS if AWS)                | Simpler than Kafka for MVP scale                                          |
| WhatsApp BSP      | Twilio                                       | Easiest WhatsApp Business API access, good docs                           |
| Deployment        | Vercel (frontend) + Railway/Render (backend) | Fastest path to live demo                                                 |
| ERP sandbox       | Xero provides free sandbox                   | Use for all development and testing                                       |
