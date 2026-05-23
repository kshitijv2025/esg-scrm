"""Alert threshold API — configurable monitoring rules."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import require_role, ADMIN_ROLES
from src.db.database import (
    fetch_alert_thresholds,
    fetch_risk_flags,
    get_connection,
    release_connection,
    _fetchall,
    _fetchone,
    _execute,
)

router = APIRouter()


_ALLOWED_SEVERITIES = {"CRITICAL", "WARNING", "INFO"}
_SEVERITY_ALIASES = {
    "HIGH": "CRITICAL",
    "MEDIUM": "WARNING",
    "MED": "WARNING",
    "LOW": "INFO",
}

_CLUSTER_NAMES = {
    "G2": "G2_supply_chain",
    "G3": "G3_ethics",
    "G5": "G5_financial",
    "G8": "G8_geopolitical",
}


def _normalize_severity(s: str) -> str:
    upper = s.upper()
    return _SEVERITY_ALIASES.get(upper, upper)


@router.get("/")
def list_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    user: dict = Depends(require_auth),
):
    """List active alerts (unacknowledged risk flags) with optional severity filter."""
    if severity is not None and _normalize_severity(severity) not in _ALLOWED_SEVERITIES:
        raise HTTPException(
            status_code=400,
            detail=f"severity must be one of: {', '.join(sorted(_ALLOWED_SEVERITIES))}",
        )
    org_id = user["org_id"]
    norm_severity = _normalize_severity(severity) if severity else None
    flags = fetch_risk_flags(
        org_id=org_id,
        severity=norm_severity,
        acknowledged=False,
        skip=skip,
        limit=limit,
    )
    conn = get_connection()
    try:
        count_query = "SELECT COUNT(*) as cnt FROM risk_flags WHERE org_id = ? AND acknowledged = 0"
        count_params: list = [org_id]
        if norm_severity:
            count_query += " AND severity = ?"
            count_params.append(norm_severity)
        total_row = _fetchone(conn, count_query, tuple(count_params))
        total = total_row["cnt"] if total_row else 0
    finally:
        release_connection(conn)
    alerts = []
    for f in flags:
        cluster_id = f.get("cluster", "")
        cluster_key = _CLUSTER_NAMES.get(cluster_id, cluster_id)
        alerts.append(
            {
                "id": f["id"],
                "flag_text": f["flag_text"],
                "cluster": cluster_id,
                "cluster_name": cluster_key,
                "severity": f["severity"],
                "priority_score": f.get("priority_score"),
                "days_overdue": f.get("days_overdue"),
                "created_at": f.get("created_at"),
                "acknowledged": False,
            }
        )
    return {"alerts": alerts, "total": total, "skip": skip, "limit": limit}


_ALLOWED_NOTIFICATION_STATUSES = {"sent", "failed", "delivered", "bounced", "pending"}


@router.get("/history")
def get_alert_history(
    status: Optional[str] = Query(None, description="Filter by notification status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    user: dict = Depends(require_auth),
):
    """Return alert notification history for the org."""
    if status is not None and status.lower() not in _ALLOWED_NOTIFICATION_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of: {', '.join(sorted(_ALLOWED_NOTIFICATION_STATUSES))}",
        )
    org_id = user["org_id"]
    conn = get_connection()
    try:
        query = "SELECT * FROM notification_log WHERE org_id = ?"
        params: list = [org_id]
        if status:
            query += " AND status = ?"
            params.append(status.lower())
        query += " ORDER BY sent_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])
        rows = _fetchall(conn, query, tuple(params))
        count_query = "SELECT COUNT(*) as cnt FROM notification_log WHERE org_id = ?"
        count_params = [org_id]
        if status:
            count_query += " AND status = ?"
            count_params.append(status.lower())
        total_row = _fetchone(conn, count_query, tuple(count_params))
        total = total_row["cnt"] if total_row else 0
        return {"history": rows, "total": total}
    finally:
        release_connection(conn)


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
        raise HTTPException(
            status_code=400, detail="severity must be one of: CRITICAL, WARNING, INFO"
        )

    conn = get_connection()
    try:
        cur = _execute(
            conn,
            """
            INSERT INTO alert_thresholds
                (org_id, cluster, metric_cluster, operator, threshold_value, severity)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                user["org_id"],
                body["cluster"],
                body["metric_cluster"],
                body["operator"],
                body["threshold_value"],
                body["severity"],
            ),
        )

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
            triggered.append(
                {
                    "threshold_id": t["id"],
                    "metric_cluster": t["metric_cluster"],
                    "operator": op,
                    "threshold_value": tv,
                    "current_value": current_value,
                    "severity": t["severity"],
                }
            )

    return {
        "cluster": cluster,
        "current_value": current_value,
        "triggered": triggered,
        "total_triggered": len(triggered),
    }
