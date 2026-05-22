"""
Unit tests for src/orchestration/disclosure_package.py
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from src.orchestration.disclosure_package import (
    ConfidenceSummary,
    DataPoint,
    DataPointType,
    DisclosurePackage,
    FrameworkType,
    Gap,
)


class TestFrameworkType:
    """Test FrameworkType enum values."""

    def test_csrd_value(self):
        assert FrameworkType.CSRD.value == "CSRD"

    def test_issb_value(self):
        assert FrameworkType.ISSB.value == "ISSB"

    def test_gri_value(self):
        assert FrameworkType.GRI.value == "GRI"

    def test_tcfd_value(self):
        assert FrameworkType.TCFD.value == "TCFD"

    def test_all_frameworks_present(self):
        assert len(FrameworkType) == 4


class TestDataPointType:
    """Test DataPointType enum values."""

    def test_energy_kwh_exists(self):
        assert DataPointType.ENERGY_KWH.value == "energy_kwh"

    def test_scope1_tco2e_exists(self):
        assert DataPointType.SCOPE1_TCO2E.value == "scope1_tco2e"

    def test_scope2_tco2e_exists(self):
        assert DataPointType.SCOPE2_TCO2E.value == "scope2_tco2e"

    def test_scope3_tco2e_exists(self):
        assert DataPointType.SCOPE3_TCO2E.value == "scope3_tco2e"

    def test_water_m3_exists(self):
        assert DataPointType.WATER_M3.value == "water_m3"

    def test_waste_kg_exists(self):
        assert DataPointType.WASTE_KG.value == "waste_kg"

    def test_employee_headcount_exists(self):
        assert DataPointType.EMPLOYEE_HEADCOUNT.value == "employee_headcount"


class TestDataPoint:
    """Test DataPoint frozen dataclass."""

    def test_create_with_all_fields(self):
        org_id = uuid4()
        now = datetime.utcnow()
        dp = DataPoint(
            id="dp_test_001",
            organization_id=org_id,
            data_point_type=DataPointType.ENERGY_KWH,
            value=Decimal("1500.50"),
            unit="kWh",
            confidence="HIGH",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            recorded_at=now,
            source_system="ERP",
            source_record_id="rec_123",
            calculation_method="direct_measurement",
            emission_factor=Decimal("0.5"),
            emission_factor_source="EPA 2023",
            emission_factor_year=2023,
            notes="Test data point",
        )

        assert dp.id == "dp_test_001"
        assert dp.organization_id == org_id
        assert dp.data_point_type == DataPointType.ENERGY_KWH
        assert dp.value == Decimal("1500.50")
        assert dp.unit == "kWh"
        assert dp.confidence == "HIGH"
        assert dp.period_start == date(2024, 1, 1)
        assert dp.period_end == date(2024, 12, 31)
        assert dp.recorded_at == now
        assert dp.source_system == "ERP"
        assert dp.source_record_id == "rec_123"
        assert dp.calculation_method == "direct_measurement"
        assert dp.emission_factor == Decimal("0.5")
        assert dp.emission_factor_source == "EPA 2023"
        assert dp.emission_factor_year == 2023
        assert dp.notes == "Test data point"

    def test_negative_value_raises_value_error(self):
        org_id = uuid4()
        now = datetime.utcnow()
        with pytest.raises(ValueError, match="must not be negative"):
            DataPoint(
                id="dp_test_002",
                organization_id=org_id,
                data_point_type=DataPointType.ENERGY_KWH,
                value=Decimal("-100"),
                unit="kWh",
                confidence="HIGH",
                period_start=date(2024, 1, 1),
                period_end=date(2024, 12, 31),
                recorded_at=now,
            )

    def test_period_end_before_start_raises_value_error(self):
        org_id = uuid4()
        now = datetime.utcnow()
        with pytest.raises(ValueError, match="must not be before"):
            DataPoint(
                id="dp_test_003",
                organization_id=org_id,
                data_point_type=DataPointType.ENERGY_KWH,
                value=Decimal("100"),
                unit="kWh",
                confidence="HIGH",
                period_start=date(2024, 12, 31),
                period_end=date(2024, 1, 1),
                recorded_at=now,
            )

    def test_period_days_property(self):
        org_id = uuid4()
        now = datetime.utcnow()
        dp = DataPoint(
            id="dp_test_004",
            organization_id=org_id,
            data_point_type=DataPointType.ENERGY_KWH,
            value=Decimal("1000"),
            unit="kWh",
            confidence="MEDIUM",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            recorded_at=now,
        )
        assert dp.period_days == 30

    def test_annual_equivalent_property(self):
        org_id = uuid4()
        now = datetime.utcnow()
        dp = DataPoint(
            id="dp_test_005",
            organization_id=org_id,
            data_point_type=DataPointType.ENERGY_KWH,
            value=Decimal("100"),
            unit="kWh",
            confidence="HIGH",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 6, 30),
            recorded_at=now,
        )
        # 181 days in first half of 2024, annualized should be roughly 2x
        assert dp.period_days == 181
        expected_annual = (Decimal("100") * Decimal("365")) / Decimal("181")
        assert dp.annual_equivalent == expected_annual


class TestDisclosurePackage:
    """Test DisclosurePackage dataclass."""

    def test_is_complete_returns_true_when_no_gaps_and_has_data_points(self):
        """is_complete() returns True when gaps is empty and data_points is non-empty."""
        org_id = uuid4()
        now = datetime.utcnow()
        period = (date(2024, 1, 1), date(2024, 12, 31))

        dp = DataPoint(
            id="dp_001",
            organization_id=org_id,
            data_point_type=DataPointType.ENERGY_KWH,
            value=Decimal("5000"),
            unit="kWh",
            confidence="HIGH",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            recorded_at=now,
        )

        confidence = ConfidenceSummary(
            high_pct=100.0,
            medium_pct=0.0,
            low_pct=0.0,
            total_data_points=1,
        )

        package = DisclosurePackage(
            framework=FrameworkType.CSRD,
            reporting_period=period,
            organization_id=org_id,
            data_points=[dp],
            generated_at=now,
            confidence_summary=confidence,
            gaps=[],  # empty gaps
        )

        assert package.is_complete() is True

    def test_is_complete_returns_false_when_gaps_present(self):
        """is_complete() returns False when gaps list is non-empty."""
        org_id = uuid4()
        now = datetime.utcnow()
        period = (date(2024, 1, 1), date(2024, 12, 31))

        dp = DataPoint(
            id="dp_001",
            organization_id=org_id,
            data_point_type=DataPointType.ENERGY_KWH,
            value=Decimal("5000"),
            unit="kWh",
            confidence="HIGH",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            recorded_at=now,
        )

        gap = Gap(
            gap_id="GAP-001",
            data_point_type=DataPointType.SCOPE1_TCO2E,
            framework_disclosure_code="ESRS E1",
            description="Missing scope1 data",
            severity="HIGH",
        )

        confidence = ConfidenceSummary(
            high_pct=100.0,
            medium_pct=0.0,
            low_pct=0.0,
            total_data_points=1,
        )

        package = DisclosurePackage(
            framework=FrameworkType.CSRD,
            reporting_period=period,
            organization_id=org_id,
            data_points=[dp],
            generated_at=now,
            confidence_summary=confidence,
            gaps=[gap],
        )

        assert package.is_complete() is False

    def test_is_complete_returns_false_when_no_data_points(self):
        """is_complete() returns False when data_points list is empty."""
        org_id = uuid4()
        now = datetime.utcnow()
        period = (date(2024, 1, 1), date(2024, 12, 31))

        confidence = ConfidenceSummary(
            high_pct=0.0,
            medium_pct=0.0,
            low_pct=0.0,
            total_data_points=0,
        )

        package = DisclosurePackage(
            framework=FrameworkType.CSRD,
            reporting_period=period,
            organization_id=org_id,
            data_points=[],  # empty data_points
            generated_at=now,
            confidence_summary=confidence,
            gaps=[],
        )

        assert package.is_complete() is False

    def test_create_with_framework_data_points_gaps_metadata(self):
        org_id = uuid4()
        now = datetime.utcnow()
        period = (date(2024, 1, 1), date(2024, 12, 31))

        dp = DataPoint(
            id="dp_001",
            organization_id=org_id,
            data_point_type=DataPointType.ENERGY_KWH,
            value=Decimal("5000"),
            unit="kWh",
            confidence="HIGH",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            recorded_at=now,
        )

        gap = Gap(
            gap_id="GAP-001",
            data_point_type=DataPointType.SCOPE1_TCO2E,
            framework_disclosure_code="ESRS E1",
            description="Missing scope1 data",
            severity="HIGH",
        )

        confidence = ConfidenceSummary(
            high_pct=100.0,
            medium_pct=0.0,
            low_pct=0.0,
            total_data_points=1,
        )

        package = DisclosurePackage(
            framework=FrameworkType.CSRD,
            reporting_period=period,
            organization_id=org_id,
            data_points=[dp],
            generated_at=now,
            confidence_summary=confidence,
            gaps=[gap],
            disclosure_id="CSRD-2024-Q4",
            reporter_name="Test Reporter",
            approval_status="draft",
        )

        assert package.framework == FrameworkType.CSRD
        assert package.reporting_period == period
        assert package.organization_id == org_id
        assert len(package.data_points) == 1
        assert package.data_points[0].id == "dp_001"
        assert len(package.gaps) == 1
        assert package.gaps[0].gap_id == "GAP-001"
        assert package.disclosure_id == "CSRD-2024-Q4"
        assert package.reporter_name == "Test Reporter"
        assert package.approval_status == "draft"

    def test_has_critical_gaps_property(self):
        org_id = uuid4()
        now = datetime.utcnow()
        period = (date(2024, 1, 1), date(2024, 12, 31))

        confidence = ConfidenceSummary(
            high_pct=100.0,
            medium_pct=0.0,
            low_pct=0.0,
            total_data_points=1,
        )

        gap_high = Gap(
            gap_id="GAP-HIGH",
            data_point_type=DataPointType.SCOPE1_TCO2E,
            framework_disclosure_code="ESRS E1",
            description="Missing data",
            severity="HIGH",
        )

        package = DisclosurePackage(
            framework=FrameworkType.CSRD,
            reporting_period=period,
            organization_id=org_id,
            data_points=[
                DataPoint(
                    id="dp_placeholder",
                    organization_id=org_id,
                    data_point_type=DataPointType.ENERGY_KWH,
                    value=Decimal("1"),
                    unit="kWh",
                    confidence="HIGH",
                    period_start=date(2024, 1, 1),
                    period_end=date(2024, 12, 31),
                    recorded_at=now,
                )
            ],
            generated_at=now,
            confidence_summary=confidence,
            gaps=[gap_high],
        )

        assert package.has_critical_gaps is True

    def test_data_points_by_type_method(self):
        org_id = uuid4()
        now = datetime.utcnow()
        period = (date(2024, 1, 1), date(2024, 12, 31))

        dp_energy = DataPoint(
            id="dp_energy",
            organization_id=org_id,
            data_point_type=DataPointType.ENERGY_KWH,
            value=Decimal("1000"),
            unit="kWh",
            confidence="HIGH",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            recorded_at=now,
        )

        dp_water = DataPoint(
            id="dp_water",
            organization_id=org_id,
            data_point_type=DataPointType.WATER_M3,
            value=Decimal("500"),
            unit="m3",
            confidence="MEDIUM",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            recorded_at=now,
        )

        confidence = ConfidenceSummary(
            high_pct=50.0,
            medium_pct=50.0,
            low_pct=0.0,
            total_data_points=2,
        )

        package = DisclosurePackage(
            framework=FrameworkType.GRI,
            reporting_period=period,
            organization_id=org_id,
            data_points=[dp_energy, dp_water],
            generated_at=now,
            confidence_summary=confidence,
        )

        energy_dps = package.data_points_by_type(DataPointType.ENERGY_KWH)
        assert len(energy_dps) == 1
        assert energy_dps[0].id == "dp_energy"

        water_dps = package.data_points_by_type(DataPointType.WATER_M3)
        assert len(water_dps) == 1
        assert water_dps[0].id == "dp_water"


class TestConfidenceSummary:
    """Test ConfidenceSummary dataclass."""

    def test_valid_percentages(self):
        cs = ConfidenceSummary(
            high_pct=60.0,
            medium_pct=30.0,
            low_pct=10.0,
            total_data_points=10,
        )
        assert cs.high_pct == 60.0
        assert cs.medium_pct == 30.0
        assert cs.low_pct == 10.0
        assert cs.total_data_points == 10

    def test_invalid_percentages_raise_error(self):
        with pytest.raises(ValueError, match="must sum to 100"):
            ConfidenceSummary(
                high_pct=50.0,
                medium_pct=30.0,
                low_pct=10.0,  # Adds to 90, not 100
                total_data_points=10,
            )


class TestGap:
    """Test Gap dataclass."""

    def test_create_gap_with_required_fields(self):
        gap = Gap(
            gap_id="TEST-GAP-001",
            data_point_type=DataPointType.WATER_M3,
            framework_disclosure_code="GRI 303",
            description="No water data available",
            severity="MEDIUM",
        )

        assert gap.gap_id == "TEST-GAP-001"
        assert gap.data_point_type == DataPointType.WATER_M3
        assert gap.framework_disclosure_code == "GRI 303"
        assert gap.description == "No water data available"
        assert gap.severity == "MEDIUM"
        assert gap.suggested_improvement is None
        assert gap.covered_by_proxy is False

    def test_create_gap_with_all_fields(self):
        gap = Gap(
            gap_id="TEST-GAP-002",
            data_point_type=DataPointType.ENERGY_KWH,
            framework_disclosure_code="GRI 302",
            description="No energy data",
            severity="HIGH",
            suggested_improvement="Install meters",
            covered_by_proxy=True,
        )

        assert gap.suggested_improvement == "Install meters"
        assert gap.covered_by_proxy is True
