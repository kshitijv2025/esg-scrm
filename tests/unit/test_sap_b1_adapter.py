"""Tests for SAP B1 adapter — demo mode, live mode, auth failure handling."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "src")

# Ensure demo mode for all tests in this module by patching ERP_MODE
os.environ["ERP_MODE"] = "demo"


class TestSAPBusinessOneAdapterDemoMode:
    """Tests for demo mode operation (CSV-backed)."""

    def test_health_check_demo_mode(self):
        """health_check() returns demo mode status with connected=True."""
        from src.connectors.sap_b1_adapter import SAPBusinessOneAdapter

        with patch.dict(os.environ, {"ERP_MODE": "demo"}):
            adapter = SAPBusinessOneAdapter()
            result = adapter.health_check()

        assert result["mode"] == "demo"
        assert result["connected"] is True
        assert result["source"] == "CSV files"

    def test_get_utility_invoices_demo_mode_no_csv(self):
        """get_utility_invoices() returns empty list when CSV is absent."""
        from src.connectors.sap_b1_adapter import SAPBusinessOneAdapter

        with patch.dict(os.environ, {"ERP_MODE": "demo"}):
            adapter = SAPBusinessOneAdapter()
            # Without the CSV file present, returns []
            result = adapter.get_utility_invoices(2025, 1)

        assert result == []

    def test_to_internal_metric_maps_fields(self):
        """to_internal_metric() correctly maps SAP record to internal schema."""
        from src.connectors.sap_b1_adapter import SAPBusinessOneAdapter

        adapter = SAPBusinessOneAdapter()
        sap_record = {
            "cluster": "energy.grid",
            "value": "1234.5",
            "unit": "kWh",
            "confidence": "HIGH",
            "source": "meter001",
            "period": "2025-01",
            "recorded_at": "2025-01-15T10:00:00Z",
        }
        result = adapter.to_internal_metric(sap_record)

        assert result["cluster"] == "energy.grid"
        assert result["value"] == 1234.5
        assert result["unit"] == "kWh"
        assert result["confidence"] == "HIGH"
        assert result["source"] == "SAP B1: meter001"
        assert result["period"] == "2025-01"
        assert result["recorded_at"] == "2025-01-15T10:00:00Z"

    def test_to_internal_metric_defaults(self):
        """to_internal_metric() uses sensible defaults for missing fields."""
        from src.connectors.sap_b1_adapter import SAPBusinessOneAdapter

        adapter = SAPBusinessOneAdapter()
        result = adapter.to_internal_metric({})

        assert result["cluster"] == "unknown"
        assert result["value"] == 0.0
        assert result["unit"] == ""
        assert result["confidence"] == "MEDIUM"
        assert result["source"] == "SAP B1: unknown"
        assert result["period"] == ""
        assert "recorded_at" in result


class TestSAPBusinessOneAdapterLiveMode:
    """Tests for live mode (ERP_MODE=live) with mocked HTTP responses.

    Note: ERP_MODE is evaluated at module load time, so we patch the module-level
    variable directly rather than the environment dict.
    """

    def test_health_check_live_missing_url(self):
        """health_check() returns error dict when SAP_B1_SERVER_URL is empty."""
        from src.connectors import sap_b1_adapter

        with patch.object(sap_b1_adapter, "ERP_MODE", "live"):
            adapter = sap_b1_adapter.SAPBusinessOneAdapter(server_url="", api_key="")
            result = adapter.health_check()

        assert result["mode"] == "live"
        assert result["connected"] is False
        assert result["error"] == "SAP_B1_SERVER_URL not configured"
        assert result["source"] == "SAP B1 Service Layer"

    def test_health_check_live_auth_failure_401(self):
        """health_check() handles 401 gracefully without raising."""
        from src.connectors import sap_b1_adapter

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch.object(sap_b1_adapter, "ERP_MODE", "live"):
            adapter = sap_b1_adapter.SAPBusinessOneAdapter(
                server_url="https://sap.example.com", api_key="test-key"
            )
            with patch.object(sap_b1_adapter.requests, "get", return_value=mock_response) as mock_get:
                result = adapter.health_check()

        assert result["mode"] == "live"
        assert result["connected"] is False
        assert "authentication_failed" in result["error"]
        assert "401" in result["error"]
        mock_get.assert_called_once()

    def test_health_check_live_auth_failure_403(self):
        """health_check() handles 403 gracefully without raising."""
        from src.connectors import sap_b1_adapter

        mock_response = MagicMock()
        mock_response.status_code = 403

        with patch.object(sap_b1_adapter, "ERP_MODE", "live"):
            adapter = sap_b1_adapter.SAPBusinessOneAdapter(
                server_url="https://sap.example.com", api_key="test-key"
            )
            with patch.object(sap_b1_adapter.requests, "get", return_value=mock_response) as mock_get:
                result = adapter.health_check()

        assert result["mode"] == "live"
        assert result["connected"] is False
        assert "authentication_failed" in result["error"]
        assert "403" in result["error"]
        mock_get.assert_called_once()

    def test_health_check_live_success(self):
        """health_check() returns connected=True on 200 response."""
        from src.connectors import sap_b1_adapter

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(sap_b1_adapter, "ERP_MODE", "live"):
            adapter = sap_b1_adapter.SAPBusinessOneAdapter(
                server_url="https://sap.example.com", api_key="test-key"
            )
            with patch.object(sap_b1_adapter.requests, "get", return_value=mock_response) as mock_get:
                result = adapter.health_check()

        assert result["mode"] == "live"
        assert result["connected"] is True
        assert result["status_code"] == 200
        mock_get.assert_called_once()

    def test_health_check_live_connection_error(self):
        """health_check() handles connection errors gracefully."""
        import requests
        from src.connectors import sap_b1_adapter

        with patch.object(sap_b1_adapter, "ERP_MODE", "live"):
            adapter = sap_b1_adapter.SAPBusinessOneAdapter(server_url="https://sap.example.com")
            with patch.object(
                sap_b1_adapter.requests, "get", side_effect=requests.exceptions.ConnectionError("Failed")
            ):
                result = adapter.health_check()

        assert result["mode"] == "live"
        assert result["connected"] is False
        assert result["error"] == "connection_failed"

    def test_health_check_live_timeout(self):
        """health_check() handles timeout gracefully."""
        import requests
        from src.connectors import sap_b1_adapter

        with patch.object(sap_b1_adapter, "ERP_MODE", "live"):
            adapter = sap_b1_adapter.SAPBusinessOneAdapter(server_url="https://sap.example.com")
            with patch.object(
                sap_b1_adapter.requests, "get", side_effect=requests.exceptions.Timeout("timed out")
            ):
                result = adapter.health_check()

        assert result["mode"] == "live"
        assert result["connected"] is False
        assert result["error"] == "connection_timeout"

    def test_get_utility_invoices_live_auth_failure(self):
        """get_utility_invoices() returns [] on 401/403 auth failure, not exception."""
        from src.connectors import sap_b1_adapter

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch.object(sap_b1_adapter, "ERP_MODE", "live"):
            adapter = sap_b1_adapter.SAPBusinessOneAdapter(
                server_url="https://sap.example.com", api_key="test-key"
            )
            with patch.object(sap_b1_adapter.requests, "get", return_value=mock_response) as mock_get:
                result = adapter.get_utility_invoices(2025, 1)

        assert result == []
        mock_get.assert_called_once()

    def test_get_utility_invoices_live_connection_error(self):
        """get_utility_invoices() returns [] on connection error, not exception."""
        import requests
        from src.connectors import sap_b1_adapter

        with patch.object(sap_b1_adapter, "ERP_MODE", "live"):
            adapter = sap_b1_adapter.SAPBusinessOneAdapter(server_url="https://sap.example.com")
            with patch.object(
                sap_b1_adapter.requests, "get", side_effect=requests.exceptions.ConnectionError("Failed")
            ):
                result = adapter.get_utility_invoices(2025, 1)

        assert result == []

    def test_get_utility_invoices_live_success_parses_value(self):
        """get_utility_invoices() in live mode parses SAP B1 response correctly."""
        from src.connectors import sap_b1_adapter

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"Code": "INV001", "Memo": "Electricity Jan 2025"},
                {"Code": "INV002", "Memo": "Water Jan 2025"},
            ]
        }

        with patch.object(sap_b1_adapter, "ERP_MODE", "live"):
            adapter = sap_b1_adapter.SAPBusinessOneAdapter(server_url="https://sap.example.com")
            with patch.object(sap_b1_adapter.requests, "get", return_value=mock_response) as mock_get:
                result = adapter.get_utility_invoices(2025, 1)

        assert len(result) == 2
        assert result[0]["Code"] == "INV001"
        mock_get.assert_called_once()
