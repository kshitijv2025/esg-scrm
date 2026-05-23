"""
DisclosurePackage dataclass for framework-specific ESG disclosures.

SPEC 01: https://github.com/kshitijv2025/esg-scrm/blob/main/specs/01-data-orchestration.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


class FrameworkType(Enum):
    """Supported ESG reporting frameworks."""

    CSRD = "CSRD"
    ISSB = "ISSB"
    GRI = "GRI"
    TCFD = "TCFD"


class DataPointType(Enum):
    """Canonical ESG data point types."""

    # Energy
    ENERGY_KWH = "energy_kwh"
    ENERGY_MJ = "energy_mj"

    # Emissions
    SCOPE1_TCO2E = "scope1_tco2e"
    SCOPE2_TCO2E = "scope2_tco2e"
    SCOPE3_TCO2E = "scope3_tco2e"
    EMISSIONS_TCO2E = "emissions_tco2e"

    # Water
    WATER_M3 = "water_m3"
    WASTE_M3 = "waste_m3"

    # Waste
    WASTE_KG = "waste_kg"
    HAZARDOUS_WASTE_KG = "hazardous_waste_kg"

    # Social
    EMPLOYEE_HEADCOUNT = "employee_headcount"
    EMPLOYEE_TURNOVER_RATE = "employee_turnover_rate"
    WORKING_HOURS_LOST = "working_hours_lost"
    INCIDENT_RATE = "incident_rate"

    # Governance
    BOARD_DIVERSITY_PCT = "board_diversity_pct"
    ESG_SPEND_USD = "esg_spend_usd"

    # Procurement
    PROCUREMENT_SPEND = "procurement_spend"
    RENEWABLE_SPEND_PCT = "renewable_spend_pct"


@dataclass(frozen=True)
class DataPoint:
    """Canonical ESG data point normalized from ERP data.

    A DataPoint is the universal currency across all framework mappers.
    """

    id: str  # e.g., "dp_en_001" — unique within organization
    organization_id: UUID
    data_point_type: DataPointType
    value: Decimal
    unit: str
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    period_start: date
    period_end: date
    recorded_at: datetime
    source_system: str = "ERP"
    source_record_id: Optional[str] = None  # Reference to raw ERP record
    calculation_method: Optional[str] = (
        None  # e.g., "direct_measurement", "activity_based", "spend_based"
    )
    emission_factor: Optional[Decimal] = None  # If applicable (tCO2e per unit)
    emission_factor_source: Optional[str] = None
    emission_factor_year: Optional[int] = None
    emission_factor_value: Optional[Decimal] = None  # Numeric emission factor value
    notes: Optional[str] = None
    upstream_data_points: list[str] = field(
        default_factory=list
    )  # References to upstream data point IDs
    reported_in_frameworks: list[str] = field(
        default_factory=list
    )  # Which frameworks this point was reported in
    reported_at: Optional[datetime] = None  # When data was reported
    reported_by: Optional[UUID] = None  # User who reported
    integration_id: Optional[UUID] = None  # FK to Integration
    extraction_timestamp: Optional[datetime] = None  # When data was extracted from source
    version: str = "1.0"  # Version identifier

    def __post_init__(self) -> None:
        """Validate the data point after initialization."""
        if self.period_end < self.period_start:
            raise ValueError(
                f"period_end ({self.period_end}) must not be before period_start ({self.period_start})"
            )
        if self.value < 0:
            raise ValueError(
                f"value ({self.value}) must not be negative for {self.data_point_type}"
            )

    @property
    def period_days(self) -> int:
        """Return the number of days in the reporting period."""
        return (self.period_end - self.period_start).days

    @property
    def annual_equivalent(self) -> Decimal:
        """Return annualized value if this is a partial-year period."""
        if self.period_days <= 0:
            return Decimal("0")
        days_in_year = Decimal("365")
        return (self.value * days_in_year) / Decimal(str(self.period_days))


@dataclass
class Gap:
    """Represents a data gap in a disclosure package."""

    gap_id: str
    data_point_type: DataPointType
    framework_disclosure_code: str
    description: str
    severity: str  # "HIGH", "MEDIUM", "LOW"
    suggested_improvement: Optional[str] = None
    covered_by_proxy: bool = False  # True if a proxy metric covers this gap


@dataclass
class ConfidenceSummary:
    """Summary of data confidence across a disclosure package."""

    high_pct: float  # Percentage of data points with HIGH confidence
    medium_pct: float  # Percentage of data points with MEDIUM confidence
    low_pct: float  # Percentage of data points with LOW confidence
    total_data_points: int

    def __post_init__(self) -> None:
        """Validate that percentages sum to 100."""
        if self.total_data_points == 0:
            return  # All zeros is valid when no data points exist
        total = self.high_pct + self.medium_pct + self.low_pct
        if abs(total - 100.0) > 0.01:
            raise ValueError(
                f"Confidence percentages must sum to 100, got {total}: "
                f"HIGH={self.high_pct}, MEDIUM={self.medium_pct}, LOW={self.low_pct}"
            )


@dataclass
class DisclosurePackage:
    """Framework-specific ESG disclosure package.

    Aggregates canonical DataPoints into a framework-specific disclosure
    suitable for regulatory filing or voluntary reporting.
    """

    framework: FrameworkType
    reporting_period: tuple[date, date]  # (start_date, end_date)
    organization_id: UUID
    data_points: list[DataPoint]
    generated_at: datetime
    confidence_summary: ConfidenceSummary
    gaps: list[Gap] = field(default_factory=list)
    disclosure_id: Optional[str] = None  # e.g., "CSRD-E1-2024-Q4"
    reporter_name: Optional[str] = None
    reviewer_name: Optional[str] = None
    approval_status: str = "draft"  # "draft", "reviewed", "approved", "filed"

    def __post_init__(self) -> None:
        """Validate the disclosure package."""
        start, end = self.reporting_period
        if end < start:
            raise ValueError(f"reporting_period end ({end}) must not be before start ({start})")
        if not self.data_points:
            logger.warning(
                "disclosure_package.empty",
                framework=self.framework.value,
                organization_id=str(self.organization_id),
            )

    @property
    def reporting_period_days(self) -> int:
        """Return the number of days in the reporting period."""
        start, end = self.reporting_period
        return (end - start).days

    @property
    def has_critical_gaps(self) -> bool:
        """Return True if any gap is marked HIGH severity."""
        return any(gap.severity == "HIGH" for gap in self.gaps)

    def is_complete(self) -> bool:
        """Return True when gaps list is empty AND data_points list is non-empty."""
        return len(self.gaps) == 0 and len(self.data_points) > 0

    def data_points_by_type(self, data_point_type: DataPointType) -> list[DataPoint]:
        """Return all data points of the given type."""
        return [dp for dp in self.data_points if dp.data_point_type == data_point_type]

    def add_data_point(self, data_point: DataPoint) -> None:
        """Add a data point to the package."""
        if data_point.organization_id != self.organization_id:
            raise ValueError(
                f"DataPoint organization_id ({data_point.organization_id}) does not match "
                f"package organization_id ({self.organization_id})"
            )
        self.data_points.append(data_point)

    def add_gap(self, gap: Gap) -> None:
        """Add a gap to the package."""
        self.gaps.append(gap)

    def rebuild_confidence_summary(self) -> None:
        """Recalculate confidence summary from current data_points."""
        if not self.data_points:
            self.confidence_summary = ConfidenceSummary(
                high_pct=0.0, medium_pct=0.0, low_pct=0.0, total_data_points=0
            )
            return

        total = len(self.data_points)
        high_count = sum(1 for dp in self.data_points if dp.confidence == "HIGH")
        medium_count = sum(1 for dp in self.data_points if dp.confidence == "MEDIUM")
        low_count = sum(1 for dp in self.data_points if dp.confidence == "LOW")

        self.confidence_summary = ConfidenceSummary(
            high_pct=round(high_count / total * 100, 2),
            medium_pct=round(medium_count / total * 100, 2),
            low_pct=round(low_count / total * 100, 2),
            total_data_points=total,
        )
