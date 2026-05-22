# B2 — WhatsApp Business API Integration

**Date:** 2026-05-20
**Phase:** B / Deal-Closer — WhatsApp Supplier Collection
**Status:** Complete

## What Was Built

### B2.1 WhatsApp Connector Rewrite (whatsapp.py)

- `src/connectors/whatsapp.py` rewritten with Twilio WhatsApp Business API client
- `send_template_message(to, template_id, language)` — sends questionnaire as interactive WhatsApp messages
- `receive_webhook(request)` — receives supplier responses
- `parse_response(message_body, question_type)` — parses free-text/numeric responses into structured data
- `verify_webhook` uses Base64-encoded HMAC with `hmac.compare_digest` (constant-time comparison)
- **Verification:** `grep "send_template_message\|receive_webhook\|parse_response\|compare_digest" src/connectors/whatsapp.py`

### B2.2 WhatsApp Webhook Route (whatsapp.py)

- `src/api/routes/whatsapp.py` — webhook endpoint for Twilio callbacks
- No auth required on webhook (verified by signature)
- Message status tracking, delivery/read receipt logging
- Demo mode: marks data with `demo_mode=1`
- **Verification:** `grep "webhook\|TwilioCallback\|demo_mode" src/api/routes/whatsapp.py`

### B2.3 Questionnaire Responses Table

- `questionnaire_responses` table: supplier_id, template_id, question_id, response_value, response_text, channel (whatsapp/web/manual), received_at, confidence, org_id
- **Verification:** `grep "questionnaire_response" src/db/schema.sql`

### B2.4 WhatsApp-Template Wiring

- `send_questionnaire()` fetches questions from template via `_resolve_template()`
- `_format_questionnaire()` uses `text_bn`/`text_vi` based on country_code
- `receive_webhook()` parses and stores responses
- Question IDs validated against template questions sent
- **Verification:** `grep "_resolve_template\|_format_questionnaire\|receive_webhook" src/connectors/whatsapp.py src/api/routes/whatsapp.py`

### B2.5 Twilio Env Vars (.env.example)

- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER`, `TWILIO_WEBHOOK_URL`
- **Verification:** `grep "TWILIO" .env.example`

### B2.5a Webhook HMAC Upgrade (security)

- Webhook verification upgraded from SHA-1 to SHA-256
- `hmac.compare_digest` for constant-time comparison (prevents timing attacks)
- **Verification:** `grep "sha256\|compare_digest\|hmac" src/connectors/whatsapp.py`

### B2.6 Email Questionnaire Fallback

- `POST /api/questionnaires/send-email` dispatches via SMTP
- Second channel alongside WhatsApp
- **Verification:** `grep "send-email\|send_email" src/api/routes/questionnaires.py`

### B2.7 Web Portal Response Capture

- Authenticated page for suppliers to fill questionnaire via browser
- Portal link generation: `POST /api/questionnaires/portal/link/{supplier_id}`
- Triggered from `SupplierEngagementTab.jsx`
- **Verification:** `grep "portal.*link\|web.*portal\|portal_link" src/api/routes/questionnaires.py`

## Specs Implemented

- `specs/supplier-engagement.md` § WhatsApp Message Format
- `specs/dashboard-api.md`
