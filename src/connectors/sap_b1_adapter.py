"""
SAP Business One Service Layer — mock adapter for demo.
Returns structured data equivalent to what a real SAP B1 integration would provide.
"""
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# In demo mode, we return structured mock data matching SAP B1 Service Layer response shapes.
# In production, this module would use the SAP Business One Service Layer REST API:
#   Base URL: https://{server}:50000/b1s/v2/
#   Auth: OAuth2 or Session-based authentication
#   Endpoints used: GET /Users, GET /Invoices, GET /JournalEntries, GET /Items


def _load_csv_metrics() -> list[dict[str, Any]]:
    csv_path = Path(__file__).parent.parent.parent.parent / "data" / "operations" / "summary.csv"
    if not csv_path.exists():
        return []
    with open(csv_path) as f:
        return list(csv.DictReader(f))


class SAPBusinessOneAdapter:
    """
    Mock adapter for SAP Business One Service Layer.
    In production, replace _demo_call with real OAuth2 + HTTP calls.
    """

    def __init__(self, server_url: str = "", api_key: str = ""):
        self.server_url = server_url
        self.api_key = api_key
        self._demo_mode = True

    def _demo_call(self, endpoint: str) -> list[dict[str, Any]]:
        """Return demo data matching SAP B1 Service Layer response shapes."""
        if "Utility" in endpoint or "Invoice" in endpoint:
            csv_data = _load_csv_metrics()
            if csv_data:
                return csv_data
        return []

    def get_utility_invoices(self, year: int, month: int) -> list[dict[str, Any]]:
        """
        GET /JournalEntries?$filter=U_IsInvoice eq 'tYES' and ...
        Returns energy and water invoices for the given period.
        """
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
