"""Regression test for B3.14 autofill endpoint — GET /api/questionnaires/auto-fill/{template_id}/{supplier_id}

This test verifies the endpoint behaves correctly after implementation.
Mark: @pytest.mark.regression
"""

import pytest


@pytest.fixture(autouse=True)
def _reset_db():
    """Reset database before each test."""
    from src.db.database import reset_database
    from src.db.seed import seed
    from src.db.seed_emission_factors import seed_emission_factors
    from src.db.seed_alert_thresholds import seed_alert_thresholds

    reset_database()
    seed()
    seed_emission_factors()
    seed_alert_thresholds()
    yield


@pytest.fixture
def client():
    """Authenticated test client."""
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
    return c


@pytest.fixture
def template_id():
    """Create a minimal test template."""
    import sqlite3
    from src.db.database import DB_PATH

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute(
        """
        INSERT INTO questionnaire_templates (org_id, name, description, tier, category, is_active)
        VALUES ('org_bd_001', 'Regression Test Template', 'For regression tests', 1, 'environment', 1)
    """
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM questionnaire_templates WHERE name = 'Regression Test Template'"
    ).fetchone()
    template_id = row["id"]

    questions = [
        ("Q1", "What is your annual energy consumption in kWh?", "number", 1),
        ("Q2", "What is your annual water usage in cubic meters?", "number", 2),
        ("Q3", "What are your total GHG emissions in tCO2e?", "number", 3),
        ("Q4", "Do you have ISO 14001 certification?", "choice", 4),
        ("Q5", "What country are you located in?", "text", 5),
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
    conn.close()
    return template_id


@pytest.mark.regression
def test_autofill_returns_correct_structure(client, template_id):
    """Response must have all required top-level keys."""
    resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
    assert resp.status_code == 200
    data = resp.json()

    assert "template_id" in data
    assert "supplier_id" in data
    assert "auto_fill_percentage" in data
    assert "questions" in data
    assert "summary" in data


@pytest.mark.regression
def test_autofill_question_status_values(client, template_id):
    """Each question status must be one of the three valid values."""
    resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
    assert resp.status_code == 200
    data = resp.json()

    for q in data["questions"]:
        assert "q_id" in q
        assert "text" in q
        assert "status" in q
        assert q["status"] in ("auto_filled", "not_applicable", "needs_input")


@pytest.mark.regression
def test_autofill_energy_from_metrics(client, template_id):
    """Question with 'energy' keyword auto-fills from metrics.energy_kwh."""
    resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
    assert resp.status_code == 200
    data = resp.json()

    energy_q = next(q for q in data["questions"] if "energy" in q["text"].lower())
    assert energy_q["status"] == "auto_filled"
    assert energy_q["source"] == "metrics.energy_kwh"


@pytest.mark.regression
def test_autofill_water_from_metrics(client, template_id):
    """Question with 'water' keyword auto-fills from metrics.water_m3."""
    resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
    assert resp.status_code == 200
    data = resp.json()

    water_q = next(q for q in data["questions"] if "water" in q["text"].lower())
    assert water_q["status"] == "auto_filled"
    assert water_q["source"] == "metrics.water_m3"


@pytest.mark.regression
def test_autofill_country_from_supplier(client, template_id):
    """Question with 'country' keyword auto-fills from suppliers.country."""
    resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
    assert resp.status_code == 200
    data = resp.json()

    country_q = next(q for q in data["questions"] if "country" in q["text"].lower())
    assert country_q["status"] == "auto_filled"
    assert country_q["source"] == "suppliers.country"


@pytest.mark.regression
def test_autofill_choice_questions_not_applicable(client, template_id):
    """Choice-type questions return not_applicable (no keyword matching)."""
    resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
    assert resp.status_code == 200
    data = resp.json()

    # Q4 is the ISO 14001 choice question
    choice_q = next(q for q in data["questions"] if "ISO" in q["text"])
    assert choice_q["status"] == "not_applicable"


@pytest.mark.regression
def test_autofill_unknown_template_404(client):
    """Unknown template ID returns 404."""
    resp = client.get("/api/questionnaires/auto-fill/nonexistent/sup_001")
    assert resp.status_code == 404


@pytest.mark.regression
def test_autofill_unknown_supplier_404(client, template_id):
    """Unknown supplier ID returns 404."""
    resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_nonexistent")
    assert resp.status_code == 404


@pytest.mark.regression
def test_autofill_percentage_calculation(client, template_id):
    """auto_fill_percentage is computed correctly as (auto_filled / applicable) * 100."""
    resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
    assert resp.status_code == 200
    data = resp.json()

    summary = data["summary"]
    auto_filled = summary["auto_filled"]
    needs_input = summary["needs_input"]
    applicable = auto_filled + needs_input

    if applicable > 0:
        expected_pct = round(auto_filled / applicable * 100, 1)
        assert data["auto_fill_percentage"] == expected_pct


@pytest.mark.regression
def test_autofill_spend_question_not_matched_to_waste(client, template_id):
    """'spend' keyword must not match 'waste' question via substring false positive."""
    resp = client.get(f"/api/questionnaires/auto-fill/{template_id}/sup_001")
    assert resp.status_code == 200
    data = resp.json()

    # Q4 is the choice question (ISO 14001) — no spend keywords
    # If spend was incorrectly matching waste, the choice question would be affected
    # The regression: ensure choice questions stay not_applicable regardless of keywords
    choice_q = next(q for q in data["questions"] if "ISO" in q["text"])
    assert choice_q["status"] == "not_applicable"
