"""Tier-2 ESG routes — Labour, Workforce Safety, Water, Waste."""

from fastapi import APIRouter, Depends

from src.api.middleware.auth import require_auth
from src.db.database import get_connection, release_connection

router = APIRouter()


@router.get("/labour/audit-summary")
def labour_audit_summary(user: dict = Depends(require_auth)):
    """Return summary of labour audit data for the org.

    Returns audit counts, compliance rates, and recent findings.
    """
    org_id = user["org_id"]

    conn = get_connection()
    try:
        # Total suppliers with labour questionnaire responses
        total_rows = conn.execute(
            """SELECT COUNT(DISTINCT supplier_id) as cnt
               FROM questionnaire_responses qr
               JOIN suppliers s ON s.id = qr.supplier_id
               WHERE s.org_id = ? AND qr.tier = 2""",
            (org_id,),
        ).fetchone()

        # Suppliers with verified responses
        verified_rows = conn.execute(
            """SELECT COUNT(DISTINCT qr.supplier_id) as cnt
               FROM questionnaire_responses qr
               JOIN suppliers s ON s.id = qr.supplier_id
               WHERE s.org_id = ? AND qr.tier = 2 AND qr.validation_status = 'verified'""",
            (org_id,),
        ).fetchone()

        # Recent responses (last 90 days)
        recent_rows = conn.execute(
            """SELECT COUNT(*) as cnt
               FROM questionnaire_responses qr
               JOIN suppliers s ON s.id = qr.supplier_id
               WHERE s.org_id = ? AND qr.tier = 2
               AND qr.responded_at >= datetime('now', '-90 days')""",
            (org_id,),
        ).fetchone()

        # Average response rate
        response_rate_rows = conn.execute(
            """SELECT
                  CAST(SUM(
                      CASE WHEN qr.response_text IS NOT NULL AND qr.response_text != ''
                      THEN 1 ELSE 0 END
                  ) AS REAL) / NULLIF(COUNT(*), 0) * 100 as rate
               FROM questionnaire_responses qr
               JOIN suppliers s ON s.id = qr.supplier_id
               WHERE s.org_id = ? AND qr.tier = 2""",
            (org_id,),
        ).fetchone()

        return {
            "org_id": org_id,
            "total_suppliers_audited": total_rows["cnt"] if total_rows else 0,
            "verified_suppliers": verified_rows["cnt"] if verified_rows else 0,
            "recent_responses_90d": recent_rows["cnt"] if recent_rows else 0,
            "response_rate_percent": round(response_rate_rows["rate"], 1)
            if response_rate_rows and response_rate_rows["rate"]
            else 0,
            "compliance_status": "compliant"
            if (verified_rows["cnt"] if verified_rows else 0) > 0
            else "pending",
        }
    finally:
        release_connection(conn)


@router.get("/workforce/safety")
def workforce_safety(user: dict = Depends(require_auth)):
    """Return workforce safety metrics — incidents, training, certifications.

    Returns aggregated safety data from supplier questionnaires and risk flags.
    """
    org_id = user["org_id"]

    conn = get_connection()
    try:
        # Active risk flags related to safety
        safety_flags = conn.execute(
            """SELECT COUNT(*) as cnt
               FROM risk_flags rf
               WHERE rf.org_id = ?
               AND (rf.flag_text LIKE '%safety%' OR rf.flag_text LIKE '%worker%'
                    OR rf.flag_text LIKE '%incident%' OR rf.flag_text LIKE '%injury%')""",
            (org_id,),
        ).fetchone()

        # Suppliers with safety certifications
        certified_suppliers = conn.execute(
            """SELECT COUNT(*) as cnt
               FROM suppliers
               WHERE org_id = ?
               AND certifications IS NOT NULL
               AND certifications != ''
               AND (certifications LIKE '%ISO 45001%' OR certifications LIKE '%OHSAS%'
                    OR certifications LIKE '%safety%')""",
            (org_id,),
        ).fetchone()

        # Total tier-1 suppliers (direct workforce)
        tier1_suppliers = conn.execute(
            """SELECT COUNT(*) as cnt FROM suppliers
               WHERE org_id = ? AND tier = 'tier1'""",
            (org_id,),
        ).fetchone()

        # Suppliers with recent questionnaire (last 180 days)
        active_suppliers = conn.execute(
            """SELECT COUNT(DISTINCT s.id) as cnt
               FROM suppliers s
               JOIN questionnaire_responses qr ON qr.supplier_id = s.id
               WHERE s.org_id = ? AND s.tier = 'tier1'
               AND qr.responded_at >= datetime('now', '-180 days')""",
            (org_id,),
        ).fetchone()

        # Training completion from questionnaire responses
        training_rows = conn.execute(
            """SELECT COUNT(*) as total,
                  SUM(CASE WHEN qr.response_text LIKE '%yes%'
                       OR qr.response_value > 0 THEN 1 ELSE 0 END) as completed
               FROM questionnaire_responses qr
               JOIN suppliers s ON s.id = qr.supplier_id
               WHERE s.org_id = ? AND s.tier = 'tier1'
               AND qr.question_id LIKE '%training%'""",
            (org_id,),
        ).fetchone()

        return {
            "org_id": org_id,
            "active_safety_flags": safety_flags["cnt"] if safety_flags else 0,
            "certified_suppliers": certified_suppliers["cnt"] if certified_suppliers else 0,
            "total_tier1_suppliers": tier1_suppliers["cnt"] if tier1_suppliers else 0,
            "active_workforce_suppliers_180d": active_suppliers["cnt"] if active_suppliers else 0,
            "training_completion_rate": (
                round(training_rows["completed"] / training_rows["total"] * 100, 1)
                if training_rows and training_rows["total"] and training_rows["total"] > 0
                else 0
            ),
            "period": "last_180_days",
        }
    finally:
        release_connection(conn)


@router.get("/water/by-source")
def water_by_source(user: dict = Depends(require_auth)):
    """Return water usage breakdown by source.

    Returns water withdrawal volumes by source type (municipal, groundwater, surface water, etc.)
    aggregated from metrics data.
    """
    org_id = user["org_id"]

    conn = get_connection()
    try:
        # Get water metrics by cluster/source
        rows = conn.execute(
            """SELECT
                 cluster,
                 SUM(value) as total_volume,
                 AVG(value) as avg_volume,
                 MAX(recorded_at) as last_recorded
               FROM metrics
               WHERE org_id = ?
               AND cluster IN ('water_m3', 'water_groundwater', 'water_surface',
                               'water_municipal', 'water_rainwater', 'water_recycled')
               GROUP BY cluster""",
            (org_id,),
        ).fetchall()

        sources = {}
        total_volume = 0
        for row in rows:
            cluster = row["cluster"]
            volume = row["total_volume"] or 0
            sources[cluster] = {
                "total_m3": round(volume, 2),
                "avg_daily_m3": round(row["avg_volume"] or 0, 2),
                "last_recorded": row["last_recorded"],
            }
            total_volume += volume

        # Water stress data from suppliers
        supplier_countries = conn.execute(
            """SELECT country, COUNT(*) as cnt FROM suppliers
               WHERE org_id = ? GROUP BY country""",
            (org_id,),
        ).fetchall()

        # WRI Aqueduct water stress mapping
        stress_map = {
            "BD": "Low",
            "IN": "High",
            "CN": "Medium-High",
            "VN": "Low",
            "TR": "Extremely High",
            "TH": "Low-Medium",
            "MM": "Low",
            "ID": "Low-Medium",
        }

        supplier_stress = {}
        for sc in supplier_countries:
            stress = stress_map.get(sc["country"], "Unknown")
            if stress not in supplier_stress:
                supplier_stress[stress] = 0
            supplier_stress[stress] += sc["cnt"]

        return {
            "org_id": org_id,
            "total_water_m3": round(total_volume, 2),
            "by_source": sources,
            "supplier_countries_by_stress": supplier_stress,
            "period": "all_time",
        }
    finally:
        release_connection(conn)


@router.get("/waste/circularity")
def waste_circularity(user: dict = Depends(require_auth)):
    """Return waste and circularity metrics.

    Returns waste generation, recycling rates, and circular economy indicators.
    """
    org_id = user["org_id"]

    conn = get_connection()
    try:
        # Waste metrics from metrics table
        waste_rows = conn.execute(
            """SELECT
                 cluster,
                 SUM(value) as total_volume,
                 AVG(value) as avg_volume
               FROM metrics
               WHERE org_id = ?
               AND cluster IN ('waste_hazardous', 'waste_non_hazardous',
                               'waste_recycled', 'waste_landfill', 'waste_incinerated')
               GROUP BY cluster""",
            (org_id,),
        ).fetchall()

        waste_data = {}
        total_waste = 0
        recycled = 0
        for row in waste_rows:
            vol = row["total_volume"] or 0
            waste_data[row["cluster"]] = round(vol, 2)
            total_waste += vol
            if row["cluster"] == "waste_recycled":
                recycled = vol

        # Circularity from questionnaire data (suppliers with circular economy practices)
        circular_rows = conn.execute(
            """SELECT COUNT(*) as total,
                  SUM(CASE WHEN qr.response_text LIKE '%circular%'
                       OR qr.response_text LIKE '%recycl%'
                       OR qr.response_value > 0 THEN 1 ELSE 0 END) as circular_count
               FROM questionnaire_responses qr
               JOIN suppliers s ON s.id = qr.supplier_id
               WHERE s.org_id = ?
               AND qr.question_id LIKE '%circular%'""",
            (org_id,),
        ).fetchone()

        # Suppliers with zero-waste certifications
        zero_waste_suppliers = conn.execute(
            """SELECT COUNT(*) as cnt FROM suppliers
               WHERE org_id = ?
               AND (certifications LIKE '%zero waste%' OR certifications LIKE '%GRI 306%')""",
            (org_id,),
        ).fetchone()

        return {
            "org_id": org_id,
            "total_waste_tonnes": round(total_waste / 1000 if total_waste else 0, 2),
            "recycled_tonnes": round(recycled / 1000 if recycled else 0, 2),
            "recycling_rate_percent": (
                round(recycled / total_waste * 100, 1) if total_waste and total_waste > 0 else 0
            ),
            "circular_economy_suppliers": (circular_rows["circular_count"] if circular_rows else 0),
            "zero_waste_certified_suppliers": (
                zero_waste_suppliers["cnt"] if zero_waste_suppliers else 0
            ),
            "waste_by_type": waste_data,
            "period": "all_time",
        }
    finally:
        release_connection(conn)
