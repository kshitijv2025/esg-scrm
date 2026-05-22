"""Tests for MQTT connector and ETL lifecycle."""

import os
import sys

sys.path.insert(0, "src")

from unittest.mock import MagicMock, patch

from src.connectors.mqtt_client import SmartMeterConsumer
from src.db.seed import seed
from src.orchestration.etl import start_mqtt_consumer, stop_mqtt_consumer


class TestSmartMeterConsumer:
    def test_constructor_reads_env_vars(self):
        with patch.dict(
            os.environ,
            {
                "MQTT_BROKER_HOST": "test-broker.local",
                "MQTT_BROKER_PORT": "2883",
                "MQTT_FACTORY_ID": "factory_test_001",
            },
        ):
            consumer = SmartMeterConsumer()
            assert consumer.broker_host == "test-broker.local"
            assert consumer.broker_port == 2883
            assert consumer.factory_id == "factory_test_001"

    def test_constructor_accepts_explicit_params(self):
        consumer = SmartMeterConsumer(
            factory_id="custom_factory",
            broker_host="custom.host",
            broker_port=9999,
        )
        assert consumer.broker_host == "custom.host"
        assert consumer.broker_port == 9999
        assert consumer.factory_id == "custom_factory"

    def test_on_message_parses_valid_payload(self):
        consumer = SmartMeterConsumer(factory_id="test_factory")
        msg = MagicMock()
        msg.topic = "factory/test_factory/meter/meter_01/energy"
        msg.payload = b'{"value": 1500.5, "unit": "kWh", "timestamp": "2026-05-18T10:00:00Z"}'
        consumer.on_message(None, None, msg)
        assert len(consumer._batch) == 1
        assert consumer._batch[0]["cluster"] == "energy"
        assert consumer._batch[0]["value"] == 1500.5
        assert consumer._batch[0]["meter_id"] == "meter_01"

    def test_on_message_ignores_bad_json(self):
        consumer = SmartMeterConsumer()
        msg = MagicMock()
        msg.topic = "factory/x/meter/m1/energy_kwh"
        msg.payload = b"not json"
        consumer.on_message(None, None, msg)
        assert len(consumer._batch) == 0

    def test_on_message_ignores_short_topic(self):
        consumer = SmartMeterConsumer()
        msg = MagicMock()
        msg.topic = "factory/x/meter"
        msg.payload = b'{"value": 100}'
        consumer.on_message(None, None, msg)
        assert len(consumer._batch) == 0

    def test_on_message_extracts_meter_id(self):
        consumer = SmartMeterConsumer()
        msg = MagicMock()
        msg.topic = "factory/f1/meter/meter_42/water"
        msg.payload = b'{"value": 500, "unit": "m3"}'
        consumer.on_message(None, None, msg)
        assert consumer._batch[0]["meter_id"] == "meter_42"
        assert consumer._batch[0]["cluster"] == "water"

    def test_flush_writes_batch(self):
        seed()
        consumer = SmartMeterConsumer()
        consumer._batch = [
            {
                "org_id": "org_bd_001",
                "factory_id": "factory_bd_001",
                "cluster": "energy_kwh",
                "value": 9999.0,
                "unit": "kWh",
                "confidence": "HIGH",
                "source": "MQTT:meter_test",
                "period": "2026-05",
                "recorded_at": "2026-05-18T12:00:00Z",
            }
        ]
        consumer._flush()
        assert len(consumer._batch) == 0


class TestETLLifecycle:
    def test_start_mqtt_consumer_creates_consumer(self):
        with patch("src.orchestration.etl.SmartMeterConsumer") as MockConsumer:
            instance = MagicMock()
            MockConsumer.return_value = instance
            start_mqtt_consumer(factory_id="test_factory")
            MockConsumer.assert_called_once_with(factory_id="test_factory")
            instance.start.assert_called_once()
        stop_mqtt_consumer()

    def test_stop_mqtt_consumer_calls_stop(self):
        with patch("src.orchestration.etl.SmartMeterConsumer") as MockConsumer:
            instance = MagicMock()
            MockConsumer.return_value = instance
            start_mqtt_consumer()
            stop_mqtt_consumer()
            instance.stop.assert_called_once()

    def test_stop_mqtt_consumer_handles_none(self):
        stop_mqtt_consumer()
