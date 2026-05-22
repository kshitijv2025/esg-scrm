"""
ERPConnector ABC and supporting dataclasses for ESG+SCRM data orchestration.

SPEC 01: https://github.com/kshitijv2025/esg-scrm/blob/main/specs/01-data-orchestration.md
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


class ConnectionStatus(Enum):
    """Connection status for ERP systems."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class ConfidenceLevel(Enum):
    """Data confidence level for ESG metrics."""

    HIGH = "HIGH"  # Direct measurement (meters, invoices)
    MEDIUM = "MEDIUM"  # Activity-based calculation
    LOW = "LOW"  # Spend-based estimate


class UtilityType(Enum):
    """Types of utility expenses."""

    ELECTRICITY = "electricity"
    GAS = "gas"
    WATER = "water"
    WASTE = "waste"
    RENEWABLE = "renewable"


@dataclass(frozen=True)
class EncryptedBlob:
    """Encrypted credential blob for ERP connections.

    Never log this object directly. Access the decrypted value only in memory
    during connection establishment and erase immediately after use.
    """

    _encrypted_value: bytes
    _organization_id: UUID

    @classmethod
    def from_credentials(cls, organization_id: UUID, encrypted_value: bytes) -> EncryptedBlob:
        """Create an EncryptedBlob from encrypted credentials."""
        return cls(_encrypted_value=encrypted_value, _organization_id=organization_id)

    @property
    def organization_id(self) -> UUID:
        """Return the organization ID this blob is scoped to."""
        return self._organization_id


@dataclass(frozen=True)
class UtilityRecord:
    """Utility expense record from ERP."""

    organization_id: UUID
    invoice_number: str
    utility_type: UtilityType
    amount: Decimal
    currency: str
    quantity: Decimal
    unit: str
    start_date: date
    end_date: date
    recorded_at: datetime
    source_system: str = "ERP"
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH

    @property
    def period_days(self) -> int:
        """Return the number of days in the billing period."""
        return (self.end_date - self.start_date).days


@dataclass(frozen=True)
class SpendRecord:
    """Procurement spend record from ERP."""

    organization_id: UUID
    purchase_order_number: str
    category_code: str
    category_description: str
    amount: Decimal
    currency: str
    vendor_name: str
    purchase_date: date
    recorded_at: datetime
    source_system: str = "ERP"
    confidence: ConfidenceLevel = ConfidenceLevel.LOW  # Spend-based = LOW confidence


@dataclass(frozen=True)
class ProductionRecord:
    """Production volume record from ERP."""

    organization_id: UUID
    product_code: str
    product_name: str
    units_produced: Decimal
    unit_of_measure: str
    production_date: date
    recorded_at: datetime
    raw_material_consumption: Optional[Decimal] = None
    raw_material_unit: Optional[str] = None
    source_system: str = "ERP"
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH


@dataclass(frozen=True)
class EmployeeData:
    """Anonymized employee data from ERP HR module."""

    organization_id: UUID
    reporting_period_start: date
    reporting_period_end: date
    total_headcount: int
    new_hires: int = 0
    departures: int = 0
    average_tenure_years: Optional[float] = None
    compensation_band_low: Optional[Decimal] = None  # Anonymized band floor
    compensation_band_high: Optional[Decimal] = None  # Anonymized band ceiling
    department_breakdown: dict[str, int] = field(default_factory=dict)
    recorded_at: datetime = field(default_factory=lambda: datetime.utcnow())
    source_system: str = "ERP"
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


@dataclass(frozen=True)
class AssetRegister:
    """Asset register for Scope 1 calculations."""

    organization_id: UUID
    asset_id: str
    asset_name: str
    asset_category: str  # e.g., "fleet", "generators", "refrigerants", "heating"
    fuel_type: Optional[str] = None  # e.g., "diesel", "natural_gas", "refrigerant_r410a"
    capacity: Optional[Decimal] = None
    capacity_unit: Optional[str] = None  # e.g., "kW", "liters", "kg"
    annual_consumption: Optional[Decimal] = None
    annual_consumption_unit: Optional[str] = None
    emission_factor: Optional[Decimal] = None  # tCO2e per unit
    acquisition_date: Optional[date] = None
    recorded_at: datetime = field(default_factory=lambda: datetime.utcnow())
    source_system: str = "ERP"
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


@dataclass
class ConnectionTestResult:
    """Result of an ERP connection test."""

    status: ConnectionStatus
    organization_id: UUID
    tested_at: datetime
    error_message: Optional[str] = None
    api_version: Optional[str] = None
    latency_ms: Optional[float] = None


class ERPConnector(ABC):
    """Abstract base class for ERP system connectors.

    All ERP adapters must implement this interface to ensure consistent
    data extraction for ESG+SCRM calculations.
    """

    organization_id: UUID
    credentials: EncryptedBlob

    def __init__(
        self,
        organization_id: UUID,
        credentials: EncryptedBlob,
    ) -> None:
        """Initialize the ERP connector.

        Args:
            organization_id: UUID of the organization connecting to the ERP.
            credentials: Encrypted credential blob. Never store or log this.
        """
        self.organization_id = organization_id
        self.credentials = credentials

    @abstractmethod
    async def test_connection(self) -> ConnectionTestResult:
        """Verify credentials and API access.

        Returns:
            ConnectionTestResult with status, latency, and any error details.
        """

    @abstractmethod
    async def extract_utility_expenses(
        self,
        start_date: date,
        end_date: date,
    ) -> list[UtilityRecord]:
        """Extract utility invoices: electricity, gas, water, waste.

        Args:
            start_date: Start of the extraction period.
            end_date: End of the extraction period.

        Returns:
            List of UtilityRecord objects for the period.
        """

    @abstractmethod
    async def extract_procurement_spend(
        self,
        category_codes: Optional[list[str]],
        start_date: date,
        end_date: date,
    ) -> list[SpendRecord]:
        """Extract purchase orders / invoices by spend category.

        Args:
            category_codes: Optional list of category codes to filter.
                           If None, extract all categories.
            start_date: Start of the extraction period.
            end_date: End of the extraction period.

        Returns:
            List of SpendRecord objects for the period.
        """

    @abstractmethod
    async def extract_production_volume(
        self,
        product_codes: Optional[list[str]],
        start_date: date,
        end_date: date,
    ) -> list[ProductionRecord]:
        """Extract units produced, raw material consumption.

        Args:
            product_codes: Optional list of product codes to filter.
                          If None, extract all products.
            start_date: Start of the extraction period.
            end_date: End of the extraction period.

        Returns:
            List of ProductionRecord objects for the period.
        """

    @abstractmethod
    async def extract_employee_data(self) -> EmployeeData:
        """Extract headcount, turnover, compensation bands (anonymized).

        Returns:
            EmployeeData with aggregated, anonymized HR metrics.
        """

    @abstractmethod
    async def extract_asset_register(self) -> AssetRegister:
        """Extract equipment list for Scope 1 calculations.

        Returns:
            AssetRegister with generator, fleet, and refrigerant assets.
        """

    async def close(self) -> None:
        """Clean up any resources held by the connector.

        Override this method to close HTTP sessions, database connections,
        or any other resources. Default implementation is a no-op.
        """
        pass
