"""
Confidence determination rules for ESG+SCRM Evidence Vault.

Implements invariant confidence assignment rules that cannot be overridden.
"""

import structlog

from src.evidence.evidence_record import ConfidenceLevel, EvidenceType

logger = structlog.get_logger(__name__)


def determine_confidence(
    source_type: EvidenceType,
    calculation_method: str,
    verification_status: str = "unverified",
) -> ConfidenceLevel:
    """
    Determine confidence level based on source type and method.

    This function implements invariant rules that cannot be overridden.
    The confidence level is determined solely by the combination of:
    - Source type (API extraction, manual entry, sensor reading, etc.)
    - Calculation method (direct measurement, estimation, projection)
    - Verification status (verified, unverified, partially verified)

    Args:
        source_type: The type of evidence source
        calculation_method: The method used to derive the value
        verification_status: Current verification status

    Returns:
        ConfidenceLevel enum value

    Rules:
        - API extraction with verified source: HIGH
        - Sensor readings with calibration: HIGH
        - Manual entry: LOW
        - Supplier response: MEDIUM (may be unverified)
        - Calculation from multiple sources: MIN of input confidences
        - Unverified: reduce by one level
    """
    if source_type == EvidenceType.API_EXTRACTION:
        if verification_status == "verified":
            confidence = ConfidenceLevel.HIGH
        elif verification_status == "partially_verified":
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.MEDIUM

    elif source_type == EvidenceType.SENSOR_READING:
        if "calibrated" in calculation_method.lower():
            confidence = ConfidenceLevel.HIGH
        elif verification_status == "verified":
            confidence = ConfidenceLevel.HIGH
        else:
            confidence = ConfidenceLevel.MEDIUM

    elif source_type == EvidenceType.MANUAL_ENTRY:
        if verification_status == "verified":
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

    elif source_type == EvidenceType.SUPPLIER_RESPONSE:
        if verification_status == "verified":
            confidence = ConfidenceLevel.HIGH
        elif verification_status == "partially_verified":
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

    elif source_type == EvidenceType.CALCULATION:
        if verification_status == "verified":
            confidence = ConfidenceLevel.HIGH
        elif verification_status == "partially_verified":
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

    else:
        confidence = ConfidenceLevel.MEDIUM

    logger.debug(
        "confidence.determined",
        source_type=source_type.value,
        calculation_method=calculation_method,
        verification_status=verification_status,
        confidence=confidence.value,
    )
    return confidence


def aggregate_confidence(confidences: list[ConfidenceLevel]) -> ConfidenceLevel:
    """
    Aggregate multiple confidence levels using MIN rule.

    When DataPoints combine through calculation, the aggregate confidence
    is the MINIMUM of all input confidences. This reflects that a
    chain is only as strong as its weakest link.

    Args:
        confidences: List of ConfidenceLevel values to aggregate

    Returns:
        Minimum confidence level from the input list

    Example:
        [HIGH, MEDIUM, LOW] -> LOW
        [HIGH, HIGH] -> HIGH
        [MEDIUM, MEDIUM, MEDIUM] -> MEDIUM
    """
    if not confidences:
        logger.warning("confidence.aggregate_empty")
        return ConfidenceLevel.MEDIUM

    confidence_order = [
        ConfidenceLevel.LOW,
        ConfidenceLevel.MEDIUM,
        ConfidenceLevel.HIGH,
    ]

    min_confidence = min(confidences, key=lambda c: confidence_order.index(c))

    logger.debug(
        "confidence.aggregated",
        input_count=len(confidences),
        min_confidence=min_confidence.value,
        input_confidences=[c.value for c in confidences],
    )
    return min_confidence


def get_confidence_rationale(
    source_type: EvidenceType,
    calculation_method: str,
    verification_status: str,
    confidence: ConfidenceLevel,
) -> str:
    """
    Generate a human-readable rationale for the assigned confidence level.

    Args:
        source_type: The evidence source type
        calculation_method: The calculation method used
        verification_status: Current verification status
        confidence: The assigned confidence level

    Returns:
        Human-readable explanation of why this confidence was assigned
    """
    source_descriptions = {
        EvidenceType.API_EXTRACTION: "API data extraction",
        EvidenceType.MANUAL_ENTRY: "Manual data entry",
        EvidenceType.SUPPLIER_RESPONSE: "Supplier questionnaire response",
        EvidenceType.SENSOR_READING: "Sensor measurement",
        EvidenceType.CALCULATION: "Derived calculation",
    }

    verification_descriptions = {
        "verified": "independently verified",
        "partially_verified": "partially verified",
        "unverified": "unverified",
    }

    source_desc = source_descriptions.get(source_type, source_type.value)
    verification_desc = verification_descriptions.get(verification_status, verification_status)

    rationale_templates = {
        ConfidenceLevel.HIGH: (
            f"High confidence based on {source_desc} with {verification_desc} status. "
            f"Methodology: {calculation_method or 'standard protocol'}."
        ),
        ConfidenceLevel.MEDIUM: (
            f"Medium confidence based on {source_desc}. "
            f"Status: {verification_desc}. "
            f"Consider additional verification for higher confidence."
        ),
        ConfidenceLevel.LOW: (
            f"Low confidence based on {source_desc} with {verification_desc} status. "
            f"Recommend manual review or additional data sources before reporting."
        ),
    }

    return rationale_templates.get(confidence, "")
