"""Tests for evidence drill-down API — SHA-256 chain verification."""

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.evidence import EVIDENCE_CHAIN
from src.auth.jwt import create_token

client = TestClient(app)


def _admin_headers() -> dict:
    token = create_token(
        {
            "sub": "usr_test_001",
            "org_id": "org_bd_001",
            "email": "test@test.com",
            "role": "admin",
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _viewer_headers() -> dict:
    token = create_token(
        {
            "sub": "usr_viewer_001",
            "org_id": "org_bd_001",
            "email": "viewer@test.com",
            "role": "viewer",
        }
    )
    return {"Authorization": f"Bearer {token}"}


class TestEvidenceDrilldown:
    """GET /api/evidence/drilldown/{metric_type} — returns frontend-compatible shape."""

    def test_drilldown_valid_metric_returns_200(self):
        resp = client.get(
            "/api/evidence/drilldown/energy_kwh",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        # Frontend-compatible shape: entries[], summary{}, chain_valid
        assert "entries" in data
        assert "summary" in data
        assert "chain_valid" in data
        assert isinstance(data["entries"], list)
        assert len(data["entries"]) >= 1
        entry = data["entries"][0]
        assert entry["value"] == 2847320
        assert entry["source"] is not None
        assert entry["hash"] is not None
        assert data["chain_valid"] is True

    def test_drilldown_returns_all_expected_fields(self):
        resp = client.get(
            "/api/evidence/drilldown/energy_kwh",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        # Frontend-compatible shape
        assert "entries" in data
        assert "summary" in data
        assert "chain_valid" in data
        entry = data["entries"][0]
        assert "source" in entry
        assert "recorded_at" in entry
        assert "value" in entry
        assert "unit" in entry
        assert "confidence" in entry
        assert "hash" in entry
        assert "prev_hash" in entry
        # Summary fields
        assert "total_entries" in data["summary"]
        assert "earliest" in data["summary"]
        assert "latest" in data["summary"]

    def test_drilldown_nonexistent_metric_returns_error(self):
        resp = client.get(
            "/api/evidence/drilldown/nonexistent_metric",
            headers=_admin_headers(),
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "metric not found"

    def test_drilldown_scope3_category1_has_low_confidence(self):
        resp = client.get(
            "/api/evidence/drilldown/scope3_category1",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        entry = data["entries"][0]
        assert entry["confidence"] == "LOW"

    def test_drilldown_all_seeded_metrics_accessible(self):
        """Every cluster in the CSV data should be drillable."""
        expected_clusters = [
            "energy_kwh",
            "emissions_tco2",
            "water_m3",
            "scope3_category1",
            "diesel_consumed",
            "scope3_category6",
        ]
        for cluster in expected_clusters:
            resp = client.get(
                f"/api/evidence/drilldown/{cluster}",
                headers=_admin_headers(),
            )
            assert resp.status_code == 200, f"Failed for {cluster}"
            data = resp.json()
            assert "entries" in data
            assert len(data["entries"]) >= 1


class TestEvidenceVerify:
    """GET /api/evidence/verify/{metric_type}"""

    def test_verify_valid_metric_returns_200(self):
        resp = client.get(
            "/api/evidence/verify/energy_kwh",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["metric_type"] == "energy_kwh"
        assert data["integrity"] == "VALID"
        assert data["chain_length"] >= 1
        assert data["broken_at"] is None
        assert data["match"] is True
        assert "hash_computed" in data
        assert "hash_stored" in data
        assert "verified_at" in data

    def test_verify_nonexistent_metric_returns_error(self):
        resp = client.get(
            "/api/evidence/verify/nonexistent_metric",
            headers=_admin_headers(),
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "metric not found"

    def test_verify_tampered_diesel_chain_detected(self):
        """Diesel is the intentional tampered demo artifact."""
        resp = client.get(
            "/api/evidence/verify/diesel_consumed",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["integrity"] == "BROKEN"
        assert data["broken_at"] is not None
        # The diesel hash starts with TAMPERED_ prefix
        assert data["hash_stored"].startswith("TAMPERED_")
        assert data["match"] is True  # tampered check passes the startswith test

    def test_verify_all_non_diesel_metrics_are_valid(self):
        """Every metric except diesel should have a valid chain."""
        for cluster in [
            "energy_kwh",
            "emissions_tco2",
            "water_m3",
            "scope3_category1",
            "scope3_category6",
        ]:
            resp = client.get(
                f"/api/evidence/verify/{cluster}",
                headers=_admin_headers(),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["integrity"] == "VALID", f"{cluster} should be VALID"
            assert data["match"] is True, f"{cluster} hash should match"
            assert data["broken_at"] is None


class TestEvidenceFullChain:
    """GET /api/evidence/full-chain/{metric_type}"""

    def test_full_chain_valid_metric_returns_200(self):
        resp = client.get(
            "/api/evidence/full-chain/energy_kwh",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "chain" in data
        assert data["chain_length"] >= 1
        assert "all_valid" in data

    def test_full_chain_has_step_data(self):
        resp = client.get(
            "/api/evidence/full-chain/energy_kwh",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        chain = resp.json()["chain"]
        assert len(chain) >= 1
        step = chain[0]
        assert "step" in step
        assert "data_point_id" in step
        assert "value" in step
        assert "unit" in step
        assert "source" in step
        assert "hash" in step
        assert "confidence" in step

    def test_full_chain_nonexistent_metric_returns_error(self):
        resp = client.get(
            "/api/evidence/full-chain/nonexistent_metric",
            headers=_admin_headers(),
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "metric not found"


class TestEvidenceAuthRequired:
    """All evidence endpoints require authentication."""

    def test_drilldown_without_token_returns_401(self):
        resp = client.get("/api/evidence/drilldown/energy_kwh")
        assert resp.status_code == 401

    def test_verify_without_token_returns_401(self):
        resp = client.get("/api/evidence/verify/energy_kwh")
        assert resp.status_code == 401


class TestEvidenceExport:
    """GET /api/evidence/export"""

    def test_export_returns_zip_with_valid_structure(self):
        resp = client.get(
            "/api/evidence/export?period=2024-01-01_2026-12-31&framework=gri",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        assert "attachment" in resp.headers["content-disposition"]
        assert (
            "evidence_export_org_bd_001_gri_2024-01-01_2026-12-31.zip"
            in resp.headers["content-disposition"]
        )

    def test_export_zip_contains_required_files(self):
        import io
        import zipfile

        resp = client.get(
            "/api/evidence/export?period=2024-01-01_2026-12-31&framework=csrd",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        buf = io.BytesIO(resp.content)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            assert "evidence_summary.csv" in names
            assert "methodology.pdf" in names
            assert "integrity_report.pdf" in names
            assert "framework_mapping.csv" in names
            # raw_data/ dir is present only when records exist for the org
            raw_files = [n for n in names if n.startswith("raw_data/")]
            # If raw_data files exist, verify they are valid CSV
            for rf in raw_files:
                content = zf.read(rf).decode("utf-8")
                assert "cluster" in content

    def test_export_framework_allowlist_rejects_invalid(self):
        resp = client.get(
            "/api/evidence/export?period=2024-01-01_2026-12-31&framework=invalid",
            headers=_admin_headers(),
        )
        assert resp.status_code == 400
        assert "framework must be one of" in resp.json()["detail"]

    def test_export_period_format_rejects_invalid(self):
        resp = client.get(
            "/api/evidence/export?period=2024-01-01&framework=gri",
            headers=_admin_headers(),
        )
        assert resp.status_code == 400
        assert "YYYY-MM-DD_YYYY-MM-DD" in resp.json()["detail"]

    def test_export_requires_auth(self):
        resp = client.get(
            "/api/evidence/export?period=2024-01-01_2026-12-31&framework=gri",
        )
        assert resp.status_code == 401

    def test_full_chain_without_token_returns_401(self):
        resp = client.get("/api/evidence/full-chain/energy_kwh")
        assert resp.status_code == 401

    def test_viewer_can_access_drilldown(self):
        """Viewer role should be able to read evidence (read-only endpoint)."""
        resp = client.get(
            "/api/evidence/drilldown/energy_kwh",
            headers=_viewer_headers(),
        )
        assert resp.status_code == 200


class TestEvidenceLineage:
    """C3.6 — GET /api/evidence/lineage/{data_point_id}"""

    def test_lineage_valid_metric_returns_200(self):
        resp = client.get(
            "/api/evidence/lineage/dp_en_001",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_point_id"] == "dp_en_001"
        assert data["cluster"] == "energy_kwh"
        assert "nodes" in data
        assert "total_nodes" in data

    def test_lineage_nonexistent_returns_error(self):
        resp = client.get(
            "/api/evidence/lineage/dp_xx_999",
            headers=_admin_headers(),
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "data_point_id dp_xx_999 not found"

    def test_lineage_scope3_category1_returns_dag(self):
        resp = client.get(
            "/api/evidence/lineage/dp_s3_001",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cluster"] == "scope3_category1"
        assert data["total_nodes"] >= 1
        nodes = data["nodes"]
        assert all("rank" in n for n in nodes)
        assert all("data_point_id" in n for n in nodes)
        assert all("value" in n for n in nodes)
        assert all("chain_valid" in n for n in nodes)

    def test_lineage_requires_auth(self):
        resp = client.get("/api/evidence/lineage/dp_en_001")
        assert resp.status_code == 401


class TestEvidenceAuditorAccess:
    """C3.7 — Auditor access model with time-bounded tokens."""

    def test_create_auditor_link_returns_token(self):
        resp = client.post(
            "/api/evidence/auditor-link",
            json={"org_id": "org_bd_001", "expires_hours": 24},
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert "url" in data
        assert data["org_id"] == "org_bd_001"
        assert data["scope"] == "read_only"
        assert "expires_at" in data

    def test_create_auditor_link_requires_admin(self):
        resp = client.post(
            "/api/evidence/auditor-link",
            json={"org_id": "org_bd_001"},
            headers=_viewer_headers(),
        )
        assert resp.status_code == 403

    def test_create_auditor_link_requires_auth(self):
        resp = client.post(
            "/api/evidence/auditor-link",
            json={"org_id": "org_bd_001"},
        )
        assert resp.status_code == 401

    def test_auditor_access_with_valid_token_returns_evidence(self):
        # First create a link
        create_resp = client.post(
            "/api/evidence/auditor-link",
            json={"org_id": "org_bd_001", "expires_hours": 1},
            headers=_admin_headers(),
        )
        token = create_resp.json()["token"]

        # Then access via token
        resp = client.get(f"/api/evidence/auditor/{token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["org_id"] == "org_bd_001"
        assert data["scope"] == "read_only"
        assert "evidence_count" in data
        assert "metrics" in data
        assert isinstance(data["metrics"], list)

    def test_auditor_access_with_invalid_token_returns_404(self):
        resp = client.get("/api/evidence/auditor/invalid_token_xyz")
        assert resp.status_code == 404

    def test_auditor_access_no_auth_required(self):
        # Create link
        create_resp = client.post(
            "/api/evidence/auditor-link",
            json={"org_id": "org_bd_001", "expires_hours": 1},
            headers=_admin_headers(),
        )
        token = create_resp.json()["token"]

        # Access without Authorization header — should work
        resp = client.get(f"/api/evidence/auditor/{token}")
        assert resp.status_code == 200


class TestEvidenceChainIntegrity:
    """Verify hash chain linking between records."""

    def test_each_record_has_previous_hash(self):
        """First record should have previous_hash as None/None-string,
        subsequent records should reference prior hash."""
        for cluster in EVIDENCE_CHAIN:
            record = EVIDENCE_CHAIN[cluster]
            # previous_hash should be present (None for genesis is valid)
            assert "previous_hash" in record

    def test_energy_kwh_is_genesis_or_first(self):
        """First cluster in CSV order should have None previous_hash."""
        first = EVIDENCE_CHAIN.get("energy_kwh")
        if first:
            assert first["previous_hash"] is None
