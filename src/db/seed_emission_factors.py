"""
Seed the emission_factors table with GHG Protocol 2022 and IPCC AR6 reference
values for garment/textile supply chain calculations.

These are global reference factors (org_id = '') used as defaults when no
organisation-specific factor has been set.

Sources:
  - GHG Protocol, Emission Factors from Cross-Sector Tools (March 2022)
  - IPCC Sixth Assessment Report (AR6), Working Group I, Chapter 7 (2021)
  - IEA "Emission Factors 2022" for country-specific grid intensities
  - DEFRA/DESNZ UK Government GHG Conversion Factors for Company Reporting
    (2022, consolidated)

Run:  python -m src.db.seed_emission_factors
"""

from src.db.database import get_connection, release_connection, _execute

# ---------------------------------------------------------------------------
# Emission factor tuples: (factor_name, category, value, unit,
#                          country_code, source, year)
# ---------------------------------------------------------------------------

FACTORS: list[tuple[str, str, float, str, str, str, int]] = [
    # ------------------------------------------------------------------
    # Grid electricity — country-specific emission factors
    # Source: IEA Emission Factors 2022 (kg CO2 / kWh)
    # ------------------------------------------------------------------
    (
        "Electricity grid — Bangladesh",
        "grid_electricity",
        0.73,
        "kgCO2/kWh",
        "BD",
        "IEA Emission Factors 2022",
        2022,
    ),
    (
        "Electricity grid — India",
        "grid_electricity",
        0.82,
        "kgCO2/kWh",
        "IN",
        "IEA Emission Factors 2022",
        2022,
    ),
    (
        "Electricity grid — Vietnam",
        "grid_electricity",
        0.72,
        "kgCO2/kWh",
        "VN",
        "IEA Emission Factors 2022",
        2022,
    ),
    (
        "Electricity grid — Thailand",
        "grid_electricity",
        0.53,
        "kgCO2/kWh",
        "TH",
        "IEA Emission Factors 2022",
        2022,
    ),
    (
        "Electricity grid — Myanmar",
        "grid_electricity",
        0.42,
        "kgCO2/kWh",
        "MM",
        "IEA Emission Factors 2022",
        2022,
    ),
    (
        "Electricity grid — Indonesia",
        "grid_electricity",
        0.76,
        "kgCO2/kWh",
        "ID",
        "IEA Emission Factors 2022",
        2022,
    ),
    (
        "Electricity grid — global average",
        "grid_electricity",
        0.46,
        "kgCO2/kWh",
        "",
        "IEA Emission Factors 2022",
        2022,
    ),
    # ------------------------------------------------------------------
    # Stationary combustion (Scope 1)
    # Source: GHG Protocol Cross-Sector Tools, March 2022, Stationary
    #         Combustion worksheet (kg CO2e per unit of fuel)
    # Values include CO2 + CH4 + N2O on a CO2-equivalent basis.
    # ------------------------------------------------------------------
    (
        "Diesel — stationary combustion",
        "stationary_combustion",
        2.70,
        "kgCO2e/litre",
        "",
        "GHG Protocol 2022 — Stationary Combustion",
        2022,
    ),
    (
        "Natural gas — stationary combustion",
        "stationary_combustion",
        2.02,
        "kgCO2e/m3",
        "",
        "GHG Protocol 2022 — Stationary Combustion",
        2022,
    ),
    (
        "LPG — stationary combustion",
        "stationary_combustion",
        1.69,
        "kgCO2e/litre",
        "",
        "GHG Protocol 2022 — Stationary Combustion",
        2022,
    ),
    (
        "Coal (bituminous) — stationary combustion",
        "stationary_combustion",
        2460.0,
        "kgCO2e/tonne",
        "",
        "GHG Protocol 2022 — Stationary Combustion",
        2022,
    ),
    (
        "Kerosene — stationary combustion",
        "stationary_combustion",
        2.58,
        "kgCO2e/litre",
        "",
        "GHG Protocol 2022 — Stationary Combustion",
        2022,
    ),
    (
        "Fuel oil (heavy) — stationary combustion",
        "stationary_combustion",
        3.18,
        "kgCO2e/litre",
        "",
        "GHG Protocol 2022 — Stationary Combustion",
        2022,
    ),
    # ------------------------------------------------------------------
    # Transport (Scope 1 / Scope 3 Category 4 & 9)
    # Source: DEFRA/DESNZ 2022 GHG Conversion Factors — Freight transport
    #         (kg CO2e per tonne-km, well-to-wheel basis)
    # ------------------------------------------------------------------
    (
        "Road freight — average articulated truck (>33t)",
        "transport",
        0.069,
        "kgCO2e/tonne-km",
        "",
        "DEFRA/DESNZ 2022 — Freight Transport",
        2022,
    ),
    (
        "Road freight — average rigid truck (<17t)",
        "transport",
        0.149,
        "kgCO2e/tonne-km",
        "",
        "DEFRA/DESNZ 2022 — Freight Transport",
        2022,
    ),
    (
        "Sea freight — container ship (average)",
        "transport",
        0.008,
        "kgCO2e/tonne-km",
        "",
        "DEFRA/DESNZ 2022 — Freight Transport",
        2022,
    ),
    (
        "Sea freight — bulk carrier (average)",
        "transport",
        0.005,
        "kgCO2e/tonne-km",
        "",
        "DEFRA/DESNZ 2022 — Freight Transport",
        2022,
    ),
    (
        "Air freight — long-haul (with RFI)",
        "transport",
        0.602,
        "kgCO2e/tonne-km",
        "",
        "DEFRA/DESNZ 2022 — Air Freight",
        2022,
    ),
    (
        "Air freight — short-haul (with RFI)",
        "transport",
        1.206,
        "kgCO2e/tonne-km",
        "",
        "DEFRA/DESNZ 2022 — Air Freight",
        2022,
    ),
    (
        "Rail freight — average diesel/electric",
        "transport",
        0.026,
        "kgCO2e/tonne-km",
        "",
        "DEFRA/DESNZ 2022 — Freight Transport",
        2022,
    ),
    (
        "Courier / express delivery — road (average van)",
        "transport",
        0.350,
        "kgCO2e/tonne-km",
        "",
        "DEFRA/DESNZ 2022 — Freight Transport",
        2022,
    ),
    # ------------------------------------------------------------------
    # Water supply
    # Source: GHG Protocol 2022 / DEFRA 2022 — Water supply factor
    #         (kg CO2e per cubic metre of potable water supplied)
    # ------------------------------------------------------------------
    (
        "Water supply — potable (global average)",
        "water_supply",
        0.344,
        "kgCO2e/m3",
        "",
        "DEFRA/DESNZ 2022 — Water Supply",
        2022,
    ),
    (
        "Wastewater treatment — global average",
        "water_supply",
        0.707,
        "kgCO2e/m3",
        "",
        "DEFRA/DESNZ 2022 — Water Treatment",
        2022,
    ),
    # ------------------------------------------------------------------
    # Scope 3 spend-based emission factors (Category 1 — Purchased Goods)
    # Source: GHG Protocol 2022, Scope 3 Calculation Guidance, Table 6.5
    #         (kg CO2e per USD of spend, cradle-to-gate)
    # ------------------------------------------------------------------
    (
        "Textiles — general (spend-based)",
        "scope3_spend",
        0.94,
        "kgCO2e/USD",
        "",
        "GHG Protocol 2022 — Scope 3 Spend-Based",
        2022,
    ),
    (
        "Cotton fibre (spend-based)",
        "scope3_spend",
        1.10,
        "kgCO2e/USD",
        "",
        "GHG Protocol 2022 — Scope 3 Spend-Based",
        2022,
    ),
    (
        "Synthetic fibres — polyester (spend-based)",
        "scope3_spend",
        0.81,
        "kgCO2e/USD",
        "",
        "GHG Protocol 2022 — Scope 3 Spend-Based",
        2022,
    ),
    (
        "Synthetic fibres — nylon (spend-based)",
        "scope3_spend",
        0.87,
        "kgCO2e/USD",
        "",
        "GHG Protocol 2022 — Scope 3 Spend-Based",
        2022,
    ),
    (
        "Accessories / trims (spend-based)",
        "scope3_spend",
        0.45,
        "kgCO2e/USD",
        "",
        "GHG Protocol 2022 — Scope 3 Spend-Based",
        2022,
    ),
    (
        "Dyes and chemicals (spend-based)",
        "scope3_spend",
        1.24,
        "kgCO2e/USD",
        "",
        "GHG Protocol 2022 — Scope 3 Spend-Based",
        2022,
    ),
    (
        "Packaging materials (spend-based)",
        "scope3_spend",
        0.52,
        "kgCO2e/USD",
        "",
        "GHG Protocol 2022 — Scope 3 Spend-Based",
        2022,
    ),
    (
        "Rubber and plastics (spend-based)",
        "scope3_spend",
        0.72,
        "kgCO2e/USD",
        "",
        "GHG Protocol 2022 — Scope 3 Spend-Based",
        2022,
    ),
    # ------------------------------------------------------------------
    # Refrigerants — GWP100 values (Scope 1 fugitive emissions)
    # Source: IPCC AR6, Working Group I, Chapter 7, Table 7.SM.7 (2021)
    # Value represents kg CO2e per kg of refrigerant released.
    # ------------------------------------------------------------------
    (
        "Refrigerant R-134a (HFC)",
        "refrigerants",
        1530.0,
        "kgCO2e/kg",
        "",
        "IPCC AR6 WG1 Ch7 Table 7.SM.7",
        2021,
    ),
    (
        "Refrigerant R-410A (HFC blend)",
        "refrigerants",
        2088.0,
        "kgCO2e/kg",
        "",
        "IPCC AR6 WG1 Ch7 Table 7.SM.7",
        2021,
    ),
    (
        "Refrigerant R-404A (HFC blend)",
        "refrigerants",
        4632.0,
        "kgCO2e/kg",
        "",
        "IPCC AR6 WG1 Ch7 Table 7.SM.7",
        2021,
    ),
    (
        "Refrigerant R-32 (HFC)",
        "refrigerants",
        771.0,
        "kgCO2e/kg",
        "",
        "IPCC AR6 WG1 Ch7 Table 7.SM.7",
        2021,
    ),
    (
        "Refrigerant R-407C (HFC blend)",
        "refrigerants",
        1774.0,
        "kgCO2e/kg",
        "",
        "IPCC AR6 WG1 Ch7 Table 7.SM.7",
        2021,
    ),
    (
        "Refrigerant R-22 (HCFC — legacy)",
        "refrigerants",
        1760.0,
        "kgCO2e/kg",
        "",
        "IPCC AR6 WG1 Ch7 Table 7.SM.7",
        2021,
    ),
    # ------------------------------------------------------------------
    # Waste disposal (Scope 3 Category 5)
    # Source: DEFRA/DESNZ 2022 — Waste disposal emission factors
    #         (kg CO2e per tonne of waste disposed)
    # ------------------------------------------------------------------
    (
        "Waste — landfill (average mixed)",
        "waste",
        415.0,
        "kgCO2e/tonne",
        "",
        "DEFRA/DESNZ 2022 — Waste Disposal",
        2022,
    ),
    (
        "Waste — recycled (average mixed)",
        "waste",
        21.0,
        "kgCO2e/tonne",
        "",
        "DEFRA/DESNZ 2022 — Waste Disposal",
        2022,
    ),
    (
        "Waste — incineration (average mixed)",
        "waste",
        31.0,
        "kgCO2e/tonne",
        "",
        "DEFRA/DESNZ 2022 — Waste Disposal",
        2022,
    ),
    (
        "Waste — textile waste to landfill",
        "waste",
        376.0,
        "kgCO2e/tonne",
        "",
        "DEFRA/DESNZ 2022 — Waste Disposal",
        2022,
    ),
    (
        "Waste — textile waste recycled",
        "waste",
        7.0,
        "kgCO2e/tonne",
        "",
        "DEFRA/DESNZ 2022 — Waste Disposal",
        2022,
    ),
    (
        "Waste — organic/food waste composted",
        "waste",
        13.0,
        "kgCO2e/tonne",
        "",
        "DEFRA/DESNZ 2022 — Waste Disposal",
        2022,
    ),
]


def seed_emission_factors() -> None:
    """Insert global reference emission factors into the emission_factors table.

    Each factor is stored with org_id = '' so it serves as a global default.
    Duplicate inserts are silently skipped if a factor with the same name and
    country_code already exists (INSERT OR IGNORE pattern is NOT used — the
    table has no unique constraint on name+country, so we delete-and-reinsert
    to keep the seed idempotent for repeated development runs).
    """
    conn = get_connection()

    # Remove any prior seed data so repeated runs stay idempotent.
    _execute(conn, "DELETE FROM emission_factors WHERE org_id = ''")

    insert_sql = """
        INSERT INTO emission_factors
            (org_id, factor_name, category, factor_value, unit, country_code, source, year)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    count = 0
    for factor_name, category, value, unit, country_code, source, year in FACTORS:
        _execute(
            conn,
            insert_sql,
            ("", factor_name, category, value, unit, country_code, source, year),
        )
        count += 1

    release_connection(conn)
    print(f"Seeded {count} emission factors into the database.")


if __name__ == "__main__":
    seed_emission_factors()
