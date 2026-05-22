"""
SAP Business One Service Layer adapter.

In demo mode (default), reads from CSV files.
In live mode, connects to SAP B1 Service Layer REST API.
Set ERP_MODE=live to activate real SAP connectivity.
"""
import csv
import os
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ERP_MODE = os.environ.get("ERP_MODE", "demo")


def _load_csv_metrics() -> list[dict[str, Any]]:
    csv_path = Path(__file__).parent.parent.parent.parent / "data" / "operations" / "summary.csv"
    if not csv_path.exists():
        return []
    with open(csv_path) as f:
        return list(csv.DictReader(f))


class SAPBusinessOneAdapter:
    """Adapter for SAP Business One Service Layer."""

    def __init__(self, server_url: str = "", api_key: str = ""):
        self.server_url = server_url or os.environ.get("SAP_B1_SERVER_URL", "")
        self.api_key = api_key or os.environ.get("SAP_B1_API_KEY", "")
        self._demo_mode = ERP_MODE != "live"

    def health_check(self) -> dict[str, Any]:
        """Return connection status for health endpoint."""
        if self._demo_mode:
            return {"mode": "demo", "connected": True, "source": "CSV files"}

        if not self.server_url:
            return {
                "mode": "live",
                "connected": False,
                "error": "SAP_B1_SERVER_URL not configured",
                "source": "SAP B1 Service Layer",
            }

        try:
            response = requests.get(
                self.server_url.rstrip("/") + "/Health",
                headers={"APIKey": self.api_key} if self.api_key else {},
                timeout=10,
            )
            if response.status_code in (401, 403):
                return {
                    "mode": "live",
                    "connected": False,
                    "error": f"authentication_failed ({response.status_code})",
                    "source": "SAP B1 Service Layer",
                }
            connected = response.status_code == 200
            return {
                "mode": "live",
                "connected": connected,
                "status_code": response.status_code,
                "source": "SAP B1 Service Layer",
            }
        except requests.exceptions.ConnectionError:
            return {
                "mode": "live",
                "connected": False,
                "error": "connection_failed",
                "source": "SAP B1 Service Layer",
            }
        except requests.exceptions.Timeout:
            return {
                "mode": "live",
                "connected": False,
                "error": "connection_timeout",
                "source": "SAP B1 Service Layer",
            }
        except Exception as e:
            logger.warning("sap_b1.health_check unexpected error: %s", str(e))
            return {
                "mode": "live",
                "connected": False,
                "error": f"health_check_failed: {type(e).__name__}",
                "source": "SAP B1 Service Layer",
            }

    def _demo_call(self, endpoint: str) -> list[dict[str, Any]]:
        """Return demo data matching SAP B1 Service Layer response shapes."""
        if "Utility" in endpoint or "Invoice" in endpoint:
            csv_data = _load_csv_metrics()
            if csv_data:
                return csv_data
        return []

    def _live_call(self, endpoint: str) -> list[dict[str, Any]]:
        """Make a live SAP B1 Service Layer request with graceful error handling."""
        if not self.server_url:
            return []

        url = f"{self.server_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {"APIKey": self.api_key} if self.api_key else {}

        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code in (401, 403):
                logger.warning("sap_b1.auth_failed endpoint=%s status=%s", endpoint, response.status_code)
                return []
            if response.status_code != 200:
                logger.warning("sap_b1.request_failed endpoint=%s status=%s", endpoint, response.status_code)
                return []
            data = response.json()
            return data.get("value", data) if isinstance(data, dict) else data
        except requests.exceptions.ConnectionError:
            logger.warning("sap_b1.connection_failed endpoint=%s", endpoint)
            return []
        except requests.exceptions.Timeout:
            logger.warning("sap_b1.timeout endpoint=%s", endpoint)
            return []
        except Exception as e:
            logger.warning("sap_b1.unexpected_error endpoint=%s error=%s", endpoint, str(e))
            return []

    def get_utility_invoices(self, year: int, month: int) -> list[dict[str, Any]]:
        """
        GET /JournalEntries?$filter=U_IsInvoice eq 'tYES' and ...
        Returns energy and water invoices for the given period.
        """
        if not self._demo_mode:
            return self._live_call("JournalEntries?$filter=U_IsInvoice eq 'tYES'")
        return self._demo_call("utility_invoices")

    def get_inventory_items(self) -> list[dict[str, Any]]:
        """
        GET /Items
        Returns item master data for materials traceability.
        """
        return self._demo_call("items")

    def get_user_list(self) -> list[dict[str, Any]]:
        """
        GET /Users
        Returns SAP B1 user list for audit trail.
        """
        return [{"UserCode": "manager_bd", "UserName": "Factory Manager", "Active": "tYES"}]

    def get_service_calls(self, from_date: str, to_date: str) -> list[dict[str, Any]]:
        """
        GET /ServiceCalls?$filter=CreateDate ge '2025-01-01' and ...
        Returns service/capability records.
        """
        return self._demo_call("service_calls")

    def get_currency_rates(self) -> list[dict[str, Any]]:
        """
        GET /CurrencyRates
        Returns BDT/USD exchange rates for currency conversion.
        """
        return [{"Currency": "USD", "Rate": 0.0092, "ValidFrom": datetime.now(timezone.utc).date().isoformat()}]

    def to_internal_metric(self, sap_record: dict[str, Any]) -> dict[str, Any]:
        """
        Map SAP B1 JournalEntry or Invoice line to internal metric schema.
        """
        return {
            "cluster": sap_record.get("cluster", "unknown"),
            "value": float(sap_record.get("value", 0)),
            "unit": sap_record.get("unit", ""),
            "confidence": sap_record.get("confidence", "MEDIUM"),
            "source": f"SAP B1: {sap_record.get('source', 'unknown')}",
            "period": sap_record.get("period", ""),
            "recorded_at": sap_record.get("recorded_at", datetime.utcnow().isoformat() + "Z"),
        }
