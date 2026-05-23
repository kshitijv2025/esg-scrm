"""
Water metrics API — wastewater discharge and water stress tracking.
"""

from fastapi import APIRouter, Depends

from src.api.middleware.auth import require_auth
from src.db.database import fetch_suppliers, fetch_wastewater_data

router = APIRouter()

# WRI Aqueduct water stress classification by country code
WATER_STRESS_BY_COUNTRY: dict[str, str] = {
    "BD": "Low",
    "IN": "High",
    "CN": "Medium-High",
    "VN": "Low",
    "TR": "Extremely High",
    "TH": "Low-Medium",
    "MM": "Low",
    "ID": "Low-Medium",
}

VALID_STRESS_LEVELS = frozenset(
    {
        "Low",
        "Low-Medium",
        "Medium-High",
        "High",
        "Extremely High",
    }
)


def get_water_stress_for_country(country_code: str) -> str:
    """Return WRI Aqueduct water stress level for a country code.

    Returns 'Unknown' for unmapped countries.
    """
    return WATER_STRESS_BY_COUNTRY.get(country_code, "Unknown")


@router.get("/wastewater")
def wastewater(user: dict = Depends(require_auth)):
    """Return wastewater discharge data, water stress level, and supplier stress mapping."""
    org_id = user["org_id"]
    data = fetch_wastewater_data(org_id)

    suppliers = fetch_suppliers(org_id=org_id)
    supplier_water_stress = [
        {
            "supplier_id": s["id"],
            "supplier_name": s["name"],
            "country": s["country"],
            "water_stress_level": get_water_stress_for_country(s["country"]),
        }
        for s in suppliers
    ]

    return {
        "wastewater_discharge": data["wastewater_discharge"],
        "water_stress_level": data["water_stress_level"],
        "water_consumption_m3": data["water_consumption_m3"],
        "supplier_water_stress": supplier_water_stress,
        "period": data["period"],
        "org_id": org_id,
    }
