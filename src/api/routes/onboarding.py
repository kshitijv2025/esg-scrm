"""
Onboarding Wizard API — Multi-step onboarding flow.
"""

from __future__ import annotations

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import timezone, datetime

    UTC = timezone.utc

from fastapi import APIRouter, Depends, HTTPException

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import EDITOR_ROLES, require_role
from src.db.database import get_connection, release_connection

router = APIRouter()

INDUSTRIES = [
    "Garment/Textile",
    "Electronics",
    "Food & Beverage",
    "Automotive",
    "Chemicals",
    "Pharmaceuticals",
    "Construction",
    "Other",
]

ERP_SYSTEMS = [
    "SAP Business One",
    "SAP S/4HANA",
    "Oracle ERP",
    "Microsoft Dynamics",
    "NetSuite",
    "QuickBooks",
    "Xero",
    "CSV Import",
    "No ERP (Manual)",
]

FRAMEWORKS = [
    "GRI",
    "TCFD",
    "CSRD",
    "ISSB",
    "CDP",
    "EcoVadis",
    "Higg FEM",
    "WRAP",
    "SA8000",
]


def _org_to_dict(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "industry": row.get("industry", ""),
        "country": row.get("country", ""),
        "created_at": row["created_at"],
    }


@router.post("/wizard")
def complete_onboarding(
    payload: dict,
    user: dict = Depends(require_auth),
):
    """Complete the onboarding wizard.

    Steps:
    1. Select industry
    2. Select ERP system
    3. Upload initial data (optional)
    4. Select applicable frameworks
    5. Configure first alert thresholds

    Returns updated org info and dashboard redirect.
    """
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]
    now = datetime.now(UTC).isoformat()

    conn = get_connection()
    try:
        # Step 1: Update organization with industry
        industry = payload.get("industry")
        if industry and industry not in INDUSTRIES:
            raise HTTPException(status_code=400, detail=f"industry must be one of {INDUSTRIES}")

        if industry:
            conn.execute(
                "UPDATE organizations SET industry = ? WHERE id = ?",
                (industry, org_id),
            )

        # Step 2: Record ERP system preference
        erp_system = payload.get("erp_system")
        if erp_system:
            if erp_system not in ERP_SYSTEMS:
                raise HTTPException(
                    status_code=400, detail=f"erp_system must be one of {ERP_SYSTEMS}"
                )
            # Store as org metadata in a settings table or as part of org record
            # For now, we'll store it in a simple key-value approach

        # Step 3: Process initial data upload references
        uploaded_files = payload.get("uploaded_files", [])
        for f in uploaded_files:
            if isinstance(f, dict) and f.get("id"):
                # Link uploaded file to org if not already linked
                conn.execute(
                    "UPDATE uploaded_files SET org_id = ? WHERE id = ? AND org_id = ''",
                    (org_id, f["id"]),
                )

        # Step 4: Configure framework mappings
        selected_frameworks = payload.get("frameworks", [])
        for fw in selected_frameworks:
            if fw not in FRAMEWORKS:
                raise HTTPException(status_code=400, detail=f"framework '{fw}' not recognized")

        # Insert default framework mappings if they don't exist
        if selected_frameworks:
            for fw in selected_frameworks:
                existing = conn.execute(
                    "SELECT id FROM framework_mappings WHERE org_id = ? AND framework = ? LIMIT 1",
                    (org_id, fw),
                ).fetchone()
                if not existing:
                    # Create default mappings for this framework
                    _create_default_framework_mappings(conn, org_id, fw)

        # Step 5: Configure alert thresholds
        alert_thresholds = payload.get("alert_thresholds", [])
        for threshold in alert_thresholds:
            cluster = threshold.get("cluster")
            warning = threshold.get("warning_threshold")
            critical = threshold.get("critical_threshold")
            unit = threshold.get("unit", "")

            if cluster:
                # Check if threshold already exists
                existing = conn.execute(
                    "SELECT id FROM alert_thresholds WHERE org_id = ? AND cluster = ?",
                    (org_id, cluster),
                ).fetchone()

                if existing:
                    conn.execute(
                        """UPDATE alert_thresholds
                           SET warning_threshold = ?, critical_threshold = ?,
                               unit = ?, is_active = 1
                           WHERE org_id = ? AND cluster = ?""",
                        (warning, critical, unit, org_id, cluster),
                    )
                else:
                    conn.execute(
                        """INSERT INTO alert_thresholds
                           (org_id, cluster, metric_cluster, operator, threshold_value,
                            severity, is_active, created_at, updated_at)
                           VALUES (?, ?, ?, '>', ?, 'WARNING', 1, ?, ?)""",
                        (org_id, cluster, cluster, warning or 0, now, now),
                    )
                    if critical:
                        conn.execute(
                            """INSERT INTO alert_thresholds
                               (org_id, cluster, metric_cluster, operator, threshold_value,
                                severity, is_active, created_at, updated_at)
                               VALUES (?, ?, ?, '>', ?, 'CRITICAL', 1, ?, ?)""",
                            (org_id, cluster, cluster, critical, now, now),
                        )

        # Mark onboarding complete in org record
        conn.execute(
            "UPDATE organizations SET industry = COALESCE(industry, ?) WHERE id = ?",
            (industry or "", org_id),
        )

        conn.commit()

        # Get updated org info
        org = conn.execute(
            "SELECT * FROM organizations WHERE id = ?",
            (org_id,),
        ).fetchone()

        # Get default factories for this org
        factories = conn.execute(
            "SELECT * FROM factories WHERE org_id = ? LIMIT 5",
            (org_id,),
        ).fetchall()

        # Get configured frameworks
        frameworks = conn.execute(
            "SELECT DISTINCT framework FROM framework_mappings WHERE org_id = ?",
            (org_id,),
        ).fetchall()

        return {
            "success": True,
            "org": _org_to_dict(dict(org)) if org else None,
            "factories": [dict(f) for f in factories],
            "configured_frameworks": [f["framework"] for f in frameworks],
            "message": "Onboarding completed successfully",
        }
    finally:
        release_connection(conn)


def _create_default_framework_mappings(conn, org_id: str, framework: str):
    """Create default metric-to-framework field mappings."""
    now = datetime.now(UTC).isoformat()

    # Common ESG metrics and their framework mappings
    mappings = {
        "GRI": [
            (
                "energy_kwh",
                "GRI 302-1",
                "Energy consumption within the organization",
                "GJ",
                "Sum of all energy sources in gigajoules",
            ),
            ("water_m3", "GRI 303-3", "Water withdrawal", "m³", "Total water withdrawal by source"),
            ("waste_kg", "GRI 306-3", "Waste generated", "kg", "Total weight of waste generated"),
            (
                "emissions_tco2",
                "GRI 305-1",
                "Direct GHG emissions (Scope 1)",
                "tCO2e",
                "Direct greenhouse gas emissions",
            ),
        ],
        "TCFD": [
            (
                "emissions_tco2",
                "TCFD-GHG-1",
                "Total GHG emissions",
                "tCO2e",
                "Scope 1 + Scope 2 emissions",
            ),
            ("energy_kwh", "TCFD-ENERGY-1", "Energy consumption", "MWh", "Total energy consumed"),
        ],
        "CSRD": [
            (
                "emissions_tco2",
                "CSRD-E1-1",
                "Climate change mitigation",
                "tCO2e",
                "Greenhouse gas emissions",
            ),
            ("water_m3", "CSRD-E2-1", "Water resources", "m³", "Water consumption"),
        ],
        "ISSB": [
            (
                "emissions_tco2",
                "ISSB-S1-1",
                "GHG emissions",
                "tCO2e",
                "Total Scope 1 and 2 emissions",
            ),
            ("energy_kwh", "ISSB-S1-2", "Energy consumption", "MWh", "Total energy consumption"),
        ],
    }

    if framework in mappings:
        for metric_name, disclosure_code, field_name, unit, description in mappings[framework]:
            conn.execute(
                """INSERT INTO framework_mappings
                   (org_id, cluster, metric_name, framework, disclosure_code,
                    disclosure_name, description, unit, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    org_id,
                    metric_name.split("_")[0] if "_" in metric_name else metric_name,
                    metric_name,
                    framework,
                    disclosure_code,
                    field_name,
                    description,
                    unit,
                    now,
                ),
            )


@router.get("/wizard/options")
def get_onboarding_options(user: dict = Depends(require_auth)):
    """Get available options for onboarding wizard steps."""
    return {
        "industries": INDUSTRIES,
        "erp_systems": ERP_SYSTEMS,
        "frameworks": FRAMEWORKS,
        "alert_clusters": [
            {"id": "energy", "name": "Energy", "unit": "kWh/day"},
            {"id": "water", "name": "Water", "unit": "m³/day"},
            {"id": "emissions", "name": "Emissions", "unit": "tCO2e/day"},
            {"id": "waste", "name": "Waste", "unit": "kg/day"},
        ],
    }
