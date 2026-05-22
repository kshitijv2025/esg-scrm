"""
MQTT Consumer — factory smart meter data ingestion.
Subscribes to factory/{factory_id}/meter/{meter_id} topics.
Batches writes to SQLite every batch_interval seconds.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Optional

import paho.mqtt.client as mqtt
from paho.mqtt.client import Client as Client

from src.db.database import DB_PATH
from src.evidence.hash_chain import compute_hash

logger = logging.getLogger(__name__)


def _get_prev_hash(cluster: str) -> Optional[str]:
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
        (
            metric_id,
            cluster,
            the_hash,
            prev_hash,
            value,
            datetime.now(timezone.utc).isoformat(),
            "mqtt",
        ),
    )
    conn.commit()
    conn.close()
    return metric_id


class SmartMeterConsumer:
    """
    MQTT consumer for factory smart meter data.

    Connects to the broker specified by environment variables:
      MQTT_BROKER_HOST (default: localhost)
      MQTT_BROKER_PORT (default: 1883)
      MQTT_FACTORY_ID  (default: factory_bd_001)
    """

    def __init__(
        self,
        factory_id: Optional[str] = None,
        broker_host: Optional[str] = None,
        broker_port: Optional[int] = None,
        batch_interval: int = 60,
    ):
        import os

        self.factory_id = factory_id or os.environ.get("MQTT_FACTORY_ID", "factory_bd_001")
        self.broker_host = broker_host or os.environ.get("MQTT_BROKER_HOST", "localhost")
        self.broker_port = broker_port or int(os.environ.get("MQTT_BROKER_PORT", "1883"))
        self.batch_interval = batch_interval
        self._batch: list[dict[str, Any]] = []
        self._last_flush = time.time()
        self._client: Optional[Client] = None

    def on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        if rc == 0:
            topic = f"factory/{self.factory_id}/meter/#"
            client.subscribe(topic)
            logger.info(
                "mqtt.connected broker=%s:%d topic=%s", self.broker_host, self.broker_port, topic
            )
        else:
            logger.error(
                "mqtt.connect_failed rc=%d broker=%s:%d", rc, self.broker_host, self.broker_port
            )

    def on_message(self, client, userdata, msg) -> None:
        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("mqtt.bad_payload topic=%s", msg.topic)
            return

        topic_parts = msg.topic.split("/")
        if len(topic_parts) < 4:
            return
        meter_id = topic_parts[3] if len(topic_parts) >= 4 else "unknown"
        cluster = topic_parts[4] if len(topic_parts) >= 5 else "unknown"

        self._batch.append(
            {
                "factory_id": self.factory_id,
                "cluster": cluster,
                "meter_id": meter_id,
                "value": payload.get("value", payload.get("kwh", payload.get("m3", 0))),
                "unit": payload.get("unit", "kWh"),
                "confidence": "MEDIUM",
                "source": f"MQTT:{meter_id}",
                "period": payload.get("period", "unknown"),
                "recorded_at": payload.get(
                    "timestamp", datetime.now(timezone.utc).isoformat() + "Z"
                ),
            }
        )

        if time.time() - self._last_flush >= self.batch_interval:
            self._flush()

    def _flush(self) -> None:
        if not self._batch:
            return
        count = len(self._batch)
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
        logger.info("mqtt.flushed records=%d factory=%s", count, self.factory_id)
        self._batch.clear()
        self._last_flush = time.time()

    def start(self) -> None:
        """Connect to MQTT broker and start the network loop."""
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self.on_connect
        self._client.on_message = self.on_message
        try:
            self._client.connect(self.broker_host, self.broker_port, 60)
            self._client.loop_start()
            logger.info(
                "mqtt.starting broker=%s:%d factory=%s",
                self.broker_host,
                self.broker_port,
                self.factory_id,
            )
        except Exception as e:
            logger.error(
                "mqtt.connection_error broker=%s:%d error=%s", self.broker_host, self.broker_port, e
            )
            raise

    def stop(self) -> None:
        """Flush pending batch and disconnect."""
        self._flush()
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
            logger.info("mqtt.stopped factory=%s", self.factory_id)


def get_current_metrics(factory_id: str = "factory_bd_001") -> list[dict]:
    """Return the latest metric per cluster for the factory."""
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
