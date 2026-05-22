# B4 — Multi-Language Questionnaire Dispatch

**Date:** 2026-05-20
**Phase:** B / Deal-Closer — WhatsApp Supplier Collection
**Status:** Complete

## What Was Built

### B4.1 Language Support in Questions

- `questionnaire_questions` table has `question_text_bn` (Bengali) and `question_text_vi` (Vietnamese) columns
- Seed data includes Bengali and Vietnamese translations for Tier 1-3 questions
- **Verification:** `grep "question_text_bn\|question_text_vi" src/db/schema.sql src/db/seed_templates.py`

### B4.2 Auto-Language Dispatch

- `_format_questionnaire()` dispatches `text_bn` for BD/BGD country codes
- Dispatches `text_vi` for VN/VNM country codes
- Default: English
- `get_supplier_questionnaire_data` also dispatches based on `country_code`
- **Verification:** `grep "text_bn\|text_vi\|BD\|BG\|VN\|country_code" src/connectors/whatsapp.py src/api/routes/questionnaires.py`

### B4.3 Bengali + Vietnamese Number Parsing

- `src/ml/number_parsing.py` provides:
  - `parse_bengali_number()` — converts ০১২৩৪৫৬৭৮৯০ to standard digits
  - `parse_vietnamese_number()` — converts Vietnamese number formats
- **Verification:** `grep "parse_bengali\|parse_vietnamese\|০" src/ml/number_parsing.py`

### B4.4 Frontend Language Selector

- `LanguageSelector.jsx` exists
- `TemplateBuilder.jsx` uses it with three textarea fields for English/Bengali/Vietnamese
- Dropdown to switch preview language
- **Verification:** `ls apps/web/src/components/LanguageSelector.jsx && grep "LanguageSelector" apps/web/src/components/TemplateBuilder.jsx`

## Specs Implemented

- `specs/supplier-engagement.md`
- `specs/dashboard-tabs.md` § Engagement tab
