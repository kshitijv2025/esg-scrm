"""
Risk flags + summary API — backed by SQLite database.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import require_role, VIEWER_ROLES, EDITOR_ROLES
from src.db.database import fetch_risk_flags, acknowledge_risk_flag, fetch_supplier_countries

router = APIRouter()

# Reference geopolitical scores — indices that don't change frequently
_REFERENCE_SCORES = {
    "Bangladesh": {"code": "BD", "political_stability": 42, "trade_exposure": 88, "currency_volatility": 71},
    "Vietnam": {"code": "VN", "political_stability": 71, "trade_exposure": 65, "currency_volatility": 38},
    "India": {"code": "IN", "political_stability": 62, "trade_exposure": 55, "currency_volatility": 52},
    "Thailand": {"code": "TH", "political_stability": 68, "trade_exposure": 48, "currency_volatility": 41},
    "Myanmar": {"code": "MM", "political_stability": 18, "trade_exposure": 22, "currency_volatility": 89},
    "Indonesia": {"code": "ID", "political_stability": 58, "trade_exposure": 42, "currency_volatility": 61},
    "China": {"code": "CN", "political_stability": 55, "trade_exposure": 72, "currency_volatility": 35},
    "Turkey": {"code": "TR", "political_stability": 45, "trade_exposure": 58, "currency_volatility": 65},
    "Cambodia": {"code": "KH", "political_stability": 38, "trade_exposure": 45, "currency_volatility": 55},
    "Pakistan": {"code": "PK", "political_stability": 28, "trade_exposure": 35, "currency_volatility": 78},
}

# Scorecard quadrant definitions — derived from active flags per cluster
SCORECARD_QUADRANTS = [
    {"id": "G2", "name": "Supply Chain Compliance", "base_score": 72, "tier": "B", "trend": "down"},
    {"id": "G5", "name": "Financial Health", "base_score": 58, "tier": "C", "trend": "down"},
    {"id": "G8", "name": "Geopolitical Risk", "base_score": 65, "tier": "B", "trend": "stable"},
    {"id": "G3", "name": "Ethics & Grievances", "base_score": 81, "tier": "A", "trend": "up"},
]


@router.get("/flags")
def get_flags(
    cluster: Optional[str] = None,
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    user: dict = Depends(require_auth),
):
    """Get risk flags with optional filters and pagination."""
    org_id = user["org_id"]
    flags = fetch_risk_flags(
        org_id=org_id, cluster=cluster, severity=severity,
        acknowledged=acknowledged, skip=skip, limit=limit,
    )

    result = []
    for f in flags:
        result.append({
            "id": f["id"],
            "flag_text": f["flag_text"],
            "cluster": f["cluster"],
            "severity": f["severity"],
            "days_overdue": f["days_overdue"],
            "priority_score": f["priority_score"],
            "created_at": f["created_at"],
            "acknowledged": bool(f["acknowledged"]),
            "acknowledged_at": f.get("acknowledged_at"),
            "acknowledged_by": f.get("acknowledged_by"),
        })

    return {"flags": result, "total": len(result)}


@router.get("/summary")
def get_risk_summary(user: dict = Depends(require_auth)):
    """Aggregate risk stats."""
    org_id = user["org_id"]
    active = fetch_risk_flags(org_id=org_id, acknowledged=False)
    by_severity = {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
    by_cluster = {}
    total_days = 0

    for f in active:
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
        by_cluster[f["cluster"]] = by_cluster.get(f["cluster"], 0) + 1
        total_days += f["days_overdue"]

    avg_days = total_days / len(active) if active else 0

    return {
        "total": len(active),
        "by_severity": {
            "critical": by_severity.get("CRITICAL", 0),
            "warning": by_severity.get("WARNING", 0),
            "info": by_severity.get("INFO", 0),
        },
        "by_cluster": by_cluster,
        "avg_days_open": round(avg_days, 1),
    }


@router.post("/flags/{flag_id}/acknowledge")
def acknowledge_flag(
    flag_id: str,
    user: dict = Depends(require_auth),
):
    """Acknowledge a risk flag. Requires editor role or above."""
    require_role(user, EDITOR_ROLES)
    result = acknowledge_risk_flag(flag_id, user.get("email", "unknown"), org_id=user["org_id"])
    if result is None:
        raise HTTPException(status_code=404, detail="not found")
    return result


@router.get("/scorecard")
def get_risk_scorecard(user: dict = Depends(require_auth)):
    """2x2 risk scorecard with quadrant scores derived from active flags."""
    org_id = user["org_id"]
    active = fetch_risk_flags(org_id=org_id, acknowledged=False)
    flag_counts: dict[str, int] = {}
    for f in active:
        flag_counts[f["cluster"]] = flag_counts.get(f["cluster"], 0) + 1

    quadrants = []
    for q in SCORECARD_QUADRANTS:
        q_flags = flag_counts.get(q["id"], 0)
        score = max(q["base_score"] - q_flags * 5, 0)
        tier = "A" if score >= 75 else "B" if score >= 60 else "C"
        quadrants.append({
            "id": q["id"],
            "name": q["name"],
            "score": score,
            "tier": tier,
            "trend": q["trend"],
            "active_flags": q_flags,
        })

    return {"quadrants": quadrants}


@router.get("/geopolitical")
def get_geopolitical(user: dict = Depends(require_auth)):
    """Country-level geopolitical risk matrix derived from supplier countries."""
    org_id = user["org_id"]
    supplier_countries = fetch_supplier_countries(org_id=org_id)
    rows = []
    for country_name in supplier_countries:
        ref = _REFERENCE_SCORES.get(country_name)
        if ref:
            overall = round((ref["political_stability"] + ref["trade_exposure"] + ref["currency_volatility"]) / 3)
            rows.append({
                "country_code": ref["code"],
                "country": country_name,
                "political_stability": ref["political_stability"],
                "trade_exposure": ref["trade_exposure"],
                "currency_volatility": ref["currency_volatility"],
                "overall_score": overall,
            })
        else:
            rows.append({
                "country_code": country_name[:2].upper(),
                "country": country_name,
                "political_stability": 50,
                "trade_exposure": 50,
                "currency_volatility": 50,
                "overall_score": 50,
            })
    rows.sort(key=lambda r: r["overall_score"])
    return {"countries": rows, "total": len(rows)}
