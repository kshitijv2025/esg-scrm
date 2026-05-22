# B5 — Multi-Channel Architecture + i18n

**Date:** 2026-05-20
**Phase:** B / Deal-Closer — WhatsApp Supplier Collection
**Status:** Complete

## What Was Built

### B5.1 react-intl i18n Framework

- `IntlProvider` added to `App.jsx`
- Locale files: `en.json` (52 keys), `bn.json` (Bengali), `vi.json` (Vietnamese)
- `LanguageSelector.jsx` uses `useIntl`/`formatMessage`
- All hardcoded English strings in UI chrome extracted to locale files
- **Verification:** `grep "IntlProvider\|useIntl\|formatMessage\|bn.json\|vi.json" apps/web/src/App.jsx apps/web/src/locales/`

### B5.2 LINE Business API Adapter

- `src/connectors/line.py` with send/receive matching WhatsApp adapter pattern
- Vietnam/Thailand market coverage
- **Verification:** `ls src/connectors/line.py`

### B5.3 WeChat Work Adapter

- `src/connectors/wechat.py` with send/receive
- China-proximate suppliers coverage
- **Verification:** `ls src/connectors/wechat.py`

## Specs Implemented

- `specs/supplier-engagement.md`
- Brief Feature 2 "Collect data via LINE", "Collect data via WeChat", "Localization required"
