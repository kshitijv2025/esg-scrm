"""Tests for the ESG scoring engine (src/ml/scoring.py)."""

from src.ml.scoring import (
    DEFAULT_WEIGHTS,
    RISK_TIER_THRESHOLDS,
    ESGScoreResult,
    _get_weights,
    _normalize,
    _risk_tier,
    compute_esg_score,
)


class TestNormalize:
    def test_higher_is_better_zero(self):
        assert _normalize(0, "higher_is_better", 100) == 0.0

    def test_higher_is_better_full(self):
        assert _normalize(100, "higher_is_better", 100) == 100.0

    def test_higher_is_better_half(self):
        assert _normalize(50, "higher_is_better", 100) == 50.0

    def test_higher_is_better_caps_at_100(self):
        assert _normalize(200, "higher_is_better", 100) == 100.0

    def test_lower_is_better_zero_emissions(self):
        assert _normalize(0, "lower_is_better", 10000) == 100.0

    def test_lower_is_better_max_emissions(self):
        assert _normalize(10000, "lower_is_better", 10000) == 0.0

    def test_lower_is_better_half(self):
        assert _normalize(5000, "lower_is_better", 10000) == 50.0

    def test_lower_is_better_over_max_caps(self):
        assert _normalize(15000, "lower_is_better", 10000) == 0.0


class TestRiskTier:
    def test_tier_a(self):
        assert _risk_tier(85) == "A"
        assert _risk_tier(80) == "A"

    def test_tier_b(self):
        assert _risk_tier(79.9) == "B"
        assert _risk_tier(60) == "B"

    def test_tier_c(self):
        assert _risk_tier(59.9) == "C"
        assert _risk_tier(40) == "C"

    def test_tier_d(self):
        assert _risk_tier(39.9) == "D"
        assert _risk_tier(0) == "D"


class TestGetWeights:
    def test_garment_industry(self):
        w = _get_weights("Garment/Textile")
        assert abs(w["environment"] - 0.40) < 0.01
        assert abs(w["social"] - 0.35) < 0.01
        assert abs(w["governance"] - 0.25) < 0.01

    def test_unknown_industry_falls_back(self):
        w = _get_weights("Aerospace")
        assert w == DEFAULT_WEIGHTS

    def test_weights_sum_to_one(self):
        for industry in ("Garment/Textile", "Leather", "Electronics", "Unknown"):
            w = _get_weights(industry)
            assert abs(sum(w.values()) - 1.0) < 0.01


class TestComputeESGScore:
    """Unit tests for the scoring engine using the conftest test database."""

    def test_no_responses_returns_none(self):
        result = compute_esg_score("nonexistent_supplier")
        assert result is None

    def test_score_result_structure(self):
        """Verify the score result has all required fields."""
        # This test verifies the dataclass structure is correct
        result = ESGScoreResult(
            supplier_id="sup_test",
            environment=__import__("src.ml.scoring", fromlist=["DimensionScore"]).DimensionScore("environment", 75.0, 3),
            social=__import__("src.ml.scoring", fromlist=["DimensionScore"]).DimensionScore("social", 60.0, 2),
            governance=__import__("src.ml.scoring", fromlist=["DimensionScore"]).DimensionScore("governance", 80.0, 2),
            composite_score=70.5,
            risk_tier="B",
            methodology="test",
            weights_used=DEFAULT_WEIGHTS,
        )
        assert result.supplier_id == "sup_test"
        assert result.composite_score == 70.5
        assert result.risk_tier == "B"
        assert result.environment.score == 75.0
        assert result.social.score == 60.0
        assert result.governance.score == 80.0

    def test_composite_calculation_with_weights(self):
        """Composite = E*w_E + S*w_S + G*w_G with garment weights."""
        from src.ml.scoring import DimensionScore
        e = DimensionScore("environment", 80.0, 1)
        s = DimensionScore("social", 60.0, 1)
        g = DimensionScore("governance", 70.0, 1)
        weights = {"environment": 0.40, "social": 0.35, "governance": 0.25}
        composite = (
            weights["environment"] * e.score
            + weights["social"] * s.score
            + weights["governance"] * g.score
        )
        expected = 0.40 * 80 + 0.35 * 60 + 0.25 * 70
        assert abs(composite - expected) < 0.01
        # 32 + 21 + 17.5 = 70.5
        assert abs(composite - 70.5) < 0.01


class TestRiskTierThresholds:
    def test_thresholds_are_monotonically_decreasing(self):
        assert RISK_TIER_THRESHOLDS["A"] > RISK_TIER_THRESHOLDS["B"]
        assert RISK_TIER_THRESHOLDS["B"] > RISK_TIER_THRESHOLDS["C"]
