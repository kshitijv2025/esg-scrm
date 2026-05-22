# C1 — Framework Mapping Engine

**Date:** 2026-05-20
**Phase:** C / The Proof — Framework Mapping + Compliance Reports
**Status:** Complete

## What Was Built

### C1.1 Framework Mappings Table

- `framework_mappings` table created
- Columns: metric_name, framework (GRI/TCFD/CSRD/ISSB/SASB), field_id, field_name, unit, calculation_method, cluster
- **Verification:** `grep "framework_mapping" src/db/schema.sql src/db/schema_pg.sql`

### C1.2 Seed Framework Mappings (seed_framework_mappings.py)

- 60+ rows seeded mapping 14 clusters × 5 frameworks
- Clusters: E1-E3 (Environment), S1-S3 (Social), G1-G8 (Governance)
- Frameworks: GRI, CSRD, ISSB, TCFD, SASB
- SASB mappings for ALL 14 clusters (not just diesel)
- CDP mapping rows for water and emissions clusters
- **Verification:** `grep "CSRD\|ISSB\|TCFD\|SASB\|GRI\|E1\|S1\|G1" src/db/seed_framework_mappings.py | head -20`

### C1.3 Frameworks API Rewrite (frameworks.py)

- `src/api/routes/frameworks.py` rewritten — database-driven mapping engine (replaces 645 lines of hardcoded static dicts)
- `require_auth` on all endpoints
- `POST /api/frameworks/map` — accepts metric values, returns framework-specific output with field IDs, units, confidence levels
- `GET /api/frameworks/compare/{cluster}` — returns all framework mappings for a cluster
- **Verification:** `grep "frameworks/map\|frameworks/compare\|require_auth" src/api/routes/frameworks.py | head -10`

### C1.4 Frontend Frameworks Tab

- Cluster dropdown (14 clusters from spec)
- Comparison table: CSRD/ISSB/GRI/TCFD/SASB field mappings
- Shows: field ID, unit, value, confidence color coding
- Click framework row → side panel with full disclosure requirements
- **Verification:** `grep "Framework\|frameworks\|ClusterDropdown" apps/web/src/pages/FrameworksTab.jsx`

## Specs Implemented

- `specs/framework-mapping.md` § Supported Frameworks, Existing Mappings, Planned Mappings
- `specs/dashboard-tabs.md` § Framework Comparison Table
