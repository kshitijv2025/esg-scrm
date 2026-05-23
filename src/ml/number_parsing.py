"""
Multi-language number parsing utilities for ESG questionnaire responses.

Supports:
  - Bengali (Bangla): shat (100), hazar (1,000), lakh (100,000), crore (10,000,000)
  - Vietnamese: nghìn/nghin (1,000), triệu (1,000,000), đồng (currency suffix)
  - Standard Arabic numerals everywhere else (no-op passthrough)
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Bengali (Bangla) number word parser
# ---------------------------------------------------------------------------

BENGALI_UNITS: dict[str, int] = {
    "shat": 100,
    "শত": 100,
    "hazar": 1_000,
    "হাজার": 1_000,
    "lakh": 100_000,
    "লক্ষ": 100_000,
    "crore": 10_000_000,
    "কোটি": 10_000_000,
}

BENGALI_DIGITS: dict[str, int] = {
    "০": 0,
    "১": 1,
    "২": 2,
    "৩": 3,
    "৪": 4,
    "৫": 5,
    "৬": 6,
    "৭": 7,
    "৮": 8,
    "৯": 9,
}


def _bengali_digits_to_int(digit_str: str) -> Optional[int]:
    """Convert a string of Bengali digit characters (with optional commas) to an int."""
    clean = digit_str.replace(",", "").replace(" ", "").replace(".", "")
    if not clean:
        return None
    try:
        return int("".join(str(BENGALI_DIGITS[d]) for d in clean if d in BENGALI_DIGITS))
    except (ValueError, KeyError):
        return None


def parse_bengali_number(text: str) -> Optional[float]:
    """Convert a Bengali number string to a numeric value.

    Handles:
      - Native Bengali digit characters (১২৩)
      - Number words: shat, hazar, lakh, crore (with Bangla script variants)
      - Mixed: "1 lakh 50 hazar" / "১ লক্ষ ৫০ হাজার"
      - Plain Arabic numerals (passthrough)

    Returns None if the text cannot be parsed as a Bengali number.
    """
    import re

    text = text.strip()
    if not text:
        return None

    # First: check for Arabic numerals + Bengali unit words (global findall)
    # E.g. "1 lakh 50 hazar" → [(1, lakh), (50, hazar)]
    word_keys = "|".join(re.escape(w) for w in BENGALI_UNITS)
    arabic_word_pattern = rf"([\d.,]+)\s*({word_keys})"
    arabic_pairs = re.findall(arabic_word_pattern, text, re.IGNORECASE)
    total = 0.0
    found_any = False
    for num_str, unit_word in arabic_pairs:
        try:
            val = float(num_str.replace(",", ""))
        except ValueError:
            continue
        multiplier = BENGALI_UNITS.get(unit_word.lower())
        if multiplier:
            total += val * multiplier
            found_any = True
    if found_any:
        return float(total)

    # Bengali digit sequences: handle comma-separated groups as single numbers
    if any(c in BENGALI_DIGITS for c in text):
        # Pattern: Bengali digits (with internal commas allowed) + space + unit word
        word_keys = "|".join(re.escape(w) for w in BENGALI_UNITS)
        # Match digits (with commas inside) + space + unit word
        pair_pattern = rf"([০-৯,]+)\s+({word_keys})"
        pairs = re.findall(pair_pattern, text)

        total = 0.0
        for digit_str, unit_word in pairs:
            val = _bengali_digits_to_int(digit_str)
            if val is not None:
                total += val * BENGALI_UNITS[unit_word]

        if total > 0:
            return float(total)

        # Pure Bengali digit strings with commas — strip commas and concatenate
        # E.g. "১,২৩" → "১২৩" → 123
        clean_text = text.replace(",", "").replace(" ", "")
        if all(c in BENGALI_DIGITS or c in "৴৵৶৷ৰৱ" for c in clean_text):
            val = _bengali_digits_to_int(clean_text)
            if val is not None:
                return float(val)

    # Try plain Arabic numeral
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None

    # Try number words
    word_pattern = "|".join(re.escape(w) for w in BENGALI_UNITS)
    pattern = rf"([\d.,]+)\s*({word_pattern})"
    matches = re.findall(pattern, text, re.IGNORECASE)

    if matches:
        total = 0.0
        for num_str, unit_word in matches:
            try:
                num = float(num_str.replace(",", ""))
            except ValueError:
                continue
            unit_val = BENGALI_UNITS.get(unit_word.lower(), BENGALI_UNITS.get(unit_word, 1))
            total += num * unit_val

        if total > 0:
            return total

    # Try plain Arabic numeral
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Vietnamese number word parser
# ---------------------------------------------------------------------------

VIETNAMESE_UNITS: dict[str, int] = {
    "nghin": 1_000,
    "nghìn": 1_000,
    "triệu": 1_000_000,
    "trieu": 1_000_000,
    "tỷ": 1_000_000_000,
    "ty": 1_000_000_000,
    "đồng": 1,
    "dong": 1,
}


def parse_vietnamese_number(text: str) -> Optional[float]:
    """Convert a Vietnamese number string to a numeric value.

    Handles:
      - Number words: nghìn/nghin (thousand), triệu/trieu (million),
        tỷ/ty (billion), đồng/dong (unit — stripped)
      - Mixed: "1.5 triệu" / "2 nghìn"
      - Plain Arabic numerals (passthrough)
      - Vietnamese decimal separator: "," as "." (e.g. "1,5 triệu" = 1.5M)

    Returns None if the text cannot be parsed as a Vietnamese number.
    """
    text = text.strip().lower()
    if not text:
        return None

    # Strip đồng / dong suffix (currency indicator)
    text = re.sub(r"\s*(đồng|dong)\s*$", "", text, flags=re.IGNORECASE).strip()

    # Replace Vietnamese comma decimal with period
    text = text.replace(",", ".")

    # Try number words
    word_pattern = "|".join(re.escape(w) for w in VIETNAMESE_UNITS)
    pattern = rf"([\d.,]+)\s*({word_pattern})"
    matches = re.findall(pattern, text, re.IGNORECASE)

    if matches:
        total = 0.0
        for num_str, unit_word in matches:
            try:
                num = float(num_str.replace(",", ""))
            except ValueError:
                continue
            unit_val = VIETNAMESE_UNITS.get(unit_word.lower(), VIETNAMESE_UNITS.get(unit_word, 1))
            total += num * unit_val

        if total > 0:
            return total

    # Try plain number
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Country → language dispatch
# ---------------------------------------------------------------------------

COUNTRY_LANGUAGE: dict[str, str] = {
    "BD": "bengali",
    "BGD": "bengali",
    "VN": "vietnamese",
    "VNM": "vietnamese",
}


def detect_language(country_code: Optional[str], message: Optional[str] = None) -> str:
    """Detect the language to use for number parsing.

    Priority:
      1. Country code (ISO 2-letter) — BD/BGD → Bengali, VN/VNM → Vietnamese
      2. Message content heuristics (contains Bengali script / Vietnamese keywords)

    Returns one of: ``"bengali"``, ``"vietnamese"``, ``"standard"``
    """
    if country_code:
        lang = COUNTRY_LANGUAGE.get(country_code.upper())
        if lang:
            return lang

    if message:
        # Bengali script detection
        bengali_chars = sum(1 for c in message if "ঀ" <= c <= "৿")
        if bengali_chars >= 3:
            return "bengali"

        # Vietnamese keyword detection
        vietnamese_markers = ["nghìn", "nghin", "triệu", "trieu", "tỷ", "đồng"]
        if any(marker in message.lower() for marker in vietnamese_markers):
            return "vietnamese"

    return "standard"


def parse_number(
    text: str, language: Optional[str] = None, country_code: Optional[str] = None
) -> Optional[float]:
    """Parse a number string in the given or detected language.

    Parameters
    ----------
    text : str
        The number string to parse.
    language : str, optional
        One of ``"bengali"``, ``"vietnamese"``, ``"standard"``.
        If omitted, detects from ``country_code`` and message content.
    country_code : str, optional
        ISO 2-letter country code for language dispatch.

    Returns
    -------
    Optional[float]
        The parsed numeric value, or None if unparseable.
    """
    if language is None:
        language = detect_language(country_code, text)

    if language == "bengali":
        return parse_bengali_number(text)
    elif language == "vietnamese":
        return parse_vietnamese_number(text)
    else:
        # Standard: strip commas and parse
        try:
            return float(text.replace(",", "").strip())
        except ValueError:
            return None
