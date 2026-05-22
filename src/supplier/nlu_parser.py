"""
Named List Understanding (NLU) Parser for supplier questionnaire responses.

Parses numbered response formats like "2. 45000 kWh" from WhatsApp/email/other channels
and extracts structured answers with confidence scoring.
"""

import re
import structlog
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional

from src.supplier.unit_normalization import (
    UNIT_ALIASES,
    convert_unit,
    normalize_unit,
    requires_conversion,
    is_standard_unit,
)

logger = structlog.get_logger(__name__)


class ConfidenceLevel:
    """Confidence level for parsed responses."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


@dataclass
class Question:
    """A questionnaire question with expected answer format."""

    question_id: str
    question_number: int
    question_text: str
    expected_unit: Optional[str] = None


@dataclass
class ParsedAnswer:
    """A single parsed answer from a supplier response."""

    question_number: int
    raw_value: str
    numeric_value: Optional[Decimal] = None
    unit: Optional[str] = None
    normalized_unit: Optional[str] = None
    normalized_value: Optional[Decimal] = None
    confidence: str = ConfidenceLevel.NONE
    is_acknowledged: bool = False
    acknowledged_value: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "question_number": self.question_number,
            "raw_value": self.raw_value,
            "numeric_value": str(self.numeric_value) if self.numeric_value else None,
            "unit": self.unit,
            "normalized_unit": self.normalized_unit,
            "normalized_value": str(self.normalized_value) if self.normalized_value else None,
            "confidence": self.confidence,
            "is_acknowledged": self.is_acknowledged,
            "acknowledged_value": self.acknowledged_value,
        }


@dataclass
class ParsedResponse:
    """Container for all parsed answers from a supplier response."""

    answers: list[ParsedAnswer] = field(default_factory=list)
    raw_message: str = ""
    parse_errors: list[str] = field(default_factory=list)
    total_questions_expected: int = 0

    def get_answer_for_question(self, question_number: int) -> Optional[ParsedAnswer]:
        """Get the parsed answer for a specific question number."""
        for answer in self.answers:
            if answer.question_number == question_number:
                return answer
        return None

    def get_high_confidence_answers(self) -> list[ParsedAnswer]:
        """Get all answers with HIGH confidence."""
        return [a for a in self.answers if a.confidence == ConfidenceLevel.HIGH]

    def get_medium_confidence_answers(self) -> list[ParsedAnswer]:
        """Get all answers with MEDIUM confidence."""
        return [a for a in self.answers if a.confidence == ConfidenceLevel.MEDIUM]

    def get_low_confidence_answers(self) -> list[ParsedAnswer]:
        """Get all answers with LOW confidence."""
        return [a for a in self.answers if a.confidence == ConfidenceLevel.LOW]

    def to_dict(self) -> dict:
        return {
            "answers": [a.to_dict() for a in self.answers],
            "raw_message": self.raw_message,
            "parse_errors": self.parse_errors,
            "total_questions_expected": self.total_questions_expected,
        }


class NLUParser:
    """Named List Understanding Parser for supplier questionnaire responses.

    Parses numbered response formats from various channels (WhatsApp, email, etc.)
    and extracts structured answers with confidence scoring.

    Supported formats:
    - "2. 45000 kWh"
    - "2. 45,000 kWh"
    - "2. 45000"
    - "2. yes"
    - "2. Yes, we have certification"
    """

    # Pattern for numbered items with optional value and unit
    NUMBERED_ITEM_PATTERN = re.compile(
        r"^\s*(\d+)[\.\)]\s*(.+?)(?:\s*[\[\(]?\s*([\w%]+)\s*[\]\)]?)?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    # Pattern for standalone numbers without explicit units
    STANDALONE_NUMBER_PATTERN = re.compile(
        r"^\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*$",
        re.MULTILINE,
    )

    # Acknowledgement patterns
    ACKNOWLEDGEMENT_PATTERNS = [
        re.compile(r"^\s*yes\s*$", re.IGNORECASE),
        re.compile(r"^\s*no\s*$", re.IGNORECASE),
        re.compile(r"^\s*true\s*$", re.IGNORECASE),
        re.compile(r"^\s*false\s*$", re.IGNORECASE),
        re.compile(r"^\s*y\s*$", re.IGNORECASE),
        re.compile(r"^\s*n\s*$", re.IGNORECASE),
    ]

    # Patterns that indicate affirmative response
    AFFIRMATIVE_PATTERNS = [
        re.compile(r"^\s*yes", re.IGNORECASE),
        re.compile(r"^\s*y\b", re.IGNORECASE),
        re.compile(r"^\s*true\b", re.IGNORECASE),
        re.compile(r"^\s*confirmed\b", re.IGNORECASE),
        re.compile(r"^\s*correct\b", re.IGNORECASE),
        re.compile(r"^\s*we do\b", re.IGNORECASE),
        re.compile(r"^\s*have\b", re.IGNORECASE),
        re.compile(r"^\s*is\b", re.IGNORECASE),
    ]

    def __init__(self) -> None:
        """Initialize the NLU parser."""
        pass

    def parse_response(
        self,
        raw_message: str,
        questions: list[Question],
    ) -> ParsedResponse:
        """Parse a raw supplier response against expected questions.

        Args:
            raw_message: The raw text response from the supplier.
            questions: List of expected questions with their numbers and units.

        Returns:
            ParsedResponse containing all parsed answers with confidence scores.

        Confidence scoring:
        - HIGH: unit matches expected unit exactly
        - MEDIUM: unit conversion needed (e.g., gallons -> m3)
        - LOW: ambiguous or missing unit
        - NONE: could not parse
        """
        response = ParsedResponse(
            raw_message=raw_message,
            total_questions_expected=len(questions),
        )

        if not raw_message or not raw_message.strip():
            response.parse_errors.append("Empty message received")
            logger.warning("nlu.empty_message")
            return response

        logger.info("nlu.parse.start", message_len=len(raw_message), question_count=len(questions))

        lines = raw_message.strip().split("\n")
        parsed_question_numbers: set[int] = set()

        for line in lines:
            line = line.strip()
            if not line:
                continue

            parsed = self._parse_single_line(line)

            if parsed is None:
                continue

            question_number, raw_value, unit = parsed

            if question_number in parsed_question_numbers:
                logger.warning("nlu.duplicate_question_number", question_number=question_number)
                continue

            parsed_question_numbers.add(question_number)

            answer = self._build_parsed_answer(
                question_number=question_number,
                raw_value=raw_value,
                unit=unit,
                questions=questions,
            )

            response.answers.append(answer)

        logger.info(
            "nlu.parse.complete",
            answers_count=len(response.answers),
            errors_count=len(response.parse_errors),
        )

        return response

    def _parse_single_line(
        self,
        line: str,
    ) -> Optional[tuple[int, str, Optional[str]]]:
        """Parse a single line of response text.

        Returns:
            Tuple of (question_number, raw_value, unit) or None if not parseable.
        """
        line = line.strip()
        if not line:
            return None

        match = self.NUMBERED_ITEM_PATTERN.match(line)
        if match:
            question_number = int(match.group(1))
            raw_value = match.group(2).strip()
            unit = match.group(3)
            if unit:
                # Validate unit is a recognized measurement unit, not arbitrary text
                normalized = normalize_unit(unit)
                if normalized not in UNIT_ALIASES.values() and not is_standard_unit(unit):
                    # Not a recognized unit; treat as part of the value
                    raw_value = f"{raw_value} {unit}".strip()
                    unit = None
            return question_number, raw_value, unit if unit else None

        standalone_match = self.STANDALONE_NUMBER_PATTERN.match(line)
        if standalone_match:
            return None, line, None

        return None

    def extract_numbered_item(
        self,
        text: str,
        question_number: int,
    ) -> tuple[str, Optional[str]]:
        """Extract a numbered item from text.

        Args:
            text: The text containing the numbered item.
            question_number: The expected question number to extract.

        Returns:
            Tuple of (value_string, unit) or (original_text, None) if not found.
        """
        lines = text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            match = self.NUMBERED_ITEM_PATTERN.match(line)
            if match:
                num = int(match.group(1))
                if num == question_number:
                    raw_value = match.group(2).strip()
                    unit = match.group(3)
                    return raw_value, unit if unit else None

        return text, None

    def _build_parsed_answer(
        self,
        question_number: int,
        raw_value: str,
        unit: Optional[str],
        questions: list[Question],
    ) -> ParsedAnswer:
        """Build a ParsedAnswer with confidence scoring.

        Args:
            question_number: The question number being answered.
            raw_value: The raw value string from the response.
            unit: The unit string if present in the response.
            questions: List of expected questions for unit matching.

        Returns:
            ParsedAnswer with confidence scoring applied.
        """
        answer = ParsedAnswer(
            question_number=question_number,
            raw_value=raw_value,
            unit=unit,
        )

        question = self._find_question(question_number, questions)
        if question is None:
            answer.confidence = ConfidenceLevel.LOW
            return answer

        if self._is_acknowledgement(raw_value):
            answer.is_acknowledged = True
            answer.acknowledged_value = raw_value.lower().strip()
            answer.confidence = ConfidenceLevel.HIGH
            return answer

        numeric_result = self._extract_numeric_value(raw_value)
        if numeric_result is None:
            answer.confidence = ConfidenceLevel.LOW
            return answer

        numeric_value, value_unit = numeric_result
        answer.numeric_value = numeric_value
        answer.unit = value_unit

        if value_unit is None and unit:
            value_unit = unit

        if value_unit is None and question.expected_unit:
            value_unit = question.expected_unit
            answer.unit = value_unit

        if value_unit:
            answer.normalized_unit = normalize_unit(value_unit)

        expected_unit = question.expected_unit
        if expected_unit:
            expected_normalized = normalize_unit(expected_unit)
        else:
            expected_normalized = None

        if expected_normalized and answer.normalized_unit:
            if answer.normalized_unit == expected_normalized:
                answer.confidence = ConfidenceLevel.HIGH
                answer.normalized_value = numeric_value
            elif requires_conversion(answer.normalized_unit, expected_normalized):
                converted = convert_unit(numeric_value, answer.normalized_unit, expected_normalized)
                if converted is not None:
                    answer.confidence = ConfidenceLevel.MEDIUM
                    answer.normalized_value = converted
                else:
                    answer.confidence = ConfidenceLevel.LOW
            else:
                answer.confidence = ConfidenceLevel.MEDIUM
        elif answer.normalized_unit and is_standard_unit(answer.normalized_unit):
            answer.confidence = ConfidenceLevel.MEDIUM
            answer.normalized_value = numeric_value
        else:
            answer.confidence = ConfidenceLevel.LOW

        return answer

    def _find_question(
        self,
        question_number: int,
        questions: list[Question],
    ) -> Optional[Question]:
        """Find a question by its number."""
        for q in questions:
            if q.question_number == question_number:
                return q
        return None

    def _is_acknowledgement(self, value: str) -> bool:
        """Check if a value is an acknowledgement (yes/no style)."""
        value_lower = value.lower().strip()

        for pattern in self.ACKNOWLEDGEMENT_PATTERNS:
            if pattern.match(value_lower):
                return True

        return False

    def _extract_numeric_value(
        self,
        value_str: str,
    ) -> Optional[tuple[Decimal, Optional[str]]]:
        """Extract numeric value and unit from a string.

        Returns:
            Tuple of (numeric_value, unit) or None if not numeric.
        """
        value_str = value_str.strip()

        if not value_str:
            return None

        if self._is_acknowledgement(value_str):
            return None

        number_pattern = re.compile(r"^([\d,]+(?:\.\d+)?)\s*([a-zA-Z%]+)?$")

        match = number_pattern.match(value_str)
        if match:
            number_str = match.group(1).replace(",", "")
            try:
                numeric_value = Decimal(number_str)
                unit = match.group(2) if match.group(2) else None
                return numeric_value, unit
            except InvalidOperation:
                pass

        try:
            clean_str = value_str.replace(",", "").strip()
            numeric_value = Decimal(clean_str)
            return numeric_value, None
        except InvalidOperation:
            return None

    def normalize_unit(self, value: Decimal, from_unit: str, to_unit: str) -> Optional[Decimal]:
        """Apply unit conversion.

        Args:
            value: The numeric value to convert.
            from_unit: The source unit.
            to_unit: The target unit.

        Returns:
            The converted value, or None if conversion not possible.
        """
        return convert_unit(value, from_unit, to_unit)
