"""Tests for Scope3Calculator and related functions."""

import sys

sys.path.insert(0, "src")

from decimal import Decimal
from datetime import datetime
import pytest

from src.supplier.scope3_calculator import (
    Confidence,
    DataPoint,
    EmissionFactor,
    INDUSTRY_BENCHMARKS,
    Scope3Calculator,
    Scope3Category,
    Supplier,
    SupplierResponse,
    calculate_response_rate,
    is_response_above_threshold,
)
from src.supplier.nlu_parser import NLUParser, ParsedResponse, ParsedAnswer, ConfidenceLevel


class TestScope3Calculator:
    """Tests for Scope3Calculator class."""

    def setup_method(self):
        """Set up calculator for each test."""
        self.calculator = Scope3Calculator()
        self.supplier = Supplier(
            supplier_id="sup_001",
            name="Test Supplier",
            industry="textile",
            country="BD",
            annual_revenue_usd=Decimal("100000"),
            employee_count=100,
        )

    def test_calculator_initialization(self):
        """Test Scope3Calculator initializes with default emission factors."""
        assert len(self.calculator._emission_factors) > 0
        assert "electricity_kwh" in self.calculator._emission_factors

    def test_get_emission_factor(self):
        """Test get_emission_factor returns factor when exists."""
        factor = self.calculator.get_emission_factor("electricity_kwh")
        assert factor is not None
        assert factor.id == "default_electricity_kwh"
        assert factor.factor_group == "CATEGORY_1"

    def test_get_emission_factor_nonexistent(self):
        """Test get_emission_factor returns None for nonexistent factor."""
        factor = self.calculator.get_emission_factor("nonexistent")
        assert factor is None

    def test_add_emission_factor(self):
        """Test add_emission_factor adds or updates factor."""
        new_factor = EmissionFactor(
            id="custom_factor",
            factor_group="CATEGORY_1",
            unit="kg",
            value=Decimal("0.5"),
            source="Custom",
        )
        self.calculator.add_emission_factor(new_factor)
        retrieved = self.calculator.get_emission_factor("custom_factor")
        assert retrieved is not None
        assert retrieved.value == Decimal("0.5")

    @pytest.mark.asyncio
    async def test_calculate_scope3_from_response_valid_spend(self):
        """Test calculate_scope3_from_response with valid spend and HIGH confidence response."""
        parser = NLUParser()
        questions = [
            type(
                "Question",
                (),
                {
                    "question_id": "q1",
                    "question_number": 1,
                    "question_text": "Electricity",
                    "expected_unit": "kWh",
                },
            )()
        ]
        parsed = parser.parse_response("1. 1000 kWh", questions)

        response = SupplierResponse(
            supplier_id="sup_001",
            questionnaire_id="qnr_001",
            responses=parsed,
            received_at=datetime.utcnow().isoformat(),
        )

        result = await self.calculator.calculate_scope3_from_response(response)

        assert result is not None
        assert result.metric_name == "scope3_emissions"
        # 1000 kWh * 0.5 kgCO2/kWh = 500 kgCO2e
        assert result.value == Decimal("500")
        assert result.unit == "kgCO2e"

    @pytest.mark.asyncio
    async def test_calculate_scope3_from_response_medium_confidence(self):
        """Test calculate_scope3_from_response with MEDIUM confidence (needs conversion)."""
        parser = NLUParser()
        questions = [
            type(
                "Question",
                (),
                {
                    "question_id": "q1",
                    "question_number": 1,
                    "question_text": "Electricity",
                    "expected_unit": "kWh",
                },
            )()
        ]
        # Response in MWh needs conversion to kWh
        parsed = parser.parse_response("1. 2 MWh", questions)

        response = SupplierResponse(
            supplier_id="sup_001",
            questionnaire_id="qnr_001",
            responses=parsed,
            received_at=datetime.utcnow().isoformat(),
        )

        result = await self.calculator.calculate_scope3_from_response(response)

        assert result is not None
        assert result.confidence == Confidence.MEDIUM
        # 2 MWh = 2000 kWh * 0.5 = 1000 kgCO2e
        assert result.value == Decimal("1000")

    def test_estimate_scope3_supplier_returns_estimate(self):
        """Test estimate_scope3_supplier returns a DataPoint estimate."""
        result = self.calculator.estimate_scope3_supplier(
            supplier=self.supplier,
            category=Scope3Category.CATEGORY_1,
        )

        assert result is not None
        assert result.metric_name == "scope3_emissions_estimated"
        assert result.unit == "kgCO2e"
        # textile industry: scope3_per_revenue_usd = 0.15
        # 100000 USD * 0.15 = 15000
        assert result.value == Decimal("15000")
        assert result.confidence == Confidence.MEDIUM

    def test_estimate_scope3_supplier_employee_based(self):
        """Test estimate_scope3_supplier with employee count instead of revenue."""
        supplier_no_revenue = Supplier(
            supplier_id="sup_002",
            name="Small Supplier",
            industry="textile",
            country="BD",
            annual_revenue_usd=None,
            employee_count=50,
        )

        result = self.calculator.estimate_scope3_supplier(
            supplier=supplier_no_revenue,
            category=Scope3Category.CATEGORY_1,
        )

        assert result is not None
        # 50 workers * 5000 kWh/worker * 0.5 kgCO2/kWh = 125000
        assert result.value == Decimal("125000")
        assert result.confidence == Confidence.MEDIUM
        assert result.methodology == "activity_based"

    def test_estimate_scope3_supplier_no_data(self):
        """Test estimate_scope3_supplier with no revenue or employee data."""
        supplier_no_data = Supplier(
            supplier_id="sup_003",
            name="Unknown Supplier",
            industry="textile",
            country="BD",
            annual_revenue_usd=None,
            employee_count=None,
        )

        result = self.calculator.estimate_scope3_supplier(
            supplier=supplier_no_data,
            category=Scope3Category.CATEGORY_1,
        )

        assert result.value == Decimal("0")
        assert result.confidence == Confidence.LOW
        assert result.methodology == "no_data"

    def test_estimate_scope3_with_default_industry(self):
        """Test estimate_scope3_supplier uses default benchmark for unknown industry."""
        supplier = Supplier(
            supplier_id="sup_004",
            name="Unknown Industry Supplier",
            industry="unknown_industry",
            country="BD",
            annual_revenue_usd=Decimal("10000"),
            employee_count=None,
        )

        result = self.calculator.estimate_scope3_supplier(
            supplier=supplier,
            category=Scope3Category.CATEGORY_1,
        )

        # default benchmark: scope3_per_revenue_usd = 0.12
        assert result.value == Decimal("1200")


class TestDataPoint:
    """Tests for DataPoint dataclass."""

    def test_datapoint_to_dict(self):
        """Test DataPoint.to_dict() method."""
        dp = DataPoint(
            metric_name="scope3_emissions",
            value=Decimal("1000"),
            unit="kgCO2e",
            confidence=Confidence.HIGH,
            source="test",
            timestamp="2024-01-01T00:00:00",
            methodology="test",
        )

        d = dp.to_dict()
        assert d["metric_name"] == "scope3_emissions"
        assert d["value"] == "1000"
        assert d["unit"] == "kgCO2e"
        assert d["confidence"] == "HIGH"


class TestIndustryBenchmarks:
    """Tests for INDUSTRY_BENCHMARKS constant."""

    def test_benchmarks_exist_for_known_industries(self):
        """Test benchmarks exist for key industries."""
        assert "textile" in INDUSTRY_BENCHMARKS
        assert "electronics" in INDUSTRY_BENCHMARKS
        assert "food" in INDUSTRY_BENCHMARKS
        assert "default" in INDUSTRY_BENCHMARKS

    def test_benchmarks_have_required_keys(self):
        """Test each benchmark has required metric keys."""
        for industry, benchmark in INDUSTRY_BENCHMARKS.items():
            assert "scope3_per_revenue_usd" in benchmark
            assert "energy_per_worker_kwh" in benchmark
            assert "water_per_worker_m3" in benchmark


class TestResponseRateTracking:
    """Tests for response rate tracking functions."""

    @pytest.mark.asyncio
    async def test_calculate_response_rate(self):
        """Test calculate_response_rate with valid inputs."""
        metrics = await calculate_response_rate(
            questions_sent=100,
            responses_received=60,
        )

        assert metrics.total_questions_sent == 100
        assert metrics.total_responses_received == 60
        assert metrics.response_rate == Decimal("60.0")

    @pytest.mark.asyncio
    async def test_calculate_response_rate_zero_questions(self):
        """Test calculate_response_rate with zero questions sent."""
        metrics = await calculate_response_rate(
            questions_sent=0,
            responses_received=0,
        )

        assert metrics.response_rate == Decimal("0")

    def test_is_response_above_threshold_true(self):
        """Test is_response_above_threshold returns True when thresholds met."""
        from src.supplier.scope3_calculator import ResponseRateMetrics

        metrics = ResponseRateMetrics(
            total_questions_sent=100,
            total_responses_received=80,
            total_complete_responses=80,
            response_rate=Decimal("80.0"),
            complete_response_rate=Decimal("100.0"),
        )

        assert is_response_above_threshold(metrics, 60.0, 80.0) is True

    def test_is_response_above_threshold_false_low_response_rate(self):
        """Test is_response_above_threshold returns False when response rate too low."""
        from src.supplier.scope3_calculator import ResponseRateMetrics

        metrics = ResponseRateMetrics(
            total_questions_sent=100,
            total_responses_received=50,
            total_complete_responses=50,
            response_rate=Decimal("50.0"),
            complete_response_rate=Decimal("100.0"),
        )

        assert is_response_above_threshold(metrics, 60.0, 80.0) is False

    def test_is_response_above_threshold_false_low_complete_rate(self):
        """Test is_response_above_threshold returns False when complete rate too low."""
        from src.supplier.scope3_calculator import ResponseRateMetrics

        metrics = ResponseRateMetrics(
            total_questions_sent=100,
            total_responses_received=80,
            total_complete_responses=60,
            response_rate=Decimal("80.0"),
            complete_response_rate=Decimal("75.0"),
        )

        assert is_response_above_threshold(metrics, 60.0, 80.0) is False
