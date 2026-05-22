"""
Scope 3 Emissions Calculator for supplier responses.

Calculates Scope 3 emissions from supplier questionnaire responses
using emission factors and industry benchmarks.
"""

import structlog
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.supplier.nlu_parser import ParsedResponse, ParsedAnswer

logger = structlog.get_logger(__name__)


class Confidence(str):
    """Confidence level for calculated data points."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class EmissionFactor:
    """Emission factor for calculating emissions."""

    id: str
    factor_group: str
    unit: str
    value: Decimal
    source: str
    year: Optional[int] = None
    applies_to: Optional[str] = None
    confidence: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


@dataclass
class Scope3Category:
    """Scope 3 emission category (GHG Protocol categories)."""

    CATEGORY_1 = "purchased_goods"
    CATEGORY_2 = "capital_goods"
    CATEGORY_3 = "fuel_and_energy"
    CATEGORY_4 = "upstream_transportation"
    CATEGORY_5 = "waste_generated"
    CATEGORY_6 = "business_travel"
    CATEGORY_7 = "employee_commuting"
    CATEGORY_8 = "upstream_leasing"
    CATEGORY_9 = "downstream_transportation"
    CATEGORY_10 = "processing_sold"
    CATEGORY_11 = "use_of_sold"
    CATEGORY_12 = "end_of_life"
    CATEGORY_13 = "downstream_leasing"
    CATEGORY_14 = "franchises"
    CATEGORY_15 = "investments"


# Default emission factors by category (kg CO2 per unit)
DEFAULT_EMISSION_FACTORS: dict[str, tuple[str, Decimal]] = {
    "electricity_kwh": ("CATEGORY_1", Decimal("0.5")),
    "natural_gas_m3": ("CATEGORY_1", Decimal("2.0")),
    "diesel_liter": ("CATEGORY_1", Decimal("2.68")),
    "gasoline_liter": ("CATEGORY_1", Decimal("2.31")),
    "water_m3": ("CATEGORY_1", Decimal("0.344")),
    "waste_tonne": ("CATEGORY_5", Decimal("0.521")),
    "business_travel_km": ("CATEGORY_6", Decimal("0.255")),
    "employee_commuting_km": ("CATEGORY_7", Decimal("0.171")),
}

INDUSTRY_BENCHMARKS: dict[str, dict[str, Decimal]] = {
    "textile": {
        "scope3_per_revenue_usd": Decimal("0.15"),
        "energy_per_worker_kwh": Decimal("5000"),
        "water_per_worker_m3": Decimal("200"),
    },
    "electronics": {
        "scope3_per_revenue_usd": Decimal("0.08"),
        "energy_per_worker_kwh": Decimal("8000"),
        "water_per_worker_m3": Decimal("150"),
    },
    "food": {
        "scope3_per_revenue_usd": Decimal("0.25"),
        "energy_per_worker_kwh": Decimal("3000"),
        "water_per_worker_m3": Decimal("500"),
    },
    "default": {
        "scope3_per_revenue_usd": Decimal("0.12"),
        "energy_per_worker_kwh": Decimal("4000"),
        "water_per_worker_m3": Decimal("250"),
    },
}


@dataclass
class Supplier:
    """Minimal supplier information for scope 3 estimation."""

    supplier_id: str
    name: str
    industry: str
    country: str
    annual_revenue_usd: Optional[Decimal] = None
    employee_count: Optional[int] = None
    organization_id: Optional[str] = None
    tier: Optional[str] = None  # tier1, tier2, tier3
    relationship_status: Optional[str] = None
    whatsapp_number: Optional[str] = None
    line_id: Optional[str] = None
    wechat_id: Optional[str] = None
    preferred_channel: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class DataPoint:
    """A calculated data point with metadata."""

    metric_name: str
    value: Decimal
    unit: str
    confidence: str
    source: str
    timestamp: str
    methodology: str
    emission_factor_id: Optional[str] = None
    raw_value: Optional[Decimal] = None
    category: Optional[str] = None
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "value": str(self.value),
            "unit": self.unit,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp,
            "methodology": self.methodology,
            "emission_factor_id": self.emission_factor_id,
            "raw_value": str(self.raw_value) if self.raw_value else None,
            "category": self.category,
            "metadata": self.metadata,
        }


@dataclass
class SupplierResponse:
    """A supplier's questionnaire response."""

    id: Optional[str] = None  # UUID as string, primary key
    supplier_id: str = ""
    questionnaire_id: str = ""
    responses: Optional[ParsedResponse] = None
    received_at: str = ""
    question_id: Optional[str] = None
    response_value: Optional[str] = None
    confidence: Optional[str] = None  # ENUM HIGH, MEDIUM, LOW
    submitted_via: Optional[str] = None
    submitted_at: Optional[datetime] = None
    validated: bool = False
    validated_by: Optional[str] = None


class Scope3Calculator:
    """Calculator for Scope 3 emissions from supplier data.

    Uses emission factors and industry benchmarks to estimate
    Scope 3 emissions when direct data is unavailable.
    """

    def __init__(self):
        """Initialize the Scope 3 calculator."""
        self._emission_factors: dict[str, EmissionFactor] = {}
        self._load_default_factors()
        logger.info("scope3_calculator.initialized")

    def _load_default_factors(self) -> None:
        """Load default emission factors."""
        for key, (factor_group, value) in DEFAULT_EMISSION_FACTORS.items():
            factor = EmissionFactor(
                id=f"default_{key}",
                factor_group=factor_group,
                unit=key.split("_")[-1] if "_" in key else key,
                value=value,
                source="GHG Protocol / DEFRA",
            )
            self._emission_factors[key] = factor

    def get_emission_factor(self, metric_name: str) -> Optional[EmissionFactor]:
        """Get an emission factor by metric name."""
        return self._emission_factors.get(metric_name)

    def add_emission_factor(self, factor: EmissionFactor) -> None:
        """Add or update an emission factor."""
        self._emission_factors[factor.id] = factor
        logger.info("scope3.emission_factor_added", factor_id=factor.id)

    async def calculate_scope3_from_response(
        self,
        response: SupplierResponse,
        emission_factor: Optional[EmissionFactor] = None,
    ) -> Optional[DataPoint]:
        """Calculate Scope 3 from a supplier response.

        Args:
            response: The supplier's questionnaire response.
            emission_factor: Optional specific emission factor to use.

        Returns:
            DataPoint with calculated Scope 3 value and confidence, or None if calculation not possible.

        Confidence scoring:
        - HIGH: numeric response with standard unit
        - MEDIUM: spend-based with reliable spend data
        - LOW: estimate or ambiguous
        """
        supplier_id = response.supplier_id
        parsed = response.responses

        logger.info(
            "scope3.calculate.start",
            supplier_id=supplier_id,
            answer_count=len(parsed.answers),
        )

        high_confidence = parsed.get_high_confidence_answers()
        if high_confidence:
            for answer in high_confidence:
                if answer.normalized_value is not None and answer.normalized_unit:
                    data_point = await self._calculate_from_numeric_answer(
                        answer=answer,
                        supplier_id=supplier_id,
                        emission_factor=emission_factor,
                    )
                    if data_point:
                        logger.info(
                            "scope3.calculate.high_confidence",
                            supplier_id=supplier_id,
                            value=str(data_point.value),
                            unit=data_point.unit,
                        )
                        return data_point

        medium_confidence = parsed.get_medium_confidence_answers()
        if medium_confidence:
            for answer in medium_confidence:
                if answer.normalized_value is not None and answer.normalized_unit:
                    data_point = await self._calculate_from_numeric_answer(
                        answer=answer,
                        supplier_id=supplier_id,
                        emission_factor=emission_factor,
                    )
                    if data_point:
                        data_point.confidence = Confidence.MEDIUM
                        logger.info(
                            "scope3.calculate.medium_confidence",
                            supplier_id=supplier_id,
                            value=str(data_point.value),
                            unit=data_point.unit,
                        )
                        return data_point

        logger.warning(
            "scope3.calculate.no_numeric",
            supplier_id=supplier_id,
            low_confidence_count=len(parsed.get_low_confidence_answers()),
        )
        return None

    async def _calculate_from_numeric_answer(
        self,
        answer: ParsedAnswer,
        supplier_id: str,
        emission_factor: Optional[EmissionFactor] = None,
    ) -> Optional[DataPoint]:
        """Calculate Scope 3 from a single numeric answer."""
        if answer.normalized_value is None or answer.normalized_unit is None:
            return None

        value = answer.normalized_value
        unit = answer.normalized_unit

        factor_key = None
        if "kwh" in unit.lower() or "mwh" in unit.lower():
            factor_key = "electricity_kwh"
        elif "m3" in unit.lower() or "liter" in unit.lower():
            factor_key = "natural_gas_m3"

        if factor_key and factor_key in self._emission_factors:
            factor = emission_factor or self._emission_factors[factor_key]
            calculated_value = value * factor.value

            return DataPoint(
                metric_name="scope3_emissions",
                value=calculated_value,
                unit="kgCO2e",
                confidence=answer.confidence,
                source=f"supplier_response_{supplier_id}",
                timestamp=datetime.utcnow().isoformat(),
                methodology="emission_factor",
                emission_factor_id=factor.id,
                raw_value=value,
                category=factor.factor_group,
                metadata={
                    "answer_question_number": answer.question_number,
                    "original_unit": answer.unit,
                    "normalized_unit": answer.normalized_unit,
                },
            )

        return None

    def estimate_scope3_supplier(
        self,
        supplier: Supplier,
        category: Scope3Category,
        last_response: Optional[SupplierResponse] = None,
    ) -> DataPoint:
        """Estimate Scope 3 using industry benchmarks.

        This is a fallback when direct supplier data is unavailable.

        Args:
            supplier: The supplier to estimate emissions for.
            category: The Scope 3 category to estimate.
            last_response: Previous response data (optional).

        Returns:
            DataPoint with estimated Scope 3 value.
        """
        industry = supplier.industry.lower() if supplier.industry else "default"
        benchmark = INDUSTRY_BENCHMARKS.get(industry, INDUSTRY_BENCHMARKS["default"])

        if supplier.annual_revenue_usd:
            scope3_per_revenue = benchmark["scope3_per_revenue_usd"]
            estimated_value = supplier.annual_revenue_usd * scope3_per_revenue
            methodology = "spend_based"
            confidence = Confidence.MEDIUM
        elif supplier.employee_count:
            energy_per_worker = benchmark["energy_per_worker_kwh"]
            factor = self._emission_factors.get("electricity_kwh")
            if factor:
                estimated_value = (
                    Decimal(supplier.employee_count) * energy_per_worker * factor.value
                )
                methodology = "activity_based"
                confidence = Confidence.MEDIUM
            else:
                estimated_value = Decimal("0")
                methodology = "fallback"
                confidence = Confidence.LOW
        else:
            estimated_value = Decimal("0")
            methodology = "no_data"
            confidence = Confidence.LOW

        logger.info(
            "scope3.estimate",
            supplier_id=supplier.supplier_id,
            industry=industry,
            estimated_value=str(estimated_value),
            methodology=methodology,
            confidence=confidence,
        )

        return DataPoint(
            metric_name="scope3_emissions_estimated",
            value=estimated_value,
            unit="kgCO2e",
            confidence=confidence,
            source=f"industry_benchmark_{industry}",
            timestamp=datetime.utcnow().isoformat(),
            methodology=methodology,
            category=category,
            metadata={
                "supplier_name": supplier.name,
                "industry": industry,
                "revenue_based": supplier.annual_revenue_usd is not None,
                "employee_based": supplier.employee_count is not None,
            },
        )


@dataclass
class ResponseRateMetrics:
    """Metrics for tracking supplier response rates."""

    total_questions_sent: int = 0
    total_responses_received: int = 0
    total_complete_responses: int = 0
    response_rate: Decimal = Decimal("0")
    complete_response_rate: Decimal = Decimal("0")
    avg_time_to_first_response_hours: Optional[float] = None
    avg_time_to_complete_days: Optional[float] = None


async def calculate_response_rate(
    questions_sent: int,
    responses_received: int,
) -> ResponseRateMetrics:
    """Calculate response rate metrics.

    Args:
        questions_sent: Total number of questions sent.
        responses_received: Number of responses received.

    Returns:
        ResponseRateMetrics with calculated rates.
    """
    metrics = ResponseRateMetrics(
        total_questions_sent=questions_sent,
        total_responses_received=responses_received,
    )

    if questions_sent > 0:
        rate = Decimal(responses_received) / Decimal(questions_sent) * Decimal("100")
        metrics.response_rate = rate.quantize(Decimal("0.1"))

    if responses_received > 0:
        complete_rate = (
            Decimal(metrics.total_complete_responses) / Decimal(responses_received) * Decimal("100")
        )
        metrics.complete_response_rate = complete_rate.quantize(Decimal("0.1"))

    logger.info(
        "response_rate.calculated",
        questions_sent=questions_sent,
        responses_received=responses_received,
        rate=float(metrics.response_rate),
    )

    return metrics


def is_response_above_threshold(
    metrics: ResponseRateMetrics,
    response_threshold: float = 60.0,
    complete_threshold: float = 80.0,
) -> bool:
    """Check if response rates meet targets.

    Args:
        metrics: The response rate metrics to check.
        response_threshold: Minimum response rate target (default 60%).
        complete_threshold: Minimum complete response rate target (default 80%).

    Returns:
        True if both thresholds are met.
    """
    rate_ok = float(metrics.response_rate) >= response_threshold
    complete_ok = float(metrics.complete_response_rate) >= complete_threshold

    return rate_ok and complete_ok
