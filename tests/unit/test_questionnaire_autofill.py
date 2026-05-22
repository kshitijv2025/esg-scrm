"""Tests for GET /api/questionnaires/auto-fill/{template_id}/{supplier_id} — B3.14."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.db.database import DB_PATH, reset_database


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


@pytest.fixture
def other_org_client():
    """Authenticates as a different org to test org isolation."""
    from src.auth.jwt import create_token

    token = create_token(
        {
            "sub": "usr_other_001",
            "org_id": "org_other_999",
            "email": "other@other.com",
            "role": "admin",
        }
    )
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


def _seed_autofill_template():
    """Create a template with questions designed to test keyword-based auto-fill mapping.

    Template has questions covering: energy, water, emissions, waste, spend, country, employee count.
    """
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
                "ESG Auto-fill Test Template",
                "Test template for B3.14",
                1,
                "environment",
                1,
            ),
        )
        conn.commit()

        row = conn.execute(
            "SELECT id FROM questionnaire_templates WHERE name = 'ESG Auto-fill Test Template'"
        ).fetchone()
        template_id = row["id"]

        questions = [
            ("Q1", "What is your annual energy consumption in kWh?", "number", 1),
            ("Q2", "What is your annual water usage in cubic meters?", "number", 2),
            ("Q3", "What are your total GHG emissions in tCO2e?", "number", 3),
            ("Q4", "How much waste did you generate in tonnes?", "number", 4),
            ("Q5", "What is your annual spend with us in USD?", "number", 5),
            ("Q6", "What country are you located in?", "text", 6),
            ("Q7", "What is your annual revenue in USD?", "number", 7),
            ("Q8", "Do you have ISO 14001 certification?", "choice", 8),
        ]
        for qid, qtext, qtype, sort_order in questions:
            conn.execute(
                """
                INSERT INTO questionnaire_questions
                    (template_id, question_id, question_text, question_type, sort_order, required)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (template_id, qid, qtext, qtype, sort_order, 1),
            )
        conn.commit()
    finally:
        conn.close()

    return template_id


class TestAutoFillResponseStructure:
    """Auto-fill endpoint returns the correct response structure."""

    def test_returns_correct_top_level_keys(self, client):
        """Response includes template_id, supplier_id, auto_fill_percentage, questions, summary."""
        template_id = _seed_autofill_template()

        resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        assert "template_id" in data
        assert "supplier_id" in data
        assert "auto_fill_percentage" in data
        assert "questions" in data
        assert "summary" in data

    def test_questions_have_required_fields(self, client):
        """Each question entry has q_id, text, status, value, source."""
        template_id = _seed_autofill_template()

        resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        for q in data["questions"]:
            assert "q_id" in q
            assert "text" in q
            assert "status" in q
            assert q["status"] in ("auto_filled", "not_applicable", "needs_input")
            if q["status"] == "auto_filled":
                assert "value" in q
                assert "source" in q
            else:
                assert q["value"] is None
                assert q["source"] is None

    def test_summary_has_counts(self, client):
        """Summary object has auto_filled, not_applicable, needs_input counts."""
        template_id = _seed_autofill_template()

        resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        summary = data["summary"]
        assert "auto_filled" in summary
        assert "not_applicable" in summary
        assert "needs_input" in summary
        assert isinstance(summary["auto_filled"], int)
        assert isinstance(summary["not_applicable"], int)
        assert isinstance(summary["needs_input"], int)


class TestAutoFillKeywordMapping:
    """Keyword matching maps question text to supplier/metrics data."""

    def test_energy_question_auto_filled_from_metrics(self, client):
        """Question text with 'energy' / 'kWh' maps to metrics.energy_kwh."""
        template_id = _seed_autofill_template()

        resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        # Q1 is the energy question
        energy_q = next(q for q in data["questions"] if "energy" in q["text"].lower())
        assert energy_q["status"] == "auto_filled"
        assert energy_q["source"] == "metrics.energy_kwh"
        # Seed data has energy_kwh cluster with value 2847320
        assert energy_q["value"] == "2,847,320 kWh"

    def test_water_question_auto_filled_from_metrics(self, client):
        """Question text with 'water' / 'cubic meters' maps to metrics.water_m3."""
        template_id = _seed_autofill_template()

        resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        water_q = next(q for q in data["questions"] if "water" in q["text"].lower())
        assert water_q["status"] == "auto_filled"
        assert water_q["source"] == "metrics.water_m3"
        # Seed data has water_m3 cluster with value 18430
        assert water_q["value"] == "18,430 m³"

    def test_emissions_question_auto_filled_from_metrics(self, client):
        """Question text with 'emissions' / 'tCO2' maps to metrics.emissions_tco2."""
        template_id = _seed_autofill_template()

        resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        emissions_q = next(
            q
            for q in data["questions"]
            if "emission" in q["text"].lower() or "ghg" in q["text"].lower()
        )
        assert emissions_q["status"] == "auto_filled"
        assert emissions_q["source"] == "metrics.emissions_tco2"
        # Seed data has emissions_tco2 cluster with value 892.4
        assert emissions_q["value"] == "892.4 tCO2e"

    def test_country_question_auto_filled_from_supplier(self, client):
        """Question text with 'country' / 'located' maps to suppliers.country."""
        template_id = _seed_autofill_template()

        resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        country_q = next(q for q in data["questions"] if "country" in q["text"].lower())
        assert country_q["status"] == "auto_filled"
        assert country_q["source"] == "suppliers.country"
        # sup_001 country is "IN" per seed data
        assert country_q["value"] == "IN"

    def test_spend_question_auto_filled_from_supplier(self, client):
        """Question text with 'spend' / 'USD' maps to suppliers.annual_spend_usd."""
        template_id = _seed_autofill_template()

        resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        spend_q = next(q for q in data["questions"] if "spend" in q["text"].lower())
        assert spend_q["status"] == "auto_filled"
        assert spend_q["source"] == "suppliers.annual_spend_usd"
        # sup_001 annual_spend_usd from seed is 2,400,000
        assert "2,400,000" in spend_q["value"]

    def test_revenue_question_not_auto_filled_when_no_data(self, client):
        """Revenue question is not_applicable since there's no revenue field mapping."""
        template_id = _seed_autofill_template()

        resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        revenue_q = next(q for q in data["questions"] if "revenue" in q["text"].lower())
        # No revenue field mapping exists, so this should be not_applicable
        assert revenue_q["status"] == "not_applicable"
        assert revenue_q["value"] is None

    def test_choice_question_not_applicable(self, client):
        """Choice-type questions have no keyword match → not_applicable."""
        template_id = _seed_autofill_template()

        resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        choice_q = next(q for q in data["questions"] if "iso" in q["text"].lower())
        # Choice questions have no keyword match in our mapping → not_applicable
        assert choice_q["status"] == "not_applicable"
        assert choice_q["value"] is None


class TestAutoFillPercentage:
    """auto_fill_percentage is computed as (auto_filled / applicable) * 100."""

    def test_percentage_calculation(self, client):
        """Percentage = (auto_filled questions / total applicable questions) * 100."""
        template_id = _seed_autofill_template()

        resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        summary = data["summary"]
        total_applicable = summary["auto_filled"] + summary["needs_input"]
        if total_applicable > 0:
            expected_pct = round(summary["auto_filled"] / total_applicable * 100, 1)
            assert data["auto_fill_percentage"] == expected_pct

    def test_percentage_rounded_to_one_decimal(self, client):
        """auto_fill_percentage is expressed to 1 decimal place."""
        template_id = _seed_autofill_template()

        resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        pct = data["auto_fill_percentage"]
        # Should be a reasonable number between 0 and 100
        assert 0 <= pct <= 100
        # Check it has at most 1 decimal place
        assert pct == round(pct, 1)


class TestAutoFillOrgIsolation:
    """Users can only auto-fill data for their own org's suppliers."""

    def test_unknown_template_returns_404(self, client):
        """Returns 404 for a template that does not exist."""
        resp = client.get("/api/questionnaires/auto-fill/999999/sup_001")
        assert resp.status_code == 404

    def test_unknown_supplier_returns_404(self, client):
        """Returns 404 for a supplier that does not exist."""
        template_id = _seed_autofill_template()
        resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_nonexistent")
        assert resp.status_code == 404

    def test_other_org_supplier_returns_403(self, client, other_org_client):
        """Returns 403 when accessing a supplier belonging to another org via globally-accessible template."""
        # Use a globally-accessible template (org_id='') so template check passes,
        # then verify the supplier org check returns 403.
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
                ("", "Global Test Template", "For org isolation test", 1, "environment", 1),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id FROM questionnaire_templates WHERE name = 'Global Test Template'"
            ).fetchone()
            global_template_id = row["id"]
        finally:
            conn.close()

        # With a globally-accessible template, org_other_999 can access it
        # but sup_001 belongs to org_bd_001 → should get 403
        resp = other_org_client.get(f"/api/questionnaires/auto-fill/{global_template_id}/sup_001")
        assert resp.status_code == 403

    def test_requires_auth(self):
        """Endpoint returns 401 without authentication."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        c = TestClient(app)
        resp = c.get("/api/questionnaires/auto-fill/1/sup_001")
        assert resp.status_code == 401


class TestAutoFillNoSupplierData:
    """When a question matches a mapped keyword but no data exists, it yields needs_input."""

    def test_waste_question_yields_needs_input_when_no_waste_data(self, client):
        """Waste question gets needs_input when metrics table has no waste_tonnes cluster."""
        template_id = _seed_autofill_template()

        resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
        assert resp.status_code == 200
        data = resp.json()

        # Q4 is the waste question — no waste_tonnes cluster exists in metrics
        waste_q = next(q for q in data["questions"] if "waste" in q["text"].lower())
        # waste_tonnes cluster not in metrics → needs_input
        assert waste_q["status"] == "needs_input"
        assert waste_q["value"] is None
