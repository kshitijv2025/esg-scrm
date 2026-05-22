"""
Supplier API — backed by SQLite database.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import require_role, VIEWER_ROLES, EDITOR_ROLES
from src.db.database import (
    fetch_suppliers,
    fetch_supplier,
    fetch_supplier_scope3,
    fetch_questionnaire_responses,
    fetch_coverage_stats,
    get_connection,
    release_connection,
    _fetchall,
)
from src.ml.scoring import compute_esg_score, persist_score

router = APIRouter()


@router.get("/")
def list_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    user: dict = Depends(require_auth),
):
    org_id = user["org_id"]
    suppliers = fetch_suppliers(org_id=org_id, skip=skip, limit=limit)
    return {"suppliers": suppliers, "total": len(suppliers)}


@router.get("/risk-ranked")
def get_risk_ranked(
    skip: int = 0,
    limit: int = 50,
    user: dict = Depends(require_auth),
):
    """Return suppliers sorted by composite risk score (ascending = lowest risk first)."""
    org_id = user["org_id"]
    suppliers = fetch_suppliers(org_id=org_id, skip=skip, limit=limit)
    ranked = sorted(suppliers, key=lambda s: s.get("risk_score", 0))
    return {"suppliers": ranked, "total": len(ranked)}


@router.get("/{supplier_id}")
def get_supplier(
    supplier_id: str,
    user: dict = Depends(require_auth),
):
    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="not found")
    if supplier.get("org_id") and supplier["org_id"] != user["org_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return supplier


@router.get("/{supplier_id}/score")
def get_supplier_score(
    supplier_id: str,
    user: dict = Depends(require_auth),
):
    """ESG score breakdown for a supplier (E/S/G dimensions + composite)."""
    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if supplier.get("org_id") and supplier["org_id"] != user["org_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = compute_esg_score(
        supplier_id=supplier_id,
        industry=supplier.get("industry", ""),
        org_id=user["org_id"],
    )
    if not result:
        raise HTTPException(status_code=404, detail="No questionnaire responses found for supplier")

    persist_score(supplier_id, result)

    return {
        "supplier_id": result.supplier_id,
        "composite_score": result.composite_score,
        "risk_tier": result.risk_tier,
        "environment": {
            "score": result.environment.score,
            "question_count": result.environment.question_count,
            "contributions": result.environment.contributions,
        },
        "social": {
            "score": result.social.score,
            "question_count": result.social.question_count,
            "contributions": result.social.contributions,
        },
        "governance": {
            "score": result.governance.score,
            "question_count": result.governance.question_count,
            "contributions": result.governance.contributions,
        },
        "methodology": result.methodology,
        "weights_used": result.weights_used,
    }


@router.get("/{supplier_id}/profile")
def get_supplier_profile(
    supplier_id: str,
    user: dict = Depends(require_auth),
):
    """Full ESG profile for a supplier."""
    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="not found")
    if supplier.get("org_id") and supplier["org_id"] != user["org_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    responses = fetch_questionnaire_responses(supplier_id)
    clusters = _compute_profile_clusters(responses)

    return {
        "supplier_id": supplier_id,
        "name": supplier["name"],
        "country": supplier["country"],
        "tier": supplier["tier"],
        "overall_risk_score": supplier.get("risk_score"),
        "risk_tier": supplier.get("risk_tier"),
        "financial_health_score": supplier.get("financial_health_score"),
        "scope3_coverage_pct": _compute_scope3_coverage(supplier, user["org_id"]),
        "traceability_status": "full_chain"
        if supplier.get("questionnaire_status") == "responded"
        else "partial",
        "active_flags": supplier.get("active_flags", 0),
        "certifications": (supplier.get("certifications") or "").split(",")
        if supplier.get("certifications")
        else [],
        "clusters": clusters,
        "ml_recommendations": _generate_recommendations(supplier, clusters),
    }


@router.get("/{supplier_id}/scope3")
def supplier_scope3(
    supplier_id: str,
    user: dict = Depends(require_auth),
):
    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="not found")
    if supplier.get("org_id") and supplier["org_id"] != user["org_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    scope3 = fetch_supplier_scope3(supplier_id)
    if scope3:
        return {
            "supplier_name": supplier["name"],
            "category": scope3["category"],
            "annual_spend_usd": scope3["annual_spend_usd"],
            "scope3_tco2e": scope3["scope3_tco2e"],
            "calculation_method": scope3["calculation_method"],
            "emission_factor": scope3.get("emission_factor", ""),
            "confidence": scope3["confidence"],
            "data_source": scope3["data_source"],
        }

    # Fallback: spend-based estimate using emission factor table
    ef = _get_spend_based_factor(supplier.get("industry", ""), user["org_id"])
    tco2e = round(supplier["annual_spend_usd"] * ef["factor_value"] / 1000, 1)
    return {
        "supplier_name": supplier["name"],
        "category": ef["category"],
        "annual_spend_usd": supplier["annual_spend_usd"],
        "scope3_tco2e": tco2e,
        "calculation_method": "spend_based_estimate",
        "emission_factor": f"{ef['source']} — {ef['factor_name']}",
        "confidence": "LOW",
        "data_source": "Spend-based estimate — supplier not yet responded",
    }


# Default profile scores when no questionnaire responses exist
_DEFAULT_CLUSTERS = {
    "labour_rights": 0,
    "environment": 0,
    "governance": 0,
    "safety": 0,
    "gender": 0,
}

_CLUSTER_MAP = {
    "labour": "labour_rights",
    "environment": "environment",
    "governance": "governance",
    "safety": "safety",
    "gender": "gender",
}


def _compute_profile_clusters(responses: list) -> dict:
    """Compute ESG cluster scores from questionnaire responses (0-100 scale)."""
    if not responses:
        return _DEFAULT_CLUSTERS.copy()
    clusters: dict[str, list[float]] = {k: [] for k in _DEFAULT_CLUSTERS}
    for r in responses:
        qid = r.get("question_id", "")
        val = r.get("response_value")
        if val is None:
            continue
        for prefix, cluster_key in _CLUSTER_MAP.items():
            if prefix in qid.lower():
                clusters[cluster_key].append(float(val))
                break
    result = {}
    for key, values in clusters.items():
        if values:
            avg = sum(values) / len(values)
            result[key] = min(100, max(0, round(avg)))
        else:
            result[key] = 0
    return result


def _generate_recommendations(supplier: dict, clusters: dict) -> list[str]:
    """Generate supplier-specific recommendations based on risk and cluster scores."""
    recs = []
    tier = supplier.get("tier", "")
    risk_score = supplier.get("risk_score", 0)
    qs = supplier.get("questionnaire_status", "")

    if qs != "responded" and tier in ("tier2", "tier3"):
        recs.append(f"Initiate follow-up questionnaire for {tier} supplier {supplier['name']}")
    if clusters.get("labour_rights", 0) < 60:
        recs.append(
            f"Schedule third-party audit for {supplier['name']} — labour rights score below threshold"
        )
    if clusters.get("environment", 0) < 50:
        recs.append(
            f"Request supplier-specific emission data from {supplier['name']} for accurate Scope 3 reporting"
        )
    if risk_score and risk_score > 70:
        recs.append(
            f"High-risk supplier ({supplier['name']}) — consider alternative sourcing or escalation"
        )
    if not recs:
        recs.append("No immediate actions required — continue monitoring")
    return recs


def _compute_scope3_coverage(supplier: dict, org_id: str) -> int:
    """Compute real scope3 coverage percentage from questionnaire responses."""
    if supplier.get("questionnaire_status") != "responded":
        return 0
    stats = fetch_coverage_stats(org_id=org_id)
    return stats.get("spend_coverage_pct", 0)


def _get_spend_based_factor(industry: str, org_id: str) -> dict:
    """Look up spend-based emission factor from the emission_factors table."""
    conn = get_connection()
    try:
        rows = _fetchall(
            conn,
            """
            SELECT factor_name, category, factor_value, unit, source
            FROM emission_factors
            WHERE category = 'scope3_spend' AND (org_id = ? OR org_id = '' OR org_id IS NULL)
            ORDER BY CASE WHEN org_id = ? THEN 0 ELSE 1 END
            LIMIT 1
        """,
            (org_id, org_id),
        )
        if rows:
            r = rows[0]
            return {
                "factor_name": r["factor_name"],
                "category": r["category"],
                "factor_value": r["factor_value"],
                "unit": r["unit"],
                "source": r["source"],
            }
        return {
            "factor_name": "Generic spend-based (textiles)",
            "category": "spend_based",
            "factor_value": 0.94,
            "unit": "kgCO2e/USD",
            "source": "GHG Protocol 2022 fallback",
        }
    finally:
        release_connection(conn)
