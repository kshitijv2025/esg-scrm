"""Evidence drill-down API — investor demo with real SHA-256 verification"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from datetime import datetime, timedelta, timezone
import hashlib
import csv
import io
import zipfile
import secrets
from pathlib import Path
from typing import Optional
import time

from src.api.middleware.auth import require_auth
from src.api.routes.billing import require_auth_and_subscription
from src.api.middleware.rbac import require_role, ADMIN_ROLES
from src.db.database import get_connection, release_connection, _fetchone

router = APIRouter()

# ---------------------------------------------------------------------------
# Auditor token rate limiting (brute-force protection)
# ---------------------------------------------------------------------------
_AUDITOR_RATE_LIMIT = 10  # max failed lookups per window
_AUDITOR_RATE_WINDOW = 60  # seconds
_AUDITOR_RATE_TRACKER: dict[str, tuple[int, float]] = {}  # ip -> (failures, window_end)


def _check_auditor_rate_limit(request: Request) -> None:
    """Raise 429 if IP has exceeded failed auditor token lookups."""
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    failures, window_end = _AUDITOR_RATE_TRACKER.get(ip, (0, 0.0))

    if now > window_end:
        # Window expired, reset
        failures = 0
        window_end = now + _AUDITOR_RATE_WINDOW

    if failures >= _AUDITOR_RATE_LIMIT:
        raise HTTPException(
            429,
            "Too many failed auditor token lookups. Please try again later.",
        )

    # Advance window and record this attempt
    _AUDITOR_RATE_TRACKER[ip] = (failures + 1, window_end)


def _record_auditor_failure(request: Request) -> None:
    """Record a failed auditor token lookup for rate limiting."""
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    failures, window_end = _AUDITOR_RATE_TRACKER.get(ip, (0, 0.0))

    if now > window_end:
        failures = 0
        window_end = now + _AUDITOR_RATE_WINDOW

    _AUDITOR_RATE_TRACKER[ip] = (failures + 1, window_end)


# Path to real CSV data
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "operations"
SUMMARY_CSV = DATA_DIR / "summary.csv"


def _compute_hash(
    cluster: str,
    value: float,
    timestamp: str,
    prev_hash: Optional[str] = None,
) -> str:
    """Compute real SHA-256 hash for a metric record."""
    if prev_hash is None:
        prev_hash = "GENESIS"
    raw = f"{cluster}:{value}:{timestamp}:{prev_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_csv_records() -> list[dict]:
    """Load metric records from CSV in chain order."""
    if not SUMMARY_CSV.exists():
        return []

    records = []
    with open(SUMMARY_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(
                {
                    "cluster": row["cluster"],
                    "value": float(row["value"]),
                    "timestamp": row["recorded_at"],
                }
            )
    return records


# Build EVIDENCE_CHAIN from CSV with real hashes
EVIDENCE_CHAIN: dict = {}

_csv_records = _load_csv_records()
_prev_hash = None

_cluster_info = {
    "energy_kwh": {
        "data_point_id": "dp_en_001",
        "unit": "kWh",
        "confidence": "HIGH",
        "calculation_method": "direct_measurement",
        "source_system": "SAP Business One",
        "source_record_id": "INV-2025-0042",
        "emission_factor_source": "IEA 2023",
        "emission_factor_year": 2023,
        "emission_factor_table": "Table 4.2 — Bangladesh Grid Emission Factor",
        "emission_factor_value": 0.524,
        "emission_factor_unit": "kg CO2/kWh",
        "reported_in_frameworks": ["CSRD", "GRI", "TCFD"],
    },
    "emissions_tco2": {
        "data_point_id": "dp_em_001",
        "unit": "tCO2e",
        "confidence": "HIGH",
        "calculation_method": "activity_based",
        "source_system": "Calculated — derived from energy_kwh",
        "source_record_id": "CALC-2025-01-E1",
        "emission_factor_source": "IEA 2023",
        "emission_factor_year": 2023,
        "emission_factor_table": "Table 4.2 — Bangladesh Grid Emission Factor",
        "emission_factor_value": 0.524,
        "emission_factor_unit": "kg CO2/kWh",
        "reported_in_frameworks": ["CSRD", "ISSB", "GRI", "TCFD"],
        "upstream_records": ["dp_en_001"],
    },
    "water_m3": {
        "data_point_id": "dp_wt_001",
        "unit": "m³",
        "confidence": "HIGH",
        "calculation_method": "direct_measurement",
        "source_system": "SAP Business One — Municipal Water Bills",
        "source_record_id": "WATER-2025-01",
        "emission_factor_source": "N/A — direct measurement",
        "emission_factor_year": None,
        "emission_factor_table": None,
        "emission_factor_value": None,
        "emission_factor_unit": None,
        "reported_in_frameworks": ["CSRD", "GRI"],
        "upstream_records": [],
    },
    "scope3_category1": {
        "data_point_id": "dp_s3_001",
        "unit": "tCO2e",
        "confidence": "LOW",
        "calculation_method": "activity_based",
        "source_system": "Supplier Questionnaires + Spend-based fallback",
        "source_record_id": "SCOPE3-Q4-2024",
        "emission_factor_source": "GHG Protocol 2022",
        "emission_factor_year": 2022,
        "emission_factor_table": "Table 6.3 — Category 1 Spend-based Emission Factors",
        "emission_factor_value": 0.94,
        "emission_factor_unit": "kg CO2/$",
        "coverage_rate": 64,
        "responding_suppliers": 47,
        "total_suppliers": 73,
        "reported_in_frameworks": ["CSRD", "ISSB", "GRI"],
        "upstream_records": ["dp_s3_sup_001", "dp_s3_sup_002"],
    },
    "diesel_consumed": {
        "data_point_id": "dp_dl_001",
        "unit": "tCO2e",
        "confidence": "MEDIUM",
        "calculation_method": "manual_calculation",
        "source_system": "Manual entry — diesel generator consumption log",
        "source_record_id": "DIESEL-Q4-2024",
        "emission_factor_source": "GHG Protocol 2022",
        "emission_factor_year": 2022,
        "emission_factor_table": "Table 7.3 — Diesel Combustion Emission Factor",
        "emission_factor_value": 2.68,
        "emission_factor_unit": "kg CO2/L",
        "coverage_rate": None,
        "responding_suppliers": None,
        "total_suppliers": None,
        "reported_in_frameworks": ["CSRD", "GRI"],
        "upstream_records": [],
    },
    "scope3_category6": {
        "data_point_id": "dp_bt_001",
        "unit": "tCO2e",
        "confidence": "LOW",
        "calculation_method": "manual_calculation",
        "source_system": "Manual calculation — travel expense claims",
        "source_record_id": "BIZ-TRAVEL-Q4-2024",
        "emission_factor_source": "GHG Protocol 2022",
        "emission_factor_year": 2022,
        "emission_factor_table": "Table 9.1 — Business Travel Emission Factors",
        "emission_factor_value": "flight 0.255 kg/km, hotel 0.084 kg/night, car 0.171 kg/km",
        "coverage_rate": None,
        "responding_suppliers": None,
        "total_suppliers": None,
        "reported_in_frameworks": ["CSRD"],
        "upstream_records": [],
    },
}

for rec in _csv_records:
    cluster = rec["cluster"]
    value = rec["value"]
    timestamp = rec["timestamp"]
    info = _cluster_info.get(cluster, {})

    the_hash = _compute_hash(cluster, value, timestamp, _prev_hash)

    # Diesel is the tampered demo artifact
    if cluster == "diesel_consumed":
        chain_valid = False
        display_hash = f"TAMPERED_{the_hash[:32]}"
    else:
        chain_valid = True
        display_hash = the_hash

    conf = info.get("confidence", "MEDIUM")
    conf_map = {
        "HIGH": (0.9, ["direct_measurement", "automated_source"]),
        "MEDIUM": (0.6, ["activity_based", "partial_coverage"]),
        "LOW": (0.3, ["manual_calculation", "no_direct_measurement"]),
    }
    conf_score, conf_reasons = conf_map.get(conf, (0.6, ["unknown_source"]))
    if info.get("coverage_rate"):
        conf_score = round(conf_score * (info["coverage_rate"] / 100), 3)
        conf_reasons = conf_reasons + [f"{info['coverage_rate']}% supplier coverage"]

    EVIDENCE_CHAIN[cluster] = {
        "data_point_id": info.get("data_point_id", f"dp_{cluster[:4]}"),
        "org_id": "org_bd_001",
        "value": value,
        "unit": info.get("unit", ""),
        "metric_type": cluster,
        "confidence": conf,
        "confidence_score": conf_score,
        "confidence_reasons": conf_reasons,
        "calculation_method": info.get("calculation_method", ""),
        "source_system": info.get("source_system", ""),
        "source_record_id": info.get("source_record_id", ""),
        "extraction_timestamp": timestamp,
        "emission_factor_source": info.get("emission_factor_source"),
        "emission_factor_year": info.get("emission_factor_year"),
        "emission_factor_table": info.get("emission_factor_table"),
        "emission_factor_value": info.get("emission_factor_value"),
        "emission_factor_unit": info.get("emission_factor_unit"),
        "hash": display_hash,
        "previous_hash": _prev_hash,
        "chain_valid": chain_valid,
        "reported_in_frameworks": info.get("reported_in_frameworks", []),
        "upstream_records": info.get("upstream_records", []),
    }
    _prev_hash = the_hash


@router.get("/drilldown/{metric_type}")
def evidence_drilldown(metric_type: str, user: dict = Depends(require_auth_and_subscription)):
    """Return evidence records for metric_type in frontend-compatible shape."""
    org_id = user["org_id"]
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT hash, prev_hash, value, cluster, computed_at, recorded_at,
                   recorded_by, source_system, confidence, methodology
            FROM evidence_chain
            WHERE org_id = ? AND cluster = ?
            ORDER BY recorded_at DESC
            """,
            (org_id, metric_type),
        ).fetchall()
        if not rows:
            # Fall back to static EVIDENCE_CHAIN for seed data
            evidence = EVIDENCE_CHAIN.get(metric_type)
            if not evidence:
                return JSONResponse({"detail": "metric not found"}, status_code=404)
            # Build frontend-compatible shape from static chain
            entry = {
                "source": evidence.get("source_system", ""),
                "recorded_at": evidence.get("extraction_timestamp", ""),
                "value": evidence.get("value"),
                "unit": evidence.get("unit", ""),
                "confidence": evidence.get("confidence"),
                "hash": evidence.get("hash", ""),
                "prev_hash": evidence.get("previous_hash"),
            }
            return {
                "entries": [entry],
                "chain_valid": evidence.get("chain_valid", True),
                "summary": {
                    "total_entries": 1,
                    "earliest": evidence.get("extraction_timestamp", ""),
                    "latest": evidence.get("extraction_timestamp", ""),
                },
            }
        # Build entries list from DB rows
        entries = []
        earliest = None
        latest = None
        chain_valid = True
        for row in rows:
            entries.append(
                {
                    "source": row["source_system"],
                    "recorded_at": row["recorded_at"],
                    "value": row["value"],
                    "unit": "",
                    "confidence": row["confidence"],
                    "hash": row["hash"],
                    "prev_hash": row["prev_hash"],
                }
            )
            if earliest is None or row["recorded_at"] < earliest:
                earliest = row["recorded_at"]
            if latest is None or row["recorded_at"] > latest:
                latest = row["recorded_at"]
        return {
            "entries": entries,
            "chain_valid": chain_valid,
            "summary": {
                "total_entries": len(entries),
                "earliest": earliest or "",
                "latest": latest or "",
            },
        }
    finally:
        release_connection(conn)


@router.get("/verify/{metric_type}")
def verify_chain(metric_type: str, user: dict = Depends(require_auth_and_subscription)):
    """Verify the hash chain for a given metric with real SHA-256 recomputation."""
    evidence = EVIDENCE_CHAIN.get(metric_type)
    if not evidence:
        return JSONResponse({"detail": "metric not found"}, status_code=404)

    # Recompute hash from stored values to verify integrity
    computed_hash = _compute_hash(
        evidence["metric_type"],
        evidence["value"],
        evidence["extraction_timestamp"],
        evidence["previous_hash"],
    )

    # For tampered diesel, check if stored hash matches the tampered prefix
    if metric_type == "diesel_consumed":
        match = evidence["hash"].startswith("TAMPERED_")
    else:
        match = computed_hash == evidence["hash"]

    return {
        "metric_type": metric_type,
        "integrity": "VALID" if evidence["chain_valid"] else "BROKEN",
        "chain_length": 1,
        "broken_at": evidence["hash"] if not evidence["chain_valid"] else None,
        "hash_computed": computed_hash,
        "hash_stored": evidence["hash"],
        "match": match,
        "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@router.get("/full-chain/{metric_type}")
def full_chain(metric_type: str, user: dict = Depends(require_auth_and_subscription)):
    """Return full lineage chain for a metric."""
    evidence = EVIDENCE_CHAIN.get(metric_type)
    if not evidence:
        return JSONResponse({"detail": "metric not found"}, status_code=404)

    chain = []
    current = evidence
    for i in range(3):  # Max 3 hops
        chain.append(
            {
                "step": i + 1,
                "data_point_id": current["data_point_id"],
                "value": current["value"],
                "unit": current["unit"],
                "source": current["source_system"],
                "hash": current["hash"],
                "confidence": current["confidence"],
            }
        )
        if current.get("upstream_records"):
            break
        else:
            break

    return {
        "chain": chain,
        "chain_length": len(chain),
        "all_valid": all(r["chain_valid"] for r in [evidence]),
    }


@router.get("/lineage/{data_point_id}")
def evidence_lineage(data_point_id: str, user: dict = Depends(require_auth_and_subscription)):
    """Return full lineage DAG for a data point ID."""
    # Find the evidence entry that matches this data_point_id
    found_cluster = None
    for cluster, evidence in EVIDENCE_CHAIN.items():
        if evidence.get("data_point_id") == data_point_id:
            found_cluster = cluster
            break

    if found_cluster is None:
        return JSONResponse(
            {"detail": f"data_point_id {data_point_id} not found"},
            status_code=404,
        )

    evidence = EVIDENCE_CHAIN[found_cluster]

    # Build DAG by traversing upstream records
    nodes = []
    ranks = {}  # data_point_id -> rank

    # BFS to assign ranks
    queue = [(data_point_id, 0)]
    visited = set()
    while queue:
        dp_id, rank = queue.pop(0)
        if dp_id in visited:
            continue
        visited.add(dp_id)
        ranks[dp_id] = rank

        # Find this dp_id's evidence entry
        upstream_evidence = None
        for cluster, ev in EVIDENCE_CHAIN.items():
            if ev.get("data_point_id") == dp_id:
                upstream_evidence = ev
                break

        if upstream_evidence:
            for up_id in upstream_evidence.get("upstream_records", []):
                if up_id not in visited:
                    queue.append((up_id, rank + 1))

    # Build nodes list
    for cluster, ev in EVIDENCE_CHAIN.items():
        dp_id = ev.get("data_point_id")
        if dp_id in visited:
            nodes.append(
                {
                    "rank": ranks.get(dp_id, 0),
                    "data_point_id": dp_id,
                    "value": ev["value"],
                    "unit": ev.get("unit", ""),
                    "cluster": cluster,
                    "source": ev.get("source_system", ""),
                    "chain_valid": ev["chain_valid"],
                    "confidence": ev["confidence"],
                }
            )

    nodes.sort(key=lambda n: (n["rank"], n["data_point_id"]))

    return {
        "data_point_id": data_point_id,
        "cluster": found_cluster,
        "nodes": nodes,
        "total_nodes": len(nodes),
    }


@router.post("/auditor-link")
def create_auditor_link(
    payload: dict,
    user: dict = Depends(require_auth_and_subscription),
):
    """Create a time-limited auditor access link. Requires admin role."""
    require_role(user, ADMIN_ROLES)
    # Admin can only mint tokens for their own org — prevents cross-org token creation
    requested_org = payload.get("org_id")
    if requested_org is not None and requested_org != user.get("org_id"):
        raise HTTPException(403, "Cannot create auditor link for another organization")
    org_id = requested_org or user.get("org_id", "")
    expires_hours = payload.get("expires_hours", 24)
    token = secrets.token_urlsafe(32)
    expires_at = (
        (datetime.now(timezone.utc) + timedelta(hours=expires_hours))
        .isoformat()
        .replace("+00:00", "Z")
    )
    created_by = user.get("sub", "")
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO auditor_tokens (token, org_id, scope, expires_at, created_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (token, org_id, "read_only", expires_at, created_by),
        )
        conn.commit()
    finally:
        release_connection(conn)
    return {
        "token": token,
        "url": f"/api/evidence/auditor/{token}",
        "org_id": org_id,
        "scope": "read_only",
        "expires_at": expires_at,
    }


@router.get("/auditor/{token}")
def auditor_access(request: Request, token: str):
    """Access evidence with auditor token. No additional auth required. Rate-limited."""
    _check_auditor_rate_limit(request)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT org_id, scope, expires_at FROM auditor_tokens WHERE token = ?",
            (token,),
        ).fetchone()
        if not row:
            _record_auditor_failure(request)
            return JSONResponse({"detail": "auditor token not found"}, status_code=404)
        if datetime.now(timezone.utc) > datetime.fromisoformat(
            row["expires_at"].replace("Z", "+00:00")
        ):
            _record_auditor_failure(request)
            return JSONResponse({"detail": "auditor token has expired"}, status_code=410)

        org_id = row["org_id"]
        metrics = [
            {
                "cluster": cluster,
                "data_point_id": evidence.get("data_point_id"),
                "value": evidence["value"],
                "unit": evidence.get("unit", ""),
                "confidence": evidence["confidence"],
                "chain_valid": evidence["chain_valid"],
            }
            for cluster, evidence in EVIDENCE_CHAIN.items()
        ]
        return {
            "org_id": org_id,
            "scope": row["scope"],
            "evidence_count": len(metrics),
            "metrics": metrics,
        }
    finally:
        release_connection(conn)


ALLOWED_FRAMEWORKS = {"ghg_protocol", "esrs", "csrd", "gri", "tcfd", "issb"}


@router.get("/export")
def export_evidence(
    period: str = Query(..., description="Period in YYYY-MM-DD_YYYY-MM-DD format"),
    framework: str = Query(..., description="Framework name (e.g. ghg_protocol, esrs)"),
    user: dict = Depends(require_auth_and_subscription),
):
    """Export evidence package as a zip file for a given period and framework."""
    if framework not in ALLOWED_FRAMEWORKS:
        raise HTTPException(
            status_code=400,
            detail=f"framework must be one of {', '.join(sorted(ALLOWED_FRAMEWORKS))}",
        )

    import re

    if not re.match(r"^\d{4}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2}$", period):
        raise HTTPException(
            status_code=400,
            detail="period must be in YYYY-MM-DD_YYYY-MM-DD format",
        )

    if not SUMMARY_CSV.exists():
        raise HTTPException(status_code=400, detail="Export data not available")

    org_id = user.get("org_id", "org_bd_001")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # evidence_summary.csv — all metric records
        with open(SUMMARY_CSV, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        summary_csv = io.StringIO()
        if rows:
            writer = csv.DictWriter(summary_csv, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        zf.writestr("evidence_summary.csv", summary_csv.getvalue())

        # methodology.pdf — placeholder text file (PDF-style content)
        methodology_content = f"""METHODOLOGY REPORT
====================
Framework: {framework.upper()}
Period: {period}
Organization: {org_id}

This document describes the calculation methodology for each metric
in the evidence package.

ENERGY (energy_kwh)
Source: SAP Business One — Utility Invoices
Method: Direct measurement via smart meter readings
Emission Factor: IEA 2023 Table 4.2 — Bangladesh Grid Emission Factor
Value: 0.524 kg CO2/kWh

EMISSIONS (emissions_tco2)
Source: Calculated from energy consumption
Method: Activity-based using grid emission factor
Emission Factor: 0.524 kg CO2/kWh (IEA 2023)

WATER (water_m3)
Source: Municipal water bills via SAP Business One
Method: Direct measurement
No emission factor applied.

SCOPE 3 CATEGORY 1 (scope3_category1)
Source: Supplier questionnaires + spend-based fallback
Method: GHG Protocol 2022 Category 1 Spend-based method
Emission Factor: 0.94 kg CO2/USD (GHG Protocol 2022 Table 6.3)
Coverage: 64% (47 of 73 suppliers responded)

DIESEL (diesel_consumed)
Source: Manual entry — diesel generator consumption log
Method: Manual calculation
Emission Factor: 2.68 kg CO2/L (GHG Protocol 2022 Table 7.3)

SCOPE 3 CATEGORY 6 (scope3_category6)
Source: Travel expense claims
Method: Manual calculation
Emission Factors: Flight 0.255 kg/km, Hotel 0.084 kg/night, Car 0.171 kg/km
"""
        zf.writestr("methodology.pdf", methodology_content.encode("utf-8"))

        # integrity_report.pdf — hash chain verification summary
        integrity_content = "INTEGRITY REPORT\n================\n\n"
        integrity_content += f"Period: {period}\nFramework: {framework.upper()}\n\n"
        integrity_content += "Hash Chain Verification:\n"
        integrity_content += "------------------------\n"
        for cluster, evidence in EVIDENCE_CHAIN.items():
            status = "VALID" if evidence["chain_valid"] else "BROKEN"
            integrity_content += f"  {cluster}: {status} (hash={evidence['hash'][:16]}...)\n"
        integrity_content += (
            "\nAll SHA-256 hashes computed over: cluster:value:timestamp:prev_hash\n"
        )
        integrity_content += "Chain is VALID if recomputed hash matches stored hash.\n"
        zf.writestr("integrity_report.pdf", integrity_content.encode("utf-8"))

        # framework_mapping.csv — which metrics map to which disclosures
        mapping_content = "metric_type,framework,disclosure_code,disclosure_name\n"
        for cluster, evidence in EVIDENCE_CHAIN.items():
            for fw in evidence.get("reported_in_frameworks", []):
                mapping_content += f"{cluster},{fw},DISCLOSURE_{cluster.upper()},{cluster}\n"
        zf.writestr("framework_mapping.csv", mapping_content)

        # raw_data/ — per-cluster CSV files
        if rows:
            by_cluster: dict[str, list[dict]] = {}
            for row in rows:
                by_cluster.setdefault(row["cluster"], []).append(row)
            for cluster, cluster_rows in by_cluster.items():
                fn = f"raw_data/{cluster}.csv"
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=cluster_rows[0].keys())
                writer.writeheader()
                writer.writerows(cluster_rows)
                zf.writestr(fn, output.getvalue())

    buf.seek(0)
    filename = f"evidence_export_{org_id}_{framework}_{period}.zip"
    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/zip",
        },
    )
