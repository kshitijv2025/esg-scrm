"""
Unit tests for src/orchestration/framework_mapper.py
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4


from src.orchestration.disclosure_package import (
    DataPoint,
    DataPointType,
    FrameworkType,
)
from src.orchestration.framework_mapper import FrameworkMappingEngine


class TestFrameworkMappingEngineConstructor:
    """Test FrameworkMappingEngine constructor."""

    def test_default_constructor(self):
        engine = FrameworkMappingEngine()
        assert engine.scope3_emission_factor == 0.5

    def test_custom_emission_factor(self):
        engine = FrameworkMappingEngine(scope3_emission_factor=0.75)
        assert engine.scope3_emission_factor == 0.75


def _make_data_point(
    dp_id: str,
    data_point_type: DataPointType,
    value: Decimal,
    org_id=None,
    confidence: str = "HIGH",
):
    """Helper to create a DataPoint for testing."""
    if org_id is None:
        org_id = uuid4()
    return DataPoint(
        id=dp_id,
        organization_id=org_id,
        data_point_type=data_point_type,
        value=value,
        unit="test_unit",
        confidence=confidence,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        recorded_at=datetime.utcnow(),
    )


class TestMapToCsrd:
    """Test map_to_csrd method."""

    def test_returns_disclosure_package_with_csrd_framework(self):
        org_id = uuid4()
        engine = FrameworkMappingEngine()
        data_points = [
            _make_data_point("dp1", DataPointType.ENERGY_KWH, Decimal("1000"), org_id),
        ]
        reporting_period = (date(2024, 1, 1), date(2024, 12, 31))

        result = engine.map_to_csrd(data_points, org_id, reporting_period)

        assert result.framework == FrameworkType.CSRD
        assert isinstance(result.data_points, list)

    def test_returns_disclosure_package_with_data_points(self):
        org_id = uuid4()
        engine = FrameworkMappingEngine()
        energy_dp = _make_data_point("dp_energy", DataPointType.ENERGY_KWH, Decimal("1500"), org_id)
        scope1_dp = _make_data_point(
            "dp_scope1", DataPointType.SCOPE1_TCO2E, Decimal("100"), org_id
        )

        data_points = [energy_dp, scope1_dp]
        reporting_period = (date(2024, 1, 1), date(2024, 12, 31))

        result = engine.map_to_csrd(data_points, org_id, reporting_period)

        assert len(result.data_points) == 2
        assert energy_dp in result.data_points
        assert scope1_dp in result.data_points

    def test_produces_gaps_list(self):
        org_id = uuid4()
        engine = FrameworkMappingEngine()
        # Empty data points should produce gaps
        data_points = []
        reporting_period = (date(2024, 1, 1), date(2024, 12, 31))

        result = engine.map_to_csrd(data_points, org_id, reporting_period)

        assert isinstance(result.gaps, list)
        # Without any data points, gaps should be populated

    def test_with_empty_data_points_produces_valid_disclosure_package(self):
        org_id = uuid4()
        engine = FrameworkMappingEngine()
        data_points = []
        reporting_period = (date(2024, 1, 1), date(2024, 12, 31))

        result = engine.map_to_csrd(data_points, org_id, reporting_period)

        # Should still return a valid DisclosurePackage
        assert result.framework == FrameworkType.CSRD
        assert result.organization_id == org_id
        assert result.reporting_period == reporting_period
        assert isinstance(result.data_points, list)
        assert isinstance(result.gaps, list)
        assert result.disclosure_id is not None


class TestMapToIssb:
    """Test map_to_issb method."""

    def test_returns_disclosure_package_with_issb_framework(self):
        org_id = uuid4()
        engine = FrameworkMappingEngine()
        data_points = [
            _make_data_point("dp1", DataPointType.ENERGY_KWH, Decimal("1000"), org_id),
        ]
        reporting_period = (date(2024, 1, 1), date(2024, 12, 31))

        result = engine.map_to_issb(data_points, org_id, reporting_period)

        assert result.framework == FrameworkType.ISSB
        assert isinstance(result.data_points, list)

    def test_returns_data_points_for_issb(self):
        org_id = uuid4()
        engine = FrameworkMappingEngine()
        energy_dp = _make_data_point("dp_energy", DataPointType.ENERGY_KWH, Decimal("2000"), org_id)
        scope1_dp = _make_data_point("dp_scope1", DataPointType.SCOPE1_TCO2E, Decimal("50"), org_id)

        data_points = [energy_dp, scope1_dp]
        reporting_period = (date(2024, 1, 1), date(2024, 12, 31))

        result = engine.map_to_issb(data_points, org_id, reporting_period)

        assert len(result.data_points) == 2

    def test_produces_gaps_list(self):
        org_id = uuid4()
        engine = FrameworkMappingEngine()
        data_points = []
        reporting_period = (date(2024, 1, 1), date(2024, 12, 31))

        result = engine.map_to_issb(data_points, org_id, reporting_period)

        assert isinstance(result.gaps, list)


class TestMapToGri:
    """Test map_to_gri method."""

    def test_returns_disclosure_package_with_gri_framework(self):
        org_id = uuid4()
        engine = FrameworkMappingEngine()
        data_points = [
            _make_data_point("dp1", DataPointType.ENERGY_KWH, Decimal("1000"), org_id),
        ]
        reporting_period = (date(2024, 1, 1), date(2024, 12, 31))

        result = engine.map_to_gri(data_points, org_id, reporting_period)

        assert result.framework == FrameworkType.GRI
        assert isinstance(result.data_points, list)

    def test_returns_data_points_for_gri(self):
        org_id = uuid4()
        engine = FrameworkMappingEngine()
        energy_dp = _make_data_point("dp_energy", DataPointType.ENERGY_KWH, Decimal("3000"), org_id)
        water_dp = _make_data_point("dp_water", DataPointType.WATER_M3, Decimal("500"), org_id)

        data_points = [energy_dp, water_dp]
        reporting_period = (date(2024, 1, 1), date(2024, 12, 31))

        result = engine.map_to_gri(data_points, org_id, reporting_period)

        assert len(result.data_points) == 2

    def test_produces_gaps_list(self):
        org_id = uuid4()
        engine = FrameworkMappingEngine()
        data_points = []
        reporting_period = (date(2024, 1, 1), date(2024, 12, 31))

        result = engine.map_to_gri(data_points, org_id, reporting_period)

        assert isinstance(result.gaps, list)


class TestMapToTcfd:
    """Test map_to_tcfd method."""

    def test_returns_disclosure_package_with_tcfd_framework(self):
        org_id = uuid4()
        engine = FrameworkMappingEngine()
        data_points = [
            _make_data_point("dp1", DataPointType.ENERGY_KWH, Decimal("1000"), org_id),
        ]
        reporting_period = (date(2024, 1, 1), date(2024, 12, 31))

        result = engine.map_to_tcfd(data_points, org_id, reporting_period)

        assert result.framework == FrameworkType.TCFD
        assert isinstance(result.data_points, list)

    def test_returns_data_points_for_tcfd(self):
        org_id = uuid4()
        engine = FrameworkMappingEngine()
        energy_dp = _make_data_point("dp_energy", DataPointType.ENERGY_KWH, Decimal("4000"), org_id)
        scope2_dp = _make_data_point("dp_scope2", DataPointType.SCOPE2_TCO2E, Decimal("75"), org_id)

        data_points = [energy_dp, scope2_dp]
        reporting_period = (date(2024, 1, 1), date(2024, 12, 31))

        result = engine.map_to_tcfd(data_points, org_id, reporting_period)

        assert len(result.data_points) == 2

    def test_produces_gaps_list(self):
        org_id = uuid4()
        engine = FrameworkMappingEngine()
        data_points = []
        reporting_period = (date(2024, 1, 1), date(2024, 12, 31))

        result = engine.map_to_tcfd(data_points, org_id, reporting_period)

        assert isinstance(result.gaps, list)


class TestFrameworkMappingWithMixedDataPoints:
    """Test mapping with data points across different frameworks."""

    def test_csrd_maps_scope3_data_point(self):
        org_id = uuid4()
        engine = FrameworkMappingEngine()
        scope3_dp = _make_data_point(
            "dp_scope3",
            DataPointType.SCOPE3_TCO2E,
            Decimal("500"),
            org_id,
        )
        data_points = [scope3_dp]
        reporting_period = (date(2024, 1, 1), date(2024, 12, 31))

        result = engine.map_to_csrd(data_points, org_id, reporting_period)

        # Scope 3 should be included in CSRD mapping
        scope3_in_result = any(
            dp.data_point_type == DataPointType.SCOPE3_TCO2E for dp in result.data_points
        )
        assert scope3_in_result

    def test_all_frameworks_produce_confidence_summary(self):
        org_id = uuid4()
        engine = FrameworkMappingEngine()
        data_points = [
            _make_data_point("dp1", DataPointType.ENERGY_KWH, Decimal("1000"), org_id),
            _make_data_point("dp2", DataPointType.SCOPE1_TCO2E, Decimal("50"), org_id, "MEDIUM"),
        ]
        reporting_period = (date(2024, 1, 1), date(2024, 12, 31))

        for method_name in ["map_to_csrd", "map_to_issb", "map_to_gri", "map_to_tcfd"]:
            method = getattr(engine, method_name)
            result = method(data_points, org_id, reporting_period)
            assert result.confidence_summary is not None
            assert hasattr(result.confidence_summary, "high_pct")
            assert hasattr(result.confidence_summary, "medium_pct")
            assert hasattr(result.confidence_summary, "low_pct")


class TestComputeConfidenceSummary:
    """Test _compute_confidence_summary helper."""

    def test_empty_data_points_returns_zero_confidence(self):
        """Test that empty data points list returns zero percentages."""
        engine = FrameworkMappingEngine()
        result = engine._compute_confidence_summary([])

        assert result.high_pct == 0.0
        assert result.medium_pct == 0.0
        assert result.low_pct == 0.0
        assert result.total_data_points == 0

    def test_single_high_confidence_data_point(self):
        """Test that a single HIGH confidence data point returns 100% high."""
        engine = FrameworkMappingEngine()
        org_id = uuid4()
        data_points = [
            _make_data_point("dp1", DataPointType.ENERGY_KWH, Decimal("100"), org_id, "HIGH"),
        ]

        result = engine._compute_confidence_summary(data_points)

        assert result.high_pct == 100.0
        assert result.medium_pct == 0.0
        assert result.low_pct == 0.0
        assert result.total_data_points == 1

    def test_all_high_confidence(self):
        engine = FrameworkMappingEngine()
        org_id = uuid4()
        data_points = [
            _make_data_point("dp1", DataPointType.ENERGY_KWH, Decimal("100"), org_id, "HIGH"),
            _make_data_point("dp2", DataPointType.WATER_M3, Decimal("50"), org_id, "HIGH"),
        ]

        result = engine._compute_confidence_summary(data_points)

        assert result.high_pct == 100.0
        assert result.medium_pct == 0.0
        assert result.low_pct == 0.0
        assert result.total_data_points == 2

    def test_mixed_confidence(self):
        """Test mixed confidence levels that divide evenly to 100."""
        engine = FrameworkMappingEngine()
        org_id = uuid4()
        # 2 HIGH, 1 MEDIUM, 1 LOW = 4 total
        # 2/4=50%, 1/4=25%, 1/4=25% - all round cleanly
        data_points = [
            _make_data_point("dp1", DataPointType.ENERGY_KWH, Decimal("100"), org_id, "HIGH"),
            _make_data_point("dp2", DataPointType.WATER_M3, Decimal("50"), org_id, "HIGH"),
            _make_data_point("dp3", DataPointType.WASTE_KG, Decimal("10"), org_id, "MEDIUM"),
            _make_data_point("dp4", DataPointType.SCOPE1_TCO2E, Decimal("5"), org_id, "LOW"),
        ]

        result = engine._compute_confidence_summary(data_points)

        assert result.high_pct == 50.0
        assert result.medium_pct == 25.0
        assert result.low_pct == 25.0
        assert result.total_data_points == 4
