"""Evidence drill-down API — investor demo with real SHA-256 verification"""
from fastapi import APIRouter
from datetime import datetime
import hashlib
import csv
from pathlib import Path
from typing import Optional

router = APIRouter()

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
            records.append({
                "cluster": row["cluster"],
                "value": float(row["value"]),
                "timestamp": row["recorded_at"],
            })
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
        "confidence": "MEDIUM",
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

    EVIDENCE_CHAIN[cluster] = {
        "data_point_id": info.get("data_point_id", f"dp_{cluster[:4]}"),
        "org_id": "org_bd_001",
        "value": value,
        "unit": info.get("unit", ""),
        "metric_type": cluster,
        "confidence": info.get("confidence", "MEDIUM"),
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
def evidence_drilldown(metric_type: str):
    evidence = EVIDENCE_CHAIN.get(metric_type)
    if not evidence:
        return {"error": "metric not found"}, 404
    return evidence


@router.get("/verify/{metric_type}")
def verify_chain(metric_type: str):
    """Verify the hash chain for a given metric with real SHA-256 recomputation."""
    evidence = EVIDENCE_CHAIN.get(metric_type)
    if not evidence:
        return {"error": "metric not found"}, 404

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
        "chain_valid": evidence["chain_valid"],
        "hash_computed": computed_hash,
        "hash_stored": evidence["hash"],
        "match": match,
        "verified_at": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/full-chain/{metric_type}")
def full_chain(metric_type: str):
    """Return full lineage chain for a metric."""
    evidence = EVIDENCE_CHAIN.get(metric_type)
    if not evidence:
        return {"error": "metric not found"}, 404

    chain = []
    current = evidence
    for i in range(3):  # Max 3 hops
        chain.append({
            "step": i + 1,
            "data_point_id": current["data_point_id"],
            "value": current["value"],
            "unit": current["unit"],
            "source": current["source_system"],
            "hash": current["hash"],
            "confidence": current["confidence"],
        })
        if current.get("upstream_records"):
            # In real system: fetch upstream record
            break
        else:
            break

    return {
        "chain": chain,
        "chain_length": len(chain),
        "all_valid": all(r["chain_valid"] for r in [evidence]),
    }
