"""
Rule-based ML supplier risk scoring system.

Scores suppliers 0-100 using weighted factors:
  - Risk tier (A/B/C)
  - Unacknowledged risk flags
  - Certification count (inverse)
  - Questionnaire status
  - Country risk

Weights are loaded from data/risk_weights.json and can be tuned
via train_weights() with corrective feedback.
"""

import json
import logging
from pathlib import Path
from typing import Any

from src.db.database import get_connection, release_connection, _fetchall, _fetchone

logger = logging.getLogger(__name__)

_WEIGHTS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "risk_weights.json"

DEFAULT_WEIGHTS = {
    "risk_tier": 0.30,
    "risk_flags": 0.25,
    "certifications": 0.15,
    "questionnaire": 0.15,
    "country": 0.15,
}

# Country codes used in seed data and their risk contribution (0-15 scale)
_COUNTRY_RISK = {
    "BD": 10,  # Bangladesh
    "IN": 5,  # India
    "VN": 8,  # Vietnam
    "TH": 6,  # Thailand
    "MM": 15,  # Myanmar
    "ID": 7,  # Indonesia
    "CN": 9,  # China
    "TR": 10,  # Turkey
    "KH": 12,  # Cambodia
    "PK": 14,  # Pakistan
}

_COUNTRY_RISK_CACHE: dict = {}
_COUNTRY_RISK_CACHE_LOADED = False


def _get_country_risk(country_code: str) -> float:
    """Return country risk score, defaulting to 15.0 (highest) for unknown codes."""
    global _COUNTRY_RISK_CACHE_LOADED
    if not _COUNTRY_RISK_CACHE_LOADED:
        global _COUNTRY_RISK_CACHE
        _COUNTRY_RISK_CACHE = _load_country_risk_from_db()
        _COUNTRY_RISK_CACHE_LOADED = True
    return _COUNTRY_RISK_CACHE.get(country_code.upper(), 15.0)


def _load_country_risk_from_db() -> dict[str, float]:
    """Load country risk scores from database (returns static dict for now)."""
    return _COUNTRY_RISK.copy()


# Risk tier base scores (0-60 scale, weighted by risk_tier weight)
_RISK_TIER_SCORES = {"A": 0, "B": 30, "C": 60}

# Questionnaire status scores (0-20 scale)
_QUESTIONNAIRE_SCORES = {
    "responded": 0,
    "pending": 10,
    "not_sent": 20,
    "overdue": 20,
}


def _load_weights() -> dict[str, float]:
    """Load weights from JSON file, falling back to defaults."""
    if _WEIGHTS_PATH.exists():
        try:
            with open(_WEIGHTS_PATH, "r") as f:
                weights = json.load(f)
            # Validate all expected keys present
            for key in DEFAULT_WEIGHTS:
                if key not in weights:
                    logger.warning("risk_predictor.missing_weight key=%s — using default", key)
                    weights[key] = DEFAULT_WEIGHTS[key]
            return weights
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("risk_predictor.weights_load_failed error=%s — using defaults", e)
    return DEFAULT_WEIGHTS.copy()


def _save_weights(weights: dict[str, float]) -> None:
    """Persist weights to JSON file."""
    _WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_WEIGHTS_PATH, "w") as f:
        json.dump(weights, f, indent=2)
    logger.info("risk_predictor.weights_saved path=%s", _WEIGHTS_PATH)


def _classify_score(score: float) -> str:
    """Convert 0-100 score to risk level label."""
    if score <= 25:
        return "low"
    if score <= 50:
        return "medium"
    if score <= 75:
        return "high"
    return "critical"


def _build_recommendation(score: float, factors: dict[str, Any]) -> str:
    """Generate a plain-language recommendation based on the score breakdown."""
    parts = []
    if factors.get("risk_tier_raw") == "C":
        parts.append("Supplier is in risk tier C — schedule a third-party audit immediately")
    elif factors.get("risk_tier_raw") == "B":
        parts.append("Supplier is in risk tier B — monitor and plan a follow-up assessment")

    if factors.get("risk_flags_count", 0) > 3:
        parts.append("High number of unacknowledged risk flags — escalate to procurement lead")
    elif factors.get("risk_flags_count", 0) > 0:
        parts.append("Outstanding risk flags require review and acknowledgment")

    if factors.get("cert_count", 0) == 0:
        parts.append(
            "No certifications on file — request ISO 14001 or equivalent compliance evidence"
        )
    elif factors.get("cert_count", 0) == 1:
        parts.append(
            "Only one certification — encourage additional certifications for risk reduction"
        )

    qs = factors.get("questionnaire_status_raw", "")
    if qs == "not_sent":
        parts.append("Questionnaire has not been sent — initiate outreach immediately")
    elif qs == "pending":
        parts.append("Questionnaire response pending — send a reminder")

    cr = factors.get("country_risk_raw", 0)
    if cr >= 12:
        parts.append("High country risk — evaluate alternative sourcing options")
    elif cr >= 8:
        parts.append("Moderate country risk — maintain monitoring of geopolitical conditions")

    if not parts:
        parts.append("Supplier risk is within acceptable thresholds — continue regular monitoring")

    return "; ".join(parts)


def predict_supplier_risk(supplier_id: str, org_id: str = "") -> dict[str, Any]:
    """Score a single supplier's risk from 0-100.

    Args:
        supplier_id: The supplier's primary key (e.g. "sup_001").
        org_id: Optional org filter for multi-tenant queries.

    Returns:
        Dict with supplier_id, risk_score (0-100), risk_level, factors breakdown,
        and a recommendation string.
    """
    conn = get_connection()

    # Fetch supplier row
    query = "SELECT * FROM suppliers WHERE id = ?"
    params: tuple = (supplier_id,)
    if org_id:
        query += " AND org_id = ?"
        params = (supplier_id, org_id)

    supplier = _fetchone(conn, query, params)
    if supplier is None:
        release_connection(conn)
        return {
            "supplier_id": supplier_id,
            "error": "Supplier not found",
            "risk_score": None,
            "risk_level": None,
            "factors": {},
            "recommendation": "Supplier not found in database",
        }

    weights = _load_weights()

    # 1. Risk tier contribution (0 or 30 or 60, weighted)
    risk_tier = supplier.get("risk_tier") or "A"
    risk_tier_raw = _RISK_TIER_SCORES.get(risk_tier, 0)
    risk_tier_score = risk_tier_raw * weights["risk_tier"]

    # 2. Unacknowledged risk flags — count flags linked to this supplier's org
    #    The risk_flags table uses org_id, not supplier_id directly.
    #    We count unacknowledged flags for the supplier's org.
    flag_query = "SELECT COUNT(*) as cnt FROM risk_flags WHERE acknowledged = 0"
    flag_params: list[Any] = []
    supplier_org = supplier.get("org_id") or org_id
    if supplier_org:
        flag_query += " AND org_id = ?"
        flag_params.append(supplier_org)

    flag_row = _fetchone(conn, flag_query, tuple(flag_params))
    risk_flags_count = flag_row["cnt"] if flag_row else 0
    # Cap at 5 flags contributing 5 points each = 25 max
    risk_flags_raw = min(risk_flags_count * 5, 25)
    risk_flags_score = risk_flags_raw * weights["risk_flags"]

    # 3. Certification count (inverse: 0 certs = 10, 1 = 5, 2+ = 0)
    certs_raw = supplier.get("certifications") or ""
    cert_list = [c.strip() for c in certs_raw.split(",") if c.strip()]
    cert_count = len(cert_list)
    if cert_count == 0:
        cert_raw_score = 10
    elif cert_count == 1:
        cert_raw_score = 5
    else:
        cert_raw_score = 0
    cert_score = cert_raw_score * weights["certifications"]

    # 4. Questionnaire status
    qs_raw = supplier.get("questionnaire_status") or "not_sent"
    qs_raw_score = _QUESTIONNAIRE_SCORES.get(qs_raw, 20)
    qs_score = qs_raw_score * weights["questionnaire"]

    # 5. Country risk
    country_code = supplier.get("country") or ""
    country_risk_raw = _COUNTRY_RISK.get(country_code, 15)
    country_score = country_risk_raw * weights["country"]

    release_connection(conn)

    # Weighted sum — normalize to 0-100 scale
    # Max possible raw weighted sum = 60*0.3 + 25*0.25 + 10*0.15 + 20*0.15 + 15*0.15
    # = 18 + 6.25 + 1.5 + 3 + 2.25 = 31
    # We scale to 100 by dividing by the max and multiplying by 100
    max_weighted = (
        60 * weights["risk_tier"]
        + 25 * weights["risk_flags"]
        + 10 * weights["certifications"]
        + 20 * weights["questionnaire"]
        + 15 * weights["country"]
    )
    raw_total = risk_tier_score + risk_flags_score + cert_score + qs_score + country_score
    risk_score = round((raw_total / max_weighted) * 100, 1) if max_weighted > 0 else 0.0
    risk_score = min(max(risk_score, 0.0), 100.0)

    risk_level = _classify_score(risk_score)

    factors = {
        "risk_tier_raw": risk_tier,
        "risk_tier_contribution": round(risk_tier_score, 2),
        "risk_flags_count": risk_flags_count,
        "risk_flags_contribution": round(risk_flags_score, 2),
        "cert_count": cert_count,
        "certifications": cert_list,
        "cert_contribution": round(cert_score, 2),
        "questionnaire_status_raw": qs_raw,
        "questionnaire_contribution": round(qs_score, 2),
        "country_risk_raw": country_risk_raw,
        "country_contribution": round(country_score, 2),
        "weights_used": weights,
    }

    recommendation = _build_recommendation(risk_score, factors)

    return {
        "supplier_id": supplier_id,
        "supplier_name": supplier.get("name", ""),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "factors": factors,
        "recommendation": recommendation,
    }


def batch_predict(org_id: str = "") -> list[dict[str, Any]]:
    """Run risk prediction for all suppliers, sorted by risk_score descending.

    Args:
        org_id: Optional org filter for multi-tenant queries.

    Returns:
        List of prediction dicts, highest risk first.
    """
    conn = get_connection()
    query = "SELECT id FROM suppliers"
    params: tuple = ()
    if org_id:
        query += " WHERE org_id = ?"
        params = (org_id,)
    query += " ORDER BY name"

    rows = _fetchall(conn, query, params)
    release_connection(conn)

    results = []
    for row in rows:
        prediction = predict_supplier_risk(row["id"], org_id=org_id)
        results.append(prediction)

    results.sort(key=lambda r: r.get("risk_score", 0) or 0, reverse=True)
    return results


def train_weights(feedback: list[dict[str, Any]]) -> dict[str, Any]:
    """Adjust scoring weights using simple gradient descent from corrective feedback.

    Each feedback entry should contain:
      - supplier_id: str
      - expected_level: "low" | "medium" | "high" | "critical"

    The function computes the error between predicted and expected levels,
    then nudges the weight of the factor contributing most to the error.

    Args:
        feedback: List of correction dicts.

    Returns:
        Dict with the new weights, number of corrections applied, and details.
    """
    LEVEL_NUMERIC = {"low": 12.5, "medium": 37.5, "high": 62.5, "critical": 87.5}

    weights = _load_weights()
    learning_rate = 0.02
    adjustments = []

    for entry in feedback:
        supplier_id = entry.get("supplier_id", "")
        expected_level = entry.get("expected_level", "")

        if not supplier_id or expected_level not in LEVEL_NUMERIC:
            logger.warning(
                "risk_predictor.train_skip supplier_id=%s expected_level=%s — invalid",
                supplier_id,
                expected_level,
            )
            continue

        prediction = predict_supplier_risk(supplier_id)
        if prediction.get("risk_score") is None:
            continue

        predicted_score = prediction["risk_score"]
        expected_score = LEVEL_NUMERIC[expected_level]
        error = predicted_score - expected_score

        if abs(error) < 1.0:
            adjustments.append(
                {
                    "supplier_id": supplier_id,
                    "predicted": predicted_score,
                    "expected": expected_score,
                    "error": round(error, 2),
                    "adjustment": "none — within tolerance",
                }
            )
            continue

        # Find which factor is most over/under-contributing
        factors = prediction.get("factors", {})
        contributions = {
            "risk_tier": factors.get("risk_tier_contribution", 0),
            "risk_flags": factors.get("risk_flags_contribution", 0),
            "certifications": factors.get("cert_contribution", 0),
            "questionnaire": factors.get("questionnaire_contribution", 0),
            "country": factors.get("country_contribution", 0),
        }

        # The factor with the largest absolute contribution is the primary lever
        dominant_factor = max(contributions, key=contributions.get)

        # If predicted is too high, reduce the dominant factor's weight; otherwise increase
        delta = -learning_rate if error > 0 else learning_rate
        old_weight = weights[dominant_factor]
        weights[dominant_factor] = round(max(0.05, min(0.60, old_weight + delta)), 4)

        adjustments.append(
            {
                "supplier_id": supplier_id,
                "predicted": predicted_score,
                "expected": expected_score,
                "error": round(error, 2),
                "adjusted_factor": dominant_factor,
                "weight_before": old_weight,
                "weight_after": weights[dominant_factor],
            }
        )

    # Renormalize weights so they sum to 1.0
    total = sum(weights.values())
    if total > 0:
        for key in weights:
            weights[key] = round(weights[key] / total, 4)

    _save_weights(weights)

    return {
        "weights": weights,
        "corrections_applied": len([a for a in adjustments if a.get("adjusted_factor")]),
        "total_feedback": len(feedback),
        "adjustments": adjustments,
    }
