# B1 — Questionnaire Template System

**Date:** 2026-05-20
**Phase:** B / Deal-Closer — WhatsApp Supplier Collection
**Status:** Complete

## What Was Built

### B1.1 Questionnaire Tables

- `questionnaire_templates` and `questionnaire_questions` tables created in both `schema.sql` and `schema_pg.sql`
- Templates: id, org_id, name, language, category (environment/social/governance), is_active
- Questions: id, template_id, question_text, question_type (number/choice/text), choices (JSON), sort_order, required
- **Verification:** `grep "questionnaire_template\|questionnaire_question" src/db/schema.sql`

### B1.2 Templates CRUD API (templates.py)

- `src/api/routes/templates.py` with full CRUD
- Endpoints: create template, add questions, reorder questions, copy template, activate/deactivate, list templates by org
- Editor role required
- **Verification:** `grep "template\|questionnaire" src/api/routes/templates.py | head -20`

### B1.3 Seed Templates (seed_templates.py)

- 3 pre-built templates seeded:
  1. H&M ESR Basic (English)
  2. H&M ESR Basic (Bengali)
  3. GRI-aligned comprehensive
- Each with 10-15 questions covering Tier 1-3 from spec
- **Verification:** `ls src/db/seed_templates.py && grep "H&M\|GRI\|Bengali" src/db/seed_templates.py`

### B1.4 Frontend Template Builder (TemplateBuilder.jsx)

- Create/edit template form
- Add/remove/reorder questions
- Question type selector
- Mobile preview panel
- **Verification:** `ls apps/web/src/components/TemplateBuilder.jsx`

## Specs Implemented

- `specs/supplier-engagement.md` § Expanded Questionnaire Scope, Tiers 1-4
- `specs/dashboard-api.md`
- `specs/dashboard-tabs.md` § Engagement tab
