"""
ESG Scoring Engine — weighted scoring methodology for supplier ESG assessment.

Computes E (Environment), S (Social), G (Governance) dimension scores from
Tier 1-4 questionnaire responses with configurable weights per industry.
Stores composite score in suppliers.esg_score and derives risk_tier (A/B/C/D).

This is THE output H&M consumes — without scores, the platform collects data
but cannot communicate results.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from src.db.database import _execute, _fetchall, get_connection, release_connection

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring configuration
# ---------------------------------------------------------------------------

RISK_TIER_THRESHOLDS = {"A": 80, "B": 60, "C": 40}
"""
A >= 80, B >= 40..80, C >= 40, D < 40.
"""

DEFAULT_WEIGHTS: dict[str, float] = {
    "environment": 0.40,
    "social": 0.35,
    "governance": 0.25,
}

INDUSTRY_WEIGHTS: dict[str, dict[str, float]] = {
    "Garment/Textile": {"environment": 0.40, "social": 0.35, "governance": 0.25},
    "Leather": {"environment": 0.45, "social": 0.30, "governance": 0.25},
    "Electronics": {"environment": 0.35, "social": 0.30, "governance": 0.35},
}

# Map question_id prefixes to E/S/G dimensions and scoring rules.
# Each entry: (dimension, scoring_method, max_possible_value)
# scoring_method: "lower_is_better" (emissions, waste), "higher_is_better" (renewable %, certifications)
QUESTION_SCORING: dict[str, tuple[str, str, float]] = {
    # Tier 1 — Environment
    "T1Q1": ("environment", "lower_is_better", 5_000_000),  # energy kWh
    "T1Q2": ("environment", "lower_is_better", 10_000),  # emissions tCO2e
    "T1Q3": ("environment", "higher_is_better", 100),  # water recycle %
    "T1Q7": ("environment", "higher_is_better", 5),  # certifications count
    # Tier 1 — Social
    "T1Q4": ("social", "higher_is_better", 3),  # labour policy completeness
    "T1Q5": ("social", "lower_is_better", 50),  # safety incidents
    # Tier 1 — Governance
    "T1Q6": ("governance", "higher_is_better", 3),  # governance completeness
    "T1Q8": ("governance", "higher_is_better", 3),  # corrective actions resolved
    # Tier 2 — Environment
    "T2Q1": ("environment", "lower_is_better", 5_000_000),  # energy kWh
    "T2Q2": ("environment", "lower_is_better", 10_000),  # emissions tCO2e
    "T2Q3": ("environment", "lower_is_better", 100_000),  # water m3
    "T2Q4": ("environment", "higher_is_better", 100),  # recycle rate %
    "T2Q5": ("environment", "higher_is_better", 3),  # certifications
    # Tier 3 — quick screening (count certifications, violations)
    "T3Q1": ("environment", "higher_is_better", 5),  # certifications
    "T3Q2": ("social", "lower_is_better", 10),  # violations
    "T3Q3": ("governance", "higher_is_better", 3),  # corrective actions
}


@dataclass
class DimensionScore:
    dimension: str
    score: float
    question_count: int
    contributions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ESGScoreResult:
    supplier_id: str
    environment: DimensionScore
    social: DimensionScore
    governance: DimensionScore
    composite_score: float
    risk_tier: str
    methodology: str
    weights_used: dict[str, float]


def _normalize(value: float, method: str, max_val: float) -> float:
    """Normalize a raw value to 0-100 scale."""
    if max_val <= 0:
        return 50.0
    if method == "higher_is_better":
        return min(100.0, max(0.0, (value / max_val) * 100))
    # lower_is_better — lower raw = higher score
    ratio = value / max_val
    return min(100.0, max(0.0, (1.0 - min(ratio, 1.0)) * 100))


def _get_weights(industry: str) -> dict[str, float]:
    """Return E/S/G weights for an industry, falling back to defaults."""
    return INDUSTRY_WEIGHTS.get(industry, DEFAULT_WEIGHTS)


def _risk_tier(score: float) -> str:
    """Convert composite score to A/B/C/D risk tier."""
    if score >= RISK_TIER_THRESHOLDS["A"]:
        return "A"
    if score >= RISK_TIER_THRESHOLDS["B"]:
        return "B"
    if score >= RISK_TIER_THRESHOLDS["C"]:
        return "C"
    return "D"


def compute_esg_score(
    supplier_id: str,
    industry: str = "",
    org_id: str = "",
) -> Optional[ESGScoreResult]:
    """Compute ESG score for a supplier from their questionnaire responses.

    Queries questionnaire_responses for the supplier, maps each response to
    an E/S/G dimension, normalizes to 0-100, applies industry weights, and
    returns the full scoring breakdown.
    """
    conn = get_connection()
    try:
        responses = _fetchall(
            conn,
            """
            SELECT question_id, response_value, response_text, tier
            FROM questionnaire_responses
            WHERE supplier_id = ?
            ORDER BY responded_at DESC
        """,
            (supplier_id,),
        )
    finally:
        release_connection(conn)

    if not responses:
        return None

    weights = _get_weights(industry)
    dimension_scores: dict[str, list[tuple[str, float, float]]] = {
        "environment": [],
        "social": [],
        "governance": [],
    }

    for r in responses:
        qid = r.get("question_id", "")
        rule = QUESTION_SCORING.get(qid)
        if rule is None:
            continue
        dimension, method, max_val = rule

        raw = r.get("response_value")
        if raw is None:
            # Try parsing response_text for a numeric value
            text = r.get("response_text", "")
            try:
                raw = float("".join(c for c in text if c.isdigit() or c == ".").strip() or "0")
            except ValueError:
                continue

        raw = float(raw)
        normalized = _normalize(raw, method, max_val)
        dimension_scores[dimension].append((qid, raw, normalized))

    dimensions: dict[str, DimensionScore] = {}
    for dim in ("environment", "social", "governance"):
        entries = dimension_scores[dim]
        if entries:
            avg = sum(e[2] for e in entries) / len(entries)
            contributions = [
                {"question_id": e[0], "raw_value": e[1], "normalized": round(e[2], 1)}
                for e in entries
            ]
            dimensions[dim] = DimensionScore(
                dimension=dim,
                score=round(avg, 1),
                question_count=len(entries),
                contributions=contributions,
            )
        else:
            dimensions[dim] = DimensionScore(
                dimension=dim,
                score=0.0,
                question_count=0,
            )

    composite = (
        weights["environment"] * dimensions["environment"].score
        + weights["social"] * dimensions["social"].score
        + weights["governance"] * dimensions["governance"].score
    )
    composite = round(composite, 1)
    tier = _risk_tier(composite)

    return ESGScoreResult(
        supplier_id=supplier_id,
        environment=dimensions["environment"],
        social=dimensions["social"],
        governance=dimensions["governance"],
        composite_score=composite,
        risk_tier=tier,
        methodology="Weighted average of E/S/G dimensions from questionnaire responses. "
        f"Industry: {industry or 'generic'}. "
        "Each response normalized to 0-100 using question-specific scoring rules.",
        weights_used=weights,
    )


def persist_score(supplier_id: str, result: ESGScoreResult) -> None:
    """Write computed score and risk tier back to the suppliers table."""
    conn = get_connection()
    try:
        _execute(
            conn,
            """
            UPDATE suppliers
            SET esg_score = ?, risk_tier = ?, updated_at = datetime('now')
            WHERE id = ?
        """,
            (result.composite_score, result.risk_tier, supplier_id),
        )
        logger.info(
            "esg.score.persisted supplier=%s score=%.1f tier=%s",
            supplier_id,
            result.composite_score,
            result.risk_tier,
        )
    finally:
        release_connection(conn)
