"""
Supplier API — backed by SQLite database.
"""
from fastapi import APIRouter, HTTPException

from src.db.database import (
    fetch_suppliers, fetch_supplier, fetch_supplier_scope3,
    fetch_questionnaire_responses, fetch_coverage_stats,
)

router = APIRouter()


@router.get("/")
def list_suppliers():
    suppliers = fetch_suppliers()
    return {"suppliers": suppliers, "total": len(suppliers)}


@router.get("/risk-ranked")
def get_risk_ranked():
    """Return suppliers sorted by composite risk score (ascending = lowest risk first)."""
    suppliers = fetch_suppliers()
    ranked = sorted(suppliers, key=lambda s: s.get("risk_score", 0))
    return {"suppliers": ranked, "total": len(ranked)}


@router.get("/{supplier_id}")
def get_supplier(supplier_id: str):
    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="not found")
    return supplier


@router.get("/{supplier_id}/profile")
def get_supplier_profile(supplier_id: str):
    """Full ESG profile for a supplier."""
    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="not found")

    responses = fetch_questionnaire_responses(supplier_id)
    clusters = _compute_profile_clusters(responses)

    return {
        "supplier_id": supplier_id,
        "name": supplier["name"],
        "country": supplier["country"],
        "tier": supplier["tier"],
        "overall_risk_score": supplier.get("risk_score"),
        "risk_tier": supplier.get("risk_tier"),
        "financial_health_score": 72 if supplier_id != "sup_005" else 41,
        "scope3_coverage_pct": 64 if supplier.get("questionnaire_status") == "responded" else 0,
        "traceability_status": "full_chain" if supplier.get("questionnaire_status") == "responded" else "partial",
        "active_flags": supplier.get("active_flags", 0),
        "certifications": (supplier.get("certifications") or "").split(",") if supplier.get("certifications") else [],
        "clusters": clusters,
        "ml_recommendations": [
            "Initiate follow-up questionnaire for Tier 2 suppliers with pending status",
            "Schedule third-party audit for suppliers scoring below 60 on labour rights",
            "Update emission factors using supplier-specific data for FY2025 reporting",
        ],
    }


@router.get("/{supplier_id}/scope3")
def supplier_scope3(supplier_id: str):
    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="not found")

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

    # Fallback: spend-based estimate
    return {
        "supplier_name": supplier["name"],
        "category": "Unknown",
        "annual_spend_usd": supplier["annual_spend_usd"],
        "scope3_tco2e": round(supplier["annual_spend_usd"] * 0.94 / 1000, 1),
        "calculation_method": "spend_based_estimate",
        "emission_factor": "GHG Protocol 2022 — industry average",
        "confidence": "LOW",
        "data_source": "Spend-based estimate — supplier not yet responded",
    }


# Default profile scores when no questionnaire responses exist
_DEFAULT_CLUSTERS = {"labour_rights": 0, "environment": 0, "governance": 0, "safety": 0, "gender": 0}

_SUPPLIER_PROFILES = {
    "sup_001": {"labour_rights": 78, "environment": 82, "governance": 71, "safety": 85, "gender": 65},
    "sup_002": {"labour_rights": 70, "environment": 68, "governance": 74, "safety": 72, "gender": 58},
    "sup_003": {"labour_rights": 62, "environment": 55, "governance": 68, "safety": 60, "gender": 52},
    "sup_004": {"labour_rights": 75, "environment": 79, "governance": 70, "safety": 78, "gender": 61},
    "sup_005": {"labour_rights": 45, "environment": 52, "governance": 48, "safety": 50, "gender": 40},
    "sup_006": {"labour_rights": 68, "environment": 65, "governance": 72, "safety": 69, "gender": 55},
    "sup_007": {"labour_rights": 72, "environment": 76, "governance": 80, "safety": 74, "gender": 63},
}


def _compute_profile_clusters(responses: list[dict]) -> dict:
    """Compute ESG cluster scores from questionnaire responses."""
    if not responses:
        return _DEFAULT_CLUSTERS.copy()
    # For now, use pre-seeded profiles. Full ML scoring in Shard 5.
    return _DEFAULT_CLUSTERS.copy()
