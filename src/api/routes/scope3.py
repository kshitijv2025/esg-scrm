"""
Scope 3 categories API — backed by SQLite database.
"""
from fastapi import APIRouter, Depends

from src.api.middleware.auth import require_auth
from src.db.database import fetch_all_scope3, fetch_suppliers, fetch_coverage_stats

router = APIRouter()

# Category display metadata (stable reference data)
CATEGORY_META = {
    "Purchased Goods": {"id": "cat_1", "name": "Purchased Goods"},
    "Finished fabrics": {"id": "cat_2", "name": "Capital Goods"},
    "Dyeing & finishing": {"id": "cat_3", "name": "Fuel & Energy Related Activities"},
    "Thread manufacturing": {"id": "cat_4", "name": "Upstream Transport"},
    "Synthetic fibers": {"id": "cat_5", "name": "Waste Generated in Operations"},
    "Trims & accessories": {"id": "cat_6", "name": "Business Travel"},
}


@router.get("/categories")
def get_categories(user: dict = Depends(require_auth)):
    org_id = user["org_id"]
    scope3_records = fetch_all_scope3(org_id=org_id)
    suppliers = fetch_suppliers(org_id=org_id)
    total_suppliers = len(suppliers)
    responded = len([s for s in suppliers if s.get("questionnaire_status") == "responded"])

    categories = []
    for rec in scope3_records:
        meta = CATEGORY_META.get(rec["category"], {"id": f"cat_{len(categories)+1}", "name": rec["category"]})
        categories.append({
            "id": meta["id"],
            "name": meta["name"],
            "coverage_pct": round(responded / total_suppliers * 100) if total_suppliers else 0,
            "respondents": responded,
            "total": total_suppliers,
            "tco2e": rec["scope3_tco2e"],
        })

    return {"categories": categories, "total": len(categories)}


@router.get("/completeness")
def get_scope3_completeness(user: dict = Depends(require_auth)):
    """Overall Scope 3 coverage + per-category breakdown."""
    org_id = user["org_id"]
    stats = fetch_coverage_stats(org_id=org_id)
    scope3_records = fetch_all_scope3(org_id=org_id)

    by_category = []
    for rec in scope3_records:
        meta = CATEGORY_META.get(rec["category"], {"id": "cat_x", "name": rec["category"]})
        by_category.append({
            "id": meta["id"],
            "name": meta["name"],
            "coverage_pct": stats["coverage_pct"],
            "tco2e": rec["scope3_tco2e"],
        })

    return {
        "overall_coverage_pct": stats["coverage_pct"],
        "total_respondents": stats["responding_suppliers"],
        "total_suppliers": stats["total_suppliers"],
        "by_category": by_category,
    }
