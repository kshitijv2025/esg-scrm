"""
Tests for src/orchestration/normalization_engine.py — NormalizationEngine.
"""

import sys

sys.path.insert(0, "src")

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from src.orchestration.disclosure_package import DataPointType
from src.orchestration.erp_connector import (
    ConfidenceLevel,
    EmployeeData,
    ProductionRecord,
    SpendRecord,
    UtilityRecord,
    UtilityType,
)
from src.orchestration.normalization_engine import NormalizationEngine


# ---------------------------------------------------------------------------
# NormalizationEngine constructor
# ---------------------------------------------------------------------------


def test_normalization_engine_default_constructor():
    """Engine initializes with default emission factors and zero counter."""
    engine = NormalizationEngine()
    assert engine.electricity_emission_factor == Decimal("0.212")
    assert engine.gas_emission_factor == Decimal("0.202")
    assert engine.water_emission_factor == Decimal("0.344")
    assert engine.diesel_emission_factor == Decimal("2.68")
    assert engine._counter == 0


def test_normalization_engine_custom_factors():
    """Engine accepts custom emission factors."""
    engine = NormalizationEngine(
        electricity_emission_factor=Decimal("0.300"),
        gas_emission_factor=Decimal("0.250"),
    )
    assert engine.electricity_emission_factor == Decimal("0.300")
    assert engine.gas_emission_factor == Decimal("0.250")
    # Unset ones still have defaults
    assert engine.water_emission_factor == Decimal("0.344")
    assert engine.diesel_emission_factor == Decimal("2.68")


# ---------------------------------------------------------------------------
# normalize_utility_record — electricity (HIGH confidence)
# ---------------------------------------------------------------------------


def test_normalize_utility_electricity_returns_high_confidence():
    """Electricity utility records produce HIGH confidence DataPoints."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = UtilityRecord(
        organization_id=org_id,
        invoice_number="INV-ELEC-001",
        utility_type=UtilityType.ELECTRICITY,
        amount=Decimal("1000.00"),
        currency="USD",
        quantity=Decimal("5000"),
        unit="kWh",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        recorded_at=now,
    )

    dp = engine.normalize_utility_record(record, source="direct_meter")

    assert dp.data_point_type == DataPointType.ENERGY_KWH
    assert dp.value == Decimal("5000")
    assert dp.unit == "kWh"
    assert dp.confidence == ConfidenceLevel.HIGH.value
    assert dp.period_start == date(2024, 1, 1)
    assert dp.period_end == date(2024, 1, 31)
    assert dp.source_record_id == "INV-ELEC-001"
    assert dp.calculation_method == "direct_measurement"


def test_normalize_utility_electricity_emissions_calculation():
    """Electricity emissions are quantity * electricity_emission_factor."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = UtilityRecord(
        organization_id=org_id,
        invoice_number="INV-ELEC-002",
        utility_type=UtilityType.ELECTRICITY,
        amount=Decimal("500.00"),
        currency="USD",
        quantity=Decimal("1000"),
        unit="kWh",
        start_date=date(2024, 2, 1),
        end_date=date(2024, 2, 29),
        recorded_at=now,
    )

    dp = engine.normalize_utility_record(record)

    # 1000 kWh * 0.212 kgCO2e/kWh = 212 kgCO2e
    expected_emissions_kg = Decimal("1000") * Decimal("0.212")
    expected_factor = expected_emissions_kg / Decimal("1000")
    assert dp.emission_factor == expected_factor


def test_normalize_utility_gas_returns_high_confidence():
    """Gas utility records produce HIGH confidence DataPoints."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = UtilityRecord(
        organization_id=org_id,
        invoice_number="INV-GAS-001",
        utility_type=UtilityType.GAS,
        amount=Decimal("800.00"),
        currency="USD",
        quantity=Decimal("4000"),
        unit="kWh",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        recorded_at=now,
    )

    dp = engine.normalize_utility_record(record, source="direct_meter")

    assert dp.data_point_type == DataPointType.ENERGY_KWH
    assert dp.value == Decimal("4000")
    assert dp.unit == "kWh"
    assert dp.confidence == ConfidenceLevel.HIGH.value


def test_normalize_utility_water_returns_high_confidence():
    """Water utility records produce HIGH confidence DataPoints."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = UtilityRecord(
        organization_id=org_id,
        invoice_number="INV-WATER-001",
        utility_type=UtilityType.WATER,
        amount=Decimal("200.00"),
        currency="USD",
        quantity=Decimal("150"),
        unit="m3",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        recorded_at=now,
    )

    dp = engine.normalize_utility_record(record, source="direct_meter")

    assert dp.data_point_type == DataPointType.WATER_M3
    assert dp.value == Decimal("150")
    assert dp.unit == "m3"
    assert dp.confidence == ConfidenceLevel.HIGH.value


def test_normalize_utility_waste_returns_medium_confidence():
    """Waste utility records produce MEDIUM confidence DataPoints."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = UtilityRecord(
        organization_id=org_id,
        invoice_number="INV-WASTE-001",
        utility_type=UtilityType.WASTE,
        amount=Decimal("300.00"),
        currency="USD",
        quantity=Decimal("500"),
        unit="kg",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        recorded_at=now,
    )

    dp = engine.normalize_utility_record(record)

    assert dp.data_point_type == DataPointType.WASTE_KG
    assert dp.value == Decimal("500")
    assert dp.unit == "kg"
    assert dp.confidence == ConfidenceLevel.MEDIUM.value


def test_normalize_utility_renewable_returns_zero_emissions():
    """Renewable utility records have zero emissions."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = UtilityRecord(
        organization_id=org_id,
        invoice_number="INV-REN-001",
        utility_type=UtilityType.RENEWABLE,
        amount=Decimal("1000.00"),
        currency="USD",
        quantity=Decimal("3000"),
        unit="kWh",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        recorded_at=now,
    )

    dp = engine.normalize_utility_record(record)

    assert dp.data_point_type == DataPointType.ENERGY_KWH
    assert dp.value == Decimal("3000")
    assert dp.emission_factor == Decimal("0")


def test_normalize_utility_source_meter_high_confidence():
    """Source containing 'meter' produces HIGH confidence."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = UtilityRecord(
        organization_id=org_id,
        invoice_number="INV-ELEC-METER",
        utility_type=UtilityType.ELECTRICITY,
        amount=Decimal("100.00"),
        currency="USD",
        quantity=Decimal("500"),
        unit="kWh",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        recorded_at=now,
    )

    dp = engine.normalize_utility_record(record, source="smart_meter")

    assert dp.confidence == ConfidenceLevel.HIGH.value


def test_normalize_utility_source_direct_high_confidence():
    """Source containing 'direct' produces HIGH confidence."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = UtilityRecord(
        organization_id=org_id,
        invoice_number="INV-ELEC-DIRECT",
        utility_type=UtilityType.ELECTRICITY,
        amount=Decimal("100.00"),
        currency="USD",
        quantity=Decimal("500"),
        unit="kWh",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        recorded_at=now,
    )

    dp = engine.normalize_utility_record(record, source="direct_reading")

    assert dp.confidence == ConfidenceLevel.HIGH.value


def test_normalize_utility_source_estimate_medium_confidence():
    """Source containing 'estimate' produces MEDIUM confidence."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = UtilityRecord(
        organization_id=org_id,
        invoice_number="INV-ELEC-EST",
        utility_type=UtilityType.ELECTRICITY,
        amount=Decimal("100.00"),
        currency="USD",
        quantity=Decimal("500"),
        unit="kWh",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        recorded_at=now,
    )

    dp = engine.normalize_utility_record(record, source="utility_estimate")

    assert dp.confidence == ConfidenceLevel.MEDIUM.value


def test_normalize_utility_source_calculated_medium_confidence():
    """Source containing 'calculated' produces MEDIUM confidence."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = UtilityRecord(
        organization_id=org_id,
        invoice_number="INV-ELEC-CALC",
        utility_type=UtilityType.ELECTRICITY,
        amount=Decimal("100.00"),
        currency="USD",
        quantity=Decimal("500"),
        unit="kWh",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        recorded_at=now,
    )

    dp = engine.normalize_utility_record(record, source="calculated_from_billing")

    assert dp.confidence == ConfidenceLevel.MEDIUM.value


def test_normalize_utility_source_spend_low_confidence():
    """Source containing 'spend' produces LOW confidence."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = UtilityRecord(
        organization_id=org_id,
        invoice_number="INV-ELEC-SPEND",
        utility_type=UtilityType.ELECTRICITY,
        amount=Decimal("100.00"),
        currency="USD",
        quantity=Decimal("500"),
        unit="kWh",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        recorded_at=now,
    )

    dp = engine.normalize_utility_record(record, source="energy_spend_based")

    assert dp.confidence == ConfidenceLevel.LOW.value


def test_normalize_utility_source_extrapolated_low_confidence():
    """Source containing 'extrapolat' produces LOW confidence."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = UtilityRecord(
        organization_id=org_id,
        invoice_number="INV-ELEC-EXT",
        utility_type=UtilityType.ELECTRICITY,
        amount=Decimal("100.00"),
        currency="USD",
        quantity=Decimal("500"),
        unit="kWh",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        recorded_at=now,
    )

    dp = engine.normalize_utility_record(record, source="extrapolated_from_annual")

    assert dp.confidence == ConfidenceLevel.LOW.value


def test_normalize_utility_source_default_medium_confidence():
    """Default source (no keyword match) produces MEDIUM confidence."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = UtilityRecord(
        organization_id=org_id,
        invoice_number="INV-ELEC-DEF",
        utility_type=UtilityType.ELECTRICITY,
        amount=Decimal("100.00"),
        currency="USD",
        quantity=Decimal("500"),
        unit="kWh",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        recorded_at=now,
    )

    dp = engine.normalize_utility_record(record, source="ERP")

    # Default case: no keyword match → MEDIUM
    assert dp.confidence == ConfidenceLevel.MEDIUM.value


def test_normalize_utility_unknown_type_raises():
    """Unknown utility type raises ValueError."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()

    class UnknownUtilityType:
        value = "unknown"

    record = UtilityRecord(
        organization_id=org_id,
        invoice_number="INV-UNK-001",
        utility_type=UnknownUtilityType(),  # type: ignore
        amount=Decimal("100.00"),
        currency="USD",
        quantity=Decimal("100"),
        unit="kWh",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        recorded_at=now,
    )

    with pytest.raises(ValueError, match="Unknown utility type"):
        engine.normalize_utility_record(record)


# ---------------------------------------------------------------------------
# normalize_procurement_spend — spend-based (LOW confidence)
# ---------------------------------------------------------------------------


def test_normalize_procurement_spend_returns_low_confidence():
    """Spend-based procurement records produce LOW confidence DataPoints."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = SpendRecord(
        organization_id=org_id,
        purchase_order_number="PO-500",
        category_code="CAT-RM",
        category_description="Raw Materials",
        amount=Decimal("10000.00"),
        currency="USD",
        vendor_name="Global Materials Ltd",
        purchase_date=date(2024, 4, 10),
        recorded_at=now,
    )

    dp = engine.normalize_procurement_spend(record, emission_factor=0.5)

    assert dp.data_point_type == DataPointType.SCOPE3_TCO2E
    assert dp.unit == "tCO2e"
    assert dp.confidence == ConfidenceLevel.LOW.value
    assert dp.calculation_method == "spend_based"
    assert dp.source_record_id == "PO-500"


def test_normalize_procurement_spend_emissions_calculation():
    """Spend emissions are amount_usd * emission_factor converted to tCO2e."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = SpendRecord(
        organization_id=org_id,
        purchase_order_number="PO-501",
        category_code="CAT-PACK",
        category_description="Packaging",
        amount=Decimal("2000.00"),
        currency="USD",
        vendor_name="Box Co",
        purchase_date=date(2024, 5, 1),
        recorded_at=now,
    )

    dp = engine.normalize_procurement_spend(record, emission_factor=0.5)

    # 2000 USD * 0.5 kgCO2e/USD = 1000 kgCO2e = 1.0 tCO2e
    assert dp.value == Decimal("1.0000")
    assert dp.emission_factor == Decimal("0.5")


# ---------------------------------------------------------------------------
# normalize_production_volume — direct measurement (HIGH confidence)
# ---------------------------------------------------------------------------


def test_normalize_production_volume_returns_high_confidence():
    """Production volume records produce HIGH confidence DataPoints."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = ProductionRecord(
        organization_id=org_id,
        product_code="PROD-WIDGET",
        product_name="Standard Widget",
        units_produced=Decimal("10000"),
        unit_of_measure="units",
        production_date=date(2024, 3, 1),
        recorded_at=now,
    )

    dp = engine.normalize_production_volume(record)

    assert dp.value == Decimal("10000")
    assert dp.unit == "units"
    assert dp.confidence == ConfidenceLevel.HIGH.value
    assert dp.calculation_method == "direct_measurement"
    assert dp.source_record_id == "PROD-WIDGET"


def test_normalize_production_volume_single_day_period():
    """Production volume uses the production date as both period start and end."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = ProductionRecord(
        organization_id=org_id,
        product_code="PROD-GADGET",
        product_name="Gadget",
        units_produced=Decimal("500"),
        unit_of_measure="units",
        production_date=date(2024, 6, 15),
        recorded_at=now,
    )

    dp = engine.normalize_production_volume(record)

    assert dp.period_start == date(2024, 6, 15)
    assert dp.period_end == date(2024, 6, 15)


# ---------------------------------------------------------------------------
# normalize_employee_data — HR data (MEDIUM confidence)
# ---------------------------------------------------------------------------


def test_normalize_employee_data_returns_medium_confidence():
    """Employee data produces DataPoints with MEDIUM confidence."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = EmployeeData(
        organization_id=org_id,
        reporting_period_start=date(2024, 1, 1),
        reporting_period_end=date(2024, 12, 31),
        total_headcount=1000,
        new_hires=100,
        departures=50,
    )

    data_points = engine.normalize_employee_data(record)

    assert len(data_points) == 2

    headcount_dp = data_points[0]
    assert headcount_dp.data_point_type == DataPointType.EMPLOYEE_HEADCOUNT
    assert headcount_dp.value == Decimal("1000")
    assert headcount_dp.unit == "people"
    assert headcount_dp.confidence == ConfidenceLevel.MEDIUM.value
    assert headcount_dp.calculation_method == "direct_measurement"


def test_normalize_employee_data_turnover_rate():
    """Employee data includes a turnover rate DataPoint."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = EmployeeData(
        organization_id=org_id,
        reporting_period_start=date(2024, 1, 1),
        reporting_period_end=date(2024, 12, 31),
        total_headcount=1000,
        new_hires=100,
        departures=50,
    )

    data_points = engine.normalize_employee_data(record)

    turnover_dp = data_points[1]
    assert turnover_dp.data_point_type == DataPointType.EMPLOYEE_TURNOVER_RATE
    # departures=50, headcount=1000 -> 0.05
    assert turnover_dp.value == Decimal("0.0500")
    assert turnover_dp.unit == "ratio"
    assert turnover_dp.confidence == ConfidenceLevel.MEDIUM.value


def test_normalize_employee_data_zero_headcount_turnover():
    """Zero headcount returns zero turnover rate, not division error."""
    engine = NormalizationEngine()
    org_id = uuid4()
    now = datetime.utcnow()
    record = EmployeeData(
        organization_id=org_id,
        reporting_period_start=date(2024, 1, 1),
        reporting_period_end=date(2024, 12, 31),
        total_headcount=0,
        new_hires=0,
        departures=0,
    )

    data_points = engine.normalize_employee_data(record)

    turnover_dp = data_points[1]
    assert turnover_dp.value == Decimal("0")
