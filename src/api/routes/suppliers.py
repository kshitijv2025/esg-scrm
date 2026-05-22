"""
Supplier API — backed by SQLite database.
"""

import csv
import io
import uuid
from typing import Any, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import require_role, EDITOR_ROLES
from src.api.routes.billing import _check_plan_limit
from src.db.database import (
    fetch_suppliers,
    fetch_supplier,
    fetch_supplier_scope3,
    fetch_questionnaire_responses,
    fetch_coverage_stats,
    get_connection,
    release_connection,
    _fetchall,
)
from src.ml.scoring import compute_esg_score, persist_score

router = APIRouter()

ALLOWED_EXCHANGE_FORMATS = {"csv", "json", "xlsx"}
EXCHANGE_SCOPES = {"default", "scope3", "country_risk", "summary"}


def _require_auth(user: dict = Depends(require_auth)) -> dict:
    return user


@router.get("/")
def list_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    user: dict = Depends(require_auth),
):
    org_id = user["org_id"]
    suppliers = fetch_suppliers(org_id=org_id, skip=skip, limit=limit)
    return {"suppliers": suppliers, "total": len(suppliers)}


# ---------------------------------------------------------------------------
# D7.7: Supplier Exchange — GET /api/suppliers/exchange
# ---------------------------------------------------------------------------


@router.get("/exchange", response_model=None)
def exchange_suppliers(
    format: str = Query("json", description="Export format: csv, json, or xlsx"),
    scope: str = Query("default", description="Data scope: default, scope3, country_risk, summary"),
    user: dict = Depends(require_auth),
) -> Union[StreamingResponse, dict]:
    """Export supplier data in CSV, JSON, or XLSX format."""
    if format not in ALLOWED_EXCHANGE_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{format}'. Allowed: {sorted(ALLOWED_EXCHANGE_FORMATS)}",
        )
    if scope not in EXCHANGE_SCOPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scope '{scope}'. Allowed: {sorted(EXCHANGE_SCOPES)}",
        )

    org_id = user["org_id"]

    if scope == "country_risk":
        suppliers = _fetch_country_risk(org_id)
    elif scope == "scope3":
        suppliers = _fetch_scope3_data(org_id)
    else:
        suppliers = fetch_suppliers(org_id=org_id)

    if format == "csv":
        return _exchange_csv(suppliers, scope)
    elif format == "xlsx":
        return _exchange_xlsx(suppliers, scope)
    else:
        if scope == "scope3":
            return {"scope3": suppliers, "total": len(suppliers)}
        elif scope == "country_risk":
            return {"country_risk": suppliers, "total": len(suppliers)}
        else:
            return {"suppliers": suppliers, "total": len(suppliers)}


def _fetch_country_risk(org_id: str) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = _fetchall(
            conn,
            """
            SELECT DISTINCT s.country, s.name, s.tier,
                   cr.risk_score AS country_risk_score, cr.country_name
            FROM suppliers s
            LEFT JOIN country_risk_scores cr ON cr.country_code = s.country
            WHERE s.org_id = ?
            ORDER BY s.name
            """,
            (org_id,),
        )
        return [dict(r) for r in rows]
    finally:
        release_connection(conn)


def _fetch_scope3_data(org_id: str) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = _fetchall(
            conn,
            """
            SELECT s.id, s.name, s.country, s.tier,
                   s3.annual_spend_usd, s3.scope3_tco2e,
                   s3.category, s3.calculation_method, s3.emission_factor
            FROM suppliers s
            LEFT JOIN supplier_scope3 s3 ON s3.supplier_id = s.id
            WHERE s.org_id = ?
            ORDER BY s.name
            """,
            (org_id,),
        )
        return [dict(r) for r in rows]
    finally:
        release_connection(conn)


def _exchange_csv(suppliers: list[dict[str, Any]], scope: str) -> StreamingResponse:
    output = io.StringIO()
    if not suppliers:
        writer = csv.DictWriter(output, fieldnames=[])
        writer.writeheader()
    else:
        if scope == "summary":
            fieldnames = [
                "id",
                "name",
                "country",
                "tier",
                "risk_score",
                "esg_score",
                "active_flags",
            ]
        elif scope == "scope3":
            fieldnames = [
                "id",
                "name",
                "country",
                "tier",
                "annual_spend_usd",
                "scope3_tco2e",
                "category",
                "calculation_method",
                "emission_factor",
            ]
        elif scope == "country_risk":
            fieldnames = ["country", "name", "tier", "country_risk_score", "country_name"]
        else:
            fieldnames = list(suppliers[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(suppliers)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=suppliers.csv",
        },
    )


def _exchange_xlsx(suppliers: list[dict[str, Any]], scope: str) -> StreamingResponse:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    scope_sheet_names = {"scope3": "Scope3", "country_risk": "CountryRisk", "summary": "Summary"}
    ws.title = scope_sheet_names.get(scope, "Suppliers")
    if suppliers:
        ws.append(list(suppliers[0].keys()))
        for row in suppliers:
            ws.append(list(row.values()))
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=suppliers.xlsx",
        },
    )


# ---------------------------------------------------------------------------
# D7.7: Supplier Exchange — POST /api/suppliers/exchange (import)
# ---------------------------------------------------------------------------


@router.post("/exchange")
def import_suppliers(
    payload: dict,
    user: dict = Depends(require_auth),
):
    """Import or update suppliers from a list of records."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]
    suppliers_list = payload.get("suppliers", [])
    if not isinstance(suppliers_list, list):
        raise HTTPException(status_code=400, detail="'suppliers' must be a list")
    if len(suppliers_list) == 0:
        raise HTTPException(status_code=400, detail="'suppliers' list cannot be empty")

    # Plan limit enforcement: count only NEW imports
    conn = get_connection()
    try:
        org_row = conn.execute("SELECT plan FROM organizations WHERE id = ?", (org_id,)).fetchone()
        plan = org_row["plan"] if org_row else "starter"

        # Count how many are actually new (not updates)
        new_count = 0
        for record in suppliers_list:
            sid = record.get("id")
            if sid:
                exists = conn.execute(
                    "SELECT id FROM suppliers WHERE id = ? AND org_id = ?",
                    (sid, org_id),
                ).fetchone()
                if not exists:
                    new_count += 1
            else:
                new_count += 1

        if new_count > 0:
            _check_plan_limit(conn, org_id, plan, "suppliers")
    finally:
        release_connection(conn)

    imported = 0
    updated = 0
    errors = []
    conn = get_connection()
    try:
        for record in suppliers_list:
            supplier_id = record.get("id") or f"sup_{uuid.uuid4().hex[:8]}"

            # Validate required fields
            name = record.get("name", "").strip() if record.get("name") else ""
            country = record.get("country", "").strip() if record.get("country") else ""
            if not name:
                errors.append({"id": supplier_id, "error": "name is required"})
                continue
            if not country:
                errors.append({"id": supplier_id, "error": "country is required"})
                continue
            existing = conn.execute(
                "SELECT id FROM suppliers WHERE id = ? AND org_id = ?",
                (supplier_id, org_id),
            ).fetchone()

            if existing:
                # Update existing — use COALESCE to handle None for NOT NULL columns
                conn.execute(
                    """UPDATE suppliers SET
                        name = ?, country = ?, tier = ?, industry = ?,
                        annual_spend_usd = COALESCE(?, annual_spend_usd),
                        updated_at = datetime('now')
                    WHERE id = ? AND org_id = ?""",
                    (
                        name,
                        country,
                        record.get("tier", "tier1"),
                        record.get("industry", ""),
                        record.get("annual_spend_usd"),
                        supplier_id,
                        org_id,
                    ),
                )
                updated += 1
            else:
                conn.execute(
                    """INSERT INTO suppliers
                        (id, org_id, name, country, tier, industry, annual_spend_usd)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        supplier_id,
                        org_id,
                        name,
                        country,
                        record.get("tier", "tier1"),
                        record.get("industry", ""),
                        record.get("annual_spend_usd") or 0,
                    ),
                )
                imported += 1

        conn.commit()
    finally:
        release_connection(conn)

    return {"imported": imported, "updated": updated, "total": imported + updated, "errors": errors}


# ---------------------------------------------------------------------------
# D7.7: Supplier Exchange — POST /api/suppliers/exchange/batch (batch update)
# ---------------------------------------------------------------------------


_UPDATABLE_SUPPLIER_FIELDS = frozenset(
    {
        "name",
        "country",
        "industry",
        "tier",
        "annual_spend_usd",
        "phone",
        "email",
        "preferred_channel",
        "relationship_status",
        "questionnaire_status",
        "certifications",
    }
)


@router.post("/exchange/batch")
def batch_update_suppliers(
    payload: dict,
    user: dict = Depends(require_auth),
):
    """Batch-update supplier fields by ID."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]
    updates = payload.get("updates", [])
    if not isinstance(updates, list):
        raise HTTPException(status_code=400, detail="'updates' must be a list")
    if len(updates) == 0:
        raise HTTPException(status_code=400, detail="'updates' list cannot be empty")

    updated = 0
    errors = []
    conn = get_connection()
    try:
        for item in updates:
            supplier_id = item.get("id") or item.get("supplier_id")
            if not supplier_id:
                errors.append({"id": None, "error": "supplier id is required"})
                continue
            # Only update if belongs to org
            existing = conn.execute(
                "SELECT id FROM suppliers WHERE id = ? AND org_id = ?",
                (supplier_id, org_id),
            ).fetchone()
            if not existing:
                errors.append({"id": supplier_id, "error": "supplier not found"})
                continue
            fields = {k: v for k, v in item.items() if k in _UPDATABLE_SUPPLIER_FIELDS}
            if not fields:
                errors.append({"id": supplier_id, "error": "no fields to update"})
                continue
            set_clause = ", ".join([f"{k} = ?" for k in fields])
            values = list(fields.values()) + [supplier_id, org_id]
            conn.execute(
                f"UPDATE suppliers SET {set_clause}, updated_at = datetime('now') "
                f"WHERE id = ? AND org_id = ?",
                values,
            )
            updated += 1
        conn.commit()
    finally:
        release_connection(conn)

    return {"updated": updated, "errors": errors}


@router.get("/risk-ranked")
def get_risk_ranked(
    skip: int = 0,
    limit: int = 50,
    user: dict = Depends(require_auth),
):
    """Return suppliers sorted by composite risk score (ascending = lowest risk first)."""
    org_id = user["org_id"]
    suppliers = fetch_suppliers(org_id=org_id, skip=skip, limit=limit)
    ranked = sorted(suppliers, key=lambda s: s.get("risk_score", 0))
    return {"suppliers": ranked, "total": len(ranked)}


@router.get("/{supplier_id}")
def get_supplier(
    supplier_id: str,
    user: dict = Depends(require_auth),
):
    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="not found")
    if supplier.get("org_id") and supplier["org_id"] != user["org_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return supplier


@router.get("/{supplier_id}/score")
def get_supplier_score(
    supplier_id: str,
    user: dict = Depends(require_auth),
):
    """ESG score breakdown for a supplier (E/S/G dimensions + composite)."""
    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if supplier.get("org_id") and supplier["org_id"] != user["org_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = compute_esg_score(
        supplier_id=supplier_id,
        industry=supplier.get("industry", ""),
        org_id=user["org_id"],
    )
    if not result:
        raise HTTPException(status_code=404, detail="No questionnaire responses found for supplier")

    persist_score(supplier_id, result)

    return {
        "supplier_id": result.supplier_id,
        "composite_score": result.composite_score,
        "risk_tier": result.risk_tier,
        "environment": {
            "score": result.environment.score,
            "question_count": result.environment.question_count,
            "contributions": result.environment.contributions,
        },
        "social": {
            "score": result.social.score,
            "question_count": result.social.question_count,
            "contributions": result.social.contributions,
        },
        "governance": {
            "score": result.governance.score,
            "question_count": result.governance.question_count,
            "contributions": result.governance.contributions,
        },
        "methodology": result.methodology,
        "weights_used": result.weights_used,
    }


@router.get("/{supplier_id}/profile")
def get_supplier_profile(
    supplier_id: str,
    user: dict = Depends(require_auth),
):
    """Full ESG profile for a supplier."""
    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="not found")
    if supplier.get("org_id") and supplier["org_id"] != user["org_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    responses = fetch_questionnaire_responses(supplier_id)
    clusters = _compute_profile_clusters(responses)

    return {
        "supplier_id": supplier_id,
        "name": supplier["name"],
        "country": supplier["country"],
        "tier": supplier["tier"],
        "overall_risk_score": supplier.get("risk_score"),
        "risk_tier": supplier.get("risk_tier"),
        "financial_health_score": supplier.get("financial_health_score"),
        "scope3_coverage_pct": _compute_scope3_coverage(supplier, user["org_id"]),
        "traceability_status": "full_chain"
        if supplier.get("questionnaire_status") == "responded"
        else "partial",
        "active_flags": supplier.get("active_flags", 0),
        "certifications": (supplier.get("certifications") or "").split(",")
        if supplier.get("certifications")
        else [],
        "clusters": clusters,
        "ml_recommendations": _generate_recommendations(supplier, clusters),
    }


@router.get("/{supplier_id}/scope3")
def supplier_scope3(
    supplier_id: str,
    user: dict = Depends(require_auth),
):
    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="not found")
    if supplier.get("org_id") and supplier["org_id"] != user["org_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

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

    # Fallback: spend-based estimate using emission factor table
    ef = _get_spend_based_factor(supplier.get("industry", ""), user["org_id"])
    tco2e = round(supplier["annual_spend_usd"] * ef["factor_value"] / 1000, 1)
    return {
        "supplier_name": supplier["name"],
        "category": ef["category"],
        "annual_spend_usd": supplier["annual_spend_usd"],
        "scope3_tco2e": tco2e,
        "calculation_method": "spend_based_estimate",
        "emission_factor": f"{ef['source']} — {ef['factor_name']}",
        "confidence": "LOW",
        "data_source": "Spend-based estimate — supplier not yet responded",
    }


# ---------------------------------------------------------------------------
# B3.13: Supplier Improvement Timeline
# ---------------------------------------------------------------------------


@router.get("/{supplier_id}/improvement-timeline")
def get_improvement_timeline(
    supplier_id: str,
    user: dict = Depends(require_auth),
):
    """Year-over-year ESG score trend per dimension with trend classification.

    Returns scores for each of 3 dimensions (environmental, social, governance)
    with trend direction derived from delta vs prior year.
    """
    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if supplier.get("org_id") and supplier["org_id"] != user["org_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    responses = fetch_questionnaire_responses(supplier_id)

    if not responses:
        # Return baseline structure with no data
        return {
            "supplier_id": supplier_id,
            "years": [],
            "dimensions": {
                "environmental": {"score": None, "trend": "stable", "delta": 0},
                "social": {"score": None, "trend": "stable", "delta": 0},
                "governance": {"score": None, "trend": "stable", "delta": 0},
            },
            "overall_trend": "stable",
        }

    # Group responses by tier (year) and dimension
    # tier 1 = year 1, tier 2 = year 2, etc.
    dim_scores: dict[str, dict[int, list[float]]] = {
        "environmental": {},
        "social": {},
        "governance": {},
    }

    # Map question_ids to dimensions using scoring rules
    scoring_rules = {
        "T1Q4": "social",
        "T1Q5": "social",
        "T1Q6": "governance",
        "T1Q8": "governance",
        "T3Q2": "social",
        "T3Q3": "governance",
    }
    # Environmental dimension from any env-labelled questions
    env_qids = {"T1Q1", "T1Q2", "T1Q3", "T2Q1", "T2Q2", "T2Q3"}

    for r in responses:
        qid = r.get("question_id", "")
        val = r.get("response_value")
        tier = r.get("tier", 1)
        if val is None:
            continue

        # Determine dimension
        if qid in scoring_rules:
            dim = scoring_rules[qid]
        elif qid in env_qids:
            dim = "environmental"
        else:
            # Try to infer from question prefix
            if qid.startswith("T2"):
                dim = "environmental"
            elif qid.startswith("T3"):
                dim = "social"
            else:
                dim = "governance"

        if tier not in dim_scores[dim]:
            dim_scores[dim][tier] = []
        dim_scores[dim][tier].append(float(val))

    # Compute average score per dimension per year
    years = sorted({r.get("tier", 1) for r in responses})

    def avg(lst: list[float]) -> float:
        return round(sum(lst) / len(lst)) if lst else 0.0

    dimension_result = {}
    overall_trend = "stable"
    prev_overall = None

    for dim_name in ("environmental", "social", "governance"):
        year_scores = {}
        for yr in years:
            scores = dim_scores[dim_name].get(yr, [])
            year_scores[yr] = avg(scores) if scores else 0.0

        # Compute trend from year-over-year delta
        if len(years) >= 2:
            sorted_yrs = sorted(year_scores.keys())
            delta = year_scores[sorted_yrs[-1]] - year_scores[sorted_yrs[-2]]
        else:
            delta = 0

        if delta > 5:
            trend = "improving"
        elif delta < -5:
            trend = "declining"
        else:
            trend = "stable"

        latest = year_scores.get(years[-1], 0.0) if years else 0.0
        dimension_result[dim_name] = {
            "score": latest,
            "trend": trend,
            "delta": delta,
        }

        # Track overall trend
        if prev_overall is None:
            prev_overall = latest
        else:
            prev_overall = (prev_overall + latest) / 2

    # Determine overall trend
    if len(years) >= 2:
        yr_sorted = sorted(years)
        latest_yr = yr_sorted[-1]
        prev_yr = yr_sorted[-2]
        latest_env = (
            dim_scores["environmental"].get(latest_yr, [0])[-1]
            if dim_scores["environmental"].get(latest_yr)
            else 0
        )
        prev_env = (
            dim_scores["environmental"].get(prev_yr, [0])[-1]
            if dim_scores["environmental"].get(prev_yr)
            else 0
        )
        latest_soc = (
            dim_scores["social"].get(latest_yr, [0])[-1]
            if dim_scores["social"].get(latest_yr)
            else 0
        )
        prev_soc = (
            dim_scores["social"].get(prev_yr, [0])[-1] if dim_scores["social"].get(prev_yr) else 0
        )
        latest_gov = (
            dim_scores["governance"].get(latest_yr, [0])[-1]
            if dim_scores["governance"].get(latest_yr)
            else 0
        )
        prev_gov = (
            dim_scores["governance"].get(prev_yr, [0])[-1]
            if dim_scores["governance"].get(prev_yr)
            else 0
        )

        latest_avg = (latest_env + latest_soc + latest_gov) / 3
        prev_avg = (prev_env + prev_soc + prev_gov) / 3
        overall_delta = latest_avg - prev_avg

        if overall_delta > 5:
            overall_trend = "improving"
        elif overall_delta < -5:
            overall_trend = "declining"
        else:
            overall_trend = "stable"

    return {
        "supplier_id": supplier_id,
        "years": years,
        "dimensions": dimension_result,
        "overall_trend": overall_trend,
    }


# Default profile scores when no questionnaire responses exist
_DEFAULT_CLUSTERS = {
    "labour_rights": 0,
    "environment": 0,
    "governance": 0,
    "safety": 0,
    "gender": 0,
}

_CLUSTER_MAP = {
    "labour": "labour_rights",
    "environment": "environment",
    "governance": "governance",
    "safety": "safety",
    "gender": "gender",
}


def _compute_profile_clusters(responses: list) -> dict:
    """Compute ESG cluster scores from questionnaire responses (0-100 scale)."""
    if not responses:
        return _DEFAULT_CLUSTERS.copy()
    clusters: dict[str, list[float]] = {k: [] for k in _DEFAULT_CLUSTERS}
    for r in responses:
        qid = r.get("question_id", "")
        val = r.get("response_value")
        if val is None:
            continue
        for prefix, cluster_key in _CLUSTER_MAP.items():
            if prefix in qid.lower():
                clusters[cluster_key].append(float(val))
                break
    result = {}
    for key, values in clusters.items():
        if values:
            avg = sum(values) / len(values)
            result[key] = min(100, max(0, round(avg)))
        else:
            result[key] = 0
    return result


def _generate_recommendations(supplier: dict, clusters: dict) -> list[str]:
    """Generate supplier-specific recommendations based on risk and cluster scores."""
    recs = []
    tier = supplier.get("tier", "")
    risk_score = supplier.get("risk_score", 0)
    qs = supplier.get("questionnaire_status", "")

    if qs != "responded" and tier in ("tier2", "tier3"):
        recs.append(f"Initiate follow-up questionnaire for {tier} supplier {supplier['name']}")
    if clusters.get("labour_rights", 0) < 60:
        recs.append(
            f"Schedule third-party audit for {supplier['name']} — "
            "labour rights score below threshold"
        )
    if clusters.get("environment", 0) < 50:
        recs.append(
            f"Request supplier-specific emission data from {supplier['name']} "
            "for accurate Scope 3 reporting"
        )
    if risk_score and risk_score > 70:
        recs.append(
            f"High-risk supplier ({supplier['name']}) — consider alternative sourcing or escalation"
        )
    if not recs:
        recs.append("No immediate actions required — continue monitoring")
    return recs


def _compute_scope3_coverage(supplier: dict, org_id: str) -> int:
    """Compute real scope3 coverage percentage from questionnaire responses."""
    if supplier.get("questionnaire_status") != "responded":
        return 0
    stats = fetch_coverage_stats(org_id=org_id)
    return stats.get("spend_coverage_pct", 0)


def _get_spend_based_factor(industry: str, org_id: str) -> dict:
    """Look up spend-based emission factor from the emission_factors table."""
    conn = get_connection()
    try:
        rows = _fetchall(
            conn,
            """
            SELECT factor_name, category, factor_value, unit, source
            FROM emission_factors
            WHERE category = 'scope3_spend' AND (org_id = ? OR org_id = '' OR org_id IS NULL)
            ORDER BY CASE WHEN org_id = ? THEN 0 ELSE 1 END
            LIMIT 1
        """,
            (org_id, org_id),
        )
        if rows:
            r = rows[0]
            return {
                "factor_name": r["factor_name"],
                "category": r["category"],
                "factor_value": r["factor_value"],
                "unit": r["unit"],
                "source": r["source"],
            }
        return {
            "factor_name": "Generic spend-based (textiles)",
            "category": "spend_based",
            "factor_value": 0.94,
            "unit": "kgCO2e/USD",
            "source": "GHG Protocol 2022 fallback",
        }
    finally:
        release_connection(conn)
