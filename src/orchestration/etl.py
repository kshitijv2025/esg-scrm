"""
ETL Pipeline — orchestrates: data sources → SQLite → compute → API.
Runs every 60 seconds as a background loop.
Uses centralized database manager from src.db.database.
"""
import asyncio
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

from src.connectors.mqtt_client import SmartMeterConsumer, get_current_metrics
from src.connectors.sap_b1_adapter import SAPBusinessOneAdapter
from src.db.database import get_connection, DB_PATH
from src.evidence.hash_chain import compute_hash


async def run_mqtt_ingestion(factory_id: str = "factory_bd_001") -> None:
    """Run MQTT consumer in demo mode (no real broker needed)."""
    consumer = SmartMeterConsumer(factory_id=factory_id, batch_interval=60)
    await asyncio.sleep(0.1)


async def run_sap_ingestion(factory_id: str = "factory_bd_001") -> None:
    """Pull data from SAP B1 mock adapter and write to metrics table.

    Skips records already present (dedup by cluster + recorded_at) so the
    ETL loop does not grow the metrics table with identical rows on every cycle.
    """
    adapter = SAPBusinessOneAdapter()
    records = adapter.get_utility_invoices(2025, 1)
    if not records:
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    try:
        inserted = 0
        for record in records:
            internal = adapter.to_internal_metric(record)

            existing = conn.execute(
                "SELECT id FROM metrics WHERE cluster = ? AND recorded_at = ? AND factory_id = ?",
                (internal["cluster"], internal["recorded_at"], factory_id),
            ).fetchone()
            if existing:
                continue

            prev_row = conn.execute(
                "SELECT hash FROM evidence_chain WHERE cluster=? ORDER BY id DESC LIMIT 1",
                (internal["cluster"],),
            ).fetchone()
            prev_hash = prev_row[0] if prev_row else None
            the_hash = compute_hash(
                internal["cluster"],
                internal["value"],
                internal["recorded_at"],
                prev_hash or "",
            )

            cursor = conn.execute(
                """INSERT INTO metrics (factory_id, cluster, value, unit, confidence, source, period, recorded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    factory_id,
                    internal["cluster"],
                    internal["value"],
                    internal["unit"],
                    internal["confidence"],
                    internal["source"],
                    internal.get("period", ""),
                    internal["recorded_at"],
                ),
            )
            metric_id = cursor.lastrowid
            conn.execute(
                """INSERT INTO evidence_chain (metric_id, cluster, hash, prev_hash, value, computed_at, source_system)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (metric_id, internal["cluster"], the_hash, prev_hash, internal["value"],
                 datetime.now(timezone.utc).isoformat(), "sap_b1"),
            )
            inserted += 1

        if inserted > 0:
            conn.commit()
    finally:
        conn.close()


async def etl_loop(interval: int = 60, factory_id: str = "factory_bd_001") -> None:
    """Main ETL loop — runs every `interval` seconds."""
    from src.realtime.risk_detector import detect_and_alert
    while True:
        try:
            await run_mqtt_ingestion(factory_id)
            await run_sap_ingestion(factory_id)
            await detect_and_alert(factory_id)
        except Exception as e:
            print(f"[etl] Error during ingestion cycle: {e}")
        await asyncio.sleep(interval)


def load_latest_metrics(factory_id: str = "factory_bd_001") -> list[dict[str, Any]]:
    """Return the latest metric record per cluster from SQLite."""
    from src.db.database import fetch_metrics
    return fetch_metrics(factory_id)
