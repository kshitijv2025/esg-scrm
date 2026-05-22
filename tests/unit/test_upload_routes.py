"""
Unit tests for CSV upload routes: suppliers, emission factors, certifications.

Security focus: upload endpoints extract org_id from the authenticated user's
JWT token, NOT from form fields. This test suite verifies that tenant isolation
is enforced through the auth dependency.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.jwt import create_token
from src.db.database import get_connection, reset_database
from tests.conftest import _auth_headers


@pytest.fixture(autouse=True)
def _clean_db():
    """Reset the database before every test so uploads start from a clean state."""
    reset_database()
    yield
    # No cleanup needed -- next test's reset_database handles it.


@pytest.fixture()
def client():
    """FastAPI TestClient wired to the production app."""
    return TestClient(app)


@pytest.fixture()
def auth():
    """Valid admin auth headers (org_id='org_bd_001', role='admin')."""
    return _auth_headers()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _csv_bytes(header: str, rows: list[str]) -> bytes:
    """Build a UTF-8 CSV byte payload from a header line and data rows."""
    lines = [header] + rows
    return "\n".join(lines).encode("utf-8")


SUPPLIER_HEADER = "name,country,industry,tier,annual_spend_usd,phone,email"
EMISSION_HEADER = "factor_name,category,value,unit,country_code,source,year"
CERT_HEADER = "supplier_id,certification_name,issued_by,valid_from,valid_to"


# ---------------------------------------------------------------------------
# POST /api/upload/suppliers
# ---------------------------------------------------------------------------


class TestUploadSuppliers:
    """Tests for the supplier bulk-import endpoint."""

    def test_valid_csv_creates_suppliers_with_jwt_org_id(self, client, auth):
        """Uploading a valid supplier CSV creates rows using org_id from the JWT."""
        payload = _csv_bytes(
            SUPPLIER_HEADER,
            [
                "Acme Corp,BD,Textiles,tier1,500000,+8801x,acme@example.com",
                "Beta Ltd,IN,Chemicals,tier2,250000,+911x,betap@example.com",
            ],
        )

        response = client.post(
            "/api/upload/suppliers",
            files={"file": ("suppliers.csv", payload, "text/csv")},
            headers=auth,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["imported"] == 2
        assert body["errors"] == []

        # Verify the org_id in the database matches the JWT's org_id, not a form field.
        conn = get_connection()
        from src.db.database import _fetchall

        rows = _fetchall(
            conn,
            "SELECT org_id, name FROM suppliers WHERE org_id = ?",
            ("org_bd_001",),
        )
        conn.close()

        assert len(rows) == 2
        names = {r["name"] for r in rows}
        assert names == {"Acme Corp", "Beta Ltd"}

    def test_rejects_without_auth_401(self, client):
        """Posting suppliers without a JWT returns 401."""
        payload = _csv_bytes(
            SUPPLIER_HEADER,
            ["Acme Corp,BD,Textiles,tier1,500000,+8801x,acme@example.com"],
        )

        response = client.post(
            "/api/upload/suppliers",
            files={"file": ("suppliers.csv", payload, "text/csv")},
        )

        assert response.status_code == 401

    def test_validates_required_columns(self, client, auth):
        """Missing required CSV columns returns 400 with column names."""
        # Only provide name and country -- missing industry, tier, annual_spend_usd, phone
        payload = _csv_bytes("name,country", ["Acme Corp,BD"])

        response = client.post(
            "/api/upload/suppliers",
            files={"file": ("suppliers.csv", payload, "text/csv")},
            headers=auth,
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "Missing required columns" in detail
        for col in ("industry", "tier", "annual_spend_usd", "phone"):
            assert col in detail

    def test_skips_rows_missing_required_fields(self, client, auth):
        """Rows missing name, country, or tier are skipped and reported as errors."""
        payload = _csv_bytes(
            SUPPLIER_HEADER,
            [
                # Row 2: valid
                "Acme Corp,BD,Textiles,tier1,500000,+8801x,acme@example.com",
                # Row 3: missing name
                ",BD,Textiles,tier1,500000,+8801x,acme@example.com",
                # Row 4: missing country
                "Beta Ltd,,Chemicals,tier2,250000,+911x,betap@example.com",
                # Row 5: missing tier
                "Gamma Inc,PK,Logistics,,100000,+921x,gamma@example.com",
            ],
        )

        response = client.post(
            "/api/upload/suppliers",
            files={"file": ("suppliers.csv", payload, "text/csv")},
            headers=auth,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["imported"] == 1
        assert len(body["errors"]) == 3

        for error in body["errors"]:
            assert "skipped" in error

    def test_validates_tier_values(self, client, auth):
        """Rows with invalid tier values are skipped with a descriptive error."""
        payload = _csv_bytes(
            SUPPLIER_HEADER,
            [
                # Row 2: invalid tier
                "Acme Corp,BD,Textiles,tier4,500000,+8801x,acme@example.com",
                # Row 3: invalid tier (not in tier1/tier2/tier3)
                "Beta Ltd,IN,Chemicals,premium,250000,+911x,betap@example.com",
                # Row 4: valid (case-insensitive: TIER1 is lowercased to tier1)
                "Gamma Inc,PK,Logistics,TIER1,100000,+921x,gamma@example.com",
                # Row 5: valid
                "Delta Co,BD,Textiles,tier2,200000,+8802x,delta@example.com",
            ],
        )

        response = client.post(
            "/api/upload/suppliers",
            files={"file": ("suppliers.csv", payload, "text/csv")},
            headers=auth,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["imported"] == 2
        assert len(body["errors"]) == 2

        for error in body["errors"]:
            assert "invalid tier" in error

        # Verify only the valid rows landed with the correct tier.
        conn = get_connection()
        from src.db.database import _fetchall

        rows = _fetchall(conn, "SELECT name, tier FROM suppliers")
        conn.close()

        assert len(rows) == 2
        names_tiers = {r["name"]: r["tier"] for r in rows}
        assert names_tiers["Gamma Inc"] == "tier1"
        assert names_tiers["Delta Co"] == "tier2"


# ---------------------------------------------------------------------------
# POST /api/upload/emission-factors
# ---------------------------------------------------------------------------


class TestUploadEmissionFactors:
    """Tests for the emission-factor bulk-import endpoint."""

    def test_valid_csv_creates_factors_with_jwt_org_id(self, client, auth):
        """Uploading a valid emission-factor CSV creates rows with org_id from JWT."""
        payload = _csv_bytes(
            EMISSION_HEADER,
            [
                "Grid Electricity,Energy,0.5,kgCO2/kWh,BD,GHG Protocol,2024",
                "Natural Gas,Energy,2.0,kgCO2/m3,IN,IPCC,2023",
            ],
        )

        response = client.post(
            "/api/upload/emission-factors",
            files={"file": ("factors.csv", payload, "text/csv")},
            headers=auth,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["imported"] == 2
        assert body["errors"] == []

        # Verify org_id in database comes from the JWT.
        conn = get_connection()
        from src.db.database import _fetchall

        rows = _fetchall(
            conn,
            "SELECT org_id, factor_name FROM emission_factors WHERE org_id = ?",
            ("org_bd_001",),
        )
        conn.close()

        assert len(rows) == 2
        names = {r["factor_name"] for r in rows}
        assert names == {"Grid Electricity", "Natural Gas"}

    def test_rejects_without_auth_401(self, client):
        """Posting emission factors without a JWT returns 401."""
        payload = _csv_bytes(
            EMISSION_HEADER,
            ["Grid Electricity,Energy,0.5,kgCO2/kWh,BD,GHG Protocol,2024"],
        )

        response = client.post(
            "/api/upload/emission-factors",
            files={"file": ("factors.csv", payload, "text/csv")},
        )

        assert response.status_code == 401

    def test_validates_required_columns(self, client, auth):
        """Missing required CSV columns for emission factors returns 400."""
        payload = _csv_bytes("factor_name,category", ["Grid Electricity,Energy"])

        response = client.post(
            "/api/upload/emission-factors",
            files={"file": ("factors.csv", payload, "text/csv")},
            headers=auth,
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "Missing required columns" in detail
        for col in ("value", "unit", "country_code", "source", "year"):
            assert col in detail


# ---------------------------------------------------------------------------
# POST /api/upload/certifications
# ---------------------------------------------------------------------------


class TestUploadCertifications:
    """Tests for the certification bulk-import endpoint."""

    def _seed_supplier(self, supplier_id: str = "sup_test01") -> None:
        """Insert a supplier row so certifications can reference it."""
        conn = get_connection()
        from src.db.database import _execute

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
                "org_bd_001",
                "Test Supplier",
                "BD",
                "Textiles",
                "tier1",
                500000,
                "+8801x",
                "whatsapp",
                "",
            ),
        )
        conn.close()

    def test_valid_csv_creates_certifications(self, client, auth):
        """Uploading a valid certification CSV appends to the supplier's certifications."""
        self._seed_supplier("sup_test01")

        payload = _csv_bytes(
            CERT_HEADER,
            [
                "sup_test01,ISO 9001,BSI,2024-01-01,2025-12-31",
                "sup_test01,ISO 14001,Bureau Veritas,2024-06-01,2025-06-01",
            ],
        )

        response = client.post(
            "/api/upload/certifications",
            files={"file": ("certs.csv", payload, "text/csv")},
            headers=auth,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["imported"] == 2
        assert body["errors"] == []

        # Verify certifications were appended to the supplier row.
        conn = get_connection()
        from src.db.database import _fetchone

        supplier = _fetchone(
            conn, "SELECT certifications FROM suppliers WHERE id = ?", ("sup_test01",)
        )
        conn.close()

        certs = supplier["certifications"]
        assert "ISO 9001" in certs
        assert "ISO 14001" in certs

    def test_rejects_supplier_id_not_found(self, client, auth):
        """Rows referencing a non-existent supplier_id are skipped with an error."""
        # No supplier seeded -- sup_nonexistent does not exist.
        payload = _csv_bytes(
            CERT_HEADER,
            ["sup_nonexistent,ISO 9001,BSI,2024-01-01,2025-12-31"],
        )

        response = client.post(
            "/api/upload/certifications",
            files={"file": ("certs.csv", payload, "text/csv")},
            headers=auth,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["imported"] == 0
        assert len(body["errors"]) == 1
        assert "sup_nonexistent" in body["errors"][0]
        assert "not found" in body["errors"][0]

    def test_rejects_without_auth_401(self, client):
        """Posting certifications without a JWT returns 401."""
        payload = _csv_bytes(
            CERT_HEADER,
            ["sup_test01,ISO 9001,BSI,2024-01-01,2025-12-31"],
        )

        response = client.post(
            "/api/upload/certifications",
            files={"file": ("certs.csv", payload, "text/csv")},
        )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# RBAC: viewer role rejected on all upload endpoints
# ---------------------------------------------------------------------------


def _viewer_headers():
    """Auth headers with viewer role (read-only — should be rejected from uploads)."""
    token = create_token(
        {
            "sub": "usr_viewer_001",
            "org_id": "org_bd_001",
            "email": "viewer@test.com",
            "role": "viewer",
        }
    )
    return {"Authorization": f"Bearer {token}"}


class TestUploadRBAC:
    """Upload endpoints require editor or admin role. Viewer gets 403."""

    def test_supplier_upload_rejects_viewer(self, client):
        payload = _csv_bytes(
            SUPPLIER_HEADER,
            ["Acme Corp,BD,Textiles,tier1,500000,+8801x,acme@example.com"],
        )
        resp = client.post(
            "/api/upload/suppliers",
            files={"file": ("suppliers.csv", payload, "text/csv")},
            headers=_viewer_headers(),
        )
        assert resp.status_code == 403

    def test_emission_factor_upload_rejects_viewer(self, client):
        payload = _csv_bytes(
            EMISSION_HEADER,
            ["Grid Electricity,Energy,0.5,kgCO2/kWh,BD,GHG Protocol,2024"],
        )
        resp = client.post(
            "/api/upload/emission-factors",
            files={"file": ("factors.csv", payload, "text/csv")},
            headers=_viewer_headers(),
        )
        assert resp.status_code == 403

    def test_certification_upload_rejects_viewer(self, client):
        payload = _csv_bytes(
            CERT_HEADER,
            ["sup_test01,ISO 9001,BSI,2024-01-01,2025-12-31"],
        )
        resp = client.post(
            "/api/upload/certifications",
            files={"file": ("certs.csv", payload, "text/csv")},
            headers=_viewer_headers(),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Cross-org isolation
# ---------------------------------------------------------------------------


def _other_org_headers():
    """Auth headers for a DIFFERENT org — should not see org_bd_001 data."""
    token = create_token(
        {
            "sub": "usr_other_001",
            "org_id": "org_other_999",
            "email": "other@test.com",
            "role": "admin",
        }
    )
    return {"Authorization": f"Bearer {token}"}


class TestUploadOrgIsolation:
    """Upload endpoints create data scoped to the JWT's org_id."""

    def test_supplier_upload_scoped_to_jwt_org(self, client):
        """Suppliers uploaded with one org's token are not visible to another org."""
        # Upload as org_bd_001
        payload = _csv_bytes(
            SUPPLIER_HEADER,
            ["Acme Corp,BD,Textiles,tier1,500000,+8801x,acme@example.com"],
        )
        resp = client.post(
            "/api/upload/suppliers",
            files={"file": ("suppliers.csv", payload, "text/csv")},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200

        # Verify the supplier belongs to org_bd_001
        conn = get_connection()
        from src.db.database import _fetchall

        rows_bd = _fetchall(conn, "SELECT org_id FROM suppliers WHERE org_id = ?", ("org_bd_001",))
        rows_other = _fetchall(
            conn, "SELECT org_id FROM suppliers WHERE org_id = ?", ("org_other_999",)
        )
        conn.close()
        assert len(rows_bd) == 1
        assert len(rows_other) == 0
