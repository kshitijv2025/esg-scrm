"""
Seed the metric_metadata table with reference metadata for ESG metric clusters.

Sources:
  - GHG Protocol Corporate Value Chain (Scope 3) Standard (2013)
  - IEA Emission Factors 2023 for grid emission factors
  - DEFRA/DESNZ UK Government GHG Conversion Factors (2023)

Run standalone: python -m src.db.seed_metric_metadata
Run via seed.py: python -m src.db.seed
"""

from src.db.database import get_connection, release_connection

# ---------------------------------------------------------------------------
# Metric metadata tuples:
# (cluster, trend, calculation_method, emission_factor, emission_factor_value,
#  coverage_rate, responding_suppliers, total_suppliers)
# ---------------------------------------------------------------------------

METRICS: list[tuple] = [
    (
        "energy_kwh",
        "+3.2% vs last month",
        "direct_measurement",
        "IEA 2023 — Bangladesh Grid Factor",
        "0.524 kg CO2/kWh",
        None,
        None,
        None,
    ),
    (
        "emissions_tco2",
        "-1.8% vs last month",
        "activity_based",
        "IEA 2023 Bangladesh grid (0.524 kg/kWh)",
        "0.524",
        None,
        None,
        None,
    ),
    (
        "water_m3",
        "+0.7% vs last month",
        "direct_measurement",
        "N/A — direct measurement",
        "—",
        None,
        None,
        None,
    ),
    (
        "scope3_category1",
        "+2.1% vs last quarter",
        "activity_based",
        "GHG Protocol 2022 — Category 1 spend-based",
        "0.94 kg CO2/$",
        64.0,
        47,
        73,
    ),
    (
        "diesel_consumed",
        "+1.2% vs last quarter",
        "manual_calculation",
        "GHG Protocol 2022 — Diesel (2.68 kg CO2/L)",
        "2.68 kg CO2/L",
        None,
        None,
        None,
    ),
    (
        "scope3_category6",
        "New this quarter",
        "manual_calculation",
        "GHG Protocol 2022 — Category 6 (Business Travel)",
        "flight 0.255 kg/km, hotel 0.084 kg/night, car 0.171 kg/km",
        None,
        None,
        None,
    ),
]


def seed_metric_metadata(conn) -> int:
    count = 0
    for metric in METRICS:
        cluster, trend, calc_method, ef, ef_value, cov_rate, resp_sup, tot_sup = metric
        conn.execute(
            """
            INSERT OR REPLACE INTO metric_metadata
            (cluster, trend, calculation_method, emission_factor, emission_factor_value,
             coverage_rate, responding_suppliers, total_suppliers)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (cluster, trend, calc_method, ef, ef_value, cov_rate, resp_sup, tot_sup),
        )
        count += 1
    return count


def run() -> dict:
    conn = get_connection()
    try:
        count = seed_metric_metadata(conn)
        conn.commit()
        return {"metric_metadata": count}
    finally:
        release_connection(conn)


if __name__ == "__main__":
    result = run()
    print(f"Seeded {result['metric_metadata']} metric_metadata rows")
