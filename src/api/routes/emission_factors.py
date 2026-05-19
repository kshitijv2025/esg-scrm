"""Emission factor API — reference data for carbon calculations."""
from fastapi import APIRouter, HTTPException
from typing import Optional

from src.db.database import fetch_emission_factors, get_connection, release_connection, _fetchall

router = APIRouter()


@router.get("/")
def list_factors(
    category: Optional[str] = None,
    country_code: Optional[str] = None,
    factor_name: Optional[str] = None,
):
    """List emission factors with optional filters."""
    conn = get_connection()
    try:
        query = "SELECT * FROM emission_factors WHERE 1=1"
        params: list = []

        if category:
            query += " AND category = ?"
            params.append(category)
        if country_code:
            query += " AND country_code = ?"
            params.append(country_code)
        if factor_name:
            query += " AND factor_name LIKE ?"
            params.append(f"%{factor_name}%")

        query += " ORDER BY category, factor_name"
        factors = _fetchall(conn, query, tuple(params))
        return {"factors": factors, "total": len(factors)}
    finally:
        release_connection(conn)


@router.get("/categories")
def list_categories():
    """List distinct emission factor categories."""
    conn = get_connection()
    try:
        rows = _fetchall(conn, "SELECT DISTINCT category FROM emission_factors ORDER BY category")
        return {"categories": [r["category"] for r in rows]}
    finally:
        release_connection(conn)


@router.get("/calculate")
def calculate_emissions(
    activity_value: float,
    factor_name: str,
    country_code: str = "",
):
    """Calculate emissions from activity data using the matching emission factor."""
    factors = fetch_emission_factors(factor_name=factor_name, country_code=country_code)

    if not factors:
        conn = get_connection()
        try:
            factors = _fetchall(conn, "SELECT * FROM emission_factors WHERE factor_name LIKE ?", (f"%{factor_name}%",))
            if not factors:
                raise HTTPException(status_code=404, detail=f"No emission factor found for '{factor_name}'")
            factor = factors[0]
        finally:
            release_connection(conn)
    else:
        factor = factors[0]

    emissions = activity_value * factor["factor_value"]

    return {
        "activity_value": activity_value,
        "activity_unit": factor["unit"].split("/")[0].replace("kgCO2e/", "").replace("kgCO2/", ""),
        "emission_factor": factor["factor_value"],
        "factor_unit": factor["unit"],
        "factor_source": factor["source"],
        "country_code": factor["country_code"] or "global",
        "calculated_emissions": round(emissions, 4),
        "emissions_unit": factor["unit"].split("/")[-1] if "/" in factor["unit"] else "kgCO2e",
    }
