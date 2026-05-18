"""
Risk flags + summary API — backed by SQLite database.
"""
from fastapi import APIRouter, HTTPException
from typing import Optional

from src.db.database import fetch_risk_flags, acknowledge_risk_flag

router = APIRouter()

# Geopolitical data — relatively stable reference data
GEOPOLITICAL_DATA = {
    "BD": {"country": "Bangladesh", "political_stability": 42, "trade_exposure": 88, "currency_volatility": 71, "overall": 67},
    "VN": {"country": "Vietnam", "political_stability": 71, "trade_exposure": 65, "currency_volatility": 38, "overall": 58},
    "IN": {"country": "India", "political_stability": 62, "trade_exposure": 55, "currency_volatility": 52, "overall": 56},
    "TH": {"country": "Thailand", "political_stability": 68, "trade_exposure": 48, "currency_volatility": 41, "overall": 52},
    "MM": {"country": "Myanmar", "political_stability": 18, "trade_exposure": 22, "currency_volatility": 89, "overall": 43},
    "ID": {"country": "Indonesia", "political_stability": 58, "trade_exposure": 42, "currency_volatility": 61, "overall": 54},
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
):
    """Get risk flags with optional filters."""
    flags = fetch_risk_flags(cluster=cluster, severity=severity, acknowledged=acknowledged)

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
def get_risk_summary():
    """Aggregate risk stats."""
    active = fetch_risk_flags(acknowledged=False)
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
def acknowledge_flag(flag_id: str):
    """Acknowledge a risk flag."""
    result = acknowledge_risk_flag(flag_id, "user@esg-scrm.com")
    if result is None:
        raise HTTPException(status_code=404, detail="not found")
    return result


@router.get("/scorecard")
def get_risk_scorecard():
    """2x2 risk scorecard with quadrant scores derived from active flags."""
    active = fetch_risk_flags(acknowledged=False)
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
def get_geopolitical():
    """Country-level geopolitical risk matrix for Tier 1 supplier countries."""
    rows = []
    for country_code, data in GEOPOLITICAL_DATA.items():
        rows.append({
            "country_code": country_code,
            "country": data["country"],
            "political_stability": data["political_stability"],
            "trade_exposure": data["trade_exposure"],
            "currency_volatility": data["currency_volatility"],
            "overall_score": data["overall"],
        })
    rows.sort(key=lambda r: r["overall_score"])
    return {"countries": rows, "total": len(rows)}
