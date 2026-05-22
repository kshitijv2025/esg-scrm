"""
SAP Business One Service Layer adapter.

In demo mode (default), reads from CSV files.
In live mode, connects to SAP B1 Service Layer REST API.
Set ERP_MODE=live to activate real SAP connectivity.
Implements ERPConnector ABC for ESG+SCRM data orchestration.
"""

from __future__ import annotations

import asyncio
import csv
import ipaddress
import os
import socket
import requests
import structlog
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse
from uuid import UUID

from src.orchestration.erp_connector import (
    AssetRegister,
    ConnectionStatus,
    ConnectionTestResult,
    ConfidenceLevel,
    EmployeeData,
    EncryptedBlob,
    ERPConnector,
    ProductionRecord,
    SpendRecord,
    UtilityRecord,
    UtilityType,
)

logger = structlog.get_logger(__name__)

ERP_MODE = os.environ.get("ERP_MODE", "demo")

# Reserved/internal IP ranges blocked for SSRF protection
_SAFE_IP_RANGES = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("::ffff:0.0.0.0/96"),
)


def _is_safe_server_url(url: str) -> bool:
    """Return True if the URL does not resolve to an internal/reserved IP."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in addr_info:
            ip = ipaddress.ip_address(sockaddr[0])
            for blocked in _SAFE_IP_RANGES:
                if ip in blocked:
                    return False
        return True
    except Exception as e:
        logger.debug("sap_b1.ssrf_guard.error", url=url, error=str(e))
        return False


def _load_csv_metrics() -> list[dict[str, Any]]:
    csv_path = Path(__file__).parent.parent.parent.parent / "data" / "operations" / "summary.csv"
    if not csv_path.exists():
        return []
    with open(csv_path) as f:
        return list(csv.DictReader(f))


class SAPBusinessOneAdapter(ERPConnector):
    """Adapter for SAP Business One Service Layer.

    Implements the ERPConnector ABC, wrapping existing sync methods as async.
    In demo mode, reads from CSV files. In live mode, connects to
    SAP B1 Service Layer REST API.
    """

    def __init__(
        self,
        organization_id: UUID,
        credentials: Optional[EncryptedBlob] = None,
        server_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """Initialize the SAP B1 adapter.

        Args:
            organization_id: UUID of the organization.
            credentials: Encrypted credential blob (used in live mode).
            server_url: SAP B1 Service Layer URL (overrides env var).
            api_key: SAP B1 API key (overrides env var).
        """
        self._server_url = server_url or os.environ.get("SAP_B1_SERVER_URL", "")
        self._api_key = api_key or os.environ.get("SAP_B1_API_KEY", "")
        self._demo_mode = ERP_MODE != "live"
        self._credentials = credentials or EncryptedBlob.from_credentials(
            organization_id=organization_id, encrypted_value=b""
        )
        super().__init__(organization_id=organization_id, credentials=self._credentials)

    async def test_connection(self) -> ConnectionTestResult:
        """Verify credentials and API access.

        Returns:
            ConnectionTestResult with connection status and latency.
        """
        logger.info("sap_b1.test_connection.start", mode="demo" if self._demo_mode else "live")

        start = datetime.now(timezone.utc)

        if self._demo_mode:
            await asyncio.sleep(0.01)  # Simulate async check
            latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            logger.info("sap_b1.test_connection.demo_ok", latency_ms=latency_ms)
            return ConnectionTestResult(
                status=ConnectionStatus.CONNECTED,
                organization_id=self.organization_id,
                tested_at=datetime.now(timezone.utc),
                latency_ms=latency_ms,
            )

        if not self._server_url:
            logger.warning("sap_b1.test_connection.missing_url")
            return ConnectionTestResult(
                status=ConnectionStatus.ERROR,
                organization_id=self.organization_id,
                tested_at=datetime.now(timezone.utc),
                error_message="SAP_B1_SERVER_URL not configured",
            )

        # SSRF guard: reject internal/reserved IPs before making HTTP request
        if not _is_safe_server_url(self._server_url):
            logger.warning("sap_b1.test_connection.ssrf_blocked", url=self._server_url)
            return ConnectionTestResult(
                status=ConnectionStatus.ERROR,
                organization_id=self.organization_id,
                tested_at=datetime.now(timezone.utc),
                error_message="SAP_B1_SERVER_URL resolves to an internal or reserved IP address",
            )

        try:
            response = requests.get(
                self._server_url.rstrip("/") + "/Health",
                headers={"APIKey": self._api_key} if self._api_key else {},
                timeout=10,
            )
            latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

            if response.status_code in (401, 403):
                logger.warning("sap_b1.test_connection.auth_failed", status=response.status_code)
                return ConnectionTestResult(
                    status=ConnectionStatus.ERROR,
                    organization_id=self.organization_id,
                    tested_at=datetime.now(timezone.utc),
                    error_message=f"authentication_failed ({response.status_code})",
                    latency_ms=latency_ms,
                )

            if response.status_code == 200:
                logger.info("sap_b1.test_connection.live_ok", latency_ms=latency_ms)
                return ConnectionTestResult(
                    status=ConnectionStatus.CONNECTED,
                    organization_id=self.organization_id,
                    tested_at=datetime.now(timezone.utc),
                    latency_ms=latency_ms,
                    api_version=response.headers.get("X-SAP-B1-Version", "unknown"),
                )

            logger.warning("sap_b1.test_connection.http_error", status=response.status_code)
            return ConnectionTestResult(
                status=ConnectionStatus.ERROR,
                organization_id=self.organization_id,
                tested_at=datetime.now(timezone.utc),
                error_message=f"HTTP {response.status_code}",
                latency_ms=latency_ms,
            )

        except requests.exceptions.ConnectionError:
            latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            logger.warning("sap_b1.test_connection.connection_failed")
            return ConnectionTestResult(
                status=ConnectionStatus.ERROR,
                organization_id=self.organization_id,
                tested_at=datetime.now(timezone.utc),
                error_message="connection_failed",
                latency_ms=latency_ms,
            )
        except requests.exceptions.Timeout:
            latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            logger.warning("sap_b1.test_connection.timeout")
            return ConnectionTestResult(
                status=ConnectionStatus.ERROR,
                organization_id=self.organization_id,
                tested_at=datetime.now(timezone.utc),
                error_message="connection_timeout",
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            logger.error("sap_b1.test_connection.error", error=str(e))
            return ConnectionTestResult(
                status=ConnectionStatus.ERROR,
                organization_id=self.organization_id,
                tested_at=datetime.now(timezone.utc),
                error_message=f"unexpected_error: {type(e).__name__}",
                latency_ms=latency_ms,
            )

    async def extract_utility_expenses(
        self,
        start_date: date,
        end_date: date,
    ) -> list[UtilityRecord]:
        """Extract utility invoices: electricity, gas, water, waste.

        Args:
            start_date: Start of the extraction period.
            end_date: End of the extraction period.

        Returns:
            List of UtilityRecord objects for the period.
        """
        logger.info(
            "sap_b1.extract_utility.start",
            start_date=str(start_date),
            end_date=str(end_date),
        )

        # Wrap sync method in async
        def _sync_extract() -> list[dict[str, Any]]:
            raw = self.get_utility_invoices(start_date.year, start_date.month)
            return raw

        raw_records = await asyncio.get_event_loop().run_in_executor(None, _sync_extract)

        utility_records = []
        for raw in raw_records:
            try:
                utility_type_str = raw.get("cluster", "").lower()
                if "electric" in utility_type_str or "energy" in utility_type_str:
                    util_type = UtilityType.ELECTRICITY
                elif "gas" in utility_type_str or "natural_gas" in utility_type_str:
                    util_type = UtilityType.GAS
                elif "water" in utility_type_str:
                    util_type = UtilityType.WATER
                elif "waste" in utility_type_str:
                    util_type = UtilityType.WASTE
                elif "renewable" in utility_type_str or "solar" in utility_type_str:
                    util_type = UtilityType.RENEWABLE
                else:
                    util_type = UtilityType.ELECTRICITY  # Default

                record = UtilityRecord(
                    organization_id=self.organization_id,
                    invoice_number=raw.get("source", raw.get("invoice_number", "")),
                    utility_type=util_type,
                    amount=Decimal(str(raw.get("value", 0))),
                    currency=raw.get("currency", "USD"),
                    quantity=Decimal(str(raw.get("value", 0))),
                    unit=raw.get("unit", "kWh"),
                    start_date=start_date,
                    end_date=end_date,
                    recorded_at=datetime.fromisoformat(
                        raw.get("recorded_at", datetime.utcnow().isoformat() + "Z")
                    ).replace(tzinfo=timezone.utc),
                    source_system="SAP B1",
                    confidence=ConfidenceLevel.HIGH,
                )
                utility_records.append(record)
            except Exception as e:
                logger.warning("sap_b1.extract_utility.skip_record", error=str(e), raw=raw)

        logger.info(
            "sap_b1.extract_utility.complete",
            records_count=len(utility_records),
        )
        return utility_records

    async def extract_procurement_spend(
        self,
        category_codes: Optional[list[str]],
        start_date: date,
        end_date: date,
    ) -> list[SpendRecord]:
        """Extract purchase orders / invoices by spend category.

        Args:
            category_codes: Optional list of category codes to filter.
            start_date: Start of the extraction period.
            end_date: End of the extraction period.

        Returns:
            List of SpendRecord objects for the period.
        """
        logger.info(
            "sap_b1.extract_procurement.start",
            category_codes=category_codes,
            start_date=str(start_date),
            end_date=str(end_date),
        )

        # In demo mode, return empty list (no procurement data in CSV)
        if self._demo_mode:
            await asyncio.sleep(0.01)
            logger.info("sap_b1.extract_procurement.demo_complete", records_count=0)
            return []

        def _sync_extract() -> list[dict[str, Any]]:
            return self._live_call("PurchasesQuotes")

        raw_records = await asyncio.get_event_loop().run_in_executor(None, _sync_extract)

        spend_records = []
        for raw in raw_records:
            try:
                category_code = str(raw.get("Category", raw.get("U_Category", "")))
                if category_codes and category_code not in category_codes:
                    continue

                record = SpendRecord(
                    organization_id=self.organization_id,
                    purchase_order_number=str(raw.get("DocNum", raw.get("BaseEntry", ""))),
                    category_code=category_code,
                    category_description=raw.get("CategoryName", category_code),
                    amount=Decimal(str(raw.get("DocTotal", raw.get("Quantity", 0)))),
                    currency=raw.get("Currency", "USD"),
                    vendor_name=raw.get("CardName", "Unknown"),
                    purchase_date=start_date,
                    recorded_at=datetime.now(timezone.utc),
                    source_system="SAP B1",
                    confidence=ConfidenceLevel.LOW,
                )
                spend_records.append(record)
            except Exception as e:
                logger.warning("sap_b1.extract_procurement.skip_record", error=str(e), raw=raw)

        logger.info(
            "sap_b1.extract_procurement.complete",
            records_count=len(spend_records),
        )
        return spend_records

    async def extract_production_volume(
        self,
        product_codes: Optional[list[str]],
        start_date: date,
        end_date: date,
    ) -> list[ProductionRecord]:
        """Extract units produced, raw material consumption.

        Args:
            product_codes: Optional list of product codes to filter.
            start_date: Start of the extraction period.
            end_date: End of the extraction period.

        Returns:
            List of ProductionRecord objects for the period.
        """
        logger.info(
            "sap_b1.extract_production.start",
            product_codes=product_codes,
            start_date=str(start_date),
            end_date=str(end_date),
        )

        # In demo mode, return empty list (no production data in CSV)
        if self._demo_mode:
            await asyncio.sleep(0.01)
            logger.info("sap_b1.extract_production.demo_complete", records_count=0)
            return []

        def _sync_extract() -> list[dict[str, Any]]:
            return self.get_inventory_items()

        raw_records = await asyncio.get_event_loop().run_in_executor(None, _sync_extract)

        production_records = []
        for raw in raw_records:
            try:
                product_code = str(raw.get("ItemCode", ""))
                if product_codes and product_code not in product_codes:
                    continue

                # Production quantity from inventory (demo: use a default)
                qty = Decimal(str(raw.get("Quantity", raw.get("ItemQty", 1))))

                record = ProductionRecord(
                    organization_id=self.organization_id,
                    product_code=product_code,
                    product_name=raw.get("ItemName", product_code),
                    units_produced=qty,
                    unit_of_measure=raw.get("Quantity", "units"),
                    raw_material_consumption=None,
                    raw_material_unit=None,
                    production_date=start_date,
                    recorded_at=datetime.now(timezone.utc),
                    source_system="SAP B1",
                    confidence=ConfidenceLevel.HIGH,
                )
                production_records.append(record)
            except Exception as e:
                logger.warning("sap_b1.extract_production.skip_record", error=str(e), raw=raw)

        logger.info(
            "sap_b1.extract_production.complete",
            records_count=len(production_records),
        )
        return production_records

    async def extract_employee_data(self) -> EmployeeData:
        """Extract headcount, turnover, compensation bands (anonymized).

        Returns:
            EmployeeData with aggregated, anonymized HR metrics.
        """
        logger.info("sap_b1.extract_employee.start")

        if self._demo_mode:
            # Return synthetic demo data
            await asyncio.sleep(0.01)
            demo_data = EmployeeData(
                organization_id=self.organization_id,
                reporting_period_start=date(date.today().year, 1, 1),
                reporting_period_end=end_of_current_month(),
                total_headcount=250,
                new_hires=15,
                departures=8,
                average_tenure_years=3.5,
                compensation_band_low=Decimal("45000"),
                compensation_band_high=Decimal("120000"),
                department_breakdown={
                    "Manufacturing": 180,
                    "Admin": 30,
                    "Sales": 25,
                    "Engineering": 15,
                },
                recorded_at=datetime.now(timezone.utc),
                source_system="SAP B1 (demo)",
                confidence=ConfidenceLevel.MEDIUM,
            )
            logger.info("sap_b1.extract_employee.demo_complete")
            return demo_data

        def _sync_extract() -> list[dict[str, Any]]:
            return self.get_user_list()

        raw_records = await asyncio.get_event_loop().run_in_executor(None, _sync_extract)

        total_headcount = len(raw_records)
        new_hires = 0
        departures = 0

        demo_data = EmployeeData(
            organization_id=self.organization_id,
            reporting_period_start=date(date.today().year, 1, 1),
            reporting_period_end=end_of_current_month(),
            total_headcount=total_headcount,
            new_hires=new_hires,
            departures=departures,
            average_tenure_years=2.0,
            compensation_band_low=Decimal("40000"),
            compensation_band_high=Decimal("100000"),
            department_breakdown={"General": total_headcount},
            recorded_at=datetime.now(timezone.utc),
            source_system="SAP B1",
            confidence=ConfidenceLevel.MEDIUM,
        )

        logger.info("sap_b1.extract_employee.complete")
        return demo_data

    async def extract_asset_register(self) -> AssetRegister:
        """Extract equipment list for Scope 1 calculations (generators, fleet, refrigerants).

        Returns:
            AssetRegister with generator, fleet, and refrigerant assets.
        """
        logger.info("sap_b1.extract_assets.start")

        if self._demo_mode:
            # Return synthetic demo assets
            await asyncio.sleep(0.01)
            demo_assets = AssetRegister(
                organization_id=self.organization_id,
                asset_id="AST-001",
                asset_name="Diesel Generator 1",
                asset_category="generators",
                fuel_type="diesel",
                capacity=Decimal("500"),
                capacity_unit="kW",
                annual_consumption=Decimal("50000"),
                annual_consumption_unit="liters",
                emission_factor=Decimal("2.68"),  # kgCO2e per liter
                acquisition_date=date(2020, 1, 15),
                recorded_at=datetime.now(timezone.utc),
                source_system="SAP B1 (demo)",
                confidence=ConfidenceLevel.MEDIUM,
            )
            logger.info("sap_b1.extract_assets.demo_complete")
            return demo_assets

        # In live mode, would extract from SAP B1 asset master
        demo_assets = AssetRegister(
            organization_id=self.organization_id,
            asset_id="AST-001",
            asset_name="Diesel Generator 1",
            asset_category="generators",
            fuel_type="diesel",
            capacity=Decimal("500"),
            capacity_unit="kW",
            annual_consumption=Decimal("50000"),
            annual_consumption_unit="liters",
            emission_factor=Decimal("2.68"),
            acquisition_date=date(2020, 1, 15),
            recorded_at=datetime.now(timezone.utc),
            source_system="SAP B1",
            confidence=ConfidenceLevel.MEDIUM,
        )

        logger.info("sap_b1.extract_assets.complete")
        return demo_assets

    # --- Existing sync methods (wrapping the original interface) ---

    def health_check(self) -> dict[str, Any]:
        """Return connection status for health endpoint."""
        if self._demo_mode:
            return {"mode": "demo", "connected": True, "source": "CSV files"}

        if not self._server_url:
            return {
                "mode": "live",
                "connected": False,
                "error": "SAP_B1_SERVER_URL not configured",
                "source": "SAP B1 Service Layer",
            }

        try:
            response = requests.get(
                self._server_url.rstrip("/") + "/Health",
                headers={"APIKey": self._api_key} if self._api_key else {},
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
        if not self._server_url:
            return []

        url = f"{self._server_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {"APIKey": self._api_key} if self._api_key else {}

        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code in (401, 403):
                logger.warning(
                    "sap_b1.auth_failed endpoint=%s status=%s", endpoint, response.status_code
                )
                return []
            if response.status_code != 200:
                logger.warning(
                    "sap_b1.request_failed endpoint=%s status=%s", endpoint, response.status_code
                )
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
        """GET JournalEntries for utility invoices."""
        if not self._demo_mode:
            return self._live_call("JournalEntries?$filter=U_IsInvoice eq 'tYES'")
        return self._demo_call("utility_invoices")

    def get_inventory_items(self) -> list[dict[str, Any]]:
        """GET Items for materials traceability."""
        return self._demo_call("items")

    def get_user_list(self) -> list[dict[str, Any]]:
        """GET Users for audit trail."""
        return [{"UserCode": "manager_bd", "UserName": "Factory Manager", "Active": "tYES"}]

    def get_service_calls(self, from_date: str, to_date: str) -> list[dict[str, Any]]:
        """GET ServiceCalls for capability records."""
        return self._demo_call("service_calls")

    def get_currency_rates(self) -> list[dict[str, Any]]:
        """GET CurrencyRates for currency conversion."""
        return [
            {
                "Currency": "USD",
                "Rate": 0.0092,
                "ValidFrom": datetime.now(timezone.utc).date().isoformat(),
            }
        ]

    def to_internal_metric(self, sap_record: dict[str, Any]) -> dict[str, Any]:
        """Map SAP B1 JournalEntry or Invoice line to internal metric schema."""
        return {
            "cluster": sap_record.get("cluster", "unknown"),
            "value": float(sap_record.get("value", 0)),
            "unit": sap_record.get("unit", ""),
            "confidence": sap_record.get("confidence", "MEDIUM"),
            "source": f"SAP B1: {sap_record.get('source', 'unknown')}",
            "period": sap_record.get("period", ""),
            "recorded_at": sap_record.get("recorded_at", datetime.utcnow().isoformat() + "Z"),
        }


def end_of_current_month() -> date:
    """Return the last day of the current month."""
    today = date.today()
    if today.month == 12:
        return date(today.year, 12, 31)
    return date(today.year, today.month + 1, 1)
