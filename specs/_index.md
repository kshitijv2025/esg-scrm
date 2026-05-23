# Specs Index — ESG SCRM Commercial Product

## Domain Overview

ESG SCRM is a commercial ESG compliance platform for mid-market manufacturers in Asia. Four investor-validated features: ESG Data Orchestration, Supply-Chain ESG Collection, Assurance-Ready Evidence Vault, and Real-Time ESG Monitoring. Target buyer: CFO/COO at factories exporting to H&M, Zara, and Uniqlo.

---

## Spec Files

| File                     | Domain         | Description                                                                                                  |
| ------------------------ | -------------- | ------------------------------------------------------------------------------------------------------------ |
| `auth.md`                | Authentication | JWT auth, registration, login, password strength, rate limiting, RBAC tiers, org isolation                   |
| `data-model.md`          | Data           | All entities, relationships, multi-tenancy schema, tables, constraints                                       |
| `dashboard-metrics.md`   | Metrics        | ESG metric definitions, calculation methodologies, confidence tiers, evidence chain schema                   |
| `dashboard-api.md`       | API            | All backend API routes with request/response schemas, pagination, org scoping                                |
| `dashboard-tabs.md`      | UI             | Tab structure, panel layout, component inventory for all 5 tabs                                              |
| `framework-mapping.md`   | Compliance     | Framework mapping engine: KPI-to-framework table, per-framework output generation, emission factor citations |
| `supplier-engagement.md` | Engagement     | WhatsApp questionnaire templates, response capture, coverage stats, multi-language dispatch                  |
| `evidence-vault.md`      | Evidence       | Hash chain integrity, methodology tagging, emission factor references, data lineage, auditor export          |
| `risk-alerts.md`         | Risk           | ML-generated risk flags, configurable thresholds, alert deduplication, acknowledgment workflow               |
| `billing.md`             | Billing        | Stripe subscriptions, plan tiers, webhook events, supplier limit enforcement                                 |
| `gdpr.md`                | GDPR           | Data export (Article 20), account deletion (Article 17), soft-delete, 30-day retention                       |
| `multi-org.md`           | Multi-Org      | Per-org role scoping, org switch, invitations, member management, role resolution                            |

---

## Key Design Decisions

1. **Dashboard = 5 tabs**: Dashboard | Supply Chain | Risk & Alerts | Frameworks | Engagement
2. **Multi-tenancy**: All tables carry `org_id`, injected from JWT by middleware, never client-supplied
3. **RBAC tiers**: ADMIN_ROLES={admin}, EDITOR_ROLES={admin,editor}, VIEWER_ROLES={admin,editor,viewer}
4. **Framework mapping is the core USP**: One data entry, multiple framework outputs
5. **Evidence chain on every metric**: SHA-256 hash chain from source system to reported number
6. **WhatsApp-first supplier engagement**: No email portals; suppliers respond via WhatsApp Business API
7. **MQTT for IoT ingestion**: Smart meter data via MQTT topics, CSV fallback for factories without MQTT brokers
8. **Emission factors from GHG Protocol**: Every emissions number cites source, region, and year
9. **Data entry via CSV upload**: Primary path for factories without ERP API access; ERP integration is premium upsell
