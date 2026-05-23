"""Tier-3 ESG routes — Governance, Ethics, Traceability, Financial, Fibre."""

from fastapi import APIRouter, Depends

from src.api.middleware.auth import require_auth
from src.db.database import get_connection, release_connection

router = APIRouter()


@router.get("/governance/board")
def governance_board(user: dict = Depends(require_auth)):
    """Return board diversity and governance metrics.

    Returns governance structure, diversity indicators, and ESG oversight mechanisms.
    """
    org_id = user["org_id"]

    conn = get_connection()
    try:
        # Get org details
        org = conn.execute(
            "SELECT name, industry, country FROM organizations WHERE id = ?",
            (org_id,),
        ).fetchone()

        # Active risk flags related to governance
        gov_flags = conn.execute(
            """SELECT COUNT(*) as cnt FROM risk_flags
               WHERE org_id = ?
               AND (flag_text LIKE '%governance%' OR flag_text LIKE '%policy%'
                    OR flag_text LIKE '%compliance%' OR flag_text LIKE '%regulatory%')""",
            (org_id,),
        ).fetchone()

        # Suppliers with governance certifications (ISO 37000, GRI, etc.)
        gov_certified = conn.execute(
            """SELECT COUNT(*) as cnt FROM suppliers
               WHERE org_id = ?
               AND (certifications LIKE '%ISO 37000%' OR certifications LIKE '%GRI%'
                    OR certifications LIKE '%governance%' OR certifications LIKE '%SEDEX%'
                    OR certifications LIKE '%BSCI%')""",
            (org_id,),
        ).fetchone()

        # Tier breakdown for governance visibility
        tier_breakdown = conn.execute(
            """SELECT tier, COUNT(*) as cnt FROM suppliers
               WHERE org_id = ? GROUP BY tier""",
            (org_id,),
        ).fetchall()

        tier_counts = {row["tier"]: row["cnt"] for row in tier_breakdown}

        # Average ESG score across suppliers
        avg_esg = conn.execute(
            """SELECT AVG(esg_score) as avg_score FROM suppliers
               WHERE org_id = ? AND esg_score IS NOT NULL""",
            (org_id,),
        ).fetchone()

        # Suppliers with active flags (governance concerns)
        flagged_suppliers = conn.execute(
            """SELECT COUNT(*) as cnt FROM suppliers
               WHERE org_id = ? AND active_flags > 0""",
            (org_id,),
        ).fetchone()

        return {
            "org_id": org_id,
            "org_name": org["name"] if org else "Unknown",
            "industry": org["industry"] if org else "",
            "governance_certified_suppliers": gov_certified["cnt"] if gov_certified else 0,
            "governance_flags": gov_flags["cnt"] if gov_flags else 0,
            "supplier_tier_breakdown": tier_counts,
            "average_esg_score": round(avg_esg["avg_score"], 1)
            if avg_esg and avg_esg["avg_score"]
            else None,
            "suppliers_with_active_flags": flagged_suppliers["cnt"] if flagged_suppliers else 0,
            "governance_status": "active"
            if (gov_flags["cnt"] if gov_flags else 0) == 0
            else "review_required",
        }
    finally:
        release_connection(conn)


@router.get("/ethics/incidents")
def ethics_incidents(user: dict = Depends(require_auth)):
    """Return ethics incidents and violations data.

    Returns counts of ethics-related incidents, violations, and remediation status.
    """
    org_id = user["org_id"]

    conn = get_connection()
    try:
        # Ethics-related risk flags (discrimination, harassment, corruption, etc.)
        ethics_flags = conn.execute(
            """SELECT COUNT(*) as cnt,
                  SUM(CASE WHEN severity = 'CRITICAL' THEN 1 ELSE 0 END) as critical_cnt,
                  SUM(CASE WHEN acknowledged = 1 THEN 1 ELSE 0 END) as acknowledged_cnt
               FROM risk_flags
               WHERE org_id = ?
               AND (flag_text LIKE '%ethics%' OR flag_text LIKE '%discrimination%'
                    OR flag_text LIKE '%harassment%' OR flag_text LIKE '%corruption%'
                    OR flag_text LIKE '%bribery%' OR flag_text LIKE '%fraud%'
                    OR flag_text LIKE '%whistleblow%' OR flag_text LIKE '%human rights%')""",
            (org_id,),
        ).fetchone()

        # Suppliers with ethics certifications
        ethics_certified = conn.execute(
            """SELECT COUNT(*) as cnt FROM suppliers
               WHERE org_id = ?
               AND (certifications LIKE '%ISO 37001%' OR certifications LIKE '%ethics%'
                    OR certifications LIKE '%SA8000%' OR certifications LIKE '%RBA%'
                    OR certifications LIKE '%ethical trade%')""",
            (org_id,),
        ).fetchone()

        # Tier-1 suppliers (most exposed to ethics risks)
        tier1_count = conn.execute(
            """SELECT COUNT(*) as cnt FROM suppliers
               WHERE org_id = ? AND tier = 'tier1'""",
            (org_id,),
        ).fetchone()

        # Suppliers with recent ethics-related questionnaire responses
        recent_ethics = conn.execute(
            """SELECT COUNT(DISTINCT s.id) as cnt
               FROM suppliers s
               JOIN questionnaire_responses qr ON qr.supplier_id = s.id
               WHERE s.org_id = ? AND s.tier = 'tier1'
               AND (qr.question_id LIKE '%ethics%' OR qr.question_id LIKE '%labour%'
                    OR qr.question_id LIKE '%human rights%')
               AND qr.responded_at >= datetime('now', '-180 days')""",
            (org_id,),
        ).fetchone()

        return {
            "org_id": org_id,
            "total_incidents": ethics_flags["cnt"] if ethics_flags else 0,
            "critical_incidents": ethics_flags["critical_cnt"] if ethics_flags else 0,
            "acknowledged_incidents": ethics_flags["acknowledged_cnt"] if ethics_flags else 0,
            "ethics_certified_suppliers": ethics_certified["cnt"] if ethics_certified else 0,
            "tier1_suppliers_at_risk": tier1_count["cnt"] if tier1_count else 0,
            "suppliers_with_recent_ethics_data_180d": recent_ethics["cnt"] if recent_ethics else 0,
            "ethics_status": "clear"
            if (ethics_flags["cnt"] if ethics_flags else 0) == 0
            else "attention_required",
        }
    finally:
        release_connection(conn)


@router.get("/traceability/certifications")
def traceability_certifications(user: dict = Depends(require_auth)):
    """Return supplier certifications and traceability metrics.

    Returns certification coverage, traceability scores, and chain of custody data.
    """
    org_id = user["org_id"]

    conn = get_connection()
    try:
        # Total suppliers with certifications
        certified = conn.execute(
            """SELECT COUNT(*) as cnt FROM suppliers
               WHERE org_id = ? AND certifications IS NOT NULL AND certifications != ''""",
            (org_id,),
        ).fetchone()

        # Suppliers by certification type
        cert_rows = conn.execute(
            """SELECT certifications FROM suppliers
               WHERE org_id = ? AND certifications IS NOT NULL AND certifications != ''""",
            (org_id,),
        ).fetchall()

        cert_counts = {}
        for row in cert_rows:
            certs = row["certifications"].split(",")
            for cert in certs:
                cert = cert.strip()
                if cert:
                    cert_counts[cert] = cert_counts.get(cert, 0) + 1

        # Suppliers with evidence chain records (traceability evidence)
        traced_suppliers = conn.execute(
            """SELECT COUNT(DISTINCT s.id) as cnt
               FROM suppliers s
               JOIN evidence_chain ec ON ec.org_id = s.org_id
               WHERE s.org_id = ?""",
            (org_id,),
        ).fetchone()

        # Total evidence chain records
        evidence_count = conn.execute(
            """SELECT COUNT(*) as cnt FROM evidence_chain WHERE org_id = ?""",
            (org_id,),
        ).fetchone()

        # Suppliers by tier
        tier_counts = conn.execute(
            """SELECT tier, COUNT(*) as cnt FROM suppliers WHERE org_id = ? GROUP BY tier""",
            (org_id,),
        ).fetchall()

        tier_breakdown = {row["tier"]: row["cnt"] for row in tier_counts}

        # Questionnaire coverage by tier
        questionnaire_coverage = {}
        for tier in ["tier1", "tier2", "tier3"]:
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM suppliers WHERE org_id = ? AND tier = ?",
                (org_id, tier),
            ).fetchone()
            responded = conn.execute(
                """SELECT COUNT(DISTINCT s.id) as cnt
                   FROM suppliers s
                   JOIN questionnaire_responses qr ON qr.supplier_id = s.id
                   WHERE s.org_id = ? AND s.tier = ?""",
                (org_id, tier),
            ).fetchone()
            questionnaire_coverage[tier] = {
                "total": total["cnt"] if total else 0,
                "responded": responded["cnt"] if responded else 0,
                "coverage_percent": (
                    round(responded["cnt"] / total["cnt"] * 100, 1)
                    if total and total["cnt"] > 0
                    else 0
                ),
            }

        return {
            "org_id": org_id,
            "certified_suppliers": certified["cnt"] if certified else 0,
            "certification_types": cert_counts,
            "traceability_coverage": {
                "suppliers_with_evidence": traced_suppliers["cnt"] if traced_suppliers else 0,
                "total_evidence_records": evidence_count["cnt"] if evidence_count else 0,
            },
            "supplier_tier_breakdown": tier_breakdown,
            "questionnaire_coverage_by_tier": questionnaire_coverage,
        }
    finally:
        release_connection(conn)


@router.get("/suppliers/financial-health")
def suppliers_financial_health(user: dict = Depends(require_auth)):
    """Return supplier financial health indicators.

    Returns financial risk assessment based on Scope 3 data and supplier metrics.
    """
    org_id = user["org_id"]

    conn = get_connection()
    try:
        # Average ESG score as proxy for financial health
        avg_esg = conn.execute(
            """SELECT AVG(esg_score) as avg_score,
                     MIN(esg_score) as min_score,
                     MAX(esg_score) as max_score
               FROM suppliers WHERE org_id = ? AND esg_score IS NOT NULL""",
            (org_id,),
        ).fetchone()

        # Suppliers by risk tier
        risk_tier_counts = conn.execute(
            """SELECT risk_tier, COUNT(*) as cnt
               FROM suppliers WHERE org_id = ? AND risk_tier IS NOT NULL
               GROUP BY risk_tier""",
            (org_id,),
        ).fetchall()
        risk_tiers = {row["risk_tier"]: row["cnt"] for row in risk_tier_counts}

        # Total annual spend across suppliers
        total_spend = conn.execute(
            """SELECT SUM(annual_spend_usd) as total FROM suppliers WHERE org_id = ?""",
            (org_id,),
        ).fetchone()

        # Scope 3 emissions as financial risk indicator
        scope3_rows = conn.execute(
            """SELECT
                 SUM(scope3_tco2e) as total_tco2e,
                 AVG(scope3_tco2e) as avg_tco2e
               FROM supplier_scope3 WHERE org_id = ?""",
            (org_id,),
        ).fetchone()

        # Suppliers with missing ESG scores (unknown financial health)
        unknown_health = conn.execute(
            """SELECT COUNT(*) as cnt FROM suppliers
               WHERE org_id = ? AND (esg_score IS NULL OR risk_tier IS NULL)""",
            (org_id,),
        ).fetchone()

        # High-risk suppliers (Tier D or very low ESG score)
        high_risk = conn.execute(
            """SELECT COUNT(*) as cnt FROM suppliers
               WHERE org_id = ? AND (risk_tier = 'D' OR esg_score < 30)""",
            (org_id,),
        ).fetchone()

        return {
            "org_id": org_id,
            "average_esg_score": round(avg_esg["avg_score"], 1)
            if avg_esg and avg_esg["avg_score"]
            else None,
            "esg_score_range": {
                "min": round(avg_esg["min_score"], 1) if avg_esg and avg_esg["min_score"] else None,
                "max": round(avg_esg["max_score"], 1) if avg_esg and avg_esg["max_score"] else None,
            },
            "risk_tier_distribution": risk_tiers,
            "total_annual_supplier_spend_usd": round(total_spend["total"], 2)
            if total_spend and total_spend["total"]
            else 0,
            "total_scope3_tco2e": round(scope3_rows["total_tco2e"], 2)
            if scope3_rows and scope3_rows["total_tco2e"]
            else 0,
            "avg_scope3_per_supplier": round(scope3_rows["avg_tco2e"], 2)
            if scope3_rows and scope3_rows["avg_tco2e"]
            else 0,
            "suppliers_unknown_financial_health": unknown_health["cnt"] if unknown_health else 0,
            "high_risk_suppliers": high_risk["cnt"] if high_risk else 0,
        }
    finally:
        release_connection(conn)


@router.get("/fibre/mix")
def fibre_mix(user: dict = Depends(require_auth)):
    """Return fibre and material sourcing mix.

    Returns breakdown of material sources (organic, recycled, conventional, etc.)
    and supplier composition by material type.
    """
    org_id = user["org_id"]

    conn = get_connection()
    try:
        # Get supplier industries as proxy for fibre/material types
        industry_counts = conn.execute(
            """SELECT industry, COUNT(*) as cnt,
                      SUM(annual_spend_usd) as total_spend
               FROM suppliers
               WHERE org_id = ? AND industry IS NOT NULL AND industry != ''
               GROUP BY industry
               ORDER BY total_spend DESC""",
            (org_id,),
        ).fetchall()

        industry_breakdown = [
            {
                "industry": row["industry"],
                "supplier_count": row["cnt"],
                "annual_spend_usd": round(row["total_spend"], 2) if row["total_spend"] else 0,
            }
            for row in industry_counts
        ]

        # Total suppliers
        total_suppliers = conn.execute(
            "SELECT COUNT(*) as cnt FROM suppliers WHERE org_id = ?",
            (org_id,),
        ).fetchone()

        total_spend = conn.execute(
            "SELECT SUM(annual_spend_usd) as total FROM suppliers WHERE org_id = ?",
            (org_id,),
        ).fetchone()

        # Certified materials (organic, GOTS, Oeko-Tex, etc.)
        certified_materials = conn.execute(
            """SELECT COUNT(*) as cnt FROM suppliers
               WHERE org_id = ?
               AND (certifications LIKE '%organic%' OR certifications LIKE '%GOTS%'
                    OR certifications LIKE '%Oeko-Tex%' OR certifications LIKE '%FSC%'
                    OR certifications LIKE '%GRS%' OR certifications LIKE '%RDS%')""",
            (org_id,),
        ).fetchone()

        # Suppliers by country (geographic sourcing diversity)
        country_counts = conn.execute(
            """SELECT country, COUNT(*) as cnt,
                      SUM(annual_spend_usd) as total_spend
               FROM suppliers
               WHERE org_id = ? AND country IS NOT NULL AND country != ''
               GROUP BY country
               ORDER BY total_spend DESC""",
            (org_id,),
        ).fetchall()

        geographic_breakdown = [
            {
                "country": row["country"],
                "supplier_count": row["cnt"],
                "annual_spend_usd": round(row["total_spend"], 2) if row["total_spend"] else 0,
            }
            for row in country_counts
        ]

        return {
            "org_id": org_id,
            "total_suppliers": total_suppliers["cnt"] if total_suppliers else 0,
            "total_annual_spend_usd": round(total_spend["total"], 2)
            if total_spend and total_spend["total"]
            else 0,
            "certified_materials_suppliers": certified_materials["cnt"]
            if certified_materials
            else 0,
            "industry_breakdown": industry_breakdown,
            "geographic_sourcing_breakdown": geographic_breakdown,
            "sourcing_diversity_score": len(country_counts) if country_counts else 0,
        }
    finally:
        release_connection(conn)
