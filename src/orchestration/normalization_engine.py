"""
NormalizationEngine — transforms raw ERP data to canonical ESG DataPoints.

SPEC 01: https://github.com/kshitijv2025/esg-scrm/blob/main/specs/01-data-orchestration.md
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal

import structlog

from src.orchestration.disclosure_package import (
    DataPoint,
    DataPointType,
)
from src.orchestration.erp_connector import (
    ConfidenceLevel,
    EmployeeData,
    ProductionRecord,
    SpendRecord,
    UtilityRecord,
)

logger = structlog.get_logger(__name__)

# Default emission factors — sourced from DEFRA / GHG Protocol
# Override via ENVIRONMENT variables for organization-specific factors
DEFAULT_ELECTRICITY_EMISSION_FACTOR_KGCO2E_PER_KWH = Decimal(
    os.environ.get("ELECTRICITY_EMISSION_FACTOR_KGCO2E_PER_KWH", "0.212")
)  # UK 2023 grid average
DEFAULT_GAS_EMISSION_FACTOR_KGCO2E_PER_KWH = Decimal(
    os.environ.get("GAS_EMISSION_FACTOR_KGCO2E_PER_KWH", "0.202")
)
DEFAULT_WATER_EMISSION_FACTOR_KGCO2E_PER_M3 = Decimal(
    os.environ.get("WATER_EMISSION_FACTOR_KGCO2E_PER_M3", "0.344")
)
DEFAULT_DIESEL_EMISSION_FACTOR_LITERS = Decimal(
    os.environ.get("DIESEL_EMISSION_FACTOR_LITERS", "2.68")
)  # kgCO2e per liter


def _kgco2e_to_tco2e(kg: Decimal) -> Decimal:
    """Convert kgCO2e to tCO2e."""
    return (kg / Decimal("1000")).quantize(Decimal("0.0001"))


@dataclass
class NormalizationEngine:
    """Transforms raw ERP records into canonical ESG DataPoints.

    The engine applies emission factors and unit conversions to produce
    standardized data points suitable for framework mapping.
    """

    electricity_emission_factor: Decimal = DEFAULT_ELECTRICITY_EMISSION_FACTOR_KGCO2E_PER_KWH
    gas_emission_factor: Decimal = DEFAULT_GAS_EMISSION_FACTOR_KGCO2E_PER_KWH
    water_emission_factor: Decimal = DEFAULT_WATER_EMISSION_FACTOR_KGCO2E_PER_M3
    diesel_emission_factor: Decimal = DEFAULT_DIESEL_EMISSION_FACTOR_LITERS

    _counter: int = 0

    def _next_id(self, prefix: str) -> str:
        """Generate a unique data point ID."""
        self._counter += 1
        return f"dp_{prefix}_{self._counter:04d}"

    def normalize_utility_record(self, record: UtilityRecord, source: str = "ERP") -> DataPoint:
        """Normalize a utility record to an energy or water DataPoint.

        Transformation rules:
        - electricity → energy_kwh
        - gas → energy_kwh (converted from cubic meters if needed)
        - water → water_m3
        - waste → waste_kg
        - renewable → energy_kwh (zero-emission)

        Confidence: HIGH (direct meter/billing data)

        Args:
            record: The raw UtilityRecord from the ERP.
            source: Source system identifier.

        Returns:
            A canonical DataPoint for the utility type.
        """
        logger.info(
            "normalize_utility.start",
            utility_type=record.utility_type.value,
            organization_id=str(record.organization_id),
            quantity=str(record.quantity),
            unit=record.unit,
        )

        if record.utility_type.value == "electricity":
            # Electricity is already in kWh or converted
            data_point_type = DataPointType.ENERGY_KWH
            value = record.quantity
            unit = "kWh"
            # Calculate embedded emissions
            emissions_kg = record.quantity * self.electricity_emission_factor
            confidence = ConfidenceLevel.HIGH.value

        elif record.utility_type.value == "gas":
            # Gas may come in kWh or cubic meters
            # Assuming incoming is already in kWh equivalent
            data_point_type = DataPointType.ENERGY_KWH
            value = record.quantity
            unit = "kWh"
            emissions_kg = record.quantity * self.gas_emission_factor
            confidence = ConfidenceLevel.HIGH.value

        elif record.utility_type.value == "water":
            data_point_type = DataPointType.WATER_M3
            value = record.quantity
            unit = "m3"
            emissions_kg = record.quantity * self.water_emission_factor
            confidence = ConfidenceLevel.HIGH.value

        elif record.utility_type.value == "waste":
            data_point_type = DataPointType.WASTE_KG
            # Assume waste is already in kg
            value = record.quantity
            unit = "kg"
            emissions_kg = Decimal("0")  # Waste emissions calculated differently
            confidence = ConfidenceLevel.MEDIUM.value

        elif record.utility_type.value == "renewable":
            data_point_type = DataPointType.ENERGY_KWH
            value = record.quantity
            unit = "kWh"
            emissions_kg = Decimal("0")  # Zero emissions for renewable
            confidence = ConfidenceLevel.HIGH.value

        else:
            logger.warning(
                "normalize_utility.unknown_type",
                utility_type=record.utility_type.value,
            )
            raise ValueError(f"Unknown utility type: {record.utility_type}")

        # Override confidence based on source parameter
        source_lower = source.lower()
        if "meter" in source_lower or "direct" in source_lower:
            confidence = ConfidenceLevel.HIGH.value
        elif "estimate" in source_lower or "calculated" in source_lower:
            confidence = ConfidenceLevel.MEDIUM.value
        elif "spend" in source_lower or "extrapolat" in source_lower:
            confidence = ConfidenceLevel.LOW.value
        else:
            confidence = ConfidenceLevel.MEDIUM.value  # Default

        data_point = DataPoint(
            id=self._next_id(data_point_type.value[:2]),
            organization_id=record.organization_id,
            data_point_type=data_point_type,
            value=value,
            unit=unit,
            confidence=confidence,
            period_start=record.start_date,
            period_end=record.end_date,
            recorded_at=record.recorded_at,
            source_system=f"{source}:{record.source_system}",
            source_record_id=record.invoice_number,
            calculation_method="direct_measurement",
            emission_factor=emissions_kg / value if value > 0 else Decimal("0"),
            emission_factor_source="DEFRA 2023" if source == "ERP" else source,
            emission_factor_year=2023,
            notes=f"Utility invoice: {record.invoice_number}",
        )

        logger.info(
            "normalize_utility.complete",
            data_point_id=data_point.id,
            data_point_type=data_point_type.value,
            value=str(value),
            unit=unit,
            confidence=confidence,
        )

        return data_point

    def normalize_procurement_spend(
        self,
        record: SpendRecord,
        emission_factor: float,
        source: str = "ERP",
    ) -> DataPoint:
        """Normalize a procurement spend record to a Scope 3 emissions DataPoint.

        Spend-based emission calculation uses industry-average emission factors
        and spend data. Confidence is LOW due to methodological uncertainty.

        Args:
            record: The raw SpendRecord from the ERP.
            emission_factor: kgCO2e per USD spent (from EPA or DEFRA spend-based factors).
            source: Source system identifier.

        Returns:
            A canonical DataPoint for Scope 3 Category 1 (purchased goods/services).
        """
        logger.info(
            "normalize_procurement.start",
            category_code=record.category_code,
            amount=str(record.amount),
            currency=record.currency,
            organization_id=str(record.organization_id),
        )

        # Convert spend to tCO2e using spend-based emission factor
        # emission_factor is in kgCO2e per USD
        spend_usd = record.amount
        emissions_kg = spend_usd * Decimal(str(emission_factor))
        emissions_tco2e = _kgco2e_to_tco2e(emissions_kg)

        data_point = DataPoint(
            id=self._next_id("s3"),
            organization_id=record.organization_id,
            data_point_type=DataPointType.SCOPE3_TCO2E,
            value=emissions_tco2e,
            unit="tCO2e",
            confidence=ConfidenceLevel.LOW.value,
            period_start=record.purchase_date,
            period_end=record.purchase_date,
            recorded_at=record.recorded_at,
            source_system=f"{source}:{record.source_system}",
            source_record_id=record.purchase_order_number,
            calculation_method="spend_based",
            emission_factor=Decimal(str(emission_factor)),
            emission_factor_source="EPA EEIO" if source == "ERP" else source,
            emission_factor_year=2023,
            notes=f"Scope 3 Cat1: {record.category_description} from {record.vendor_name}",
        )

        logger.info(
            "normalize_procurement.complete",
            data_point_id=data_point.id,
            category=record.category_code,
            spend_usd=str(spend_usd),
            tco2e=str(emissions_tco2e),
            confidence=ConfidenceLevel.LOW.value,
        )

        return data_point

    def normalize_production_volume(
        self,
        record: ProductionRecord,
        source: str = "ERP",
    ) -> DataPoint:
        """Normalize a production record for emissions intensity calculations.

        Production volume is used as the denominator for emissions intensity
        metrics (e.g., tCO2e per unit produced).

        Confidence: HIGH (direct production records)

        Args:
            record: The raw ProductionRecord from the ERP.
            source: Source system identifier.

        Returns:
            A canonical DataPoint for production volume.
        """
        logger.info(
            "normalize_production.start",
            product_code=record.product_code,
            units_produced=str(record.units_produced),
            organization_id=str(record.organization_id),
        )

        data_point = DataPoint(
            id=self._next_id("pr"),
            organization_id=record.organization_id,
            data_point_type=DataPointType.ENERGY_KWH,  # Production volume is distinct but used with energy
            value=record.units_produced,
            unit=record.unit_of_measure,
            confidence=ConfidenceLevel.HIGH.value,
            period_start=record.production_date,
            period_end=record.production_date,
            recorded_at=record.recorded_at,
            source_system=f"{source}:{record.source_system}",
            source_record_id=record.product_code,
            calculation_method="direct_measurement",
            notes=f"Production: {record.product_name} ({record.product_code})",
        )

        logger.info(
            "normalize_production.complete",
            data_point_id=data_point.id,
            product_code=record.product_code,
            units=str(record.units_produced),
            unit=record.unit_of_measure,
        )

        return data_point

    def normalize_employee_data(
        self,
        record: EmployeeData,
        source: str = "ERP",
    ) -> list[DataPoint]:
        """Normalize employee data into social DataPoints.

        Returns multiple DataPoints covering headcount, turnover, and
        compensation metrics.

        Confidence: MEDIUM (HR system data, anonymized bands)

        Args:
            record: The raw EmployeeData from the ERP.
            source: Source system identifier.

        Returns:
            List of canonical DataPoints for social metrics.
        """
        logger.info(
            "normalize_employee.start",
            organization_id=str(record.organization_id),
            headcount=record.total_headcount,
        )

        data_points = []

        # Headcount DataPoint
        headcount_dp = DataPoint(
            id=self._next_id("em"),
            organization_id=record.organization_id,
            data_point_type=DataPointType.EMPLOYEE_HEADCOUNT,
            value=Decimal(str(record.total_headcount)),
            unit="people",
            confidence=ConfidenceLevel.MEDIUM.value,
            period_start=record.reporting_period_start,
            period_end=record.reporting_period_end,
            recorded_at=record.recorded_at,
            source_system=f"{source}:{record.source_system}",
            calculation_method="direct_measurement",
            notes="Total active headcount at period end",
        )
        data_points.append(headcount_dp)

        # Turnover rate DataPoint
        if record.total_headcount > 0:
            turnover_rate = Decimal(str(record.departures)) / Decimal(str(record.total_headcount))
        else:
            turnover_rate = Decimal("0")

        turnover_dp = DataPoint(
            id=self._next_id("tr"),
            organization_id=record.organization_id,
            data_point_type=DataPointType.EMPLOYEE_TURNOVER_RATE,
            value=turnover_rate.quantize(Decimal("0.0001")),
            unit="ratio",
            confidence=ConfidenceLevel.MEDIUM.value,
            period_start=record.reporting_period_start,
            period_end=record.reporting_period_end,
            recorded_at=record.recorded_at,
            source_system=f"{source}:{record.source_system}",
            calculation_method="activity_based",
            notes=f"Departures: {record.departures}, New hires: {record.new_hires}",
        )
        data_points.append(turnover_dp)

        logger.info(
            "normalize_employee.complete",
            data_points_count=len(data_points),
            organization_id=str(record.organization_id),
        )

        return data_points
