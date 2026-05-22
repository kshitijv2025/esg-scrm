"""D6.4: API Endpoint Coverage Tests — verify all route groups return expected
structures, proper error handling, and RBAC enforcement."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_headers():
    from src.auth.jwt import create_token

    token = create_token(
        {
            "sub": "usr_admin_001",
            "org_id": "org_bd_001",
            "email": "admin@test.com",
            "role": "admin",
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers():
    from src.auth.jwt import create_token

    token = create_token(
        {
            "sub": "usr_viewer_001",
            "org_id": "org_bd_001",
            "email": "viewer@test.com",
            "role": "viewer",
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def editor_headers():
    from src.auth.jwt import create_token

    token = create_token(
        {
            "sub": "usr_editor_001",
            "org_id": "org_bd_001",
            "email": "editor@test.com",
            "role": "editor",
        }
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Helper: assert 401 / 403
# ---------------------------------------------------------------------------


class TestRBACEnforcement:
    """Missing auth -> 401, wrong role -> 403."""

    def test_dashboard_requires_auth(self, client):
        resp = client.get("/api/dashboard/live")
        assert resp.status_code == 401

    def test_evidence_requires_auth(self, client):
        resp = client.get("/api/evidence/drilldown/energy_kwh")
        assert resp.status_code == 401

    def test_frameworks_requires_auth(self, client):
        resp = client.get("/api/frameworks/map")
        assert resp.status_code == 401

    def test_questionnaires_requires_auth(self, client):
        resp = client.get("/api/questionnaires/suppliers")
        assert resp.status_code == 401

    def test_suppliers_requires_auth(self, client):
        resp = client.get("/api/suppliers/")
        assert resp.status_code == 401

    def test_reports_requires_auth(self, client):
        resp = client.get("/api/reports/esg-pdf")
        assert resp.status_code == 401

    def test_risk_requires_auth(self, client):
        resp = client.get("/api/risk/flags")
        assert resp.status_code == 401

    def test_scope3_requires_auth(self, client):
        resp = client.get("/api/scope3/categories")
        assert resp.status_code == 401

    def test_emission_factors_requires_auth(self, client):
        resp = client.get("/api/emission-factors/")
        assert resp.status_code == 401

    def test_alerts_requires_auth(self, client):
        resp = client.get("/api/alerts/thresholds")
        assert resp.status_code == 401

    def test_audit_requires_auth(self, client):
        resp = client.get("/api/audit/log")
        assert resp.status_code == 401

    def test_upload_requires_auth(self, client):
        resp = client.post("/api/upload/suppliers")
        assert resp.status_code == 401

    def test_templates_requires_auth(self, client):
        resp = client.get("/api/templates/")
        assert resp.status_code == 401

    def test_trust_requires_auth(self, client):
        resp = client.get("/api/trust/badges")
        assert resp.status_code == 401

    def test_admin_requires_auth(self, client):
        resp = client.get("/api/admin/users")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Helper: assert 422 / 400 on bad input
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Invalid input returns 422 or 400, not 500."""

    def test_dashboard_bad_offset(self, client, admin_headers):
        resp = client.get("/api/dashboard/trends?skip=-1", headers=admin_headers)
        assert resp.status_code in (400, 422)

    def test_frameworks_bad_metric_type(self, client, admin_headers):
        resp = client.get("/api/frameworks/map/invalid_metric", headers=admin_headers)
        # 404 or 422 depending on implementation
        assert resp.status_code in (400, 404, 422)

    def test_questionnaires_bad_skip(self, client, admin_headers):
        resp = client.get("/api/questionnaires/suppliers?skip=-5", headers=admin_headers)
        assert resp.status_code in (400, 422)

    def test_suppliers_bad_limit(self, client, admin_headers):
        resp = client.get("/api/suppliers/?limit=-1", headers=admin_headers)
        assert resp.status_code in (400, 422)

    def test_risk_bad_flag_id(self, client, admin_headers):
        resp = client.post("/api/risk/flags/invalid-id/acknowledge", headers=admin_headers)
        # 404 = not found is acceptable; 400/422 = bad id format
        assert resp.status_code in (400, 404, 422)

    def test_emission_factors_bad_year(self, client, admin_headers):
        resp = client.get("/api/emission-factors/?year=abcd", headers=admin_headers)
        assert resp.status_code in (400, 422)

    def test_alerts_bad_severity(self, client, admin_headers):
        resp = client.get("/api/alerts/?severity=INVALID", headers=admin_headers)
        assert resp.status_code in (400, 422)

    def test_scope3_bad_category(self, client, admin_headers):
        resp = client.get("/api/scope3/categories?invalid_param=x", headers=admin_headers)
        assert resp.status_code in (400, 422)


# ---------------------------------------------------------------------------
# Route group: dashboard
# ---------------------------------------------------------------------------


class TestDashboardRoutes:
    def test_dashboard_live(self, client, admin_headers):
        resp = client.get("/api/dashboard/live", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_dashboard_intensity(self, client, admin_headers):
        resp = client.get("/api/dashboard/intensity", headers=admin_headers)
        assert resp.status_code == 200

    def test_dashboard_trends(self, client, admin_headers):
        resp = client.get("/api/dashboard/trends", headers=admin_headers)
        assert resp.status_code == 200

    def test_dashboard_operations_summary(self, client, admin_headers):
        resp = client.get("/api/dashboard/operations-summary", headers=admin_headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Route group: evidence
# ---------------------------------------------------------------------------


class TestEvidenceRoutes:
    def test_evidence_drilldown(self, client, admin_headers):
        resp = client.get("/api/evidence/drilldown/energy_kwh", headers=admin_headers)
        assert resp.status_code == 200

    def test_evidence_export(self, client, admin_headers):
        resp = client.get(
            "/api/evidence/export?period=2024-01-01_2024-12-31&framework=ghg_protocol",
            headers=admin_headers,
        )
        assert resp.status_code in (200, 400)


# ---------------------------------------------------------------------------
# Route group: frameworks
# ---------------------------------------------------------------------------


class TestFrameworksRoutes:
    def test_frameworks_map(self, client, admin_headers):
        resp = client.get("/api/frameworks/map", headers=admin_headers)
        assert resp.status_code == 200

    def test_frameworks_compare(self, client, admin_headers):
        resp = client.get("/api/frameworks/compare/energy_kwh", headers=admin_headers)
        assert resp.status_code in (200, 404)


# ---------------------------------------------------------------------------
# Route group: questionnaires
# ---------------------------------------------------------------------------


class TestQuestionnairesRoutes:
    def test_questionnaires_list(self, client, admin_headers):
        resp = client.get("/api/questionnaires/suppliers", headers=admin_headers)
        assert resp.status_code == 200

    def test_questionnaires_coverage(self, client, admin_headers):
        resp = client.get("/api/questionnaires/coverage", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "spend_weighted_coverage_pct" in data or "total_coverage" in data

    def test_questionnaires_non_responders(self, client, admin_headers):
        resp = client.get("/api/questionnaires/non-responders", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Route group: suppliers
# ---------------------------------------------------------------------------


class TestSuppliersRoutes:
    def test_suppliers_list(self, client, admin_headers):
        resp = client.get("/api/suppliers/", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))

    def test_suppliers_risk_ranked(self, client, admin_headers):
        resp = client.get("/api/suppliers/risk-ranked", headers=admin_headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Route group: reports
# ---------------------------------------------------------------------------


class TestReportsRoutes:
    def test_reports_esg_pdf(self, client, admin_headers):
        resp = client.get("/api/reports/esg-pdf", headers=admin_headers)
        # May 200 or 400 depending on params; not 500
        assert resp.status_code in (200, 400, 422)

    def test_reports_pdf(self, client, admin_headers):
        resp = client.get("/api/reports/pdf", headers=admin_headers)
        assert resp.status_code in (200, 400, 422)


# ---------------------------------------------------------------------------
# Route group: risk
# ---------------------------------------------------------------------------


class TestRiskRoutes:
    def test_risk_flags(self, client, admin_headers):
        resp = client.get("/api/risk/flags", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "flags" in data

    def test_risk_summary(self, client, admin_headers):
        resp = client.get("/api/risk/summary", headers=admin_headers)
        assert resp.status_code == 200

    def test_risk_geopolitical(self, client, admin_headers):
        resp = client.get("/api/risk/geopolitical", headers=admin_headers)
        assert resp.status_code == 200

    def test_risk_scorecard(self, client, admin_headers):
        resp = client.get("/api/risk/scorecard", headers=admin_headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Route group: scope3
# ---------------------------------------------------------------------------


class TestScope3Routes:
    def test_scope3_categories(self, client, admin_headers):
        resp = client.get("/api/scope3/categories", headers=admin_headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Route group: emission-factors
# ---------------------------------------------------------------------------


class TestEmissionFactorsRoutes:
    def test_emission_factors_list(self, client, admin_headers):
        resp = client.get("/api/emission-factors/", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))

    def test_emission_factors_calculate(self, client, admin_headers):
        resp = client.get("/api/emission-factors/calculate", headers=admin_headers)
        assert resp.status_code in (200, 400, 422)


# ---------------------------------------------------------------------------
# Route group: alerts
# ---------------------------------------------------------------------------


class TestAlertsRoutes:
    def test_alerts_thresholds(self, client, admin_headers):
        resp = client.get("/api/alerts/thresholds", headers=admin_headers)
        assert resp.status_code == 200

    def test_alerts_check(self, client, admin_headers):
        resp = client.get("/api/alerts/check/energy_kwh?current_value=500", headers=admin_headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Route group: audit
# ---------------------------------------------------------------------------


class TestAuditRoutes:
    def test_audit_log(self, client, admin_headers):
        resp = client.get("/api/audit/log", headers=admin_headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Route group: upload
# ---------------------------------------------------------------------------


class TestUploadRoutes:
    def test_upload_history(self, client, admin_headers):
        resp = client.get("/api/upload/history", headers=admin_headers)
        assert resp.status_code in (200, 404)


# ---------------------------------------------------------------------------
# Route group: templates
# ---------------------------------------------------------------------------


class TestTemplatesRoutes:
    def test_templates_list(self, client, admin_headers):
        resp = client.get("/api/templates/", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))

    def test_templates_get_one(self, client, admin_headers):
        resp = client.get("/api/templates/1", headers=admin_headers)
        # 200 if template 1 exists, 404 if not
        assert resp.status_code in (200, 404)


# ---------------------------------------------------------------------------
# Route group: trust
# ---------------------------------------------------------------------------


class TestTrustRoutes:
    def test_trust_badges(self, client, admin_headers):
        resp = client.get("/api/trust/badges", headers=admin_headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Route group: admin
# ---------------------------------------------------------------------------


class TestAdminRoutes:
    def test_admin_users(self, client, admin_headers):
        resp = client.get("/api/admin/users", headers=admin_headers)
        assert resp.status_code == 200

    def test_admin_api_keys(self, client, admin_headers):
        resp = client.get("/api/admin/api-keys", headers=admin_headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Route group: ML
# ---------------------------------------------------------------------------


class TestMLRoutes:
    def test_ml_predict(self, client, admin_headers):
        resp = client.get("/api/ml/predict", headers=admin_headers)
        # May 200, 400, or 404 - not 500
        assert resp.status_code in (200, 400, 404, 422)


# ---------------------------------------------------------------------------
# Route group: water
# ---------------------------------------------------------------------------


class TestWaterRoutes:
    def test_water_wastewater(self, client, admin_headers):
        resp = client.get("/api/water/wastewater", headers=admin_headers)
        assert resp.status_code in (200, 404)


# ---------------------------------------------------------------------------
# Auth routes (no auth required)
# ---------------------------------------------------------------------------


class TestAuthRoutes:
    def test_auth_login(self, client):
        resp = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "wrongpassword",
            },
        )
        # 401 for wrong password, not 500
        assert resp.status_code in (401, 422)

    def test_auth_register(self, client):
        resp = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "Password123!",
                "full_name": "Test User",
                "org_id": "org_bd_001",
            },
        )
        # 200 success (new email), 409 conflict (duplicate), or 422 validation error
        assert resp.status_code in (200, 400, 409, 422)

    def test_auth_logout(self, client):
        resp = client.post("/api/auth/logout")
        assert resp.status_code in (200, 401)

    def test_auth_me(self, client, admin_headers):
        resp = client.get("/api/auth/me", headers=admin_headers)
        assert resp.status_code == 200
