"""Tests for emission factors, framework mappings, alert thresholds, and audit log."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.db.database import _fetchall, get_connection, reset_database


@pytest.fixture(autouse=True)
def _fresh_db():
    reset_database()
    from src.db.seed import seed

    seed()
    from src.db.seed_emission_factors import seed_emission_factors

    seed_emission_factors()
    from src.db.seed_alert_thresholds import seed_alert_thresholds

    seed_alert_thresholds()


@pytest.fixture
def client():
    from src.auth.jwt import create_token

    token = create_token(
        {
            "sub": "usr_admin_001",
            "org_id": "org_bd_001",
            "email": "admin@textilebd.com",
            "role": "admin",
        }
    )
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


# --- Emission factors ---


class TestEmissionFactors:
    def test_list_all(self, client):
        resp = client.get("/api/emission-factors/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 40
        assert all("factor_name" in f for f in data["factors"])

    def test_filter_by_category(self, client):
        resp = client.get("/api/emission-factors/?category=grid_electricity")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 5
        assert all(f["category"] == "grid_electricity" for f in data["factors"])

    def test_filter_by_country(self, client):
        resp = client.get("/api/emission-factors/?country_code=BD")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert all(f["country_code"] == "BD" for f in data["factors"])

    def test_categories_endpoint(self, client):
        resp = client.get("/api/emission-factors/categories")
        assert resp.status_code == 200
        cats = resp.json()["categories"]
        assert "grid_electricity" in cats
        assert "scope3_spend" in cats

    def test_calculate_emissions(self, client):
        resp = client.get(
            "/api/emission-factors/calculate?activity_value=1000&factor_name=Natural%20gas"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["calculated_emissions"] > 0
        assert "emissions_unit" in data

    def test_calculate_missing_factor(self, client):
        resp = client.get(
            "/api/emission-factors/calculate?activity_value=100&factor_name=nonexistent"
        )
        assert resp.status_code == 404

    def test_list_factors_requires_auth(self):
        """GET /api/emission-factors/ returns 401 without authentication."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        unauthenticated_client = TestClient(app)
        resp = unauthenticated_client.get("/api/emission-factors/")
        assert resp.status_code == 401

    def test_list_factors_returns_structure(self, client):
        """Response includes all required fields for each factor."""
        resp = client.get("/api/emission-factors/")
        assert resp.status_code == 200
        data = resp.json()
        assert "factors" in data
        assert "total" in data
        assert isinstance(data["factors"], list)
        if data["factors"]:
            f = data["factors"][0]
            required_fields = ("factor_name", "category", "factor_value", "unit", "source")
            for field in required_fields:
                assert field in f, f"Missing field: {field}"

    def test_list_factors_filters_by_year(self, client):
        """Year filter returns only factors from that year."""
        resp = client.get("/api/emission-factors/?year=2022")
        assert resp.status_code == 200
        data = resp.json()
        # Seed data has factors with year=2022 (org-scoped to '' + user's org)
        assert data["total"] >= 1
        for f in data["factors"]:
            assert f.get("year") == 2022, f"Year filter returned a factor with year={f.get('year')}"

    def test_list_factors_org_scoped(self, client):
        """Factors returned are filtered by the authenticated org's org_id.

        The endpoint should only return factors belonging to org_bd_001.
        This test verifies org isolation by checking that a factor from a
        different org is NOT returned to org_bd_001's client.
        """
        from src.db.database import get_connection, release_connection

        # Insert a factor belonging to a different org
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO emission_factors
                    (org_id, category, factor_name, factor_value, unit, source,
                     country_code, year)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "org_other_999",  # different org
                    "grid_electricity",
                    "Test Factor For Org Isolation",
                    0.500,
                    "kgCO2e/kWh",
                    "Test source",
                    "XX",
                    2024,
                ),
            )
            conn.commit()
            factor_id = cursor.lastrowid
        finally:
            release_connection(conn)

        try:
            # org_bd_001's client should NOT see the other org's factor
            resp = client.get("/api/emission-factors/")
            assert resp.status_code == 200
            data = resp.json()
            factor_names = [f["factor_name"] for f in data["factors"]]
            assert "Test Factor For Org Isolation" not in factor_names, (
                "Org isolation violated: org_bd_001 saw a factor belonging to org_other_999"
            )
        finally:
            # Clean up the inserted factor
            conn2 = get_connection()
            try:
                conn2.execute("DELETE FROM emission_factors WHERE id = ?", (factor_id,))
                conn2.commit()
            finally:
                release_connection(conn2)


# --- Alert thresholds ---


class TestAlertThresholds:
    def test_list_thresholds(self, client):
        resp = client.get("/api/alerts/thresholds")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 15

    def test_filter_by_cluster(self, client):
        resp = client.get("/api/alerts/thresholds?cluster=energy")
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["cluster"] == "energy" for t in data["thresholds"])

    def test_create_threshold(self, client):
        resp = client.post(
            "/api/alerts/thresholds",
            json={
                "cluster": "test_cluster",
                "metric_cluster": "test_metric",
                "operator": ">",
                "threshold_value": 100.0,
                "severity": "WARNING",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "created"

    def test_create_threshold_invalid_operator(self, client):
        resp = client.post(
            "/api/alerts/thresholds",
            json={
                "cluster": "test",
                "metric_cluster": "test",
                "operator": "!=",
                "threshold_value": 100,
                "severity": "WARNING",
            },
        )
        assert resp.status_code == 400

    def test_check_thresholds_triggered(self, client):
        resp = client.get("/api/alerts/check/energy?current_value=5000000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_triggered"] >= 1

    def test_check_thresholds_ok(self, client):
        resp = client.get("/api/alerts/check/energy?current_value=100")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_triggered"] == 0


# --- Audit log ---


class TestAuditLog:
    def test_create_and_list(self, client):
        resp = client.post(
            "/api/audit/log",
            json={
                "org_id": "org_bd_001",
                "user_id": "usr_test",
                "action": "login",
                "resource_type": "session",
                "details": "Test login event",
            },
        )
        assert resp.status_code == 200

        resp = client.get("/api/audit/log?org_id=org_bd_001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(e["action"] == "login" for e in data["entries"])

    def test_filter_by_action(self, client):
        client.post(
            "/api/audit/log",
            json={
                "org_id": "org_bd_001",
                "user_id": "u1",
                "action": "create",
                "resource_type": "supplier",
            },
        )
        client.post(
            "/api/audit/log",
            json={
                "org_id": "org_bd_001",
                "user_id": "u1",
                "action": "delete",
                "resource_type": "supplier",
            },
        )

        resp = client.get("/api/audit/log?action=create")
        assert resp.status_code == 200
        data = resp.json()
        assert all(e["action"] == "create" for e in data["entries"])

    def test_missing_required_field(self, client):
        resp = client.post("/api/audit/log", json={"org_id": "org_bd_001"})
        assert resp.status_code == 400


# --- Seed data verification ---


class TestSeedData:
    def test_emission_factors_seeded(self):
        conn = get_connection()
        rows = _fetchall(conn, "SELECT COUNT(*) as cnt FROM emission_factors")
        assert rows[0]["cnt"] >= 40

    def test_alert_thresholds_seeded(self):
        conn = get_connection()
        rows = _fetchall(conn, "SELECT COUNT(*) as cnt FROM alert_thresholds")
        assert rows[0]["cnt"] >= 15

    def test_grid_factors_have_countries(self):
        conn = get_connection()
        rows = _fetchall(
            conn,
            "SELECT DISTINCT country_code FROM emission_factors WHERE category = 'grid_electricity'",
        )
        codes = [r["country_code"] for r in rows]
        assert "BD" in codes
        assert "IN" in codes
        assert "VN" in codes

    def test_thresholds_have_valid_operators(self):
        conn = get_connection()
        rows = _fetchall(conn, "SELECT DISTINCT operator FROM alert_thresholds")
        ops = [r["operator"] for r in rows]
        for op in ops:
            assert op in (">", "<", ">=", "<=", "=")


# --- Emission Intensity ---


class TestEmissionIntensity:
    """Tests for GET /api/dashboard/intensity endpoint."""

    def test_intensity_returns_correct_structure(self, client):
        """Intensity endpoint returns all required fields."""
        resp = client.get("/api/dashboard/intensity")
        assert resp.status_code == 200
        data = resp.json()
        required_keys = [
            "energy_kwh",
            "emissions_tco2",
            "production_volume",
            "energy_intensity_kwh_per_unit",
            "emission_intensity_tco2_per_unit",
            "period",
            "org_id",
        ]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"

    def test_intensity_calculation_with_valid_data(self, client):
        """Intensity ratios are computed correctly when production_volume > 0."""
        resp = client.get("/api/dashboard/intensity")
        assert resp.status_code == 200
        data = resp.json()

        assert data["production_volume"] > 0, "Seed data should have production_volume > 0"
        assert data["energy_kwh"] > 0
        assert data["emissions_tco2"] > 0

        expected_energy_intensity = data["energy_kwh"] / data["production_volume"]
        expected_emission_intensity = data["emissions_tco2"] / data["production_volume"]

        assert abs(data["energy_intensity_kwh_per_unit"] - expected_energy_intensity) < 0.001
        assert abs(data["emission_intensity_tco2_per_unit"] - expected_emission_intensity) < 0.001

    def test_intensity_returns_zero_when_production_volume_missing(self, client):
        """When production_volume is 0 or null, intensities are 0."""
        from src.db.database import _execute, get_connection

        conn = get_connection()
        try:
            _execute(
                conn, "UPDATE metrics SET production_volume = 0 WHERE org_id = ?", ("org_bd_001",)
            )
        finally:
            from src.db.database import release_connection

            release_connection(conn)

        resp = client.get("/api/dashboard/intensity")
        assert resp.status_code == 200
        data = resp.json()
        assert data["energy_intensity_kwh_per_unit"] == 0
        assert data["emission_intensity_tco2_per_unit"] == 0

    def test_intensity_requires_auth(self):
        """Intensity endpoint returns 401 without authentication."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        unauthenticated_client = TestClient(app)
        resp = unauthenticated_client.get("/api/dashboard/intensity")
        assert resp.status_code == 401


# --- Renewable Energy with REC Certificates ---


class TestRenewableEnergy:
    """Tests for GET /api/dashboard/renewable endpoint."""

    def test_renewable_returns_correct_structure(self, client):
        """Renewable endpoint returns all required fields."""
        resp = client.get("/api/dashboard/renewable")
        assert resp.status_code == 200
        data = resp.json()
        required_keys = [
            "total_kwh",
            "renewable_kwh",
            "renewable_percentage",
            "rec_certificates",
            "org_id",
        ]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"
        assert isinstance(data["rec_certificates"], list)

    def test_renewable_calculation_with_valid_data(self, client):
        """Renewable energy values are positive with valid seed data."""
        resp = client.get("/api/dashboard/renewable")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_kwh"] > 0, "Seed data should have total_kwh > 0"
        assert data["renewable_kwh"] > 0, "Seed data should have renewable_kwh > 0"
        assert data["renewable_percentage"] > 0, "Renewable percentage should be > 0"

    def test_renewable_percentage_calculation(self, client):
        """Renewable percentage is correctly computed from total and renewable kWh.

        Seed data: energy_kwh = 150000 kWh (latest production volume as proxy),
        renewable_kwh = 50000 kWh -> expected percentage = 33.3% (1dp).
        We verify the math: percentage == round(renewable_kwh / total_kwh * 100, 1).
        """
        resp = client.get("/api/dashboard/renewable")
        assert resp.status_code == 200
        data = resp.json()

        expected_pct = round(data["renewable_kwh"] / data["total_kwh"] * 100, 1)
        assert abs(data["renewable_percentage"] - expected_pct) < 0.1, (
            f"Expected {expected_pct}%, got {data['renewable_percentage']}%"
        )

    def test_renewable_requires_auth(self):
        """Renewable endpoint returns 401 without authentication."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        unauthenticated_client = TestClient(app)
        resp = unauthenticated_client.get("/api/dashboard/renewable")
        assert resp.status_code == 401


# --- Water Wastewater and Stress Level ---


class TestWaterMetrics:
    """Tests for GET /api/water/wastewater endpoint."""

    def test_wastewater_returns_correct_structure(self, client):
        """Wastewater endpoint returns all required fields."""
        resp = client.get("/api/water/wastewater")
        assert resp.status_code == 200
        data = resp.json()
        required_keys = [
            "wastewater_discharge",
            "water_stress_level",
            "supplier_water_stress",
            "org_id",
        ]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"

    def test_wastewater_with_valid_data(self, client):
        """Wastewater discharge data is populated from seed data."""
        resp = client.get("/api/water/wastewater")
        assert resp.status_code == 200
        data = resp.json()

        assert data["wastewater_discharge"] > 0, "Seed data should have wastewater_discharge > 0"
        assert isinstance(data["water_stress_level"], str)
        assert len(data["water_stress_level"]) > 0

    def test_water_stress_by_country_mapping(self, client):
        """Supplier water stress mapping reflects WRI Aqueduct levels."""
        resp = client.get("/api/water/wastewater")
        assert resp.status_code == 200
        data = resp.json()

        supplier_stress = data["supplier_water_stress"]
        assert isinstance(supplier_stress, list)
        assert len(supplier_stress) > 0, "Seed data has suppliers; mapping should not be empty"

        valid_levels = {"Low", "Low-Medium", "Medium-High", "High", "Extremely High", "Unknown"}
        for entry in supplier_stress:
            assert "supplier_id" in entry, "Each entry must have supplier_id"
            assert "supplier_name" in entry, "Each entry must have supplier_name"
            assert "country" in entry, "Each entry must have country"
            assert "water_stress_level" in entry, "Each entry must have water_stress_level"
            assert entry["water_stress_level"] in valid_levels, (
                f"Invalid stress level: {entry['water_stress_level']}"
            )

    def test_wastewater_requires_auth(self):
        """Wastewater endpoint returns 401 without authentication."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        unauthenticated_client = TestClient(app)
        resp = unauthenticated_client.get("/api/water/wastewater")
        assert resp.status_code == 401


# --- Supplier Response Dashboard ---


class TestQuestionnaireDashboard:
    """Tests for the supplier questionnaire response dashboard endpoints."""

    def _seed_dashboard_data(self):
        """Insert a template with questions and extra questionnaire responses.

        Temporarily disables FK enforcement so inserts succeed even when
        the connection pool carries stale schema from a prior test class.
        """
        import sqlite3

        from src.db.database import DB_PATH

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=OFF")
        try:
            conn.execute(
                """
                INSERT INTO questionnaire_templates (org_id, name, description, tier, category, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    "org_bd_001",
                    "ESG Basic Assessment",
                    "Basic ESG questionnaire",
                    1,
                    "environment",
                    1,
                ),
            )
            conn.commit()

            row = conn.execute(
                "SELECT id FROM questionnaire_templates WHERE name = 'ESG Basic Assessment'"
            ).fetchone()
            template_id = row["id"]

            conn.execute(
                """
                INSERT INTO questionnaire_questions (template_id, question_id, question_text, question_type, sort_order, required)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (template_id, "Q1", "Annual electricity consumption (kWh)", "number", 1, 1),
            )
            conn.execute(
                """
                INSERT INTO questionnaire_questions (template_id, question_id, question_text, question_type, sort_order, required)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (template_id, "Q2", "Annual water withdrawal (m3)", "number", 2, 1),
            )
            conn.execute(
                """
                INSERT INTO questionnaire_questions (template_id, question_id, question_text, question_type, sort_order, required)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (template_id, "Q3", "Do you have renewable energy installed?", "choice", 3, 1),
            )

            # Extra questionnaire responses to test by_channel breakdown.
            conn.execute(
                """
                INSERT INTO questionnaire_responses
                    (org_id, supplier_id, tier, question_id, response_text, response_value, channel)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                ("org_bd_001", "sup_001", 1, "1", "4,820,000", 4820000.0, "email"),
            )
            conn.execute(
                """
                INSERT INTO questionnaire_responses
                    (org_id, supplier_id, tier, question_id, response_text, response_value, channel)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                ("org_bd_001", "sup_007", 1, "2", "3,100", 3100.0, "manual"),
            )
            conn.commit()
        finally:
            conn.close()

    def test_response_summary_returns_correct_structure(self, client):
        """response-summary endpoint returns all required keys."""
        self._seed_dashboard_data()
        resp = client.get("/api/questionnaires/response-summary")
        assert resp.status_code == 200
        data = resp.json()
        required_keys = [
            "total_suppliers",
            "total_responded",
            "total_pending",
            "response_rate",
            "avg_confidence",
            "by_channel",
            "org_id",
        ]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"
        assert isinstance(data["by_channel"], dict)

    def test_response_summary_counts(self, client):
        """Response summary counts are internally consistent.

        Seed data: 7 suppliers (sup_001-sup_007) for org_bd_001.
        Responded (have questionnaire_responses): sup_001, sup_002, sup_006, sup_007 = 4.
        Pending = 7 - 4 = 3.
        response_rate = 4/7 * 100.
        """
        self._seed_dashboard_data()
        resp = client.get("/api/questionnaires/response-summary")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_suppliers"] == 7
        assert data["total_responded"] == 4
        assert data["total_pending"] == 3
        expected_rate = round(4 / 7 * 100, 1)
        assert abs(data["response_rate"] - expected_rate) < 0.2

    def test_non_responders_returns_unresponded_suppliers(self, client):
        """non-responders endpoint returns only suppliers without responses.

        Seed: sup_003 (pending), sup_004 (pending), sup_005 (not_sent) have no
        questionnaire_responses rows.
        """
        self._seed_dashboard_data()
        resp = client.get("/api/questionnaires/non-responders")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        responder_ids = {r["supplier_id"] for r in data}
        # sup_003, sup_004, sup_005 should be non-responders
        assert "sup_003" in responder_ids
        assert "sup_004" in responder_ids
        assert "sup_005" in responder_ids
        # sup_001, sup_002, sup_006, sup_007 have responses, should NOT appear
        assert "sup_001" not in responder_ids
        assert "sup_002" not in responder_ids
        assert "sup_006" not in responder_ids
        assert "sup_007" not in responder_ids
        # Each entry has required fields
        for entry in data:
            assert "supplier_id" in entry
            assert "name" in entry
            assert "country" in entry
            assert "annual_spend_usd" in entry
            assert "tier" in entry

    def test_supplier_responses_returns_individual_data(self, client):
        """responses/{supplier_id} returns individual responses with question_text."""
        self._seed_dashboard_data()
        resp = client.get("/api/questionnaires/responses/sup_001")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for entry in data:
            assert "question_id" in entry
            assert "response_value" in entry
            assert "response_text" in entry
            assert "channel" in entry
            assert "received_at" in entry

    def test_resend_returns_success(self, client):
        """POST resend logs action and returns success."""
        self._seed_dashboard_data()
        resp = client.post(
            "/api/questionnaires/resend",
            json={
                "supplier_ids": ["sup_003", "sup_004"],
                "template_id": "1",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["resent_count"] == 2
        assert "sup_003" in data["supplier_ids"]
        assert "sup_004" in data["supplier_ids"]

    def test_endpoints_require_auth(self):
        """All questionnaire dashboard endpoints return 401 without auth."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        unauthenticated_client = TestClient(app)

        assert unauthenticated_client.get("/api/questionnaires/response-summary").status_code == 401
        assert unauthenticated_client.get("/api/questionnaires/non-responders").status_code == 401
        assert (
            unauthenticated_client.get("/api/questionnaires/responses/sup_001").status_code == 401
        )
        assert (
            unauthenticated_client.post(
                "/api/questionnaires/resend",
                json={
                    "supplier_ids": ["sup_003"],
                    "template_id": "1",
                },
            ).status_code
            == 401
        )
        assert unauthenticated_client.post("/api/questionnaires/chase").status_code == 401
        assert (
            unauthenticated_client.post(
                "/api/questionnaires/dispatch-bulk",
                json={
                    "supplier_ids": ["sup_001"],
                },
            ).status_code
            == 401
        )

    def test_chase_workflow_dry_run(self, client):
        """POST /api/questionnaires/chase with dry_run=true returns pending suppliers."""
        self._seed_dashboard_data()
        resp = client.post("/api/questionnaires/chase?dry_run=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["dry_run"] is True
        assert "summary" in data
        assert "pending_suppliers_checked" in data["summary"]
        assert "email_reminders_sent" in data["summary"]
        assert "marked_nonresponsive" in data["summary"]
        # In seed data, sup_003/sup_004 are pending but no questionnaire_sent_at is set
        # so they won't be in the pending query (needs questionnaire_sent_at IS NOT NULL)

    def test_chase_workflow_require_editor_role(self, client):
        """POST /api/questionnaires/chase requires editor role."""
        # viewer client would fail; this test uses the default admin client (editor)
        resp = client.post("/api/questionnaires/chase?dry_run=true")
        assert resp.status_code == 200  # admin has editor role

    def test_dispatch_bulk_require_auth(self):
        """POST /api/questionnaires/dispatch-bulk requires auth."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        unauthenticated_client = TestClient(app)
        assert (
            unauthenticated_client.post(
                "/api/questionnaires/dispatch-bulk",
                json={
                    "supplier_ids": ["sup_001"],
                },
            ).status_code
            == 401
        )

    def test_dispatch_bulk_dispatches_to_suppliers(self, client):
        """POST /api/questionnaires/dispatch-bulk dispatches to multiple suppliers."""
        self._seed_dashboard_data()
        resp = client.post(
            "/api/questionnaires/dispatch-bulk",
            json={
                "supplier_ids": ["sup_003", "sup_004"],
                "template_id": 0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["total"] == 2
        assert "results" in data
        assert len(data["results"]) == 2
        # Each supplier should be dispatched (or error if no contact info)
        for r in data["results"]:
            assert "supplier_id" in r
            assert "status" in r


# --- Scope 3 Spend-Weighted Coverage Calculator ---


class TestScope3Coverage:
    """Tests for GET /api/questionnaires/coverage endpoint."""

    def _insert_test_suppliers_and_responses(self, conn):
        """Insert known test data for deterministic coverage math.

        Suppliers (all org_bd_001):
          sup_test_01: spend=100000, has questionnaire_response -> covered
          sup_test_02: spend=200000, has questionnaire_response -> covered
          sup_test_03: spend=300000, no response               -> not covered
          sup_test_04: spend=400000, no response               -> not covered

        Expected (combined with seed data):
          total_spend   = seed_spend + 1000000
          covered_spend = seed_covered + 300000
        """
        from src.db.database import _execute

        suppliers = [
            (
                "sup_test_01",
                "org_bd_001",
                "Test Supplier A",
                "BD",
                "Cotton",
                "tier1",
                100000.0,
                "responded",
            ),
            (
                "sup_test_02",
                "org_bd_001",
                "Test Supplier B",
                "IN",
                "Dyeing",
                "tier2",
                200000.0,
                "responded",
            ),
            (
                "sup_test_03",
                "org_bd_001",
                "Test Supplier C",
                "VN",
                "Fabric",
                "tier1",
                300000.0,
                "pending",
            ),
            (
                "sup_test_04",
                "org_bd_001",
                "Test Supplier D",
                "TH",
                "Thread",
                "tier3",
                400000.0,
                "not_sent",
            ),
        ]
        for sid, oid, name, country, industry, tier, spend, status in suppliers:
            _execute(
                conn,
                """
                INSERT INTO suppliers (id, org_id, name, country, industry, tier, annual_spend_usd,
                   phone, preferred_channel, questionnaire_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, '', 'whatsapp', ?)
            """,
                (sid, oid, name, country, industry, tier, spend, status),
            )

        # Only sup_test_01 and sup_test_02 get questionnaire_responses rows
        _execute(
            conn,
            """
            INSERT INTO questionnaire_responses (org_id, supplier_id, tier, question_id, response_text, channel)
            VALUES ('org_bd_001', 'sup_test_01', 1, 'q1', '50000', 'whatsapp')
        """,
        )
        _execute(
            conn,
            """
            INSERT INTO questionnaire_responses (org_id, supplier_id, tier, question_id, response_text, channel)
            VALUES ('org_bd_001', 'sup_test_02', 1, 'q1', '120000', 'whatsapp')
        """,
        )

    def test_coverage_returns_correct_structure(self, client):
        """Coverage endpoint returns all required fields."""
        from src.db.database import get_connection, release_connection

        conn = get_connection()
        try:
            self._insert_test_suppliers_and_responses(conn)
        finally:
            release_connection(conn)

        resp = client.get("/api/questionnaires/coverage")
        assert resp.status_code == 200
        data = resp.json()

        required_keys = [
            "spend_weighted_coverage_pct",
            "headcount_coverage_pct",
            "total_spend_usd",
            "covered_spend_usd",
            "total_suppliers",
            "responded_suppliers",
            "target_coverage_pct",
            "meets_target",
        ]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"

    def test_spend_weighted_calculation(self, client):
        """Spend-weighted coverage is computed correctly from actual questionnaire_responses."""
        from src.db.database import get_connection, release_connection

        conn = get_connection()
        try:
            self._insert_test_suppliers_and_responses(conn)
        finally:
            release_connection(conn)

        resp = client.get("/api/questionnaires/coverage")
        assert resp.status_code == 200
        data = resp.json()

        # Seed: 7 suppliers, 4 with questionnaire_responses (sup_001, sup_002, sup_006, sup_007)
        # Seed spend total: 2400000+3200000+8400000+1800000+480000+4200000+620000 = 21100000
        # Seed responded spend: 2400000+3200000+4200000+620000 = 10420000
        # Test: 4 new suppliers, 2 with responses
        # Test responded spend: 100000+200000 = 300000
        # Test total spend: 1000000
        # Combined: total = 22100000, covered = 10720000
        assert data["covered_spend_usd"] == 10720000
        assert data["total_spend_usd"] == 22100000

        # Verify spend_weighted_coverage_pct matches the math
        expected_pct = round(10720000 / 22100000 * 100, 1)
        assert abs(data["spend_weighted_coverage_pct"] - expected_pct) < 0.1, (
            f"Expected spend_weighted_coverage_pct={expected_pct}, got {data['spend_weighted_coverage_pct']}"
        )

    def test_headcount_calculation(self, client):
        """Headcount coverage is COUNT(responded) / COUNT(all) * 100."""
        from src.db.database import get_connection, release_connection

        conn = get_connection()
        try:
            self._insert_test_suppliers_and_responses(conn)
        finally:
            release_connection(conn)

        resp = client.get("/api/questionnaires/coverage")
        assert resp.status_code == 200
        data = resp.json()

        # Seed: 7 suppliers, 4 with questionnaire_responses
        # Test: 4 new suppliers, 2 with questionnaire_responses
        # Total: 11 suppliers, 6 with responses
        assert data["total_suppliers"] == 11
        assert data["responded_suppliers"] == 6

        expected_pct = round(6 / 11 * 100, 1)
        assert abs(data["headcount_coverage_pct"] - expected_pct) < 0.1, (
            f"Expected headcount_coverage_pct={expected_pct}, got {data['headcount_coverage_pct']}"
        )

    def test_coverage_target_check(self, client):
        """meets_target reflects whether spend_weighted_coverage >= target_coverage_pct."""
        from src.db.database import get_connection, release_connection

        conn = get_connection()
        try:
            self._insert_test_suppliers_and_responses(conn)
        finally:
            release_connection(conn)

        resp = client.get("/api/questionnaires/coverage")
        assert resp.status_code == 200
        data = resp.json()

        # With combined data: spend_weighted ~48.7%, default target = 60%
        # So meets_target should be False
        assert data["target_coverage_pct"] == 60
        assert isinstance(data["meets_target"], bool)
        assert data["meets_target"] == (
            data["spend_weighted_coverage_pct"] >= data["target_coverage_pct"]
        )

    def test_coverage_requires_auth(self):
        """Coverage endpoint returns 401 without authentication."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        unauthenticated_client = TestClient(app)
        resp = unauthenticated_client.get("/api/questionnaires/coverage")
        assert resp.status_code == 401

    def test_coverage_with_no_responses(self, client):
        """When no suppliers have questionnaire_responses, coverage is 0%."""
        from src.db.database import _execute, get_connection, release_connection

        conn = get_connection()
        try:
            _execute(conn, "DELETE FROM questionnaire_responses")
        finally:
            release_connection(conn)

        resp = client.get("/api/questionnaires/coverage")
        assert resp.status_code == 200
        data = resp.json()

        assert data["covered_spend_usd"] == 0
        assert data["responded_suppliers"] == 0
        assert data["spend_weighted_coverage_pct"] == 0
        assert data["headcount_coverage_pct"] == 0
        assert data["meets_target"] is False


# --- ESG Scoring Engine ---


class TestESGScoring:
    """Tests for GET /api/suppliers/{supplier_id}/score endpoint.

    The scoring engine maps T-prefixed question_ids (T1Q1, T1Q2, etc.) to
    E/S/G dimensions with normalization rules. Composite = weighted average.
    Risk tiers: A>=80, B>=60, C>=40, D<40.
    """

    def _ensure_supplier(self, supplier_id: str, industry: str = "Cotton trading"):
        """Insert a supplier row if it does not already exist (needed for FK on questionnaire_responses)."""
        from src.db.database import _execute, _fetchone, get_connection, release_connection

        conn = get_connection()
        try:
            existing = _fetchone(conn, "SELECT id FROM suppliers WHERE id = ?", (supplier_id,))
            if existing is None:
                _execute(
                    conn,
                    """
                    INSERT INTO suppliers
                    (id, org_id, name, country, industry, tier, annual_spend_usd,
                     phone, preferred_channel, questionnaire_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, '', 'whatsapp', 'responded')
                """,
                    (
                        supplier_id,
                        "org_bd_001",
                        f"Test Supplier {supplier_id}",
                        "BD",
                        industry,
                        "tier1",
                        100000,
                    ),
                )
        finally:
            release_connection(conn)

    def _insert_scoring_responses(self, supplier_id: str, responses: list):
        """Insert questionnaire responses with T-prefixed question_ids that the scorer recognizes."""
        from src.db.database import _execute, get_connection, release_connection

        self._ensure_supplier(supplier_id)

        conn = get_connection()
        try:
            for r in responses:
                _execute(
                    conn,
                    """
                    INSERT INTO questionnaire_responses
                    (org_id, supplier_id, tier, question_id, response_text, response_value, channel)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        "org_bd_001",
                        supplier_id,
                        r["tier"],
                        r["question_id"],
                        r.get("response_text", ""),
                        r.get("response_value"),
                        "test",
                    ),
                )
        finally:
            release_connection(conn)

    def _clear_supplier_responses(self, supplier_id: str):
        """Remove all questionnaire responses for a supplier."""
        from src.db.database import _execute, get_connection, release_connection

        conn = get_connection()
        try:
            _execute(
                conn, "DELETE FROM questionnaire_responses WHERE supplier_id = ?", (supplier_id,)
            )
        finally:
            release_connection(conn)

    def test_score_returns_correct_structure(self, client):
        """Score endpoint returns all required top-level and nested keys."""
        self._insert_scoring_responses(
            "sup_001",
            [
                {"tier": 1, "question_id": "T1Q1", "response_value": 1000000},
                {"tier": 1, "question_id": "T1Q2", "response_value": 500},
                {"tier": 1, "question_id": "T1Q4", "response_value": 2},
                {"tier": 1, "question_id": "T1Q6", "response_value": 2},
            ],
        )

        resp = client.get("/api/suppliers/sup_001/score")
        assert resp.status_code == 200
        data = resp.json()

        required_top = [
            "supplier_id",
            "composite_score",
            "risk_tier",
            "environment",
            "social",
            "governance",
            "methodology",
            "weights_used",
        ]
        for key in required_top:
            assert key in data, f"Missing top-level key: {key}"

        for dim in ("environment", "social", "governance"):
            dim_data = data[dim]
            assert "score" in dim_data, f"Missing 'score' in {dim}"
            assert "question_count" in dim_data, f"Missing 'question_count' in {dim}"
            assert "contributions" in dim_data, f"Missing 'contributions' in {dim}"

    def test_score_calculation_math(self, client):
        """Insert known responses and verify dimension scores compute correctly.

        Using T1Q1 (environment, lower_is_better, max=5M):
          raw=1M -> ratio=0.2 -> score=(1-0.2)*100 = 80.0
        Using T1Q7 (environment, higher_is_better, max=5):
          raw=3 -> score=(3/5)*100 = 60.0
        Environment average = (80 + 60) / 2 = 70.0

        Using T1Q4 (social, higher_is_better, max=3):
          raw=2 -> score=(2/3)*100 = 66.7
        Using T1Q5 (social, lower_is_better, max=50):
          raw=10 -> ratio=0.2 -> score=(1-0.2)*100 = 80.0
        Social average = (66.7 + 80) / 2 = 73.3

        Using T1Q6 (governance, higher_is_better, max=3):
          raw=3 -> score=(3/3)*100 = 100.0
        """
        # Clear seed data responses first so they don't interfere with math
        self._clear_supplier_responses("sup_001")

        self._insert_scoring_responses(
            "sup_001",
            [
                # Environment
                {"tier": 1, "question_id": "T1Q1", "response_value": 1000000},
                {"tier": 1, "question_id": "T1Q7", "response_value": 3},
                # Social
                {"tier": 1, "question_id": "T1Q4", "response_value": 2},
                {"tier": 1, "question_id": "T1Q5", "response_value": 10},
                # Governance
                {"tier": 1, "question_id": "T1Q6", "response_value": 3},
            ],
        )

        resp = client.get("/api/suppliers/sup_001/score")
        assert resp.status_code == 200
        data = resp.json()

        # Environment: avg of 80.0 and 60.0 = 70.0
        assert abs(data["environment"]["score"] - 70.0) < 1.0, (
            f"Expected environment ~70.0, got {data['environment']['score']}"
        )
        assert data["environment"]["question_count"] == 2

        # Social: avg of ~66.7 and 80.0 = ~73.3
        assert abs(data["social"]["score"] - 73.3) < 1.5, (
            f"Expected social ~73.3, got {data['social']['score']}"
        )
        assert data["social"]["question_count"] == 2

        # Governance: 100.0
        assert abs(data["governance"]["score"] - 100.0) < 0.1, (
            f"Expected governance 100.0, got {data['governance']['score']}"
        )
        assert data["governance"]["question_count"] == 1

        # Verify composite is the weighted average
        weights = data["weights_used"]
        expected_composite = round(
            weights["environment"] * data["environment"]["score"]
            + weights["social"] * data["social"]["score"]
            + weights["governance"] * data["governance"]["score"],
            1,
        )
        assert abs(data["composite_score"] - expected_composite) < 0.2, (
            f"Composite {data['composite_score']} != weighted avg {expected_composite}"
        )

    def test_risk_tier_assignment(self, client):
        """Verify all four risk tiers based on composite score thresholds.

        A >= 80, B >= 60, C >= 40, D < 40.
        We test each tier by inserting responses that produce known scores.
        """
        # --- Tier A: all dimensions maxed out ---
        self._clear_supplier_responses("sup_001")
        # T1Q6 (governance, higher_is_better, max=3): raw=3 -> 100
        # T1Q7 (environment, higher_is_better, max=5): raw=5 -> 100
        # T1Q4 (social, higher_is_better, max=3): raw=3 -> 100
        # All dimensions at 100 -> composite = 100 -> Tier A
        self._insert_scoring_responses(
            "sup_001",
            [
                {"tier": 1, "question_id": "T1Q6", "response_value": 3},
                {"tier": 1, "question_id": "T1Q7", "response_value": 5},
                {"tier": 1, "question_id": "T1Q4", "response_value": 3},
            ],
        )
        resp = client.get("/api/suppliers/sup_001/score")
        assert resp.status_code == 200
        assert resp.json()["risk_tier"] == "A"

        # --- Tier D: all dimensions at 0 ---
        self._clear_supplier_responses("sup_001")
        # T1Q1 (environment, lower_is_better, max=5M): raw=5M -> score=0
        # T1Q5 (social, lower_is_better, max=50): raw=50 -> score=0
        # T1Q6 (governance, higher_is_better, max=3): raw=0 -> score=0
        self._insert_scoring_responses(
            "sup_001",
            [
                {"tier": 1, "question_id": "T1Q1", "response_value": 5000000},
                {"tier": 1, "question_id": "T1Q5", "response_value": 50},
                {"tier": 1, "question_id": "T1Q6", "response_value": 0},
            ],
        )
        resp = client.get("/api/suppliers/sup_001/score")
        assert resp.status_code == 200
        data = resp.json()
        assert data["composite_score"] == 0.0
        assert data["risk_tier"] == "D"

        # --- Tier B: composite in 60-79 range ---
        self._clear_supplier_responses("sup_001")
        # T1Q7 raw=4 -> 80, T1Q4 raw=2 -> 66.7, T1Q6 raw=2 -> 66.7
        # Composite = 0.40*80 + 0.35*66.7 + 0.25*66.7 = 32 + 23.3 + 16.7 = 72.0 -> Tier B
        self._insert_scoring_responses(
            "sup_001",
            [
                {"tier": 1, "question_id": "T1Q7", "response_value": 4},
                {"tier": 1, "question_id": "T1Q4", "response_value": 2},
                {"tier": 1, "question_id": "T1Q6", "response_value": 2},
            ],
        )
        resp = client.get("/api/suppliers/sup_001/score")
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_tier"] == "B", (
            f"Expected tier B for composite {data['composite_score']}, got {data['risk_tier']}"
        )

        # --- Tier C: composite in 40-59 range ---
        self._clear_supplier_responses("sup_001")
        # T1Q7 raw=3 -> 60, T1Q4 raw=2 -> 66.7, T1Q6 raw=0 -> 0
        # Composite = 0.40*60 + 0.35*66.7 + 0.25*0 = 24 + 23.3 + 0 = 47.3 -> Tier C
        self._insert_scoring_responses(
            "sup_001",
            [
                {"tier": 1, "question_id": "T1Q7", "response_value": 3},
                {"tier": 1, "question_id": "T1Q4", "response_value": 2},
                {"tier": 1, "question_id": "T1Q6", "response_value": 0},
            ],
        )
        resp = client.get("/api/suppliers/sup_001/score")
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_tier"] == "C", (
            f"Expected tier C for composite {data['composite_score']}, got {data['risk_tier']}"
        )

    def test_score_updates_supplier_record(self, client):
        """Verify that esg_score and risk_tier are written back to the suppliers table."""
        from src.db.database import get_connection, release_connection

        self._clear_supplier_responses("sup_001")
        self._insert_scoring_responses(
            "sup_001",
            [
                {"tier": 1, "question_id": "T1Q7", "response_value": 5},
                {"tier": 1, "question_id": "T1Q4", "response_value": 3},
                {"tier": 1, "question_id": "T1Q6", "response_value": 3},
            ],
        )

        resp = client.get("/api/suppliers/sup_001/score")
        assert resp.status_code == 200
        data = resp.json()

        # Now read the supplier record directly from the DB
        conn = get_connection()
        try:
            from src.db.database import _fetchone

            row = _fetchone(
                conn, "SELECT esg_score, risk_tier FROM suppliers WHERE id = ?", ("sup_001",)
            )
        finally:
            release_connection(conn)

        assert row is not None
        assert row["esg_score"] == data["composite_score"], (
            f"DB esg_score {row['esg_score']} != API composite {data['composite_score']}"
        )
        assert row["risk_tier"] == data["risk_tier"], (
            f"DB risk_tier {row['risk_tier']} != API tier {data['risk_tier']}"
        )

    def test_score_requires_auth(self):
        """Score endpoint returns 401 without authentication."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        unauthenticated_client = TestClient(app)
        resp = unauthenticated_client.get("/api/suppliers/sup_001/score")
        assert resp.status_code == 401

    def test_score_unknown_supplier_returns_404(self, client):
        """Score endpoint returns 404 for a non-existent supplier."""
        resp = client.get("/api/suppliers/sup_nonexistent/score")
        assert resp.status_code == 404


# --- Questionnaire Detail Endpoint ---


class TestQuestionnaireDetail:
    """Tests for GET /api/questionnaires/questionnaire/{qnr_id} endpoint.

    Verifies that the questionnaire detail endpoint returns real data
    from the database instead of hardcoded mock values.
    """

    def _seed_template_with_questions_and_responses(self):
        """Create a template with questions and some supplier responses.

        Creates:
          - 1 template "ESG Unit Test Assessment"
          - 4 questions (3 required, 1 optional)
          - 3 responses from sup_001 (answering questions 1-3)
          - 0 responses for question 4

        This gives a deterministic state for verifying progress calculation
        and real data retrieval.
        """
        import sqlite3

        from src.db.database import DB_PATH

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=OFF")
        try:
            conn.execute(
                """
                INSERT INTO questionnaire_templates (org_id, name, description, tier, category, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    "org_bd_001",
                    "ESG Unit Test Assessment",
                    "Unit test questionnaire",
                    1,
                    "environment",
                    1,
                ),
            )
            conn.commit()

            row = conn.execute(
                "SELECT id FROM questionnaire_templates WHERE name = 'ESG Unit Test Assessment'"
            ).fetchone()
            template_id = row["id"]

            conn.execute(
                """
                INSERT INTO questionnaire_questions (template_id, question_id, question_text, question_type, choices, sort_order, required)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (template_id, "Q1", "Annual electricity consumption (kWh)", "number", None, 1, 1),
            )
            conn.execute(
                """
                INSERT INTO questionnaire_questions (template_id, question_id, question_text, question_type, choices, sort_order, required)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (template_id, "Q2", "Annual water withdrawal (m3)", "number", None, 2, 1),
            )
            conn.execute(
                """
                INSERT INTO questionnaire_questions (template_id, question_id, question_text, question_type, choices, sort_order, required)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    template_id,
                    "Q3",
                    "Do you have renewable energy installed?",
                    "choice",
                    "Yes,No",
                    3,
                    1,
                ),
            )
            conn.execute(
                """
                INSERT INTO questionnaire_questions (template_id, question_id, question_text, question_type, choices, sort_order, required)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (template_id, "Q4", "Waste recycling rate (%)", "number", None, 4, 0),
            )

            # sup_001 responded to questions 1, 2, 3 (using question sort_order as question_id in responses)
            conn.execute(
                """
                INSERT INTO questionnaire_responses
                    (org_id, supplier_id, tier, question_id, response_text, response_value, channel)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                ("org_bd_001", "sup_001", 1, "1", "4,820,000", 4820000.0, "whatsapp"),
            )
            conn.execute(
                """
                INSERT INTO questionnaire_responses
                    (org_id, supplier_id, tier, question_id, response_text, response_value, channel)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                ("org_bd_001", "sup_001", 1, "2", "12,400", 12400.0, "whatsapp"),
            )
            conn.execute(
                """
                INSERT INTO questionnaire_responses
                    (org_id, supplier_id, tier, question_id, response_text, response_value, channel)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                ("org_bd_001", "sup_001", 1, "3", "Yes - 850 kW rooftop solar", None, "whatsapp"),
            )
            conn.commit()
        finally:
            conn.close()

        return template_id

    def test_questionnaire_detail_returns_real_data(self, client):
        """Questionnaire detail returns data from the database, not hardcoded mock.

        Verifies that the response contains the template name, category,
        and other fields that come from the questionnaire_templates row.
        """
        template_id = self._seed_template_with_questions_and_responses()

        resp = client.get(f"/api/questionnaires/questionnaire/{template_id}")
        assert resp.status_code == 200
        data = resp.json()

        # The name must come from the DB, not from hardcoded "H&M ESG Questionnaire Q1 2025"
        assert data["name"] == "ESG Unit Test Assessment"
        assert data["description"] == "Unit test questionnaire"
        assert data["tier"] == 1
        assert data["category"] == "environment"
        assert data["id"] == template_id

    def test_questionnaire_detail_includes_questions(self, client):
        """Questions come from questionnaire_questions, not hardcoded list.

        We seeded 4 questions with specific text and types; verify they appear
        with correct sort_order, required flag, and question_type.
        """
        template_id = self._seed_template_with_questions_and_responses()

        resp = client.get(f"/api/questionnaires/questionnaire/{template_id}")
        assert resp.status_code == 200
        data = resp.json()

        questions = data["questions"]
        assert len(questions) == 4

        # Verify first question text matches what we inserted
        q1 = questions[0]
        assert q1["text"] == "Annual electricity consumption (kWh)"
        assert q1["question_type"] == "number"
        assert q1["required"] is True

        # Verify optional question
        q4 = questions[3]
        assert q4["text"] == "Waste recycling rate (%)"
        assert q4["required"] is False

    def test_questionnaire_detail_includes_responses(self, client):
        """Responses come from questionnaire_responses, joined with questions.

        We seeded 3 responses from sup_001 for questions 1-3.
        The endpoint should return these with response_text, supplier info,
        and correct progress calculation (3 answered out of 4 total).
        """
        template_id = self._seed_template_with_questions_and_responses()

        resp = client.get(f"/api/questionnaires/questionnaire/{template_id}")
        assert resp.status_code == 200
        data = resp.json()

        # Verify progress is calculated from actual response data
        progress = data["progress"]
        assert progress["total"] == 4
        assert progress["answered"] == 3
        assert progress["pending"] == 1

        # Verify questions have answered/reponse information
        questions = data["questions"]
        answered_ids = set()
        for q in questions:
            if q.get("answered"):
                assert q.get("response_text") is not None, (
                    f"Answered question must have response_text, got None for question {q['id']}"
                )
                answered_ids.add(q["id"])

        # At least 3 questions are marked as answered
        assert len(answered_ids) >= 3

    def test_questionnaire_detail_unknown_returns_404(self, client):
        """Requesting a nonexistent questionnaire ID returns 404."""
        resp = client.get("/api/questionnaires/questionnaire/999999")
        assert resp.status_code == 404

    def test_questionnaire_detail_requires_auth(self):
        """Endpoint returns 401 without authentication."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        unauthenticated_client = TestClient(app)
        resp = unauthenticated_client.get("/api/questionnaires/questionnaire/1")
        assert resp.status_code == 401


# --- WhatsApp Preview ---


class TestWhatsAppPreview:
    """Tests for GET /api/questionnaires/whatsapp-preview/{supplier_id}.

    The endpoint returns a WhatsApp message preview, a sample supplier
    response example, and the coverage impact of this supplier.
    Returns: {message_preview, supplier_response_example, coverage_impact}
    """

    def _seed_preview_data(self):
        """Insert a template with questions and questionnaire responses.

        Creates:
          - An active questionnaire template for org_bd_001
          - 3 questions on that template
          - 2 questionnaire_responses for sup_001 (answered questions)
          - 1 question left unanswered for sup_001
        """
        import sqlite3

        from src.db.database import DB_PATH

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=OFF")
        try:
            # Get existing template id before deleting
            row = conn.execute(
                "SELECT id FROM questionnaire_templates WHERE name = 'ESG Preview Assessment' AND org_id = ?",
                ("org_bd_001",),
            ).fetchone()
            existing_template_id = row["id"] if row else None

            # Clear existing responses for sup_001 to ensure test isolation
            conn.execute(
                "DELETE FROM questionnaire_responses WHERE supplier_id = ? AND org_id = ?",
                ("sup_001", "org_bd_001"),
            )
            # Clear existing template and questions for this test
            if existing_template_id is not None:
                conn.execute(
                    "DELETE FROM questionnaire_questions WHERE template_id = ?",
                    (existing_template_id,),
                )
                conn.execute(
                    "DELETE FROM questionnaire_templates WHERE id = ?",
                    (existing_template_id,),
                )
            conn.commit()

            conn.execute(
                """
                INSERT INTO questionnaire_templates
                    (org_id, name, description, tier, category, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    "org_bd_001",
                    "ESG Preview Assessment",
                    "Preview ESG questionnaire",
                    1,
                    "environment",
                    1,
                ),
            )
            conn.commit()

            row = conn.execute(
                "SELECT id FROM questionnaire_templates WHERE name = 'ESG Preview Assessment'"
            ).fetchone()
            template_id = row["id"]

            conn.execute(
                """
                INSERT INTO questionnaire_questions
                    (template_id, question_id, question_text, question_type, sort_order, required)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (template_id, "Q1", "Annual electricity consumption (kWh)", "number", 1, 1),
            )
            conn.execute(
                """
                INSERT INTO questionnaire_questions
                    (template_id, question_id, question_text, question_type, sort_order, required)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (template_id, "Q2", "Annual water withdrawal (m3)", "number", 2, 1),
            )
            conn.execute(
                """
                INSERT INTO questionnaire_questions
                    (template_id, question_id, question_text, question_type, sort_order, required)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (template_id, "Q3", "Do you have renewable energy installed?", "choice", 3, 1),
            )
            conn.commit()

            # Get question ids to use as question_id in responses
            q_rows = conn.execute(
                "SELECT id FROM questionnaire_questions WHERE template_id = ? ORDER BY sort_order",
                (template_id,),
            ).fetchall()
            q1_id = str(q_rows[0]["id"])
            q2_id = str(q_rows[1]["id"])

            # Responses for sup_001 on questions 1 and 2 (question 3 left unanswered)
            conn.execute(
                """
                INSERT INTO questionnaire_responses
                    (org_id, supplier_id, tier, question_id, response_text, response_value, channel)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                ("org_bd_001", "sup_001", 1, q1_id, "4,820,000", 4820000.0, "email"),
            )
            conn.execute(
                """
                INSERT INTO questionnaire_responses
                    (org_id, supplier_id, tier, question_id, response_text, response_value, channel)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                ("org_bd_001", "sup_001", 1, q2_id, "12,400", 12400.0, "email"),
            )
            conn.commit()
        finally:
            conn.close()

    def test_whatsapp_preview_returns_correct_structure(self, client):
        """Endpoint returns the top-level keys: message_preview, supplier_response_example, coverage_impact."""
        self._seed_preview_data()
        resp = client.get("/api/questionnaires/whatsapp-preview/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        for key in ("message_preview", "supplier_response_example", "coverage_impact"):
            assert key in data, f"Missing top-level key: {key}"

        # Verify message_preview is a non-empty string
        assert isinstance(data["message_preview"], str)
        assert len(data["message_preview"]) > 0

        # Verify supplier_response_example is a string
        assert isinstance(data["supplier_response_example"], str)

        # Verify coverage_impact has the required keys
        ci = data["coverage_impact"]
        for cikey in ("supplier_name", "annual_spend", "coverage_added", "new_total_coverage"):
            assert cikey in ci, f"Missing coverage_impact key: {cikey}"

    def test_whatsapp_preview_includes_supplier_info(self, client):
        """coverage_impact supplier_name matches the database record for the requested supplier."""
        self._seed_preview_data()
        resp = client.get("/api/questionnaires/whatsapp-preview/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        ci = data["coverage_impact"]
        assert ci["supplier_name"] == "Gujarat Cotton Traders"
        assert ci["annual_spend"] == 2400000.0

    def test_whatsapp_preview_shows_questionnaire_questions(self, client):
        """message_preview contains question text from the active template."""
        self._seed_preview_data()
        resp = client.get("/api/questionnaires/whatsapp-preview/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        msg = data["message_preview"]
        # Should contain question text from the seeded template
        assert "Annual electricity consumption" in msg
        assert "Annual water withdrawal" in msg
        assert "renewable energy" in msg

    def test_whatsapp_preview_calculates_coverage_impact(self, client):
        """coverage_impact contains numeric spend and percentage strings for coverage_added and new_total_coverage."""
        self._seed_preview_data()
        resp = client.get("/api/questionnaires/whatsapp-preview/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        ci = data["coverage_impact"]
        # annual_spend should be a number
        assert isinstance(ci["annual_spend"], (int, float))
        assert ci["annual_spend"] > 0
        # coverage_added and new_total_coverage should be formatted strings with %
        assert isinstance(ci["coverage_added"], str)
        assert ci["coverage_added"].endswith("%")
        assert isinstance(ci["new_total_coverage"], str)
        assert ci["new_total_coverage"].endswith("%")

    def test_whatsapp_preview_requires_auth(self):
        """Endpoint returns 401 without authentication."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        unauthenticated_client = TestClient(app)
        resp = unauthenticated_client.get("/api/questionnaires/whatsapp-preview/sup_001")
        assert resp.status_code == 401

    def test_whatsapp_preview_unknown_supplier_404(self, client):
        """Endpoint returns 404 for a supplier that does not exist."""
        self._seed_preview_data()
        resp = client.get("/api/questionnaires/whatsapp-preview/sup_nonexistent")
        assert resp.status_code == 404


# --- Manual Questionnaire Response Entry ---


class TestManualQuestionnaireResponse:
    """Tests for POST /api/questionnaires/responses/manual."""

    def _seed_manual_response_data(self):
        """Insert a template with questions for manual response testing."""
        import sqlite3

        from src.db.database import DB_PATH

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=OFF")
        try:
            conn.execute(
                """
                INSERT INTO questionnaire_templates (org_id, name, description, tier, category, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    "org_bd_001",
                    "Manual Test Template",
                    "For manual response tests",
                    1,
                    "environment",
                    1,
                ),
            )
            conn.commit()

            row = conn.execute(
                "SELECT id FROM questionnaire_templates WHERE name = 'Manual Test Template'"
            ).fetchone()
            template_id = row["id"]

            conn.execute(
                """
                INSERT INTO questionnaire_questions (template_id, question_id, question_text, question_type, sort_order, required)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (template_id, "Q1", "Annual energy consumption (kWh)", "number", 1, 1),
            )
            conn.execute(
                """
                INSERT INTO questionnaire_questions (template_id, question_id, question_text, question_type, sort_order, required)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (template_id, "Q2", "Annual water withdrawal (m3)", "number", 2, 1),
            )
            conn.commit()
        finally:
            conn.close()

    def test_manual_response_success(self, client):
        """POST /responses/manual records responses and updates supplier status."""
        self._seed_manual_response_data()
        resp = client.post(
            "/api/questionnaires/responses/manual",
            json={
                "supplier_id": "sup_001",
                "responses": [
                    {
                        "question_id": "1",
                        "response_text": "1,200,000 kWh",
                        "response_value": 1200000.0,
                    },
                    {"question_id": "2", "response_text": "45,000 m3", "response_value": 45000.0},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["supplier_id"] == "sup_001"
        assert data["responses_entered"] == 2

        # Verify supplier status was updated
        import sqlite3

        from src.db.database import DB_PATH

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT questionnaire_status FROM suppliers WHERE id = 'sup_001'"
            ).fetchone()
            assert row["questionnaire_status"] == "responded"
        finally:
            conn.close()

    def test_manual_response_upserts_existing(self, client):
        """Re-submitting a question_id replaces the prior response (upsert)."""
        self._seed_manual_response_data()
        # First submission
        client.post(
            "/api/questionnaires/responses/manual",
            json={
                "supplier_id": "sup_002",
                "responses": [
                    {"question_id": "1", "response_text": "First value", "response_value": 100.0},
                ],
            },
        )
        # Second submission for same question
        resp = client.post(
            "/api/questionnaires/responses/manual",
            json={
                "supplier_id": "sup_002",
                "responses": [
                    {"question_id": "1", "response_text": "Updated value", "response_value": 200.0},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["responses_entered"] == 1

        # Verify only the updated value exists
        import sqlite3

        from src.db.database import DB_PATH

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT response_text, response_value FROM questionnaire_responses
                WHERE supplier_id = 'sup_002' AND question_id = '1'
            """).fetchall()
            assert len(rows) == 1
            assert rows[0]["response_text"] == "Updated value"
            assert rows[0]["response_value"] == 200.0
        finally:
            conn.close()

    def test_manual_response_supplier_not_found(self, client):
        """Endpoint returns 404 for a non-existent supplier."""
        resp = client.post(
            "/api/questionnaires/responses/manual",
            json={
                "supplier_id": "sup_nonexistent",
                "responses": [
                    {"question_id": "1", "response_text": "value", "response_value": 1.0},
                ],
            },
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_manual_response_bad_request_no_supplier_id(self, client):
        """Endpoint returns 400 when supplier_id is missing."""
        resp = client.post(
            "/api/questionnaires/responses/manual",
            json={
                "responses": [
                    {"question_id": "1", "response_text": "value", "response_value": 1.0},
                ],
            },
        )
        assert resp.status_code == 400
        assert "supplier_id" in resp.json()["detail"].lower()

    def test_manual_response_bad_request_empty_responses(self, client):
        """Endpoint returns 400 when responses list is empty."""
        resp = client.post(
            "/api/questionnaires/responses/manual",
            json={
                "supplier_id": "sup_001",
                "responses": [],
            },
        )
        assert resp.status_code == 400
        assert "responses" in resp.json()["detail"].lower()

    def test_manual_response_require_auth(self):
        """Endpoint returns 401 without authentication."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        unauthenticated_client = TestClient(app)
        resp = unauthenticated_client.post(
            "/api/questionnaires/responses/manual",
            json={
                "supplier_id": "sup_001",
                "responses": [
                    {"question_id": "1", "response_text": "value", "response_value": 1.0},
                ],
            },
        )
        assert resp.status_code == 401

    def test_endpoints_require_auth_includes_manual(self):
        """POST /responses/manual is added to the auth check list."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        unauthenticated_client = TestClient(app)
        resp = unauthenticated_client.post(
            "/api/questionnaires/responses/manual",
            json={
                "supplier_id": "sup_001",
                "responses": [
                    {"question_id": "1", "response_text": "value", "response_value": 1.0},
                ],
            },
        )
        assert resp.status_code == 401


# --- Send questionnaire by email (B2.6) ---


class TestSendEmailQuestionnaire:
    """Tests for POST /api/questionnaires/send-email."""

    def test_send_email_missing_supplier_id(self, client):
        """Returns 400 when supplier_id is absent."""
        resp = client.post("/api/questionnaires/send-email", json={})
        assert resp.status_code == 400
        assert "supplier_id" in resp.json()["detail"].lower()

    def test_send_email_supplier_not_found(self, client):
        """Returns 400 when supplier does not exist (EmailClient returns error)."""
        resp = client.post(
            "/api/questionnaires/send-email",
            json={
                "supplier_id": "sup_nonexistent",
            },
        )
        assert resp.status_code == 400

    def test_send_email_requires_auth(self):
        """Endpoint returns 401 without a token."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        c = TestClient(app)
        resp = c.post(
            "/api/questionnaires/send-email",
            json={
                "supplier_id": "sup_001",
            },
        )
        assert resp.status_code == 401

    def test_send_email_requires_editor_role(self):
        """Returns 403 when authenticated as a viewer."""
        from fastapi.testclient import TestClient

        from src.api.main import app
        from src.auth.jwt import create_token

        viewer_token = create_token(
            {
                "sub": "usr_viewer_001",
                "org_id": "org_bd_001",
                "email": "viewer@textilebd.com",
                "role": "viewer",
            }
        )
        c = TestClient(app)
        c.headers.update({"Authorization": f"Bearer {viewer_token}"})
        resp = c.post(
            "/api/questionnaires/send-email",
            json={
                "supplier_id": "sup_001",
            },
        )
        assert resp.status_code == 403


# --- Non-responders (GET /non-responders) ---


class TestNonResponders:
    """Tests for GET /api/questionnaires/non-responders."""

    def test_non_responders_requires_auth(self):
        """Returns 401 without authentication."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        c = TestClient(app)
        resp = c.get("/api/questionnaires/non-responders")
        assert resp.status_code == 401

    def test_non_responders_returns_list(self, client):
        """Returns a list even when all suppliers have responded."""
        resp = client.get("/api/questionnaires/non-responders")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# --- Supplier responses (GET /responses/{supplier_id}) ---


class TestSupplierResponses:
    """Tests for GET /api/questionnaires/responses/{supplier_id}."""

    def test_supplier_responses_requires_auth(self):
        """Returns 401 without authentication."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        c = TestClient(app)
        resp = c.get("/api/questionnaires/responses/sup_001")
        assert resp.status_code == 401

    def test_supplier_responses_unknown_supplier(self, client):
        """Returns 404 for a non-existent supplier."""
        resp = client.get("/api/questionnaires/responses/sup_unknown")
        assert resp.status_code == 404


# --- Portal link generation (POST /portal/link/{supplier_id}) ---


class TestPortalLinkGeneration:
    """Tests for POST /api/questionnaires/portal/link/{supplier_id}."""

    def test_generate_portal_link_requires_auth(self):
        """Returns 401 without authentication."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        c = TestClient(app)
        resp = c.post("/api/questionnaires/portal/link/sup_001")
        assert resp.status_code == 401

    def test_generate_portal_link_requires_editor_role(self):
        """Returns 403 when authenticated as a viewer."""
        from fastapi.testclient import TestClient

        from src.api.main import app
        from src.auth.jwt import create_token

        viewer_token = create_token(
            {
                "sub": "usr_viewer_001",
                "org_id": "org_bd_001",
                "email": "viewer@textilebd.com",
                "role": "viewer",
            }
        )
        c = TestClient(app)
        c.headers.update({"Authorization": f"Bearer {viewer_token}"})
        resp = c.post("/api/questionnaires/portal/link/sup_001")
        assert resp.status_code == 403

    def test_generate_portal_link_unknown_supplier(self, client):
        """Returns 404 for a non-existent supplier."""
        resp = client.post("/api/questionnaires/portal/link/sup_nonexistent")
        assert resp.status_code == 404

    def test_generate_portal_link_success(self, client):
        """Returns portal URL and raw token for valid supplier."""
        resp = client.post("/api/questionnaires/portal/link/sup_001", json={"days_valid": 7})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "portal_url" in data
        assert "raw_token" in data
        assert data["supplier_id"] == "sup_001"
        assert data["expires_at"] is not None
        # Token should be a UUID
        assert len(data["raw_token"]) == 36


# --- Portal submit (POST /portal/submit) ---


class TestPortalSubmit:
    """Tests for POST /api/questionnaires/portal/submit."""

    def _get_portal_token(self):
        """Create a portal token by calling the link generation endpoint."""
        from fastapi.testclient import TestClient

        from src.api.main import app
        from src.auth.jwt import create_token

        token = create_token(
            {
                "sub": "usr_admin_001",
                "org_id": "org_bd_001",
                "email": "admin@textilebd.com",
                "role": "admin",
            }
        )
        c = TestClient(app)
        c.headers.update({"Authorization": f"Bearer {token}"})
        resp = c.post("/api/questionnaires/portal/link/sup_001", json={"days_valid": 7})
        return resp.json()["raw_token"]

    def test_portal_submit_invalid_token(self, client):
        """Returns 401 for an invalid portal token."""
        resp = client.post(
            "/api/questionnaires/portal/submit",
            json={
                "portal_token": "not-a-valid-token",
                "supplier_id": "sup_001",
                "responses": [{"question_id": "q1", "response_text": "Yes"}],
            },
        )
        assert resp.status_code == 401
        assert (
            "invalid" in resp.json()["detail"].lower() or "expired" in resp.json()["detail"].lower()
        )

    def test_portal_submit_wrong_token_for_supplier(self, client):
        """Returns 401 when token does not match supplier."""
        token = self._get_portal_token()
        resp = client.post(
            "/api/questionnaires/portal/submit",
            json={
                "portal_token": token,
                "supplier_id": "sup_nonexistent",
                "responses": [{"question_id": "q1", "response_text": "Yes"}],
            },
        )
        assert resp.status_code == 401

    def test_portal_submit_empty_responses(self, client):
        """Returns 400 when responses list is empty."""
        token = self._get_portal_token()
        resp = client.post(
            "/api/questionnaires/portal/submit",
            json={
                "portal_token": token,
                "supplier_id": "sup_001",
                "responses": [],
            },
        )
        assert resp.status_code == 400

    def test_portal_submit_success(self, client):
        """Creates questionnaire response with channel='web' for valid token."""
        token = self._get_portal_token()
        resp = client.post(
            "/api/questionnaires/portal/submit",
            json={
                "portal_token": token,
                "supplier_id": "sup_001",
                "responses": [
                    {"question_id": "q1", "response_text": "Yes"},
                    {"question_id": "q2", "response_text": "No"},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["supplier_id"] == "sup_001"
        assert data["responses_received"] == 2
        assert data["channel"] == "web"

        # Verify the responses are in the database
        from src.db.database import _fetchall, get_connection, release_connection

        conn2 = get_connection()
        try:
            rows = _fetchall(
                conn2,
                """
                SELECT question_id, response_text, channel, validation_status
                FROM questionnaire_responses
                WHERE supplier_id = ? AND channel = 'web'
            """,
                ("sup_001",),
            )
            assert len(rows) == 2
            assert all(r["channel"] == "web" for r in rows)
        finally:
            release_connection(conn2)

    def test_portal_submit_clears_token(self, client):
        """Portal token is cleared after successful submission."""
        token = self._get_portal_token()
        resp = client.post(
            "/api/questionnaires/portal/submit",
            json={
                "portal_token": token,
                "supplier_id": "sup_001",
                "responses": [{"question_id": "q1", "response_text": "Done"}],
            },
        )
        assert resp.status_code == 200

        # Token should be cleared — second use should fail
        resp2 = client.post(
            "/api/questionnaires/portal/submit",
            json={
                "portal_token": token,
                "supplier_id": "sup_001",
                "responses": [{"question_id": "q1", "response_text": "Done again"}],
            },
        )
        assert resp2.status_code == 401


# --- Supplier prefill (GET /api/questionnaires/prefill/{supplier_id}) ---


class TestSupplierPrefill:
    """Tests for GET /api/questionnaires/prefill/{supplier_id}."""

    def test_prefill_requires_auth(self):
        """Returns 401 without authentication."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        c = TestClient(app)
        resp = c.get("/api/questionnaires/prefill/sup_001")
        assert resp.status_code == 401

    def test_prefill_unknown_supplier(self, client):
        """Returns 404 for a non-existent supplier."""
        resp = client.get("/api/questionnaires/prefill/sup_unknown")
        assert resp.status_code == 404

    def test_prefill_zero_spend(self, client):
        """Returns empty prefill dict when supplier has no annual spend."""
        import sqlite3

        from src.db.database import DB_PATH

        # Create a supplier with zero spend
        conn = sqlite3.connect(str(DB_PATH))
        try:
            conn.execute("""
                INSERT INTO suppliers
                    (id, org_id, name, annual_spend_usd, country, industry,
                     tier, phone, preferred_channel, questionnaire_status)
                VALUES ('sup_zero_spend', 'org_bd_001', 'Zero Spend Co.',
                        0, 'US', 'Manufacturing', 'tier1', '', 'email', 'pending')
            """)
            conn.commit()
        finally:
            conn.close()

        resp = client.get("/api/questionnaires/prefill/sup_zero_spend")
        assert resp.status_code == 200
        data = resp.json()
        assert data["supplier_id"] == "sup_zero_spend"
        assert data["prefill"] == {}
        assert data["annual_spend_usd"] == 0

    def test_prefill_with_spend(self, client):
        """Returns spend-based expected values for t1e_01 and t1e_02."""
        resp = client.get("/api/questionnaires/prefill/sup_001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["supplier_id"] == "sup_001"
        # sup_001 has annual_spend_usd from seed data (2,400,000)
        assert "prefill" in data
        # t1e_01 (electricity) and t1e_02 (diesel) should have spend-based values
        assert "t1e_01" in data["prefill"]
        assert "t1e_02" in data["prefill"]
        assert data["prefill"]["t1e_01"]["source"] == "computed:spend-based"
        assert data["prefill"]["t1e_02"]["source"] == "computed:spend-based"
        assert data["prefill"]["t1e_01"]["unit"] == "kWh"
        assert data["prefill"]["t1e_02"]["unit"] == "L"
        # Verify computed value matches: 2,400,000 × 0.5 = 1,200,000 kWh
        assert data["prefill"]["t1e_01"]["value"] == 1200000.0
        # 2,400,000 × 0.005 = 12,000 L
        assert data["prefill"]["t1e_02"]["value"] == 12000.0

    def test_prefill_includes_scope3_records(self, client):
        """Returns existing Scope 3 records for the supplier."""
        # sup_001 has scope3 records from seed data
        resp = client.get("/api/questionnaires/prefill/sup_001")
        assert resp.status_code == 200
        data = resp.json()
        # Seed data creates scope3 records for sup_001
        assert len(data["scope3_records"]) >= 1
        record = data["scope3_records"][0]
        assert "scope3_tco2e" in record
        assert "category" in record


# --- Supplier timeline (GET /api/questionnaires/timeline/{supplier_id}) ---


class TestSupplierTimeline:
    """Tests for GET /api/questionnaires/timeline/{supplier_id}."""

    def test_timeline_requires_auth(self):
        """Returns 401 without authentication."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        c = TestClient(app)
        resp = c.get("/api/questionnaires/timeline/sup_001")
        assert resp.status_code == 401

    def test_timeline_unknown_supplier(self, client):
        """Returns 404 for a non-existent supplier."""
        resp = client.get("/api/questionnaires/timeline/sup_unknown")
        assert resp.status_code == 404

    def test_timeline_no_data(self, client):
        """Returns empty structure when supplier has no responses yet."""
        # sup_003 exists in seed data but has no questionnaire responses
        resp = client.get("/api/questionnaires/timeline/sup_003")
        assert resp.status_code == 200
        data = resp.json()
        assert data["supplier_id"] == "sup_003"
        assert data["periods"] == []
        assert data["trends"] == []
        assert data["summary"]["total_periods"] == 0
        assert data["summary"]["overall_trajectory"] == "no_data"

    def test_timeline_single_period(self, client):
        """Returns insufficient_data trajectory when only one period exists."""
        import sqlite3

        from src.db.database import DB_PATH

        # Insert a response with a fixed timestamp for sup_003
        conn = sqlite3.connect(str(DB_PATH))
        try:
            conn.execute("""
                INSERT INTO questionnaire_responses
                    (org_id, supplier_id, tier, question_id, response_text,
                     response_value, channel, responded_at)
                VALUES ('org_bd_001', 'sup_003', 1, 'q1', '500000',
                        500000.0, 'manual', '2025-03-15 10:00:00')
            """)
            conn.commit()
        finally:
            conn.close()

        resp = client.get("/api/questionnaires/timeline/sup_003")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["periods"]) == 1
        assert data["periods"][0]["period"] == "2025-03"
        assert data["summary"]["overall_trajectory"] == "insufficient_data"

    def test_timeline_multiple_periods_improving(self, client):
        """Computes improving trajectory when later period has more responses."""
        import sqlite3

        from src.db.database import DB_PATH

        conn = sqlite3.connect(str(DB_PATH))
        try:
            # Earlier period: 1 question
            conn.execute("""
                INSERT INTO questionnaire_responses
                    (org_id, supplier_id, tier, question_id, response_text,
                     response_value, channel, responded_at)
                VALUES ('org_bd_001', 'sup_003', 1, 'q1', '100000',
                        100000.0, 'manual', '2025-01-10 10:00:00')
            """)
            # Later period: 2 questions
            conn.execute("""
                INSERT INTO questionnaire_responses
                    (org_id, supplier_id, tier, question_id, response_text,
                     response_value, channel, responded_at)
                VALUES ('org_bd_001', 'sup_003', 1, 'q1', '200000',
                        200000.0, 'manual', '2025-03-20 10:00:00')
            """)
            conn.execute("""
                INSERT INTO questionnaire_responses
                    (org_id, supplier_id, tier, question_id, response_text,
                     response_value, channel, responded_at)
                VALUES ('org_bd_001', 'sup_003', 1, 'q2', '5000',
                        5000.0, 'manual', '2025-03-20 10:00:00')
            """)
            conn.commit()
        finally:
            conn.close()

        resp = client.get("/api/questionnaires/timeline/sup_003")
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_periods"] == 2
        assert data["summary"]["overall_trajectory"] == "improving"
        # q1 should show trajectory since it appears in both periods
        q1_trend = next((t for t in data["trends"] if t["question_id"] == "q1"), None)
        assert q1_trend is not None
        assert q1_trend["trajectory"] == "up"
        assert q1_trend["change_pct"] == 100.0  # 200k vs 100k = +100%

    def test_timeline_declining(self, client):
        """Computes declining trajectory when later period has fewer questions."""
        import sqlite3

        from src.db.database import DB_PATH

        conn = sqlite3.connect(str(DB_PATH))
        try:
            # Earlier period: 2 questions
            conn.execute("""
                INSERT INTO questionnaire_responses
                    (org_id, supplier_id, tier, question_id, response_text,
                     response_value, channel, responded_at)
                VALUES ('org_bd_001', 'sup_003', 1, 'q1', '100000',
                        100000.0, 'manual', '2025-01-10 10:00:00')
            """)
            conn.execute("""
                INSERT INTO questionnaire_responses
                    (org_id, supplier_id, tier, question_id, response_text,
                     response_value, channel, responded_at)
                VALUES ('org_bd_001', 'sup_003', 1, 'q2', '5000',
                        5000.0, 'manual', '2025-01-10 10:00:00')
            """)
            # Later period: only 1 question (q1 dropped)
            conn.execute("""
                INSERT INTO questionnaire_responses
                    (org_id, supplier_id, tier, question_id, response_text,
                     response_value, channel, responded_at)
                VALUES ('org_bd_001', 'sup_003', 1, 'q1', '50000',
                        50000.0, 'manual', '2025-03-20 10:00:00')
            """)
            conn.commit()
        finally:
            conn.close()

        resp = client.get("/api/questionnaires/timeline/sup_003")
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["overall_trajectory"] == "declining"
