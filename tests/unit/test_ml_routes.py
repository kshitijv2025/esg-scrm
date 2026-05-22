"""ML route tests — org isolation, batch endpoint, admin-only train, risk scoring.

These tests cover the API surface of src/api/routes/ml.py:
  GET  /api/ml/predict/{supplier_id}
  GET  /api/ml/predict
  POST /api/ml/train

These are distinct from tests/unit/test_ml.py which covers the risk_predictor
unit functions directly. This file focuses on API-level org isolation and routing.
"""
import json
import sys

sys.path.insert(0, "src")

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.jwt import create_token
from src.db.database import _execute, get_connection, reset_database
from src.ml.risk_predictor import _WEIGHTS_PATH, DEFAULT_WEIGHTS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_suppliers():
    """Reset DB and seed minimal supplier + flag data for ML route tests."""
    reset_database()
    conn = get_connection()

    _execute(conn, """
        INSERT OR IGNORE INTO organizations (id, name, industry, employee_count)
        VALUES (?, ?, ?, ?)
    """, ("org_bd_001", "Test Org", "Manufacturing", 100))

    _execute(conn, """
        INSERT OR IGNORE INTO organizations (id, name, industry, employee_count)
        VALUES (?, ?, ?, ?)
    """, ("org_other", "Other Org", "Textiles", 50))

    suppliers = [
        ("ml_sup_001", "org_bd_001", "Tier1 Supplier", "IN", "Garment",
         "tier1", 5000000, "", "whatsapp", "responded", "A", 1.0, 0, "ISO14001"),
        ("ml_sup_002", "org_bd_001", "Tier2 Risky Supplier", "MM", "Dyeing",
         "tier2", 800000, "", "email", "not_sent", "C", 8.5, 3, ""),
        ("ml_sup_003", "org_other", "Other Org Supplier", "BD", "Cotton",
         "tier1", 2000000, "", "whatsapp", "pending", "B", 4.2, 1, "GOTS"),
    ]
    for s in suppliers:
        _execute(conn, """
            INSERT OR REPLACE INTO suppliers
            (id, org_id, name, country, industry, tier, annual_spend_usd,
             phone, preferred_channel, questionnaire_status, risk_tier,
             risk_score, active_flags, certifications)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, s)

    # Unacknowledged risk flags
    flags = [
        ("ml_flag_001", "org_bd_001", "factory_bd_001",
         "Water usage spike", "water", "WARNING", 30, 2.5, 0),
        ("ml_flag_002", "org_bd_001", "factory_bd_001",
         "Emissions exceed threshold", "emissions", "CRITICAL", 10, 4.0, 0),
        ("ml_flag_003", "org_other", "factory_bd_001",
         "Minor flag", "energy", "INFO", 5, 0.5, 0),
    ]
    for f in flags:
        _execute(conn, """
            INSERT OR REPLACE INTO risk_flags
            (id, org_id, factory_id, flag_text, cluster, severity,
             days_overdue, priority_score, acknowledged)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, f)

    conn.close()


def _auth_headers(org_id: str = "org_bd_001", role: str = "admin"):
    token = create_token({
        "sub": "ml_test_user",
        "org_id": org_id,
        "email": "ml@test.com",
        "role": role,
    })
    return {"Authorization": f"Bearer {token}"}


def _restore_weights():
    _WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_WEIGHTS_PATH, "w") as f:
        json.dump(DEFAULT_WEIGHTS, f, indent=2)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _seed_and_restore():
    _seed_suppliers()
    _restore_weights()
    yield
    _restore_weights()


@pytest.fixture()
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/ml/predict/{supplier_id}
# ---------------------------------------------------------------------------

class TestPredictSingleRoute:
    """Test GET /api/ml/predict/{supplier_id}."""

    def test_returns_correct_structure(self, client):
        """Response must have supplier_id, risk_score, risk_level, factors, recommendation."""
        resp = client.get("/api/ml/predict/ml_sup_001", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "supplier_id" in data
        assert "risk_score" in data
        assert "risk_level" in data
        assert "factors" in data
        assert "recommendation" in data

    def test_org_isolation_blocks_wrong_org(self, client):
        """Supplier from org_other must not be accessible by org_bd_001 token."""
        resp = client.get("/api/ml/predict/ml_sup_003", headers=_auth_headers(org_id="org_bd_001"))
        # ml_sup_003 belongs to org_other, so it should not be found
        assert resp.status_code == 404

    def test_org_other_can_access_own_supplier(self, client):
        """Supplier from org_other must be accessible by org_other token."""
        resp = client.get("/api/ml/predict/ml_sup_003", headers=_auth_headers(org_id="org_other"))
        assert resp.status_code == 200
        data = resp.json()
        assert data["supplier_id"] == "ml_sup_003"

    def test_risk_score_in_valid_range(self, client):
        """risk_score must be between 0 and 100."""
        resp = client.get("/api/ml/predict/ml_sup_001", headers=_auth_headers())
        assert resp.status_code == 200
        score = resp.json()["risk_score"]
        assert 0.0 <= score <= 100.0

    def test_risk_level_is_valid_label(self, client):
        """risk_level must be one of the four valid labels."""
        resp = client.get("/api/ml/predict/ml_sup_001", headers=_auth_headers())
        assert resp.status_code == 200
        level = resp.json()["risk_level"]
        assert level in ("low", "medium", "high", "critical")

    def test_factors_has_expected_keys(self, client):
        """factors dict must contain all expected scoring component keys."""
        resp = client.get("/api/ml/predict/ml_sup_001", headers=_auth_headers())
        assert resp.status_code == 200
        factors = resp.json()["factors"]
        expected = {
            "risk_tier_raw", "risk_tier_contribution",
            "risk_flags_count", "risk_flags_contribution",
            "cert_count", "certifications", "cert_contribution",
            "questionnaire_status_raw", "questionnaire_contribution",
            "country_risk_raw", "country_contribution",
            "weights_used",
        }
        missing = expected - set(factors.keys())
        assert not missing, f"Missing factor keys: {missing}"

    def test_recommendation_is_non_empty_string(self, client):
        """recommendation must be a non-empty string."""
        resp = client.get("/api/ml/predict/ml_sup_001", headers=_auth_headers())
        assert resp.status_code == 200
        rec = resp.json()["recommendation"]
        assert isinstance(rec, str)
        assert len(rec) > 0

    def test_nonexistent_supplier_returns_404(self, client):
        """Unknown supplier_id must return 404."""
        resp = client.get("/api/ml/predict/nonexistent", headers=_auth_headers())
        assert resp.status_code == 404

    def test_requires_auth(self, client):
        """Request without auth must return 401."""
        resp = client.get("/api/ml/predict/ml_sup_001")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/ml/predict (batch)
# ---------------------------------------------------------------------------

class TestPredictBatchRoute:
    """Test GET /api/ml/predict (batch prediction for all suppliers)."""

    def test_returns_summary_and_suppliers(self, client):
        """Response must have 'summary' and 'suppliers' keys."""
        resp = client.get("/api/ml/predict", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "suppliers" in data

    def test_summary_has_correct_structure(self, client):
        """Summary must have 'total' and 'by_level' with all four levels."""
        resp = client.get("/api/ml/predict", headers=_auth_headers())
        assert resp.status_code == 200
        summary = resp.json()["summary"]
        assert "total" in summary
        assert "by_level" in summary
        by_level = summary["by_level"]
        for level in ("critical", "high", "medium", "low"):
            assert level in by_level, f"Missing '{level}' in by_level"

    def test_batch_is_org_scoped(self, client):
        """Batch must only return suppliers from the authenticated org."""
        resp = client.get("/api/ml/predict", headers=_auth_headers(org_id="org_bd_001"))
        assert resp.status_code == 200
        supplier_ids = {s["supplier_id"] for s in resp.json()["suppliers"]}
        # ml_sup_003 is in org_other — must not appear
        assert "ml_sup_003" not in supplier_ids
        # ml_sup_001 and ml_sup_002 are in org_bd_001
        assert "ml_sup_001" in supplier_ids
        assert "ml_sup_002" in supplier_ids

    def test_suppliers_sorted_by_risk_descending(self, client):
        """Suppliers list must be sorted by risk_score descending."""
        resp = client.get("/api/ml/predict", headers=_auth_headers())
        assert resp.status_code == 200
        suppliers = resp.json()["suppliers"]
        scores = [s["risk_score"] for s in suppliers if s.get("risk_score") is not None]
        assert scores == sorted(scores, reverse=True), "Suppliers not sorted by risk_score descending"

    def test_all_returned_suppliers_have_valid_scores(self, client):
        """Every supplier in the batch must have a valid risk_score."""
        resp = client.get("/api/ml/predict", headers=_auth_headers())
        assert resp.status_code == 200
        suppliers = resp.json()["suppliers"]
        for s in suppliers:
            assert s.get("risk_score") is not None, f"Supplier {s['supplier_id']} missing risk_score"
            assert 0.0 <= s["risk_score"] <= 100.0

    def test_batch_total_matches_suppliers_count(self, client):
        """summary.total must equal len(suppliers)."""
        resp = client.get("/api/ml/predict", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total"] == len(data["suppliers"])

    def test_batch_requires_auth(self, client):
        """Request without auth must return 401."""
        resp = client.get("/api/ml/predict")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/ml/train (admin-only)
# ---------------------------------------------------------------------------

class TestTrainRoute:
    """Test POST /api/ml/train — requires admin role."""

    def test_admin_can_train(self, client):
        """Admin user must be able to submit training feedback."""
        resp = client.post("/api/ml/train", headers=_auth_headers(role="admin"), json=[
            {"supplier_id": "ml_sup_001", "expected_level": "high"},
        ])
        assert resp.status_code == 200
        data = resp.json()
        assert "weights" in data
        assert "corrections_applied" in data
        assert "total_feedback" in data
        assert "adjustments" in data

    def test_non_admin_gets_403(self, client):
        """Non-admin (viewer, editor) must receive 403."""
        for role in ("viewer", "editor"):
            resp = client.post("/api/ml/train", headers=_auth_headers(role=role), json=[
                {"supplier_id": "ml_sup_001", "expected_level": "high"},
            ])
            assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"

    def test_train_feedback_validates_required_fields(self, client):
        """Missing supplier_id or expected_level must return 400."""
        resp = client.post("/api/ml/train", headers=_auth_headers(role="admin"), json=[
            {"supplier_id": "ml_sup_001"},  # missing expected_level
        ])
        assert resp.status_code == 400

        resp = client.post("/api/ml/train", headers=_auth_headers(role="admin"), json=[
            {"expected_level": "high"},  # missing supplier_id
        ])
        assert resp.status_code == 400

    def test_train_validates_expected_level_values(self, client):
        """Invalid expected_level values must return 400."""
        resp = client.post("/api/ml/train", headers=_auth_headers(role="admin"), json=[
            {"supplier_id": "ml_sup_001", "expected_level": "invalid"},
        ])
        assert resp.status_code == 400

    def test_train_requires_auth(self, client):
        """Request without auth must return 401."""
        resp = client.post("/api/ml/train", json=[
            {"supplier_id": "ml_sup_001", "expected_level": "high"},
        ])
        assert resp.status_code == 401

    def test_train_returns_weights_dict(self, client):
        """Response weights must be a dict with all expected weight keys."""
        resp = client.post("/api/ml/train", headers=_auth_headers(role="admin"), json=[
            {"supplier_id": "ml_sup_001", "expected_level": "critical"},
        ])
        assert resp.status_code == 200
        weights = resp.json()["weights"]
        expected_keys = {"risk_tier", "risk_flags", "certifications", "questionnaire", "country"}
        assert set(weights.keys()) == expected_keys
        # Weights should sum to approximately 1.0
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01

    def test_train_adjustments_detail_returned(self, client):
        """Each adjustment entry must include supplier_id, predicted, expected, error."""
        resp = client.post("/api/ml/train", headers=_auth_headers(role="admin"), json=[
            {"supplier_id": "ml_sup_001", "expected_level": "critical"},
        ])
        assert resp.status_code == 200
        adjustments = resp.json()["adjustments"]
        assert len(adjustments) == 1
        adj = adjustments[0]
        for field in ("supplier_id", "predicted", "expected", "error"):
            assert field in adj, f"Missing adjustment field: {field}"

    def test_train_invalid_supplier_in_feedback_skipped(self, client):
        """Invalid supplier_id in feedback must not cause error, just be skipped."""
        resp = client.post("/api/ml/train", headers=_auth_headers(role="admin"), json=[
            {"supplier_id": "nonexistent_supplier", "expected_level": "high"},
        ])
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_feedback"] == 1
        assert data["corrections_applied"] == 0

    def test_train_persists_weights_to_file(self, client):
        """train_weights must persist new weights to risk_weights.json."""
        _restore_weights()
        resp = client.post("/api/ml/train", headers=_auth_headers(role="admin"), json=[
            {"supplier_id": "ml_sup_001", "expected_level": "critical"},
            {"supplier_id": "ml_sup_002", "expected_level": "low"},
        ])
        assert resp.status_code == 200
        with open(_WEIGHTS_PATH) as f:
            persisted = json.load(f)
        assert isinstance(persisted, dict)
        assert set(persisted.keys()) == {"risk_tier", "risk_flags", "certifications", "questionnaire", "country"}


# ---------------------------------------------------------------------------
# Risk scoring with sample data
# ---------------------------------------------------------------------------

class TestRiskScoringWithSampleData:
    """Test risk scoring produces expected results for known supplier profiles."""

    def test_high_risk_supplier_scores_high(self, client):
        """Supplier with tier C, no certs, not_sent questionnaire, high country risk should score high."""
        resp = client.get("/api/ml/predict/ml_sup_002", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_score"] > 50, \
            f"Expected high risk for ml_sup_002, got {data['risk_score']}"
        assert data["risk_level"] in ("high", "critical")

    def test_low_risk_supplier_scores_low(self, client):
        """Supplier with tier A, responded questionnaire, ISO cert should score low."""
        resp = client.get("/api/ml/predict/ml_sup_001", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_score"] < 50, \
            f"Expected low risk for ml_sup_001, got {data['risk_score']}"
        assert data["risk_level"] in ("low", "medium")

    def test_risk_score_determinism(self, client):
        """Same request twice must return the same risk_score (no randomness)."""
        resp1 = client.get("/api/ml/predict/ml_sup_001", headers=_auth_headers())
        resp2 = client.get("/api/ml/predict/ml_sup_001", headers=_auth_headers())
        assert resp1.json()["risk_score"] == resp2.json()["risk_score"]
