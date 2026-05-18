"""
MQTT Consumer — factory smart meter data ingestion.
Subscribes to factory/{factory_id}/meter/{meter_id} topics.
Batches writes to SQLite every 60 seconds.
"""
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None  # Demo mode — MQTT not installed

from src.evidence.hash_chain import compute_hash

SCHEMA_PATH = Path(__file__).parent.parent / "db" / "schema.sql"
DB_PATH = Path(__file__).parent.parent / "db" / "esg_scrm.db"


def _init_db() -> None:
    if not DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.executescript(SCHEMA_PATH.read_text())
        conn.close()


def _get_prev_hash(cluster: str) -> str | None:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT hash FROM evidence_chain WHERE cluster=? ORDER BY id DESC LIMIT 1",
        (cluster,),
    ).fetchone()
    conn.close()
    return row[0] if row else None


def _insert_metric(
    factory_id: str,
    cluster: str,
    value: float,
    unit: str,
    confidence: str,
    source: str,
    period: str,
    recorded_at: str,
) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        """INSERT INTO metrics
           (factory_id, cluster, value, unit, confidence, source, period, recorded_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (factory_id, cluster, value, unit, confidence, source, period, recorded_at),
    )
    metric_id = cursor.lastrowid

    prev_hash = _get_prev_hash(cluster)
    the_hash = compute_hash(cluster, value, recorded_at, prev_hash or "")
    conn.execute(
        """INSERT INTO evidence_chain
           (metric_id, cluster, hash, prev_hash, value, computed_at, source_system)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (metric_id, cluster, the_hash, prev_hash, value, datetime.utcnow().isoformat() + "Z", "mqtt"),
    )
    conn.commit()
    conn.close()
    return metric_id


class SmartMeterConsumer:
    """
    MQTT consumer for factory smart meter data.
    In demo mode (no paho-mqtt), logs incoming payloads instead.
    """

    def __init__(self, factory_id: str = "factory_bd_001", batch_interval: int = 60):
        self.factory_id = factory_id
        self.batch_interval = batch_interval
        self._batch: list[dict[str, Any]] = []
        self._last_flush = time.time()
        _init_db()

    def on_message(self, client, userdata, msg) -> None:
        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return

        topic_parts = msg.topic.split("/")
        if len(topic_parts) < 4:
            return
        cluster = topic_parts[3] if len(topic_parts) >= 4 else "unknown"
        meter_id = topic_parts[4] if len(topic_parts) >= 5 else "unknown"

        self._batch.append({
            "factory_id": self.factory_id,
            "cluster": cluster,
            "meter_id": meter_id,
            "value": payload.get("value", payload.get("kwh", payload.get("m3", 0))),
            "unit": payload.get("unit", "kWh"),
            "confidence": "MEDIUM",
            "source": f"MQTT:{meter_id}",
            "period": payload.get("period", "unknown"),
            "recorded_at": payload.get("timestamp", datetime.utcnow().isoformat() + "Z"),
        })

        if time.time() - self._last_flush >= self.batch_interval:
            self._flush()

    def _flush(self) -> None:
        if not self._batch:
            return
        for record in self._batch:
            _insert_metric(
                record["factory_id"],
                record["cluster"],
                record["value"],
                record["unit"],
                record["confidence"],
                record["source"],
                record["period"],
                record["recorded_at"],
            )
        self._batch.clear()
        self._last_flush = time.time()

    def start(self) -> None:
        if mqtt is None:
            print("[mqtt] Demo mode — paho-mqtt not installed, no real MQTT connection")
            return
        client = mqtt.Client()
        client.on_message = self.on_message
        client.connect("localhost", 1883, 60)
        client.subscribe(f"factory/{self.factory_id}/meter/#")
        client.loop_start()

    def stop(self) -> None:
        self._flush()
        if mqtt is not None:
            mqtt.Client().loop_stop()


def get_current_metrics(factory_id: str = "factory_bd_001") -> list[dict]:
    """Return the latest metric per cluster for the factory."""
    _init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT m.* FROM metrics m
           INNER JOIN (
               SELECT cluster, MAX(recorded_at) as max_recorded
               FROM metrics WHERE factory_id=? GROUP BY cluster
           ) latest ON m.cluster = latest.cluster AND m.recorded_at = latest.max_recorded
           WHERE m.factory_id=? ORDER BY m.cluster""",
        (factory_id, factory_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
