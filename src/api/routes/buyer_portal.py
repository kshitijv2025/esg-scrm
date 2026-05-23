"""
Buyer Portal API — Read-only access for buyer organizations.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from src.api.middleware.auth import require_auth
from src.db.database import get_connection, release_connection

# Auth-required router (included at /api/access)
router = APIRouter()

# Public router for token-based access (included at /api/buyer-portal)
public_router = APIRouter()


def _supplier_to_buyer_dict(row: dict, scope_filter: list) -> dict:
    """Convert supplier row to buyer-portal view, filtering by scope."""
    if scope_filter and row["id"] not in scope_filter:
        return None

    return {
        "id": row["id"],
        "name": row["name"],
        "country": row["country"],
        "industry": row["industry"],
        "tier": row["tier"],
        "risk_tier": row.get("risk_tier"),
        "esg_score": row.get("esg_score"),
        "certifications": json.loads(row.get("certifications", "[]"))
        if row.get("certifications")
        else [],
        "questionnaire_status": row["questionnaire_status"],
    }


@router.post("/buyer-link")
def create_buyer_link(
    payload: dict,
    user: dict = Depends(require_auth),
):
    """Create a buyer portal access link. Requires auth."""
    from src.api.middleware.rbac import ADMIN_ROLES, require_role

    require_role(user, ADMIN_ROLES)

    org_id = user["org_id"]
    buyer_org_id = payload.get("buyer_org_id")
    buyer_org_name = payload.get("buyer_org_name", "Unknown Buyer")
    scope_filter = payload.get("scope_filter", [])

    if isinstance(scope_filter, list):
        scope_filter = json.dumps(scope_filter)
    else:
        scope_filter = str(scope_filter)

    # Generate secure token
    token = uuid.uuid4().hex + uuid.uuid4().hex[:16]
    expires = datetime.now(timezone.utc) + timedelta(days=payload.get("expires_days", 365))
    access_id = f"bp_{uuid.uuid4().hex[:12]}"

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO buyer_portal_access
               (id, org_id, buyer_org_id, buyer_org_name, scope_filter, token,
                token_expires, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                access_id,
                org_id,
                buyer_org_id or "",
                buyer_org_name,
                scope_filter,
                token,
                expires.isoformat(),
                user.get("email", ""),
            ),
        )
        conn.commit()
    finally:
        release_connection(conn)

    return {
        "id": access_id,
        "token": token,
        "expires": expires.isoformat(),
        "portal_url": f"/buyer-portal/{token}",
    }


@public_router.get("/{token}")
def get_buyer_portal(
    token: str,
    org_id: Optional[str] = None,
):
    """Get buyer portal data. Read-only, token-authenticated."""
    conn = get_connection()
    try:
        # Look up access by token
        row = conn.execute(
            "SELECT * FROM buyer_portal_access WHERE token = ? AND is_active = 1",
            (token,),
        ).fetchone()

        if not row:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid or expired portal link"},
            )

        # Convert sqlite3.Row to dict for .get() access
        row = dict(row)

        # Check expiry
        if (
            row.get("token_expires")
            and row["token_expires"] < datetime.now(timezone.utc).isoformat()
        ):
            return JSONResponse(
                status_code=403,
                content={"detail": "Portal link has expired"},
            )

        portal_org_id = row["org_id"]
        scope_filter = json.loads(row.get("scope_filter", "[]"))
        buyer_org_name = row["buyer_org_name"]

        # Get suppliers in scope
        supplier_query = "SELECT * FROM suppliers WHERE org_id = ?"
        supplier_params = [portal_org_id]

        if scope_filter is not None and len(scope_filter) > 0:
            placeholders = ",".join(["?"] * len(scope_filter))
            supplier_query += f" AND id IN ({placeholders})"
            supplier_params.extend(scope_filter)
        elif scope_filter is not None:
            # Empty list means "no access" — add impossible constraint
            supplier_query += " AND 1=0"

        suppliers = conn.execute(supplier_query, supplier_params).fetchall()

        # Get summary metrics for the org
        metrics_rows = conn.execute(
            """SELECT cluster, AVG(value) as avg_value, MAX(recorded_at) as latest
               FROM metrics WHERE org_id = ? GROUP BY cluster""",
            (portal_org_id,),
        ).fetchall()

        metrics = {
            r["cluster"]: {"value": round(r["avg_value"], 2), "latest": r["latest"]}
            for r in metrics_rows
        }

        # Get risk flags for scoped suppliers
        risk_flags = []
        if scope_filter is not None and len(scope_filter) > 0:
            placeholders = ",".join(["?"] * len(scope_filter))
            risk_flags = conn.execute(
                f"""SELECT rf.*, f.name as supplier_name
                    FROM risk_flags rf
                    LEFT JOIN factories f ON f.id = rf.factory_id
                    WHERE rf.org_id = ? AND rf.factory_id IN ({placeholders})
                    AND rf.acknowledged = 0
                    ORDER BY rf.priority_score DESC LIMIT 20""",
                [portal_org_id] + scope_filter,
            ).fetchall()
        elif scope_filter is not None:
            # Empty list means no access — risk_flags stays []
            pass
        else:
            risk_flags = conn.execute(
                """SELECT rf.*, f.name as supplier_name
                   FROM risk_flags rf
                   LEFT JOIN factories f ON f.id = rf.factory_id
                   WHERE rf.org_id = ? AND rf.acknowledged = 0
                   ORDER BY rf.priority_score DESC LIMIT 20""",
                (portal_org_id,),
            ).fetchall()

        # Get recent evidence chain entries
        evidence = conn.execute(
            """SELECT ec.*, m.cluster
               FROM evidence_chain ec
               JOIN metrics m ON m.id = ec.metric_id
               WHERE ec.org_id = ?
               ORDER BY ec.recorded_at DESC LIMIT 50""",
            (portal_org_id,),
        ).fetchall()

        # Compute summary from suppliers
        supplier_list = [_supplier_to_buyer_dict(dict(r), scope_filter) for r in suppliers]
        # Filter out None (scope-filtered)
        supplier_list = [s for s in supplier_list if s is not None]

        total = len(supplier_list)
        scores = [s["esg_score"] for s in supplier_list if s.get("esg_score") is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else None

        # Coverage: % of suppliers with questionnaire_status = 'submitted'
        submitted = sum(1 for s in supplier_list if s.get("questionnaire_status") == "submitted")
        coverage_pct = round(submitted / total * 100, 1) if total > 0 else 0.0

        return {
            "buyer_org_name": buyer_org_name,
            "suppliers": supplier_list,
            "metrics": metrics,
            "risk_flags": [
                {
                    "id": rf["id"],
                    "supplier_name": rf.get("supplier_name"),
                    "flag_text": rf["flag_text"],
                    "cluster": rf["cluster"],
                    "severity": rf["severity"],
                    "priority_score": rf["priority_score"],
                    "created_at": rf["created_at"],
                }
                for rf in risk_flags
            ],
            "evidence_count": len(evidence),
            "evidence_summary": {
                "total_entries": len(evidence),
                "latest_entry": evidence[0]["recorded_at"] if evidence else None,
            },
            "summary": {
                "total_suppliers": total,
                "average_score": avg_score,
                "coverage_pct": coverage_pct,
            },
        }
    finally:
        release_connection(conn)


@router.delete("/{access_id}")
def revoke_buyer_access(
    access_id: str,
    user: dict = Depends(require_auth),
):
    """Revoke buyer portal access."""
    from src.api.middleware.rbac import EDITOR_ROLES, require_role

    require_role(user, EDITOR_ROLES)

    org_id = user["org_id"]

    conn = get_connection()
    try:
        result = conn.execute(
            "UPDATE buyer_portal_access SET is_active = 0 WHERE id = ? AND org_id = ?",
            (access_id, org_id),
        )
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="not found")
        return {"revoked": True}
    finally:
        release_connection(conn)
