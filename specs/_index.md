# Specs Index — ESG SCRM Dashboard

## Domain Overview

The ESG SCRM dashboard is an investor demo for a Bangladesh garment supplier (Bangladesh Export Textiles Ltd.) selling to H&M. The dashboard demonstrates an ESG data orchestration platform that maps internal KPIs to multiple disclosure frameworks (CSRD, ISSB, GRI, TCFD) and collects supplier ESG data via WhatsApp.

Current scope: Scope 1+2 energy/emissions tracker with supplier coverage measurement.
Target scope: Full ESG platform covering 14 clusters (9 from friend + 5 gaps).

---

## Spec Files

| File                     | Domain     | Description                                                                                        |
| ------------------------ | ---------- | -------------------------------------------------------------------------------------------------- |
| `dashboard-metrics.md`   | Metrics    | All ESG metric definitions, calculation methodologies, confidence tiers, and evidence chain schema |
| `dashboard-api.md`       | API        | All backend API routes — existing + planned — with request/response schemas                        |
| `dashboard-tabs.md`      | UI         | Tab structure, panel layout, component inventory for all 5 tabs                                    |
| `framework-mapping.md`   | Compliance | Framework mapping engine: how each metric maps to CSRD/ESSB/GRI/TCFD field IDs                     |
| `supplier-engagement.md` | Engagement | WhatsApp questionnaire template, coverage stats, supplier data collection flow                     |
| `esg-ratings.md`         | Ratings    | ESG rating computation (EcoVadis-style 0-100 + MSCI-style AAA-to-CCC), per-cluster scoring         |
| `risk-alerts.md`         | Risk       | ML-generated risk flags, prioritization, acknowledgment workflow                                   |

---

## Key Design Decisions

1. **Dashboard = 5 tabs**: Dashboard | Supply Chain | Risk & Alerts | Frameworks | Engagement
2. **Risk scoring = A/B/C/D tiers**: Suppliers and clusters scored 0-100, bucketed into risk tiers
3. **Framework mapping is the core USP**: One data entry, multiple framework outputs — expand beyond 4 metrics
4. **Evidence chain on every metric**: SHA-256 hash chain from source system to reported number
5. **WhatsApp-first supplier engagement**: No email portals; suppliers respond via WhatsApp Business API
