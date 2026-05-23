"""
Risk flags + summary API — backed by SQLite database.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import require_role, EDITOR_ROLES
from src.db.database import fetch_risk_flags, acknowledge_risk_flag, fetch_supplier_countries

router = APIRouter()

# Reference geopolitical scores — indices that don't change frequently
_REFERENCE_SCORES = {
    "Bangladesh": {
        "code": "BD",
        "political_stability": 42,
        "trade_exposure": 88,
        "currency_volatility": 71,
    },
    "Vietnam": {
        "code": "VN",
        "political_stability": 71,
        "trade_exposure": 65,
        "currency_volatility": 38,
    },
    "India": {
        "code": "IN",
        "political_stability": 62,
        "trade_exposure": 55,
        "currency_volatility": 52,
    },
    "Thailand": {
        "code": "TH",
        "political_stability": 68,
        "trade_exposure": 48,
        "currency_volatility": 41,
    },
    "Myanmar": {
        "code": "MM",
        "political_stability": 18,
        "trade_exposure": 22,
        "currency_volatility": 89,
    },
    "Indonesia": {
        "code": "ID",
        "political_stability": 58,
        "trade_exposure": 42,
        "currency_volatility": 61,
    },
    "China": {
        "code": "CN",
        "political_stability": 55,
        "trade_exposure": 72,
        "currency_volatility": 35,
    },
    "Turkey": {
        "code": "TR",
        "political_stability": 45,
        "trade_exposure": 58,
        "currency_volatility": 65,
    },
    "Cambodia": {
        "code": "KH",
        "political_stability": 38,
        "trade_exposure": 45,
        "currency_volatility": 55,
    },
    "Pakistan": {
        "code": "PK",
        "political_stability": 28,
        "trade_exposure": 35,
        "currency_volatility": 78,
    },
}

# Scorecard quadrant definitions — derived from active flags per cluster
SCORECARD_QUADRANTS = [
    {"id": "G2", "name": "Supply Chain Compliance", "base_score": 72, "tier": "B", "trend": "down"},
    {"id": "G5", "name": "Financial Health", "base_score": 58, "tier": "C", "trend": "down"},
    {"id": "G8", "name": "Geopolitical Risk", "base_score": 65, "tier": "B", "trend": "stable"},
    {"id": "G3", "name": "Ethics & Grievances", "base_score": 81, "tier": "A", "trend": "up"},
]


# Cluster ID → full name mapping
_CLUSTER_NAMES = {
    "G2": "G2_supply_chain",
    "G3": "G3_ethics",
    "G5": "G5_financial",
    "G8": "G8_geopolitical",
}

_CLUSTER_TITLES = {
    "G2_supply_chain": "Supply Chain Compliance",
    "G3_ethics": "Ethics & Grievances",
    "G5_financial": "Financial Health",
    "G8_geopolitical": "Geopolitical Risk",
}

_CLUSTER_RECOMMENDATIONS = {
    "G2_supply_chain": "Review supplier ESG certifications and conduct due diligence visits.",
    "G3_ethics": "Investigate grievances through the ethics committee and track remediation.",
    "G5_financial": "Assess supplier financial health through updated audit reports.",
    "G8_geopolitical": "Monitor trade corridor developments and diversify sourcing where exposed.",
}

# Severity multipliers for risk score penalty computation
_SEVERITY_MULTIPLIER = {
    "CRITICAL": 3.0,
    "WARNING": 2.0,
    "INFO": 1.0,
}


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
        org_id=org_id,
        cluster=cluster,
        severity=severity,
        acknowledged=acknowledged,
        skip=skip,
        limit=limit,
    )

    result = []
    for f in flags:
        cluster_id = f["cluster"]
        cluster_key = _CLUSTER_NAMES.get(cluster_id, cluster_id)
        result.append(
            {
                "id": f["id"],
                "flag_text": f["flag_text"],
                "cluster": cluster_id,
                "cluster_name": cluster_key,
                "title": f["flag_text"].split(":")[0] if f["flag_text"] else cluster_key,
                "detail": f["flag_text"],
                "recommendation": _CLUSTER_RECOMMENDATIONS.get(
                    cluster_key, "Review and remediate the flagged issue."
                ),
                "severity": f["severity"],
                "days_overdue": f["days_overdue"],
                "priority_score": f["priority_score"],
                "created_at": f["created_at"],
                "acknowledged": bool(f["acknowledged"]),
                "acknowledged_at": f.get("acknowledged_at"),
                "acknowledged_by": f.get("acknowledged_by"),
            }
        )

    return {"flags": result, "total": len(result)}


@router.get("/summary")
def get_risk_summary(user: dict = Depends(require_auth)):
    """D3.3: 4-chip risk summary by cluster with dynamic score computation."""
    org_id = user["org_id"]
    active = fetch_risk_flags(org_id=org_id, acknowledged=False)

    # Aggregate per cluster: sum of (severity_mult * min(days_overdue/30, 2)) for each flag
    cluster_priority: dict[str, float] = {}
    cluster_flags: dict[str, int] = {}
    by_severity: dict[str, int] = {"critical": 0, "warning": 0, "info": 0}
    total_days = 0
    for f in active:
        cluster = f["cluster"]
        cluster_flags[cluster] = cluster_flags.get(cluster, 0) + 1
        sev_mult = _SEVERITY_MULTIPLIER.get(f["severity"], 1.0)
        days_factor = min(f["days_overdue"] / 30, 2)
        cluster_priority[cluster] = cluster_priority.get(cluster, 0) + sev_mult * days_factor
        sev_lower = f["severity"].lower()
        if sev_lower == "critical":
            by_severity["critical"] += 1
        elif sev_lower == "warning":
            by_severity["warning"] += 1
        else:
            by_severity["info"] += 1
        total_days += f["days_overdue"]

    result = {}
    for q in SCORECARD_QUADRANTS:
        key = _CLUSTER_NAMES[q["id"]]
        priority = cluster_priority.get(q["id"], 0)
        score = int(max(0, q["base_score"] - priority * 5))
        result[key] = {
            "score": score,
            "tier": q["tier"],
            "trend": q["trend"],
            "flags": cluster_flags.get(q["id"], 0),
        }

    result["by_severity"] = by_severity
    result["total"] = len(active)
    result["avg_days_open"] = total_days / len(active) if active else 0

    return result


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
        quadrants.append(
            {
                "id": q["id"],
                "name": q["name"],
                "score": score,
                "tier": tier,
                "trend": q["trend"],
                "active_flags": q_flags,
            }
        )

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
            overall = round(
                (ref["political_stability"] + ref["trade_exposure"] + ref["currency_volatility"])
                / 3
            )
            rows.append(
                {
                    "country_code": ref["code"],
                    "country": country_name,
                    "political_stability": ref["political_stability"],
                    "trade_exposure": ref["trade_exposure"],
                    "currency_volatility": ref["currency_volatility"],
                    "overall_score": overall,
                }
            )
        else:
            rows.append(
                {
                    "country_code": country_name[:2].upper(),
                    "country": country_name,
                    "political_stability": 50,
                    "trade_exposure": 50,
                    "currency_volatility": 50,
                    "overall_score": 50,
                }
            )
    rows.sort(key=lambda r: r["overall_score"])
    return {"countries": rows, "total": len(rows)}


@router.get("/country-risk")
def get_country_risk(user: dict = Depends(require_auth)):
    """Return country risk scores for all known countries."""
    from src.ml.risk_predictor import _COUNTRY_RISK

    countries = [
        {"country_code": code, "risk_score": score} for code, score in _COUNTRY_RISK.items()
    ]
    return {"countries": countries, "total": len(countries)}
