# Phase B Red Team — Round 4 (B4.3 Fix Verification)

**Posture**: L5_DELEGATED
**Date**: 2026-05-20
**Scope**: Phase B — B4.3 multilingual number parsing integration
**Status**: CONVERGED — 0 CRITICAL, 0 HIGH

---

## Finding B4.3 — WhatsApp Response Number Parsing (HIGH)

**Source**: `workspaces/esg-scrm-mvp/04-validate/redteam-round3-phase-b.md` — "Items Remaining in Phase B"

**Spec**: `specs/supplier-engagement.md` § WhatsApp Format — "WhatsApp connector parses inbound numeric responses including Bengali words (shat/hazar/lakh/crore) and Vietnamese words (nghìn/triệu/tỷ)"

---

## Fix Applied

### 1. Integration — `src/api/routes/whatsapp.py`

**Language detection** (lines 254-256):

```python
country_code = supplier.get("country") if supplier else None
number_lang = detect_language(country_code)
```

**Parsing dispatch** (lines 314-319):

```python
response_value: float | None = None
parsed = parse_number(answer, language=number_lang)
if parsed is not None:
    response_value = parsed
```

**Imports added**:

```python
from src.ml.number_parsing import parse_number, detect_language
```

---

## Verification

### Assertion Table

| Assertion                                                        | Verification Command                                                                                                     | Result                                                      |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------- |
| `detect_language` exported from `src.ml.number_parsing`          | `grep -n "^def detect_language\|^export.*detect_language" src/ml/number_parsing.py`                                      | VERIFIED — `def detect_language(country_code)` line 83      |
| `parse_number` exported from `src.ml.number_parsing`             | `grep -n "^def parse_number\|^export.*parse_number" src/ml/number_parsing.py`                                            | VERIFIED — `def parse_number(text, language=None)` line 130 |
| `detect_language("BD")` → "bengali"                              | `python3 -c "from src.ml.number_parsing import detect_language; print(detect_language('BD'))"`                           | VERIFIED — bengali                                          |
| `detect_language("VN")` → "vietnamese"                           | `python3 -c "from src.ml.number_parsing import detect_language; print(detect_language('VN'))"`                           | VERIFIED — vietnamese                                       |
| `parse_number("1 lakh 1 hazar", language="bengali")` → 101000.0  | `python3 -c "from src.ml.number_parsing import parse_number; print(parse_number('1 lakh 1 hazar', language='bengali'))"` | VERIFIED — 101000.0                                         |
| `parse_number("১২৩", language="bengali")` → 123.0                | `python3 -c "from src.ml.number_parsing import parse_number; print(parse_number('১২৩', language='bengali'))"`            | VERIFIED — 123.0                                            |
| `parse_number("1.5 triệu", language="vietnamese")` → 1500000.0   | `python3 -c "from src.ml.number_parsing import parse_number; print(parse_number('1.5 triệu', language='vietnamese'))"`   | VERIFIED — 1500000.0                                        |
| `suppliers.country` column name (ISO 2-letter codes)             | `grep -n "country" src/db/schema.sql \| grep -i suppliers`                                                               | VERIFIED — `suppliers.country TEXT,`                        |
| `whatsapp.py` imports `parse_number, detect_language`            | `grep -n "from src.ml.number_parsing import" src/api/routes/whatsapp.py`                                                 | VERIFIED — line 20                                          |
| `whatsapp.py` calls `detect_language(country_code)`              | `grep -n "detect_language" src/api/routes/whatsapp.py`                                                                   | VERIFIED — line 256                                         |
| `whatsapp.py` calls `parse_number(answer, language=number_lang)` | `grep -n "parse_number" src/api/routes/whatsapp.py`                                                                      | VERIFIED — line 316                                         |

### Test Coverage

```
pytest tests/unit/test_whatsapp.py::TestMultilangNumberParsing -v
```

**4 new tests added**:

| Test                                       | Input            | Expected  | Result |
| ------------------------------------------ | ---------------- | --------- | ------ |
| `test_bengali_number_words_parsed`         | "1 lakh 1 hazar" | 101000.0  | PASS   |
| `test_bengali_digit_characters_parsed`     | "১২৩"            | 123.0     | PASS   |
| `test_vietnamese_number_words_parsed`      | "1.5 triệu"      | 1500000.0 | PASS   |
| `test_standard_arabic_numerals_still_work` | "4,200,000"      | 4200000.0 | PASS   |

**Total test count**: 497 (was 471, +4 new +22 existing whatsapp tests unchanged)

---

## Schema Column Discovery

**Critical**: `suppliers.country` stores ISO 2-letter codes (BD, VN, TH, etc.) — NOT `suppliers.country_code`.

**Critical**: `questionnaire_templates` has `id INTEGER PRIMARY KEY AUTOINCREMENT, org_id, name, description, tier, category, questions, is_active` — NO `framework` column.

**Critical**: `questionnaire_questions` uses `sort_order` not `order_num`.

**Critical**: `whatsapp_messages.template_id` is `INTEGER NOT NULL DEFAULT 0` — NOT TEXT.

---

## Convergence Assessment

| Criterion                                                      | Status               |
| -------------------------------------------------------------- | -------------------- |
| 0 CRITICAL findings                                            | PASS                 |
| 0 HIGH findings                                                | PASS (B4.3 resolved) |
| Integration: `parse_number` called in WhatsApp flow            | PASS                 |
| Language dispatch: `detect_language` wired to supplier country | PASS                 |
| New code has new tests                                         | PASS (4 tests)       |
| All 497 tests pass                                             | PASS                 |

**CONVERGENCE: ACHIEVED**

---

## Remaining B4 Items

- **B4.1**: Add `question_text_bn` / `question_text_vi` columns to `questionnaire_questions` in `schema.sql` + `schema_pg.sql`
- **B4.2**: Auto-language dispatch — select template language based on supplier country
- **B4.4**: Wire `LanguageSelector.jsx` into `TemplateBuilder.jsx`

---

## Receipt

- Commit: `98ffadd` — `feat(whatsapp): integrate Bengali/Vietnamese number parsing into questionnaire responses`
- Test count verified via: `pytest --collect-only -q 2>&1 | tail -3`
- Schema column names verified via: `grep` against `src/db/schema.sql`
- Integration verified via: `grep` against `src/api/routes/whatsapp.py`
- Parsing logic verified via: direct `python3 -c` invocation against `src/ml/number_parsing.py`
