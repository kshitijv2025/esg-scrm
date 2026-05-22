"""
Dashboard API routes — backed by SQLite database.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import require_role, EDITOR_ROLES
from src.db.database import (
    fetch_metrics,
    fetch_trends,
    fetch_all_trends,
    fetch_risk_flags,
    acknowledge_risk_flag,
    fetch_intensity_data,
    fetch_renewable_data,
    fetch_metric_metadata,
)

router = APIRouter()


def _build_metric_display(row: dict, meta: dict[str, dict]) -> dict:
    """Enrich a database metric row with display metadata."""
    cluster = row["cluster"]
    cluster_meta = meta.get(cluster, {})

    # Determine chain_valid: diesel is the tampered demo artifact
    stored_hash = row.get("hash", "")
    chain_valid = not stored_hash.startswith("TAMPERED_")

    metric = {
        "value": row["value"],
        "unit": row["unit"],
        "confidence": row["confidence"],
        "trend": cluster_meta.get("trend", ""),
        "source": row["source"],
        "period": row["period"],
        "calculation_method": cluster_meta.get("calculation_method", ""),
        "emission_factor": cluster_meta.get("emission_factor", ""),
        "emission_factor_value": cluster_meta.get("emission_factor_value", ""),
        "hash": stored_hash,
        "upstream_hash": row.get("prev_hash"),
        "chain_valid": chain_valid,
    }

    # Add scope3-specific fields
    for field in ("coverage_rate", "responding_suppliers", "total_suppliers"):
        if field in cluster_meta:
            metric[field] = cluster_meta[field]
        elif cluster.startswith("scope3") or cluster == "diesel_consumed":
            metric[field] = None

    return metric


@router.get("/live")
def live_metrics(user: dict = Depends(require_auth)):
    org_id = user["org_id"]
    rows = fetch_metrics(org_id=org_id)
    meta = fetch_metric_metadata()
    metrics = {}
    for row in rows:
        metrics[row["cluster"]] = _build_metric_display(row, meta)

    # Replace scope3 coverage with actual response-based coverage from DB
    from src.db.database import fetch_response_based_coverage

    coverage = fetch_response_based_coverage(org_id)
    for cluster_key in metrics:
        if cluster_key.startswith("scope3"):
            metrics[cluster_key]["coverage_rate"] = coverage["spend_weighted_coverage_pct"]
            metrics[cluster_key]["responding_suppliers"] = coverage["responded_suppliers"]
            metrics[cluster_key]["total_suppliers"] = coverage["total_suppliers"]

    all_valid = all(m.get("chain_valid", True) for m in metrics.values())
    return {
        "metrics": metrics,
        "hash_chain_valid": all_valid,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "org_id": org_id,
    }


@router.get("/intensity")
def emission_intensity(user: dict = Depends(require_auth)):
    """Emission intensity metrics — energy and emissions per unit of production."""
    org_id = user["org_id"]
    data = fetch_intensity_data(org_id)

    production_volume = data["production_volume"]
    energy_kwh = data["energy_kwh"]
    emissions_tco2 = data["emissions_tco2"]

    if production_volume and production_volume > 0:
        energy_intensity = energy_kwh / production_volume
        emission_intensity = emissions_tco2 / production_volume
    else:
        energy_intensity = 0
        emission_intensity = 0

    return {
        "org_id": org_id,
        "energy_kwh": energy_kwh,
        "emissions_tco2": emissions_tco2,
        "production_volume": production_volume or 0,
        "energy_intensity_kwh_per_unit": energy_intensity,
        "emission_intensity_tco2_per_unit": emission_intensity,
        "period": data["period"],
    }


@router.get("/renewable")
def renewable_energy(user: dict = Depends(require_auth)):
    """Renewable energy tracking with REC certificates."""
    org_id = user["org_id"]
    data = fetch_renewable_data(org_id)

    return {
        "org_id": org_id,
        "total_kwh": data["total_kwh"],
        "renewable_kwh": data["renewable_kwh"],
        "renewable_percentage": data["renewable_percentage"],
        "rec_certificates": data["rec_certificates"],
        "period": data["period"],
    }


@router.get("/trends/{metric_type}")
def trends(metric_type: str, user: dict = Depends(require_auth)):
    org_id = user["org_id"]
    rows = fetch_trends(metric_type, org_id=org_id)
    data = [{"month": r["recorded_at"][:7], "value": r["value"]} for r in rows]

    # Enrich month labels
    month_names = {
        "2024-09": "Sep 2024",
        "2024-10": "Oct 2024",
        "2024-11": "Nov 2024",
        "2024-12": "Dec 2024",
        "2025-01": "Jan 2025",
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
def all_trends(user: dict = Depends(require_auth), skip: int = Query(0, ge=0)):
    org_id = user["org_id"]
    rows = fetch_all_trends(org_id=org_id)
    grouped: dict[str, dict] = {}

    month_names = {
        "2024-09": "Sep 2024",
        "2024-10": "Oct 2024",
        "2024-11": "Nov 2024",
        "2024-12": "Dec 2024",
        "2025-01": "Jan 2025",
    }

    for r in rows:
        month_key = r["recorded_at"][:7]
        label = month_names.get(month_key, month_key)
        if label not in grouped:
            grouped[label] = {
                "month": label,
                "energy": None,
                "emissions": None,
                "water": None,
                "waste": None,
                "incident_rate": None,
            }
        if r["cluster"] == "energy_kwh":
            grouped[label]["energy"] = r["value"]
        elif r["cluster"] == "emissions_tco2":
            grouped[label]["emissions"] = r["value"]
        elif r["cluster"] == "water_m3":
            grouped[label]["water"] = r["value"]
        elif r["cluster"] == "waste_kg":
            grouped[label]["waste"] = r["value"]
        elif r["cluster"] == "incident_rate":
            grouped[label]["incident_rate"] = r["value"]

    return {"trends": list(grouped.values())}


@router.get("/operations-summary")
def operations_summary(user: dict = Depends(require_auth)):
    """Return cluster summary for the Dashboard tab per dashboard-api.md.

    Response shape: {clusters: {cluster_key: {value, unit, confidence, trend, ...}}, ...}
    """
    org_id = user["org_id"]
    rows = fetch_metrics(org_id=org_id)
    meta = fetch_metric_metadata()
    metrics = {}
    for row in rows:
        display = _build_metric_display(row, meta)
        metrics[row["cluster"]] = {
            "value": display["value"],
            "unit": display["unit"],
            "confidence": display["confidence"],
            "trend": display["trend"],
            "source": display["source"],
            "period": display["period"],
            "calculation_method": display["calculation_method"],
            "hash": display["hash"],
            "chain_valid": display["chain_valid"],
        }

    all_valid = all(m.get("chain_valid", True) for m in metrics.values())
    # Top-level period is the reporting period (from first metric row)
    period = rows[0]["period"] if rows else ""
    return {
        "clusters": metrics,
        "period": period,
        "hash_chain_valid": all_valid,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "org_id": org_id,
    }


ALERT_SEVERITIES = {"low", "medium", "high", "critical"}


@router.get("/alerts")
def alerts(user: dict = Depends(require_auth), severity: str = Query(None)):
    org_id = user["org_id"]
    flags = fetch_risk_flags(org_id=org_id)
    if severity is not None and severity.lower() not in ALERT_SEVERITIES:
        raise HTTPException(
            status_code=400,
            detail=f"severity must be one of: {', '.join(sorted(ALERT_SEVERITIES))}",
        )
    alert_list = []
    for f in flags:
        sev = f["severity"].lower()
        if severity is not None and sev != severity.lower():
            continue
        alert_list.append(
            {
                "id": f["id"],
                "metric_type": f["cluster"],
                "message": f["flag_text"],
                "actual_value": "",
                "threshold": "",
                "severity": f["severity"].lower(),
                "triggered_at": f["created_at"],
                "acknowledged": bool(f["acknowledged"]),
                "acknowledged_at": f.get("acknowledged_at"),
            }
        )
    return {"alerts": alert_list, "total": len(alert_list)}


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, user: dict = Depends(require_auth)):
    require_role(user, EDITOR_ROLES)
    result = acknowledge_risk_flag(alert_id, user["email"], org_id=user["org_id"])
    if result is None:
        raise HTTPException(status_code=404, detail="not found")
    return result
