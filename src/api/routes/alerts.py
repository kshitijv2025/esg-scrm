"""Alert threshold API — configurable monitoring rules."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import require_role, VIEWER_ROLES, EDITOR_ROLES, ADMIN_ROLES
from src.db.database import fetch_alert_thresholds, get_connection, release_connection, _fetchall, _execute

router = APIRouter()


@router.get("/thresholds")
def list_thresholds(
    cluster: Optional[str] = None,
    user: dict = Depends(require_auth),
):
    """List active alert thresholds for the user's org, falling back to global."""
    effective_org = user["org_id"]
    thresholds = fetch_alert_thresholds(org_id=effective_org, cluster=cluster)
    if not thresholds:
        thresholds = fetch_alert_thresholds(org_id="", cluster=cluster)
    return {"thresholds": thresholds, "total": len(thresholds)}


@router.post("/thresholds")
def create_threshold(
    body: dict,
    user: dict = Depends(require_auth),
):
    """Create a new alert threshold. Requires admin role."""
    require_role(user, ADMIN_ROLES)
    required = ["cluster", "metric_cluster", "operator", "threshold_value", "severity"]
    for field in required:
        if field not in body:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    if body["operator"] not in (">", "<", ">=", "<=", "="):
        raise HTTPException(status_code=400, detail="operator must be one of: >, <, >=, <=, =")
    if body["severity"] not in ("CRITICAL", "WARNING", "INFO"):
        raise HTTPException(status_code=400, detail="severity must be one of: CRITICAL, WARNING, INFO")

    conn = get_connection()
    try:
        cur = _execute(conn, """
            INSERT INTO alert_thresholds (org_id, cluster, metric_cluster, operator, threshold_value, severity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user["org_id"], body["cluster"], body["metric_cluster"],
              body["operator"], body["threshold_value"], body["severity"]))

        return {"id": cur.lastrowid, "status": "created"}
    finally:
        release_connection(conn)


@router.get("/check/{cluster}")
def check_thresholds(
    cluster: str,
    current_value: float,
    user: dict = Depends(require_auth),
):
    """Check if a metric value triggers any alert thresholds."""
    effective_org = user["org_id"]
    thresholds = fetch_alert_thresholds(org_id=effective_org, cluster=cluster)
    if not thresholds:
        thresholds = fetch_alert_thresholds(org_id="", cluster=cluster)

    triggered = []
    for t in thresholds:
        op = t["operator"]
        tv = t["threshold_value"]
        hit = False
        if op == ">" and current_value > tv:
            hit = True
        elif op == "<" and current_value < tv:
            hit = True
        elif op == ">=" and current_value >= tv:
            hit = True
        elif op == "<=" and current_value <= tv:
            hit = True
        elif op == "=" and current_value == tv:
            hit = True

        if hit:
            triggered.append({
                "threshold_id": t["id"],
                "metric_cluster": t["metric_cluster"],
                "operator": op,
                "threshold_value": tv,
                "current_value": current_value,
                "severity": t["severity"],
            })

    return {"cluster": cluster, "current_value": current_value, "triggered": triggered, "total_triggered": len(triggered)}
