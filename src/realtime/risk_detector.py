"""
Real-time risk detector — monitors metrics against thresholds,
creates risk flags, and pushes alerts via the AlertBus.
"""
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

from src.db.database import DB_PATH, get_connection, release_connection
from src.realtime.alerts import push_new_flag

DEFAULT_THRESHOLDS: dict[str, dict[str, Any]] = {
    "energy_kwh": {"max": 3500000, "severity": "WARNING", "text": "Energy consumption exceeds threshold"},
    "water_m3": {"max": 20000, "severity": "WARNING", "text": "Water withdrawal exceeds threshold"},
    "diesel_consumed": {"max": 100, "severity": "CRITICAL", "text": "Diesel usage exceeds threshold"},
    "waste_tonnes": {"max": 50, "severity": "WARNING", "text": "Waste generation exceeds threshold"},
    "scope3_category6": {"max": 10000, "severity": "INFO", "text": "Scope 3 Cat 6 emissions elevated"},
}

COOLDOWN_HOURS = int(os.environ.get("RISK_COOLDOWN_HOURS", "24"))

# Backward-compatible alias used by tests
THRESHOLDS = DEFAULT_THRESHOLDS


def _load_thresholds() -> dict[str, dict[str, Any]]:
    """Load thresholds from env vars, falling back to defaults.

    Override any cluster via RISK_THRESHOLD_<CLUSTER_NAME> (uppercased).
    Example: RISK_THRESHOLD_ENERGY_KWH=4000000
    """
    thresholds: dict[str, dict[str, Any]] = {}
    for cluster, default in DEFAULT_THRESHOLDS.items():
        env_key = f"RISK_THRESHOLD_{cluster.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            try:
                thresholds[cluster] = {**default, "max": float(env_val)}
            except ValueError:
                thresholds[cluster] = default
        else:
            thresholds[cluster] = default
    return thresholds


def check_latest_metrics(factory_id: str = "factory_bd_001") -> list[dict[str, Any]]:
    """Check latest metrics against thresholds. Returns list of new flags created.

    Dedup: skips alerting if a flag for the same cluster was created within
    COOLDOWN_HOURS, regardless of acknowledgement status.
    """
    thresholds = _load_thresholds()
    conn = get_connection()

    try:
        latest = conn.execute(
            """SELECT m.cluster, m.value, m.unit, m.id
               FROM metrics m
               WHERE m.factory_id = ?
                 AND m.id IN (
                   SELECT MAX(id) FROM metrics WHERE factory_id = ? GROUP BY cluster
                 )
               ORDER BY m.cluster""",
            (factory_id, factory_id),
        ).fetchall()

        new_flags = []
        for row in latest:
            cluster = row["cluster"]
            value = row["value"]
            threshold = thresholds.get(cluster)
            if not threshold:
                continue
            if value > threshold["max"]:
                cutoff = datetime.now(timezone.utc).timestamp() - (COOLDOWN_HOURS * 3600)
                recent = conn.execute(
                    "SELECT id FROM risk_flags WHERE cluster = ? AND created_at >= datetime(?, 'unixepoch')",
                    (cluster, cutoff),
                ).fetchone()
                if recent:
                    continue

                flag_id = f"flag_auto_{cluster}_{int(datetime.now(timezone.utc).timestamp())}"
                priority = 80.0 if threshold["severity"] == "CRITICAL" else 50.0
                flag_text = f"{threshold['text']}: {value} {row['unit']} (threshold: {threshold['max']})"

                conn.execute(
                    """INSERT INTO risk_flags (id, factory_id, flag_text, cluster, severity, days_overdue, priority_score)
                       VALUES (?, ?, ?, ?, ?, 0, ?)""",
                    (flag_id, factory_id, flag_text, cluster, threshold["severity"], priority),
                )

                flag_data = {
                    "id": flag_id,
                    "flag_text": flag_text,
                    "cluster": cluster,
                    "severity": threshold["severity"],
                    "priority_score": priority,
                }
                new_flags.append(flag_data)

        if new_flags:
            conn.commit()
        return new_flags
    finally:
        release_connection(conn)


async def detect_and_alert(factory_id: str = "factory_bd_001") -> None:
    """Check thresholds and broadcast alerts for any new flags."""
    new_flags = check_latest_metrics(factory_id)
    for flag in new_flags:
        await push_new_flag(flag)
