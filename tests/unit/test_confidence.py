"""
Unit tests for confidence module.
Tests determine_confidence() and aggregate_confidence() functions.
"""


from src.evidence.confidence import aggregate_confidence, determine_confidence
from src.evidence.evidence_record import ConfidenceLevel, EvidenceType


class TestDetermineConfidence:
    """Tests for determine_confidence() function."""

    def test_api_extraction_verified_returns_high(self):
        """API extraction with verified status returns HIGH confidence."""
        result = determine_confidence(
            source_type=EvidenceType.API_EXTRACTION,
            calculation_method="direct",
            verification_status="verified",
        )
        assert result == ConfidenceLevel.HIGH

    def test_api_extraction_partially_verified_returns_medium(self):
        """API extraction with partially_verified status returns MEDIUM."""
        result = determine_confidence(
            source_type=EvidenceType.API_EXTRACTION,
            calculation_method="direct",
            verification_status="partially_verified",
        )
        assert result == ConfidenceLevel.MEDIUM

    def test_api_extraction_unverified_returns_medium(self):
        """API extraction with unverified status returns MEDIUM."""
        result = determine_confidence(
            source_type=EvidenceType.API_EXTRACTION,
            calculation_method="direct",
            verification_status="unverified",
        )
        assert result == ConfidenceLevel.MEDIUM

    def test_sensor_reading_calibrated_returns_high(self):
        """Sensor reading with calibrated method returns HIGH confidence."""
        result = determine_confidence(
            source_type=EvidenceType.SENSOR_READING,
            calculation_method="calibrated measurement",
            verification_status="unverified",
        )
        assert result == ConfidenceLevel.HIGH

    def test_sensor_reading_verified_returns_high(self):
        """Sensor reading with verified status returns HIGH confidence."""
        result = determine_confidence(
            source_type=EvidenceType.SENSOR_READING,
            calculation_method="direct",
            verification_status="verified",
        )
        assert result == ConfidenceLevel.HIGH

    def test_sensor_reading_unverified_returns_medium(self):
        """Sensor reading with unverified status returns MEDIUM confidence."""
        result = determine_confidence(
            source_type=EvidenceType.SENSOR_READING,
            calculation_method="direct",
            verification_status="unverified",
        )
        assert result == ConfidenceLevel.MEDIUM

    def test_manual_entry_verified_returns_medium(self):
        """Manual entry with verified status returns MEDIUM confidence."""
        result = determine_confidence(
            source_type=EvidenceType.MANUAL_ENTRY,
            calculation_method="direct",
            verification_status="verified",
        )
        assert result == ConfidenceLevel.MEDIUM

    def test_manual_entry_unverified_returns_low(self):
        """Manual entry with unverified status returns LOW confidence."""
        result = determine_confidence(
            source_type=EvidenceType.MANUAL_ENTRY,
            calculation_method="direct",
            verification_status="unverified",
        )
        assert result == ConfidenceLevel.LOW

    def test_supplier_response_verified_returns_high(self):
        """Supplier response with verified status returns HIGH confidence."""
        result = determine_confidence(
            source_type=EvidenceType.SUPPLIER_RESPONSE,
            calculation_method="direct",
            verification_status="verified",
        )
        assert result == ConfidenceLevel.HIGH

    def test_supplier_response_partially_verified_returns_medium(self):
        """Supplier response with partially_verified returns MEDIUM."""
        result = determine_confidence(
            source_type=EvidenceType.SUPPLIER_RESPONSE,
            calculation_method="direct",
            verification_status="partially_verified",
        )
        assert result == ConfidenceLevel.MEDIUM

    def test_supplier_response_unverified_returns_low(self):
        """Supplier response with unverified returns LOW confidence."""
        result = determine_confidence(
            source_type=EvidenceType.SUPPLIER_RESPONSE,
            calculation_method="direct",
            verification_status="unverified",
        )
        assert result == ConfidenceLevel.LOW

    def test_calculation_verified_returns_high(self):
        """Calculation with verified status returns HIGH confidence."""
        result = determine_confidence(
            source_type=EvidenceType.CALCULATION,
            calculation_method="sum",
            verification_status="verified",
        )
        assert result == ConfidenceLevel.HIGH

    def test_calculation_partially_verified_returns_medium(self):
        """Calculation with partially_verified returns MEDIUM confidence."""
        result = determine_confidence(
            source_type=EvidenceType.CALCULATION,
            calculation_method="sum",
            verification_status="partially_verified",
        )
        assert result == ConfidenceLevel.MEDIUM

    def test_calculation_unverified_returns_low(self):
        """Calculation with unverified status returns LOW confidence."""
        result = determine_confidence(
            source_type=EvidenceType.CALCULATION,
            calculation_method="sum",
            verification_status="unverified",
        )
        assert result == ConfidenceLevel.LOW


class TestAggregateConfidence:
    """Tests for aggregate_confidence() function."""

    def test_aggregate_high_medium_low_returns_low(self):
        """aggregate_confidence([HIGH, MEDIUM, LOW]) returns LOW."""
        result = aggregate_confidence(
            [
                ConfidenceLevel.HIGH,
                ConfidenceLevel.MEDIUM,
                ConfidenceLevel.LOW,
            ]
        )
        assert result == ConfidenceLevel.LOW

    def test_aggregate_high_high_returns_high(self):
        """aggregate_confidence([HIGH, HIGH]) returns HIGH."""
        result = aggregate_confidence(
            [
                ConfidenceLevel.HIGH,
                ConfidenceLevel.HIGH,
            ]
        )
        assert result == ConfidenceLevel.HIGH

    def test_aggregate_medium_medium_returns_medium(self):
        """aggregate_confidence([MEDIUM, MEDIUM]) returns MEDIUM."""
        result = aggregate_confidence(
            [
                ConfidenceLevel.MEDIUM,
                ConfidenceLevel.MEDIUM,
            ]
        )
        assert result == ConfidenceLevel.MEDIUM

    def test_aggregate_low_low_returns_low(self):
        """aggregate_confidence([LOW, LOW]) returns LOW."""
        result = aggregate_confidence(
            [
                ConfidenceLevel.LOW,
                ConfidenceLevel.LOW,
            ]
        )
        assert result == ConfidenceLevel.LOW

    def test_aggregate_high_medium_returns_medium(self):
        """aggregate_confidence([HIGH, MEDIUM]) returns MEDIUM."""
        result = aggregate_confidence(
            [
                ConfidenceLevel.HIGH,
                ConfidenceLevel.MEDIUM,
            ]
        )
        assert result == ConfidenceLevel.MEDIUM

    def test_aggregate_medium_low_returns_low(self):
        """aggregate_confidence([MEDIUM, LOW]) returns LOW."""
        result = aggregate_confidence(
            [
                ConfidenceLevel.MEDIUM,
                ConfidenceLevel.LOW,
            ]
        )
        assert result == ConfidenceLevel.LOW

    def test_aggregate_single_high_returns_high(self):
        """aggregate_confidence([HIGH]) returns HIGH."""
        result = aggregate_confidence([ConfidenceLevel.HIGH])
        assert result == ConfidenceLevel.HIGH

    def test_aggregate_single_medium_returns_medium(self):
        """aggregate_confidence([MEDIUM]) returns MEDIUM."""
        result = aggregate_confidence([ConfidenceLevel.MEDIUM])
        assert result == ConfidenceLevel.MEDIUM

    def test_aggregate_single_low_returns_low(self):
        """aggregate_confidence([LOW]) returns LOW."""
        result = aggregate_confidence([ConfidenceLevel.LOW])
        assert result == ConfidenceLevel.LOW

    def test_aggregate_empty_returns_medium(self):
        """aggregate_confidence([]) returns MEDIUM (default for empty)."""
        result = aggregate_confidence([])
        assert result == ConfidenceLevel.MEDIUM

    def test_aggregate_all_same_levels_returns_that_level(self):
        """aggregate_confidence with all same levels returns that level."""
        # Test with multiple HIGH values
        result = aggregate_confidence(
            [
                ConfidenceLevel.HIGH,
                ConfidenceLevel.HIGH,
                ConfidenceLevel.HIGH,
            ]
        )
        assert result == ConfidenceLevel.HIGH

        # Test with multiple MEDIUM values
        result = aggregate_confidence(
            [
                ConfidenceLevel.MEDIUM,
                ConfidenceLevel.MEDIUM,
                ConfidenceLevel.MEDIUM,
            ]
        )
        assert result == ConfidenceLevel.MEDIUM

        # Test with multiple LOW values
        result = aggregate_confidence(
            [
                ConfidenceLevel.LOW,
                ConfidenceLevel.LOW,
                ConfidenceLevel.LOW,
            ]
        )
        assert result == ConfidenceLevel.LOW

    def test_aggregate_many_different_levels(self):
        """aggregate_confidence with many levels returns minimum."""
        result = aggregate_confidence(
            [
                ConfidenceLevel.HIGH,
                ConfidenceLevel.HIGH,
                ConfidenceLevel.MEDIUM,
                ConfidenceLevel.MEDIUM,
                ConfidenceLevel.MEDIUM,
                ConfidenceLevel.LOW,
            ]
        )
        assert result == ConfidenceLevel.LOW
