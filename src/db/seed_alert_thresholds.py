"""
Seed default alert thresholds for the ESG SCRM platform.

Populates the alert_thresholds table with factory-default templates
covering energy, emissions, water, diesel, Scope 3 coverage,
supplier risk, and evidence-chain integrity for a garment factory.
"""

from src.db.database import get_connection, release_connection, _execute, _fetchone


def seed_alert_thresholds():
    """Insert default alert thresholds into the database.

    Each row is a template (org_id = '') that applies globally unless
    overridden by an org-specific threshold of the same cluster/metric.
    """
    conn = get_connection()

    # Check if defaults already exist to avoid duplicates on re-seed.
    row = _fetchone(conn, "SELECT COUNT(*) AS cnt FROM alert_thresholds WHERE org_id = ?", ("",))
    existing = row["cnt"] if row else 0
    if existing > 0:
        print(f"Skipping alert thresholds seed: {existing} default rows already exist.")
        release_connection(conn)
        return

    thresholds = [
        # ── Energy ───────────────────────────────────────────────────────
        # Monthly electricity consumption exceeds 3,000,000 kWh
        ("", "energy", "monthly_consumption_kwh", ">", 3_000_000, "WARNING", 1),
        # Daily energy spike exceeds 120% of the rolling 30-day average
        ("", "energy", "daily_spike_pct_of_30d_avg", ">", 120.0, "WARNING", 1),
        # Monthly energy consumption critically high
        ("", "energy", "monthly_consumption_kwh", ">", 4_500_000, "CRITICAL", 1),
        # ── Emissions ────────────────────────────────────────────────────
        # Scope 1+2 emissions exceed 1,200 tCO2e per month
        ("", "emissions", "scope1_plus_2_monthly_tco2e", ">", 1_200.0, "WARNING", 1),
        # Scope 1+2 emissions at critical level
        ("", "emissions", "scope1_plus_2_monthly_tco2e", ">", 1_800.0, "CRITICAL", 1),
        # Scope 3 upstream emissions exceed 5,000 tCO2e per quarter
        ("", "emissions", "scope3_quarterly_tco2e", ">", 5_000.0, "WARNING", 1),
        # Scope 3 quarterly emissions at critical level
        ("", "emissions", "scope3_quarterly_tco2e", ">", 7_500.0, "CRITICAL", 1),
        # ── Water ────────────────────────────────────────────────────────
        # Monthly water consumption exceeds 20,000 m3
        ("", "water", "monthly_consumption_m3", ">", 20_000.0, "WARNING", 1),
        # Monthly water consumption at critical level
        ("", "water", "monthly_consumption_m3", ">", 30_000.0, "CRITICAL", 1),
        # Daily water consumption exceeds 800 m3
        ("", "water", "daily_consumption_m3", ">", 800.0, "WARNING", 1),
        # Daily water consumption at critical level
        ("", "water", "daily_consumption_m3", ">", 1_200.0, "CRITICAL", 1),
        # ── Diesel ───────────────────────────────────────────────────────
        # Any diesel consumption detected (flag for evidence chain review)
        ("", "diesel", "consumption_liters", ">", 0.0, "WARNING", 1),
        # Diesel consumption above baseline threshold
        ("", "diesel", "monthly_consumption_liters", ">", 500.0, "CRITICAL", 1),
        # ── Scope 3 Coverage ─────────────────────────────────────────────
        # Supplier questionnaire response rate drops below 70%
        ("", "scope3_coverage", "questionnaire_response_rate_pct", "<", 70.0, "WARNING", 1),
        # Response rate critically low
        ("", "scope3_coverage", "questionnaire_response_rate_pct", "<", 50.0, "CRITICAL", 1),
        # ── Supplier Risk ────────────────────────────────────────────────
        # Individual supplier risk score exceeds 8.0
        ("", "supplier_risk", "risk_score", ">", 8.0, "CRITICAL", 1),
        # Supplier has more than 3 active risk flags
        ("", "supplier_risk", "active_flags_count", ">", 3.0, "WARNING", 1),
        # Supplier risk score elevated
        ("", "supplier_risk", "risk_score", ">", 6.0, "WARNING", 1),
        # ── Evidence Chain Integrity ─────────────────────────────────────
        # Broken hash chain detected (any break is critical; threshold = 0
        # means any non-zero count triggers the alert)
        ("", "evidence_chain", "broken_hash_chain_count", ">", 0.0, "CRITICAL", 1),
        # Missing evidence entries for recorded metrics
        ("", "evidence_chain", "missing_evidence_count", ">", 0.0, "WARNING", 1),
    ]

    for (
        org_id,
        cluster,
        metric_cluster,
        operator,
        threshold_value,
        severity,
        is_active,
    ) in thresholds:
        _execute(
            conn,
            """
            INSERT INTO alert_thresholds
                (org_id, cluster, metric_cluster, operator, threshold_value, severity, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (org_id, cluster, metric_cluster, operator, threshold_value, severity, is_active),
        )

    release_connection(conn)
    print(f"Seeded {len(thresholds)} default alert thresholds.")


if __name__ == "__main__":
    seed_alert_thresholds()
