"""Tests for framework mapping API — CSRD, ISSB, GRI, TCFD mappings."""
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.frameworks import FRAMEWORK_OUTPUTS
from src.auth.jwt import create_token

client = TestClient(app)


def _admin_headers() -> dict:
    token = create_token({
        "sub": "usr_test_001",
        "org_id": "org_bd_001",
        "email": "test@test.com",
        "role": "admin",
    })
    return {"Authorization": f"Bearer {token}"}


class TestListAllMappings:
    """GET /api/frameworks/map"""

    def test_returns_200_with_mappings_list(self):
        resp = client.get("/api/frameworks/map", headers=_admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "mappings" in data
        assert "total" in data
        assert isinstance(data["total"], int)
        assert data["total"] >= 1

    def test_total_matches_mappings_count(self):
        resp = client.get("/api/frameworks/map", headers=_admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == len(data["mappings"])

    def test_each_mapping_has_required_fields(self):
        resp = client.get("/api/frameworks/map", headers=_admin_headers())
        assert resp.status_code == 200
        mappings = resp.json()["mappings"]
        for mapping in mappings:
            assert "key" in mapping
            assert "metric_name" in mapping
            assert "frameworks" in mapping
            assert isinstance(mapping["frameworks"], list)

    def test_mappings_include_known_metrics(self):
        resp = client.get("/api/frameworks/map", headers=_admin_headers())
        assert resp.status_code == 200
        keys = [m["key"] for m in resp.json()["mappings"]]
        # These are known cluster keys (DB-driven, not the old static key format)
        assert "energy_kwh" in keys
        assert "diesel_consumed" in keys
        assert "water_m3" in keys

    def test_without_auth_returns_401(self):
        resp = client.get("/api/frameworks/map")
        assert resp.status_code == 401


class TestSingleFrameworkMap:
    """GET /api/frameworks/map/{metric_type}"""

    def test_energy_kwh_mapping_returns_200(self):
        resp = client.get(
            "/api/frameworks/map/energy_kwh",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source_metric"] == "energy_kwh"
        assert "frameworks" in data
        assert "source_value" in data

    def test_energy_mapping_has_csrd_issb_gri_tcfd(self):
        resp = client.get(
            "/api/frameworks/map/energy_kwh",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        frameworks = resp.json()["frameworks"]
        # New DB-driven format uses framework name as key (csrd_esrs, not csrd_esrs_e1)
        assert "csrd_esrs" in frameworks
        assert "issb_ifrs" in frameworks
        assert "gri" in frameworks
        assert "tcfd" in frameworks

    def test_framework_entry_has_required_fields(self):
        resp = client.get(
            "/api/frameworks/map/energy_kwh",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        frameworks = resp.json()["frameworks"]
        # Check one framework entry in detail (DB-driven: key is framework name, not framework+disclosure)
        csrd = frameworks["csrd_esrs"]
        assert "field_id" in csrd
        assert "label" in csrd
        assert "value" in csrd
        assert "unit" in csrd
        assert "description" in csrd  # DB maps to description, not methodology
        assert "confidence" in csrd

    def test_scope3_category1_mapping_returns_200(self):
        resp = client.get(
            "/api/frameworks/map/scope3_category_1",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source_metric"] == "scope3_category_1"

    def test_diesel_mapping_returns_200(self):
        resp = client.get(
            "/api/frameworks/map/diesel_consumed",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source_metric"] == "diesel_consumed"

    def test_water_m3_mapping_returns_200(self):
        resp = client.get(
            "/api/frameworks/map/water_m3",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200

    def test_nonexistent_metric_returns_error(self):
        resp = client.get(
            "/api/frameworks/map/nonexistent_metric",
            headers=_admin_headers(),
        )
        data = resp.json()
        if isinstance(data, list):
            assert any("detail" in item for item in data if isinstance(item, dict))
        else:
            assert "detail" in data

    def test_without_auth_returns_401(self):
        resp = client.get("/api/frameworks/map/energy_kwh")
        assert resp.status_code == 401


class TestCompareFrameworks:
    """GET /api/frameworks/compare/{metric_type}"""

    def test_compare_energy_returns_200(self):
        resp = client.get(
            "/api/frameworks/compare/energy_kwh",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["metric"] == "Energy Consumption"
        assert "source_value" in data
        assert "frameworks" in data
        assert len(data["frameworks"]) >= 2

    def test_compare_framework_entries_have_name_and_field_id(self):
        resp = client.get(
            "/api/frameworks/compare/energy_kwh",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        frameworks = resp.json()["frameworks"]
        for fw in frameworks:
            assert "name" in fw
            assert "field_id" in fw
            assert "value" in fw
            assert "unit" in fw
            assert "confidence" in fw

    def test_compare_scope3_category1_returns_200(self):
        resp = client.get(
            "/api/frameworks/compare/scope3_category_1",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200

    def test_compare_nonexistent_returns_error(self):
        resp = client.get(
            "/api/frameworks/compare/nonexistent_metric",
            headers=_admin_headers(),
        )
        data = resp.json()
        if isinstance(data, list):
            assert any("detail" in item for item in data if isinstance(item, dict))
        else:
            assert "detail" in data

    def test_compare_without_auth_returns_401(self):
        resp = client.get("/api/frameworks/compare/energy_kwh")
        assert resp.status_code == 401


class TestFrameworkDataStructure:
    """Verify FRAMEWORK_OUTPUTS data quality and completeness."""

    def test_all_entries_have_at_least_one_framework(self):
        for key, frameworks in FRAMEWORK_OUTPUTS.items():
            assert len(frameworks) >= 1, (
                f"Framework entry '{key}' has no frameworks mapped"
            )

    def test_all_framework_entries_have_field_id(self):
        for key, frameworks in FRAMEWORK_OUTPUTS.items():
            for fw_key, fw_data in frameworks.items():
                assert "field_id" in fw_data, (
                    f"{key} -> {fw_key} missing field_id"
                )

    def test_all_framework_entries_have_confidence(self):
        valid_confidences = {"HIGH", "MEDIUM", "LOW"}
        for key, frameworks in FRAMEWORK_OUTPUTS.items():
            for fw_key, fw_data in frameworks.items():
                assert fw_data.get("confidence") in valid_confidences, (
                    f"{key} -> {fw_key} has invalid confidence: "
                    f"{fw_data.get('confidence')}"
                )

    def test_total_entries_count(self):
        """Verify the number of distinct metric clusters mapped."""
        assert len(FRAMEWORK_OUTPUTS) >= 14, (
            f"Expected at least 14 framework output entries, "
            f"got {len(FRAMEWORK_OUTPUTS)}"
        )
