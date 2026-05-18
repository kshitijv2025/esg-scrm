"""
CSV reference-data upload API — suppliers, emission factors, certifications.

This handles REFERENCE DATA ONLY. Operational data (metrics, evidence) must go
through MQTT as defined by the platform architecture.
"""
import csv
import io
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import require_role, EDITOR_ROLES
from src.db.database import _execute, get_connection

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_ROWS = 1000
VALID_TIERS = {"tier1", "tier2", "tier3"}


def _validate_csv_headers(
    reader: csv.DictReader, required: list[str], entity_name: str
) -> None:
    """Raise HTTPException if required columns are missing from the CSV header."""
    missing = [col for col in required if col not in (reader.fieldnames or [])]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns for {entity_name}: {', '.join(missing)}",
        )


def _read_csv(file: UploadFile) -> tuple[csv.DictReader, bytes]:
    """Read upload, enforce size limit, return parsed CSV reader and raw bytes."""
    raw = file.file.read()
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(raw)} bytes). Maximum is {MAX_FILE_SIZE} bytes.",
        )
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return reader, raw


# ---------------------------------------------------------------------------
# POST /suppliers
# ---------------------------------------------------------------------------

SUPPLIER_REQUIRED_COLUMNS = [
    "name", "country", "industry", "tier",
    "annual_spend_usd", "phone", "preferred_channel", "certifications",
]
SUPPLIER_REQUIRED_FIELDS = ["name", "country", "tier"]


@router.post("/suppliers")
def upload_suppliers(
    file: UploadFile = File(...),
    user: dict = Depends(require_auth),
):
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]
    """Bulk-import suppliers from a CSV file.

    CSV columns: name, country, industry, tier, annual_spend_usd, phone,
    preferred_channel, certifications.

    Rows missing name, country, or tier are skipped and reported as errors.
    """
    reader, _raw = _read_csv(file)
    _validate_csv_headers(reader, SUPPLIER_REQUIRED_COLUMNS, "suppliers")

    conn = get_connection()
    imported = 0
    errors: list[str] = []

    for row_index, row in enumerate(reader, start=2):
        if imported >= MAX_ROWS:
            errors.append(f"Row limit of {MAX_ROWS} reached; remaining rows skipped.")
            break

        # Skip rows missing required fields
        missing_fields = [
            f for f in SUPPLIER_REQUIRED_FIELDS if not row.get(f, "").strip()
        ]
        if missing_fields:
            errors.append(
                f"Row {row_index}: skipped — missing {', '.join(missing_fields)}"
            )
            continue

        tier_value = row["tier"].strip().lower()
        if tier_value not in VALID_TIERS:
            errors.append(
                f"Row {row_index}: skipped — invalid tier '{row['tier'].strip()}' "
                f"(must be one of {', '.join(sorted(VALID_TIERS))})"
            )
            continue

        supplier_id = f"sup_{uuid.uuid4().hex[:8]}"

        try:
            annual_spend = float(row.get("annual_spend_usd", "0") or "0")
        except ValueError:
            annual_spend = 0.0

        _execute(
            conn,
            """
            INSERT INTO suppliers
                (id, org_id, name, country, industry, tier,
                 annual_spend_usd, phone, preferred_channel, certifications)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                supplier_id,
                org_id,
                row["name"].strip(),
                row["country"].strip(),
                row.get("industry", "").strip(),
                tier_value,
                annual_spend,
                row.get("phone", "").strip(),
                row.get("preferred_channel", "whatsapp").strip(),
                row.get("certifications", "").strip(),
            ),
        )
        imported += 1

    if not _is_postgres():
        conn.close()

    return {"imported": imported, "errors": errors}


# ---------------------------------------------------------------------------
# POST /emission-factors
# ---------------------------------------------------------------------------

EMISSION_FACTOR_COLUMNS = [
    "factor_name", "category", "value", "unit", "country_code", "source", "year",
]


@router.post("/emission-factors")
def upload_emission_factors(
    file: UploadFile = File(...),
    user: dict = Depends(require_auth),
):
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]
    """Bulk-import emission factors from a CSV file.

    CSV columns: factor_name, category, value, unit, country_code, source, year.
    """
    reader, _raw = _read_csv(file)
    _validate_csv_headers(reader, EMISSION_FACTOR_COLUMNS, "emission factors")

    conn = get_connection()
    imported = 0
    errors: list[str] = []

    for row_index, row in enumerate(reader, start=2):
        if imported >= MAX_ROWS:
            errors.append(f"Row limit of {MAX_ROWS} reached; remaining rows skipped.")
            break

        factor_name = row.get("factor_name", "").strip()
        category = row.get("category", "").strip()
        raw_value = row.get("value", "").strip()
        unit = row.get("unit", "").strip()

        if not factor_name or not category or not raw_value or not unit:
            errors.append(
                f"Row {row_index}: skipped — missing required field(s) "
                f"(factor_name, category, value, and unit are required)"
            )
            continue

        try:
            value = float(raw_value)
        except ValueError:
            errors.append(f"Row {row_index}: skipped — invalid numeric value '{raw_value}'")
            continue

        year_val = row.get("year", "2024").strip()
        try:
            year_int = int(year_val) if year_val else 2024
        except ValueError:
            year_int = 2024

        _execute(
            conn,
            """
            INSERT INTO emission_factors
                (org_id, factor_name, category, value, unit, country_code, source, year)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                org_id,
                factor_name,
                category,
                value,
                unit,
                row.get("country_code", "").strip(),
                row.get("source", "GHG Protocol").strip(),
                year_int,
            ),
        )
        imported += 1

    if not _is_postgres():
        conn.close()

    return {"imported": imported, "errors": errors}


# ---------------------------------------------------------------------------
# POST /certifications
# ---------------------------------------------------------------------------

CERTIFICATION_COLUMNS = [
    "supplier_id", "certification_name", "issued_by", "valid_from", "valid_to",
]


@router.post("/certifications")
def upload_certifications(
    file: UploadFile = File(...),
    user: dict = Depends(require_auth),
):
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]
    """Bulk-import certifications from a CSV file.

    CSV columns: supplier_id, certification_name, issued_by, valid_from, valid_to.

    Each row appends the certification to the supplier's existing certifications
    field as a comma-separated string.
    """
    reader, _raw = _read_csv(file)
    _validate_csv_headers(reader, CERTIFICATION_COLUMNS, "certifications")

    conn = get_connection()
    imported = 0
    errors: list[str] = []

    for row_index, row in enumerate(reader, start=2):
        if imported >= MAX_ROWS:
            errors.append(f"Row limit of {MAX_ROWS} reached; remaining rows skipped.")
            break

        supplier_id = row.get("supplier_id", "").strip()
        cert_name = row.get("certification_name", "").strip()

        if not supplier_id or not cert_name:
            errors.append(
                f"Row {row_index}: skipped — supplier_id and certification_name are required"
            )
            continue

        # Verify supplier exists AND belongs to the user's org
        from src.db.database import _fetchone

        supplier = _fetchone(
            conn, "SELECT certifications, org_id FROM suppliers WHERE id = ?", (supplier_id,)
        )
        if not supplier:
            errors.append(
                f"Row {row_index}: skipped — supplier '{supplier_id}' not found"
            )
            continue
        if supplier.get("org_id") and supplier["org_id"] != org_id:
            errors.append(
                f"Row {row_index}: skipped — supplier '{supplier_id}' does not belong to your organization"
            )
            continue

        existing_certs = supplier.get("certifications") or ""
        if existing_certs:
            updated_certs = f"{existing_certs},{cert_name}"
        else:
            updated_certs = cert_name

        _execute(
            conn,
            "UPDATE suppliers SET certifications = ?, updated_at = datetime('now') WHERE id = ?",
            (updated_certs, supplier_id),
        )
        imported += 1

    if not _is_postgres():
        conn.close()

    return {"imported": imported, "errors": errors}


def _is_postgres() -> bool:
    """Check if the database backend is PostgreSQL."""
    from src.db.database import is_postgres
    return is_postgres()
