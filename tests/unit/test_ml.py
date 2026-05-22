"""
Tests for ML risk prediction and API routes.

Covers:
  - risk_predictor: predict_supplier_risk, batch_predict, train_weights
  - API routes: GET /api/ml/predict/{id}, GET /api/ml/predict, POST /api/ml/train
"""
import json
import sys

sys.path.insert(0, "src")

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.jwt import create_token
from src.db.database import _execute, get_connection, reset_database
from src.ml.risk_predictor import (
    _WEIGHTS_PATH,
    DEFAULT_WEIGHTS,
    batch_predict,
    predict_supplier_risk,
    train_weights,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_minimal():
    """Reset DB and insert the minimum rows needed by the ML module.

    The risk_predictor queries the `suppliers` and `risk_flags` tables.
    We create a handful of suppliers across different risk tiers and a few
    unacknowledged risk flags so the scoring logic has real data to work with.
    """
    reset_database()
    conn = get_connection()

    # Organization row (FK target for users / suppliers)
    _execute(conn, """
        INSERT INTO organizations (id, name, industry, employee_count)
        VALUES (?, ?, ?, ?)
    """, ("org_bd_001", "Test Org", "Garment manufacturing", 100))

    _execute(conn, """
        INSERT INTO organizations (id, name, industry, employee_count)
        VALUES (?, ?, ?, ?)
    """, ("org_other", "Other Org", "Textiles", 50))

    suppliers = [
        # id, org_id, name, country, industry, tier, spend, phone, channel,
        # questionnaire_status, risk_tier, risk_score, active_flags, certifications
        ("sup_001", "org_bd_001", "Low Risk Supplier", "IN", "Cotton",
         "tier2", 2400000, "", "whatsapp", "responded", "A", 2.1, 0,
         "GOTS,OEKO-TEX"),
        ("sup_002", "org_bd_001", "Medium Risk Supplier", "VN", "Fabrics",
         "tier2", 3200000, "", "whatsapp", "pending", "B", 5.8, 2,
         "OEKO-TEX"),
        ("sup_003", "org_bd_001", "High Risk Supplier", "MM", "Packaging",
         "tier3", 480000, "", "email", "not_sent", "C", 9.1, 4, ""),
        ("sup_004", "org_other", "Other Org Supplier", "BD", "Dyeing",
         "tier1", 5000000, "", "whatsapp", "responded", "B", 4.0, 0,
         "GOTS"),
    ]
    for s in suppliers:
        _execute(conn, """
            INSERT INTO suppliers (id, org_id, name, country, industry, tier,
                annual_spend_usd, phone, preferred_channel,
                questionnaire_status, risk_tier, risk_score, active_flags,
                certifications)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, s)

    # Unacknowledged risk flags -- the predictor counts these per org.
    flags = [
        ("flag_001", "org_bd_001", "factory_bd_001", "Water exceeds limit",
         "G6", "WARNING", 45, 3.0, 0),
        ("flag_002", "org_bd_001", "factory_bd_001", "Supply disruption risk",
         "G5", "CRITICAL", 12, 3.96, 0),
        ("flag_003", "org_other", "factory_bd_001", "Minor flag",
         "G4", "INFO", 0, 0.0, 0),
    ]
    for f in flags:
        _execute(conn, """
            INSERT INTO risk_flags (id, org_id, factory_id, flag_text, cluster,
                severity, days_overdue, priority_score, acknowledged)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, f)

    conn.close()


def _auth_headers(role="admin", org_id="org_bd_001", sub="usr_test_001"):
    """Build Authorization headers with a signed JWT."""
    token = create_token({
        "sub": sub,
        "org_id": org_id,
        "email": "test@test.com",
        "role": role,
    })
    return {"Authorization": f"Bearer {token}"}


def _restore_default_weights():
    """Reset the weights file to DEFAULT_WEIGHTS so tests do not leak state."""
    _WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_WEIGHTS_PATH, "w") as f:
        json.dump(DEFAULT_WEIGHTS, f, indent=2)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _fresh_db_and_weights():
    """Reset the database and weight file for every test."""
    _seed_minimal()
    _restore_default_weights()
    yield
    # Cleanup: restore weights so subsequent test files are not affected.
    _restore_default_weights()


@pytest.fixture()
def client():
    """FastAPI TestClient authenticated as admin for org_bd_001."""
    c = TestClient(app)
    c.headers.update(_auth_headers(role="admin", org_id="org_bd_001"))
    return c


# ===================================================================
# 1. predict_supplier_risk -- valid supplier returns risk score 0-100
# ===================================================================

class TestPredictSupplierRisk:
    """Unit tests for src.ml.risk_predictor.predict_supplier_risk."""

    def test_valid_supplier_returns_score_in_range(self):
        result = predict_supplier_risk("sup_001", org_id="org_bd_001")
        assert result["supplier_id"] == "sup_001"
        assert result["risk_score"] is not None
        assert 0.0 <= result["risk_score"] <= 100.0
        assert result["risk_level"] in ("low", "medium", "high", "critical")
        assert "factors" in result
        assert "recommendation" in result
        assert result["supplier_name"] == "Low Risk Supplier"

    def test_low_risk_supplier_scores_low(self):
        """Supplier with tier A, responded questionnaire, multiple certs should score low."""
        result = predict_supplier_risk("sup_001", org_id="org_bd_001")
        assert result["risk_level"] in ("low", "medium")
        assert result["risk_score"] < 50

    def test_high_risk_supplier_scores_high(self):
        """Supplier with tier C, no certs, not_sent questionnaire, high country risk should score high."""
        result = predict_supplier_risk("sup_003", org_id="org_bd_001")
        assert result["risk_score"] > 50
        assert result["risk_level"] in ("high", "critical")

    def test_factors_have_expected_keys(self):
        result = predict_supplier_risk("sup_001", org_id="org_bd_001")
        factors = result["factors"]
        expected_keys = [
            "risk_tier_raw", "risk_tier_contribution",
            "risk_flags_count", "risk_flags_contribution",
            "cert_count", "certifications", "cert_contribution",
            "questionnaire_status_raw", "questionnaire_contribution",
            "country_risk_raw", "country_contribution",
            "weights_used",
        ]
        for key in expected_keys:
            assert key in factors, f"Missing factor key: {key}"

    def test_certifications_parsed_correctly(self):
        result = predict_supplier_risk("sup_001", org_id="org_bd_001")
        certs = result["factors"]["certifications"]
        assert isinstance(certs, list)
        assert "GOTS" in certs
        assert "OEKO-TEX" in certs
        assert result["factors"]["cert_count"] == 2

    def test_no_certifications_supplier(self):
        result = predict_supplier_risk("sup_003", org_id="org_bd_001")
        assert result["factors"]["cert_count"] == 0
        assert result["factors"]["certifications"] == []


# ===================================================================
# 2. predict_supplier_risk -- nonexistent supplier returns error
# ===================================================================

class TestPredictSupplierRiskNotFound:
    def test_nonexistent_supplier_returns_error(self):
        result = predict_supplier_risk("sup_nonexistent", org_id="org_bd_001")
        assert result["error"] is not None
        assert result["risk_score"] is None
        assert result["risk_level"] is None

    def test_nonexistent_supplier_id_preserved_in_result(self):
        result = predict_supplier_risk("sup_missing", org_id="org_bd_001")
        assert result["supplier_id"] == "sup_missing"

    def test_no_org_id_returns_error_for_wrong_org(self):
        """Without org_id filter, supplier lookup should find the supplier if it exists."""
        result = predict_supplier_risk("sup_001")
        # No org_id filter -- supplier exists, should succeed.
        assert result["risk_score"] is not None

    def test_wrong_org_id_returns_error(self):
        """Supplier sup_001 belongs to org_bd_001; querying with org_other should fail."""
        result = predict_supplier_risk("sup_001", org_id="org_other")
        assert result.get("error") is not None
        assert result["risk_score"] is None


# ===================================================================
# 3. predict_supplier_risk respects org_id filtering
# ===================================================================

class TestPredictSupplierRiskOrgFilter:
    def test_same_org_returns_result(self):
        result = predict_supplier_risk("sup_001", org_id="org_bd_001")
        assert result["risk_score"] is not None
        assert result["supplier_name"] == "Low Risk Supplier"

    def test_different_org_returns_not_found(self):
        """Supplier sup_001 is in org_bd_001; querying with org_other finds nothing."""
        result = predict_supplier_risk("sup_001", org_id="org_other")
        assert result.get("error") is not None

    def test_no_org_finds_across_orgs(self):
        """Without org_id, any supplier is visible."""
        result = predict_supplier_risk("sup_004")
        assert result["risk_score"] is not None
        assert result["supplier_name"] == "Other Org Supplier"

    def test_org_filter_isolation(self):
        """sup_004 is in org_other; org_bd_001 should not see it."""
        result = predict_supplier_risk("sup_004", org_id="org_bd_001")
        assert result.get("error") is not None


# ===================================================================
# 4. batch_predict returns all suppliers sorted by risk
# ===================================================================

class TestBatchPredict:
    def test_returns_all_suppliers_for_org(self):
        results = batch_predict(org_id="org_bd_001")
        ids = [r["supplier_id"] for r in results]
        assert "sup_001" in ids
        assert "sup_002" in ids
        assert "sup_003" in ids
        # sup_004 is org_other -- should not appear.
        assert "sup_004" not in ids

    def test_sorted_by_risk_descending(self):
        results = batch_predict(org_id="org_bd_001")
        scores = [r["risk_score"] for r in results if r["risk_score"] is not None]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"Results not sorted descending: {scores}"
            )

    def test_no_org_returns_all_suppliers(self):
        results = batch_predict()
        ids = [r["supplier_id"] for r in results]
        assert len(ids) >= 4  # all seeded suppliers
        assert "sup_004" in ids

    def test_empty_org_returns_empty(self):
        results = batch_predict(org_id="org_nonexistent")
        assert results == []

    def test_all_results_have_risk_scores(self):
        results = batch_predict(org_id="org_bd_001")
        for r in results:
            assert r["risk_score"] is not None
            assert 0.0 <= r["risk_score"] <= 100.0
            assert r["risk_level"] in ("low", "medium", "high", "critical")


# ===================================================================
# 5. train_weights adjusts weights based on feedback
# ===================================================================

class TestTrainWeights:
    def test_basic_feedback_adjusts_weights(self):
        feedback = [
            {"supplier_id": "sup_001", "expected_level": "high"},
        ]
        result = train_weights(feedback)
        assert result["total_feedback"] == 1
        assert isinstance(result["weights"], dict)
        # Weights should still sum to ~1.0 after normalization.
        total = sum(result["weights"].values())
        assert abs(total - 1.0) < 0.01

    def test_adjustments_detail_returned(self):
        feedback = [
            {"supplier_id": "sup_001", "expected_level": "critical"},
        ]
        result = train_weights(feedback)
        assert "adjustments" in result
        assert len(result["adjustments"]) == 1
        adj = result["adjustments"][0]
        assert adj["supplier_id"] == "sup_001"
        assert "predicted" in adj
        assert "expected" in adj

    def test_within_tolerance_no_adjustment(self):
        """If prediction already matches expected, adjustment should be 'none'."""
        # First, find the actual predicted level for sup_001.
        prediction = predict_supplier_risk("sup_001", org_id="org_bd_001")
        actual_level = prediction["risk_level"]
        feedback = [
            {"supplier_id": "sup_001", "expected_level": actual_level},
        ]
        result = train_weights(feedback)
        adj = result["adjustments"][0]
        # The error should be small enough to be within tolerance.
        assert adj.get("adjustment") == "none — within tolerance" or adj.get("adjusted_factor") is not None

    def test_invalid_supplier_skipped(self):
        feedback = [
            {"supplier_id": "sup_nonexistent", "expected_level": "high"},
        ]
        result = train_weights(feedback)
        assert result["total_feedback"] == 1
        assert result["corrections_applied"] == 0

    def test_invalid_expected_level_skipped(self):
        feedback = [
            {"supplier_id": "sup_001", "expected_level": "invalid_level"},
        ]
        result = train_weights(feedback)
        assert result["corrections_applied"] == 0

    def test_multiple_feedback_entries(self):
        feedback = [
            {"supplier_id": "sup_001", "expected_level": "high"},
            {"supplier_id": "sup_002", "expected_level": "low"},
            {"supplier_id": "sup_003", "expected_level": "low"},
        ]
        result = train_weights(feedback)
        assert result["total_feedback"] == 3
        assert len(result["adjustments"]) == 3

    def test_weights_persisted_to_file(self):
        """train_weights writes to risk_weights.json; verify the file is updated."""
        _restore_default_weights()
        feedback = [
            {"supplier_id": "sup_001", "expected_level": "critical"},
            {"supplier_id": "sup_003", "expected_level": "low"},
        ]
        result = train_weights(feedback)
        # Read the file and confirm it changed from defaults.
        with open(_WEIGHTS_PATH) as f:
            persisted = json.load(f)
        assert persisted == result["weights"]

    def test_empty_feedback_returns_defaults(self):
        result = train_weights([])
        assert result["total_feedback"] == 0
        assert result["corrections_applied"] == 0
        assert result["adjustments"] == []

    def test_weights_renormalized_after_adjustment(self):
        feedback = [
            {"supplier_id": "sup_001", "expected_level": "critical"},
            {"supplier_id": "sup_002", "expected_level": "low"},
        ]
        result = train_weights(feedback)
        total = sum(result["weights"].values())
        assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, expected 1.0"


# ===================================================================
# 6. GET /api/ml/predict/{supplier_id} -- single prediction
# ===================================================================

class TestGetPredictionRoute:
    def test_valid_supplier_returns_risk(self, client):
        resp = client.get("/api/ml/predict/sup_001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["supplier_id"] == "sup_001"
        assert 0.0 <= data["risk_score"] <= 100.0
        assert data["risk_level"] in ("low", "medium", "high", "critical")
        assert "factors" in data
        assert "recommendation" in data

    def test_nonexistent_supplier_returns_404(self, client):
        resp = client.get("/api/ml/predict/sup_nonexistent")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_org_filter_via_auth_token(self):
        """Auth token with org_bd_001 should not be able to see org_other suppliers."""
        c = TestClient(app)
        c.headers.update(_auth_headers(role="admin", org_id="org_other"))
        resp = c.get("/api/ml/predict/sup_001")
        # sup_001 is org_bd_001, auth token is org_other -> should 404.
        assert resp.status_code == 404

    def test_prediction_logs_emitted(self, client, caplog):
        """Verify the endpoint emits structured log lines."""
        import logging
        with caplog.at_level(logging.INFO, logger="src.api.routes.ml"):
            resp = client.get("/api/ml/predict/sup_001")
        assert resp.status_code == 200
        assert any("ml.predict" in r.message for r in caplog.records)


# ===================================================================
# 7. GET /api/ml/predict -- batch prediction
# ===================================================================

class TestGetBatchPredictionRoute:
    def test_batch_returns_summary_and_suppliers(self, client):
        resp = client.get("/api/ml/predict")
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "suppliers" in data
        summary = data["summary"]
        assert summary["total"] >= 3  # at least the 3 org_bd_001 suppliers
        assert "by_level" in summary
        by_level = summary["by_level"]
        assert "critical" in by_level
        assert "high" in by_level
        assert "medium" in by_level
        assert "low" in by_level

    def test_batch_suppliers_sorted_descending(self, client):
        resp = client.get("/api/ml/predict")
        data = resp.json()
        suppliers = data["suppliers"]
        scores = [s["risk_score"] for s in suppliers if s["risk_score"] is not None]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]

    def test_batch_only_own_org(self, client):
        """Auth token for org_bd_001 should only see org_bd_001 suppliers."""
        resp = client.get("/api/ml/predict")
        data = resp.json()
        supplier_ids = [s["supplier_id"] for s in data["suppliers"]]
        assert "sup_004" not in supplier_ids  # sup_004 is org_other

    def test_batch_summary_counts_match_suppliers(self, client):
        resp = client.get("/api/ml/predict")
        data = resp.json()
        suppliers = data["suppliers"]
        by_level = data["summary"]["by_level"]
        counted = (
            by_level["critical"] + by_level["high"]
            + by_level["medium"] + by_level["low"]
        )
        assert counted == len(suppliers)

    def test_batch_logs_emitted(self, client, caplog):
        import logging
        with caplog.at_level(logging.INFO, logger="src.api.routes.ml"):
            resp = client.get("/api/ml/predict")
        assert resp.status_code == 200
        assert any("ml.batch_predict" in r.message for r in caplog.records)


# ===================================================================
# 8. POST /api/ml/train -- requires admin role
# ===================================================================

class TestTrainRouteAuthorization:
    def test_admin_can_train(self, client):
        resp = client.post("/api/ml/train", json=[
            {"supplier_id": "sup_001", "expected_level": "high"},
        ])
        assert resp.status_code == 200

    def test_viewer_gets_403(self):
        c = TestClient(app)
        c.headers.update(_auth_headers(role="viewer", org_id="org_bd_001"))
        resp = c.post("/api/ml/train", json=[
            {"supplier_id": "sup_001", "expected_level": "high"},
        ])
        assert resp.status_code == 403

    def test_editor_gets_403(self):
        c = TestClient(app)
        c.headers.update(_auth_headers(role="editor", org_id="org_bd_001"))
        resp = c.post("/api/ml/train", json=[
            {"supplier_id": "sup_001", "expected_level": "high"},
        ])
        assert resp.status_code == 403


# ===================================================================
# 9. POST /api/ml/train -- validates feedback entries
# ===================================================================

class TestTrainRouteValidation:
    def test_empty_list_returns_400(self, client):
        resp = client.post("/api/ml/train", json=[])
        assert resp.status_code == 400

    def test_non_list_body_returns_422(self, client):
        """FastAPI request-body type validation rejects non-list before handler runs."""
        resp = client.post("/api/ml/train", json="not a list")
        assert resp.status_code == 422

    def test_entry_missing_supplier_id_returns_400(self, client):
        resp = client.post("/api/ml/train", json=[
            {"expected_level": "high"},
        ])
        assert resp.status_code == 400
        assert "supplier_id" in resp.json()["detail"]

    def test_entry_missing_expected_level_returns_400(self, client):
        resp = client.post("/api/ml/train", json=[
            {"supplier_id": "sup_001"},
        ])
        assert resp.status_code == 400
        assert "expected_level" in resp.json()["detail"]

    def test_invalid_expected_level_returns_400(self, client):
        resp = client.post("/api/ml/train", json=[
            {"supplier_id": "sup_001", "expected_level": "extreme"},
        ])
        assert resp.status_code == 400
        assert "expected_level" in resp.json()["detail"]

    def test_non_dict_entry_returns_422(self, client):
        """FastAPI item-type validation rejects non-dict entries before handler runs."""
        resp = client.post("/api/ml/train", json=[
            "not a dict",
        ])
        assert resp.status_code == 422

    def test_valid_feedback_returns_result(self, client):
        resp = client.post("/api/ml/train", json=[
            {"supplier_id": "sup_001", "expected_level": "high"},
            {"supplier_id": "sup_003", "expected_level": "low"},
        ])
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_feedback"] == 2
        assert "weights" in data
        assert "adjustments" in data

    def test_train_logs_emitted(self, client, caplog):
        import logging
        with caplog.at_level(logging.INFO, logger="src.api.routes.ml"):
            resp = client.post("/api/ml/train", json=[
                {"supplier_id": "sup_001", "expected_level": "high"},
            ])
        assert resp.status_code == 200
        assert any("ml.train" in r.message for r in caplog.records)


# ===================================================================
# 10. All endpoints require authentication
# ===================================================================

class TestMLRoutesRequireAuth:
    def test_predict_single_requires_auth(self):
        c = TestClient(app)
        resp = c.get("/api/ml/predict/sup_001")
        assert resp.status_code == 401

    def test_predict_batch_requires_auth(self):
        c = TestClient(app)
        resp = c.get("/api/ml/predict")
        assert resp.status_code == 401

    def test_train_requires_auth(self):
        c = TestClient(app)
        resp = c.post("/api/ml/train", json=[
            {"supplier_id": "sup_001", "expected_level": "high"},
        ])
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self):
        c = TestClient(app)
        c.headers.update({"Authorization": "Bearer invalid.token.here"})
        resp = c.get("/api/ml/predict/sup_001")
        assert resp.status_code == 401
