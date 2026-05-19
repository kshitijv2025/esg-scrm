"""
Dashboard API routes — backed by SQLite database.
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import require_role, EDITOR_ROLES
from src.db.database import (
    fetch_metrics, fetch_trends, fetch_all_trends,
    fetch_risk_flags, acknowledge_risk_flag,
)

router = APIRouter()

# Metric display metadata
METRIC_META = {
    "energy_kwh": {
        "trend": "+3.2% vs last month",
        "calculation_method": "direct_measurement",
        "emission_factor": "IEA 2023 — Bangladesh Grid Factor",
        "emission_factor_value": "0.524 kg CO2/kWh",
    },
    "emissions_tco2": {
        "trend": "-1.8% vs last month",
        "calculation_method": "activity_based",
        "emission_factor": "IEA 2023 Bangladesh grid (0.524 kg/kWh)",
        "emission_factor_value": "0.524",
    },
    "water_m3": {
        "trend": "+0.7% vs last month",
        "calculation_method": "direct_measurement",
        "emission_factor": "N/A — direct measurement",
        "emission_factor_value": "—",
    },
    "scope3_category1": {
        "trend": "+2.1% vs last quarter",
        "calculation_method": "activity_based",
        "emission_factor": "GHG Protocol 2022 — Category 1 spend-based",
        "emission_factor_value": "0.94 kg CO2/$",
        "coverage_rate": 64,
        "responding_suppliers": 47,
        "total_suppliers": 73,
    },
    "diesel_consumed": {
        "trend": "+1.2% vs last quarter",
        "calculation_method": "manual_calculation",
        "emission_factor": "GHG Protocol 2022 — Diesel (2.68 kg CO2/L)",
        "emission_factor_value": "2.68 kg CO2/L",
    },
    "scope3_category6": {
        "trend": "New this quarter",
        "calculation_method": "manual_calculation",
        "emission_factor": "GHG Protocol 2022 — Category 6 (Business Travel)",
        "emission_factor_value": "flight 0.255 kg/km, hotel 0.084 kg/night, car 0.171 kg/km",
    },
}


def _build_metric_display(row: dict) -> dict:
    """Enrich a database metric row with display metadata."""
    cluster = row["cluster"]
    meta = METRIC_META.get(cluster, {})

    # Determine chain_valid: diesel is the tampered demo artifact
    stored_hash = row.get("hash", "")
    chain_valid = not stored_hash.startswith("TAMPERED_")

    metric = {
        "value": row["value"],
        "unit": row["unit"],
        "confidence": row["confidence"],
        "trend": meta.get("trend", ""),
        "source": row["source"],
        "period": row["period"],
        "calculation_method": meta.get("calculation_method", ""),
        "emission_factor": meta.get("emission_factor", ""),
        "emission_factor_value": meta.get("emission_factor_value", ""),
        "hash": stored_hash,
        "upstream_hash": row.get("prev_hash"),
        "chain_valid": chain_valid,
    }

    # Add scope3-specific fields
    for field in ("coverage_rate", "responding_suppliers", "total_suppliers"):
        if field in meta:
            metric[field] = meta[field]
        elif cluster.startswith("scope3") or cluster == "diesel_consumed":
            metric[field] = None

    return metric


@router.get("/live")
def live_metrics(user: dict = Depends(require_auth)):
    org_id = user["org_id"]
    rows = fetch_metrics(org_id=org_id)
    metrics = {}
    for row in rows:
        metrics[row["cluster"]] = _build_metric_display(row)

    all_valid = all(m.get("chain_valid", True) for m in metrics.values())
    return {
        "metrics": metrics,
        "hash_chain_valid": all_valid,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "org_id": org_id,
    }


@router.get("/trends/{metric_type}")
def trends(metric_type: str, user: dict = Depends(require_auth)):
    rows = fetch_trends(metric_type)
    data = [{"month": r["recorded_at"][:7], "value": r["value"]} for r in rows]

    # Enrich month labels
    month_names = {
        "2024-09": "Sep 2024", "2024-10": "Oct 2024", "2024-11": "Nov 2024",
        "2024-12": "Dec 2024", "2025-01": "Jan 2025",
    }
    for d in data:
        d["month"] = month_names.get(d["month"], d["month"])

    unit_map = {"energy_kwh": "kWh", "emissions_tco2": "tCO2e", "water_m3": "m³"}
    return {
        "metric_type": metric_type,
        "data": data,
        "unit": unit_map.get(metric_type, ""),
    }


@router.get("/trends")
def all_trends(user: dict = Depends(require_auth)):
    rows = fetch_all_trends()
    grouped: dict[str, dict] = {}

    month_names = {
        "2024-09": "Sep 2024", "2024-10": "Oct 2024", "2024-11": "Nov 2024",
        "2024-12": "Dec 2024", "2025-01": "Jan 2025",
    }

    for r in rows:
        month_key = r["recorded_at"][:7]
        label = month_names.get(month_key, month_key)
        if label not in grouped:
            grouped[label] = {"month": label, "energy": None, "emissions": None, "water": None}
        if r["cluster"] == "energy_kwh":
            grouped[label]["energy"] = r["value"]
        elif r["cluster"] == "emissions_tco2":
            grouped[label]["emissions"] = r["value"]
        elif r["cluster"] == "water_m3":
            grouped[label]["water"] = r["value"]

    return {"trends": list(grouped.values())}


@router.get("/operations-summary")
def operations_summary(user: dict = Depends(require_auth)):
    org_id = user["org_id"]
    rows = fetch_metrics(org_id=org_id)
    if not rows:
        return {"error": "no data available"}, 503

    clusters = []
    for row in rows:
        display = _build_metric_display(row)
        clusters.append({
            "cluster": row["cluster"],
            "value": display["value"],
            "unit": display["unit"],
            "confidence": display["confidence"],
            "trend": display["trend"],
            "source": display["source"],
            "period": display["period"],
            "calculation_method": display["calculation_method"],
            "hash": display["hash"],
            "chain_valid": display["chain_valid"],
        })

    return {
        "org_id": org_id,
        "period": "January 2025",
        "clusters": clusters,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/alerts")
def alerts(user: dict = Depends(require_auth)):
    org_id = user["org_id"]
    flags = fetch_risk_flags(org_id=org_id)
    alert_list = []
    for f in flags:
        alert_list.append({
            "id": f["id"],
            "metric_type": f["cluster"],
            "message": f["flag_text"],
            "actual_value": "",
            "threshold": "",
            "severity": f["severity"].lower(),
            "triggered_at": f["created_at"],
            "acknowledged": bool(f["acknowledged"]),
            "acknowledged_at": f.get("acknowledged_at"),
        })
    return {"alerts": alert_list, "total": len(alert_list)}


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, user: dict = Depends(require_auth)):
    require_role(user, EDITOR_ROLES)
    result = acknowledge_risk_flag(alert_id, user["email"], org_id=user["org_id"])
    if result is None:
        return {"error": "not found"}, 404
    return result
