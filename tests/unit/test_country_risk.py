"""D6.11: Country risk score tests — verify database-backed risk predictor."""
import pytest

from src.ml.risk_predictor import _get_country_risk, _load_country_risk_from_db


@pytest.fixture(autouse=True)
def _reset_cache():
    """Clear the country risk cache before each test."""
    from src.ml import risk_predictor
    risk_predictor._COUNTRY_RISK_CACHE_LOADED = False
    risk_predictor._COUNTRY_RISK_CACHE = {}
    yield


# ---------------------------------------------------------------------------
# Unit tests — _get_country_risk
# ---------------------------------------------------------------------------

class TestGetCountryRisk:
    def test_unknown_country_defaults_to_highest(self):
        """Unknown country should default to 15.0 (highest risk)."""
        score = _get_country_risk("ZZ")  # Unknown country
        assert score == 15.0

    def test_unknown_country_not_in_dict(self):
        """Unknown country does not appear in the cache."""
        score = _get_country_risk("UNKNOWN_CODE")
        assert score == 15.0
        from src.ml import risk_predictor
        assert "UNKNOWN_CODE" not in risk_predictor._COUNTRY_RISK_CACHE

    def test_known_country_bd(self):
        """Known country Bangladesh returns 10.0."""
        score = _get_country_risk("BD")
        assert score == 10.0

    def test_known_country_in(self):
        """Known country India returns 5.0."""
        score = _get_country_risk("IN")
        assert score == 5.0

    def test_known_country_vn(self):
        """Known country Vietnam returns 8.0."""
        score = _get_country_risk("VN")
        assert score == 8.0

    def test_known_country_mm_highest(self):
        """Myanmar returns 15.0 (highest risk)."""
        score = _get_country_risk("MM")
        assert score == 15.0

    def test_load_from_db_returns_dict(self):
        """_load_country_risk_from_db returns a dict."""
        data = _load_country_risk_from_db()
        assert isinstance(data, dict)
        assert len(data) >= 10  # Seeded with 10+ countries
        assert data["BD"] == 10.0
        assert data["MM"] == 15.0


class TestCountryRiskCache:
    def test_cache_is_loaded(self):
        """Cache is populated after first call."""
        from src.ml import risk_predictor
        risk_predictor._COUNTRY_RISK_CACHE = {}
        risk_predictor._COUNTRY_RISK_CACHE_LOADED = False

        _get_country_risk("BD")
        assert risk_predictor._COUNTRY_RISK_CACHE_LOADED is True
        assert "BD" in risk_predictor._COUNTRY_RISK_CACHE

    def test_cache_is_reused(self):
        """Subsequent calls reuse the cache without DB hit."""
        from src.ml import risk_predictor
        risk_predictor._COUNTRY_RISK_CACHE = {"TEST": 7.0}
        risk_predictor._COUNTRY_RISK_CACHE_LOADED = True

        score = _get_country_risk("TEST")
        assert score == 7.0


# ---------------------------------------------------------------------------
# Integration test — API endpoint
# ---------------------------------------------------------------------------

class TestCountryRiskAPI:
    def test_country_risk_endpoint_requires_auth(self):
        """GET /api/risk/country-risk returns 401 without auth."""
        from fastapi.testclient import TestClient

        from src.api.main import app
        client = TestClient(app)
        resp = client.get("/api/risk/country-risk")
        assert resp.status_code == 401

    def test_country_risk_endpoint_returns_scores(self):
        """GET /api/risk/country-risk returns a list of scores."""
        from fastapi.testclient import TestClient

        from src.api.main import app
        from src.auth.jwt import create_token
        client = TestClient(app)
        token = create_token({
            "sub": "usr_test_001",
            "org_id": "org_bd_001",
            "email": "test@test.com",
            "role": "viewer",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/risk/country-risk", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "countries" in data
        assert "total" in data
        assert data["total"] >= 10
        codes = {c["country_code"] for c in data["countries"]}
        assert "BD" in codes
        assert "MM" in codes

    def test_country_risk_endpoint_viewer_role(self):
        """Viewer role can access country-risk endpoint."""
        from fastapi.testclient import TestClient

        from src.api.main import app
        from src.auth.jwt import create_token
        client = TestClient(app)
        token = create_token({
            "sub": "usr_viewer_001",
            "org_id": "org_bd_001",
            "email": "viewer@test.com",
            "role": "viewer",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/risk/country-risk", headers=headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Org isolation
# ---------------------------------------------------------------------------

class TestCountryRiskOrgIsolation:
    def test_country_risk_same_for_all_orgs(self):
        """Country risk scores are org-agnostic (same DB table for all orgs)."""
        from fastapi.testclient import TestClient

        from src.api.main import app
        from src.auth.jwt import create_token
        client = TestClient(app)

        for org_id in ["org_bd_001", "org_other_001"]:
            token = create_token({
                "sub": f"usr_{org_id}",
                "org_id": org_id,
                "email": f"test@{org_id}.com",
                "role": "viewer",
            })
            headers = {"Authorization": f"Bearer {token}"}
            resp = client.get("/api/risk/country-risk", headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            # Same country codes available regardless of org
            codes = {c["country_code"] for c in data["countries"]}
            assert "BD" in codes
            assert "MM" in codes
            # Scores are identical
            bd_score = next(c["risk_score"] for c in data["countries"] if c["country_code"] == "BD")
            assert bd_score == 10.0
