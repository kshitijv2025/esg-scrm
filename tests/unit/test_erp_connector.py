"""
Tests for src/orchestration/erp_connector.py — ABC and supporting dataclasses.
"""

import sys

sys.path.insert(0, "src")

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from src.orchestration.erp_connector import (
    AssetRegister,
    ConfidenceLevel,
    ConnectionStatus,
    ConnectionTestResult,
    EmployeeData,
    EncryptedBlob,
    ERPConnector,
    ProductionRecord,
    SpendRecord,
    UtilityRecord,
    UtilityType,
)


# ---------------------------------------------------------------------------
# ERPConnector ABC — cannot be instantiated directly
# ---------------------------------------------------------------------------


def test_erp_connector_is_abstract():
    """ERPConnector cannot be instantiated — it is an abstract base class."""
    with pytest.raises(TypeError):
        ERPConnector(
            organization_id=uuid4(),
            credentials=EncryptedBlob.from_credentials(uuid4(), b"fake"),
        )


# ---------------------------------------------------------------------------
# ConnectionStatus enum
# ---------------------------------------------------------------------------


def test_connection_status_values():
    assert ConnectionStatus.CONNECTED.value == "connected"
    assert ConnectionStatus.DISCONNECTED.value == "disconnected"
    assert ConnectionStatus.ERROR.value == "error"


# ---------------------------------------------------------------------------
# ConfidenceLevel enum
# ---------------------------------------------------------------------------


def test_confidence_level_values():
    assert ConfidenceLevel.HIGH.value == "HIGH"
    assert ConfidenceLevel.MEDIUM.value == "MEDIUM"
    assert ConfidenceLevel.LOW.value == "LOW"


# ---------------------------------------------------------------------------
# UtilityType enum
# ---------------------------------------------------------------------------


def test_utility_type_values():
    assert UtilityType.ELECTRICITY.value == "electricity"
    assert UtilityType.GAS.value == "gas"
    assert UtilityType.WATER.value == "water"
    assert UtilityType.WASTE.value == "waste"
    assert UtilityType.RENEWABLE.value == "renewable"


# ---------------------------------------------------------------------------
# EncryptedBlob dataclass
# ---------------------------------------------------------------------------


def test_encrypted_blob_from_credentials():
    org_id = uuid4()
    blob = EncryptedBlob.from_credentials(org_id, b"\x00\x01\x02")
    assert blob._encrypted_value == b"\x00\x01\x02"
    assert blob.organization_id == org_id


def test_encrypted_blob_organization_id_property():
    org_id = uuid4()
    blob = EncryptedBlob.from_credentials(org_id, b"encrypted")
    assert blob.organization_id == org_id


# ---------------------------------------------------------------------------
# UtilityRecord dataclass
# ---------------------------------------------------------------------------


def test_utility_record_defaults():
    org_id = uuid4()
    now = datetime.utcnow()
    record = UtilityRecord(
        organization_id=org_id,
        invoice_number="INV-001",
        utility_type=UtilityType.ELECTRICITY,
        amount=Decimal("1500.00"),
        currency="USD",
        quantity=Decimal("5000"),
        unit="kWh",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        recorded_at=now,
    )
    assert record.source_system == "ERP"
    assert record.confidence == ConfidenceLevel.HIGH


def test_utility_record_period_days():
    org_id = uuid4()
    now = datetime.utcnow()
    record = UtilityRecord(
        organization_id=org_id,
        invoice_number="INV-001",
        utility_type=UtilityType.GAS,
        amount=Decimal("500.00"),
        currency="USD",
        quantity=Decimal("1000"),
        unit="kWh",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        recorded_at=now,
    )
    assert record.period_days == 30


# ---------------------------------------------------------------------------
# SpendRecord dataclass
# ---------------------------------------------------------------------------


def test_spend_record_defaults():
    org_id = uuid4()
    now = datetime.utcnow()
    record = SpendRecord(
        organization_id=org_id,
        purchase_order_number="PO-100",
        category_code="CAT-A",
        category_description="Raw Materials",
        amount=Decimal("25000.00"),
        currency="USD",
        vendor_name="Acme Corp",
        purchase_date=date(2024, 3, 15),
        recorded_at=now,
    )
    assert record.source_system == "ERP"
    assert record.confidence == ConfidenceLevel.LOW  # Spend-based = LOW


# ---------------------------------------------------------------------------
# ProductionRecord dataclass
# ---------------------------------------------------------------------------


def test_production_record_defaults():
    org_id = uuid4()
    now = datetime.utcnow()
    record = ProductionRecord(
        organization_id=org_id,
        product_code="PROD-001",
        product_name="Widget A",
        units_produced=Decimal("10000"),
        unit_of_measure="units",
        production_date=date(2024, 2, 1),
        recorded_at=now,
    )
    assert record.source_system == "ERP"
    assert record.confidence == ConfidenceLevel.HIGH
    assert record.raw_material_consumption is None
    assert record.raw_material_unit is None


def test_production_record_with_raw_material():
    org_id = uuid4()
    now = datetime.utcnow()
    record = ProductionRecord(
        organization_id=org_id,
        product_code="PROD-002",
        product_name="Widget B",
        units_produced=Decimal("5000"),
        unit_of_measure="units",
        production_date=date(2024, 2, 1),
        recorded_at=now,
        raw_material_consumption=Decimal("2500"),
        raw_material_unit="kg",
    )
    assert record.raw_material_consumption == Decimal("2500")
    assert record.raw_material_unit == "kg"


# ---------------------------------------------------------------------------
# EmployeeData dataclass
# ---------------------------------------------------------------------------


def test_employee_data_defaults():
    org_id = uuid4()
    now = datetime.utcnow()
    record = EmployeeData(
        organization_id=org_id,
        reporting_period_start=date(2024, 1, 1),
        reporting_period_end=date(2024, 12, 31),
        total_headcount=500,
    )
    assert record.new_hires == 0
    assert record.departures == 0
    assert record.average_tenure_years is None
    assert record.confidence == ConfidenceLevel.MEDIUM
    assert record.department_breakdown == {}


def test_employee_data_full_fields():
    org_id = uuid4()
    now = datetime.utcnow()
    record = EmployeeData(
        organization_id=org_id,
        reporting_period_start=date(2024, 1, 1),
        reporting_period_end=date(2024, 12, 31),
        total_headcount=500,
        new_hires=50,
        departures=20,
        average_tenure_years=4.5,
        compensation_band_low=Decimal("30000"),
        compensation_band_high=Decimal("100000"),
        department_breakdown={"Engineering": 200, "Operations": 150},
        recorded_at=now,
    )
    assert record.new_hires == 50
    assert record.departures == 20
    assert record.average_tenure_years == 4.5
    assert record.compensation_band_low == Decimal("30000")
    assert record.compensation_band_high == Decimal("100000")
    assert record.department_breakdown == {"Engineering": 200, "Operations": 150}


# ---------------------------------------------------------------------------
# AssetRegister dataclass
# ---------------------------------------------------------------------------


def test_asset_register_defaults():
    org_id = uuid4()
    record = AssetRegister(
        organization_id=org_id,
        asset_id="AST-001",
        asset_name="Diesel Generator",
        asset_category="generators",
    )
    assert record.fuel_type is None
    assert record.capacity is None
    assert record.capacity_unit is None
    assert record.confidence == ConfidenceLevel.MEDIUM


def test_asset_register_full_fields():
    org_id = uuid4()
    record = AssetRegister(
        organization_id=org_id,
        asset_id="AST-002",
        asset_name="Fleet Truck",
        asset_category="fleet",
        fuel_type="diesel",
        capacity=Decimal("5000"),
        capacity_unit="liters",
        annual_consumption=Decimal("12000"),
        annual_consumption_unit="liters",
        emission_factor=Decimal("2.68"),
        acquisition_date=date(2020, 1, 1),
    )
    assert record.fuel_type == "diesel"
    assert record.capacity == Decimal("5000")
    assert record.emission_factor == Decimal("2.68")


# ---------------------------------------------------------------------------
# ConnectionTestResult dataclass
# ---------------------------------------------------------------------------


def test_connection_test_result_connected():
    org_id = uuid4()
    now = datetime.utcnow()
    result = ConnectionTestResult(
        status=ConnectionStatus.CONNECTED,
        organization_id=org_id,
        tested_at=now,
        api_version="v2.1",
        latency_ms=45.3,
    )
    assert result.status == ConnectionStatus.CONNECTED
    assert result.organization_id == org_id
    assert result.error_message is None
    assert result.api_version == "v2.1"
    assert result.latency_ms == 45.3


def test_connection_test_result_error():
    org_id = uuid4()
    now = datetime.utcnow()
    result = ConnectionTestResult(
        status=ConnectionStatus.ERROR,
        organization_id=org_id,
        tested_at=now,
        error_message="Authentication failed",
    )
    assert result.status == ConnectionStatus.ERROR
    assert result.error_message == "Authentication failed"
    assert result.api_version is None
    assert result.latency_ms is None
