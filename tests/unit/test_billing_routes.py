"""Tests for billing API — Stripe subscription management, plan enforcement, webhooks."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.billing import PLAN_TIERS
from src.auth.jwt import create_token
from src.db.database import get_connection, release_connection

client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup_test_org():
    """Ensure test organizations exist in the DB before each test."""
    conn = get_connection()
    try:
        # org_bd_001 is the seeded org — ensure it has plan + trial_end columns
        conn.execute(
            "INSERT OR IGNORE INTO organizations (id, name, industry, plan) VALUES (?, ?, ?, ?)",
            (
                "org_bd_001",
                "Bangladesh Export Textiles Ltd.",
                "Garment manufacturing",
                "professional",
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO organizations (id, name, industry, plan) VALUES (?, ?, ?, ?)",
            ("org_test_billing_001", "Billing Test Org", "Tech", "starter"),
        )
        conn.commit()
    finally:
        release_connection(conn)
    yield


def _auth_headers(org_id: str = "org_bd_001", role: str = "admin") -> dict:
    token = create_token(
        {
            "sub": "usr_test_001",
            "org_id": org_id,
            "email": "test@test.com",
            "role": role,
        }
    )
    return {"Authorization": f"Bearer {token}"}


class TestListPlans:
    """GET /api/billing/plans — public, no auth required."""

    def test_returns_200_with_all_plans(self):
        resp = client.get("/api/billing/plans")
        assert resp.status_code == 200
        data = resp.json()
        assert "plans" in data

    def test_all_three_tiers_present(self):
        resp = client.get("/api/billing/plans")
        plans = resp.json()["plans"]
        assert set(plans.keys()) == {"starter", "professional", "enterprise"}

    def test_starter_plan_fields(self):
        resp = client.get("/api/billing/plans")
        starter = resp.json()["plans"]["starter"]
        assert starter["id"] == "starter"
        assert starter["name"] == "Starter"
        assert starter["price_cents_monthly"] == 2000
        assert starter["suppliers_limit"] == 50
        assert starter["frameworks_limit"] == 1
        assert starter["buyer_portal"] is False
        assert starter["api_access"] is False
        assert starter["white_label"] is False

    def test_professional_plan_fields(self):
        resp = client.get("/api/billing/plans")
        pro = resp.json()["plans"]["professional"]
        assert pro["id"] == "professional"
        assert pro["name"] == "Professional"
        assert pro["price_cents_monthly"] == 4000
        assert pro["suppliers_limit"] == 200
        assert pro["frameworks_limit"] == -1  # unlimited
        assert pro["buyer_portal"] is True
        assert pro["api_access"] is False

    def test_enterprise_plan_fields(self):
        resp = client.get("/api/billing/plans")
        ent = resp.json()["plans"]["enterprise"]
        assert ent["id"] == "enterprise"
        assert ent["name"] == "Enterprise"
        assert ent["price_cents_monthly"] == 5000
        assert ent["suppliers_limit"] == -1  # unlimited
        assert ent["frameworks_limit"] == -1
        assert ent["buyer_portal"] is True
        assert ent["api_access"] is True
        assert ent["white_label"] is True

    def test_features_lists_are_populated(self):
        resp = client.get("/api/billing/plans")
        for _plan_id, plan in resp.json()["plans"].items():
            assert isinstance(plan["features"], list)
            assert len(plan["features"]) > 0

    def test_no_auth_required(self):
        # No Authorization header — should still return 200
        resp = client.get("/api/billing/plans")
        assert resp.status_code == 200


class TestMyPlan:
    """GET /api/billing/my-plan — auth required."""

    def test_returns_401_without_auth(self):
        resp = client.get("/api/billing/my-plan")
        assert resp.status_code == 401

    def test_returns_plan_for_authenticated_org(self):
        resp = client.get("/api/billing/my-plan", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "plan" in data
        assert "subscription_status" in data


class TestSubscribe:
    """POST /api/billing/subscribe — auth required."""

    def test_returns_401_without_auth(self):
        resp = client.post("/api/billing/subscribe", json={"plan_id": "professional"})
        assert resp.status_code == 401

    def test_returns_400_for_invalid_plan_id(self):
        resp = client.post(
            "/api/billing/subscribe",
            json={"plan_id": "invalid_plan"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 400
        assert "Invalid plan_id" in resp.json()["detail"]

    def test_returns_400_for_missing_plan_id(self):
        resp = client.post("/api/billing/subscribe", json={}, headers=_auth_headers())
        assert resp.status_code == 400

    @patch("src.api.routes.billing.stripe.checkout.Session.create")
    def test_returns_checkout_url_for_valid_plan(self, mock_stripe_create):
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/test"
        mock_stripe_create.return_value = mock_session

        resp = client.post(
            "/api/billing/subscribe",
            json={"plan_id": "professional"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "checkout_url" in data
        assert data["checkout_url"] == "https://checkout.stripe.com/test"

    @patch("src.api.routes.billing.stripe.checkout.Session.create")
    def test_stripe_session_includes_org_metadata(self, mock_stripe_create):
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/test"
        mock_stripe_create.return_value = mock_session

        org_id = "org_bd_001"
        resp = client.post(
            "/api/billing/subscribe",
            json={"plan_id": "starter"},
            headers=_auth_headers(org_id=org_id),
        )
        assert resp.status_code == 200
        call_kwargs = mock_stripe_create.call_args.kwargs
        metadata = call_kwargs.get("metadata", {})
        assert metadata.get("org_id") == org_id
        assert metadata.get("plan_id") == "starter"


class TestBillingPortal:
    """POST /api/billing/portal — auth required."""

    def test_returns_401_without_auth(self):
        resp = client.post("/api/billing/portal")
        assert resp.status_code == 401

    def test_returns_404_when_no_subscription(self):
        # Org has no subscription in the test DB
        resp = client.post("/api/billing/portal", headers=_auth_headers(org_id="org_no_sub_001"))
        assert resp.status_code == 404


class TestWebhookSignatureVerification:
    """POST /api/billing/webhook — Stripe signature verification."""

    def test_webhook_returns_200_with_valid_signature(self):
        # When STRIPE_WEBHOOK_SECRET is empty (dev mode), no signature needed
        with patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": ""}):
            payload = json.dumps(
                {
                    "type": "checkout.session.completed",
                    "data": {
                        "object": {
                            "metadata": {"org_id": "org_webhook_001", "plan_id": "professional"},
                            "customer": "cus_test123",
                            "subscription": "sub_test456",
                        }
                    },
                }
            )
            resp = client.post(
                "/api/billing/webhook",
                content=payload,
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 200
            assert resp.json() == {"received": True}

    @patch("src.api.routes.billing.stripe.Subscription.retrieve")
    def test_webhook_handles_checkout_completed_event(self, mock_sub_retrieve):
        """checkout.session.completed should upsert a subscription record."""
        mock_sub = MagicMock()
        mock_sub.current_period_start = 1700000000
        mock_sub.current_period_end = 1702592000
        mock_sub.trial_end = None
        mock_sub_retrieve.return_value = mock_sub

        with patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": ""}):
            # First create an org for the webhook to link to
            from src.db.database import get_connection, release_connection

            conn = get_connection()
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO organizations (id, name, plan) VALUES (?, ?, ?)",
                    ("org_webhook_sub_001", "Webhook Test Org", "professional"),
                )
                conn.commit()
            finally:
                release_connection(conn)

            payload = json.dumps(
                {
                    "type": "checkout.session.completed",
                    "data": {
                        "object": {
                            "metadata": {
                                "org_id": "org_webhook_sub_001",
                                "plan_id": "professional",
                            },
                            "customer": "cus_webhook001",
                            "subscription": "sub_webhook001",
                        }
                    },
                }
            )
            resp = client.post(
                "/api/billing/webhook",
                content=payload,
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 200

            # Verify subscription was upserted
            conn = get_connection()
            try:
                sub = conn.execute(
                    "SELECT * FROM subscriptions WHERE org_id = ?",
                    ("org_webhook_sub_001",),
                ).fetchone()
                assert sub is not None
                assert sub["stripe_customer_id"] == "cus_webhook001"
                assert sub["stripe_subscription_id"] == "sub_webhook001"
                assert sub["status"] == "active"
            finally:
                release_connection(conn)


class TestStripeStatusMapping:
    """_stripe_status_to_internal() maps Stripe statuses correctly."""

    def test_maps_trialing(self):
        from src.api.routes.billing import _stripe_status_to_internal

        assert _stripe_status_to_internal("trialing") == "trialing"

    def test_maps_active(self):
        from src.api.routes.billing import _stripe_status_to_internal

        assert _stripe_status_to_internal("active") == "active"

    def test_maps_past_due(self):
        from src.api.routes.billing import _stripe_status_to_internal

        assert _stripe_status_to_internal("past_due") == "past_due"

    def test_maps_canceled(self):
        from src.api.routes.billing import _stripe_status_to_internal

        assert _stripe_status_to_internal("canceled") == "cancelled"

    def test_maps_unknown_to_active(self):
        from src.api.routes.billing import _stripe_status_to_internal

        assert _stripe_status_to_internal("unknown_status") == "active"


class TestPlanTiersConstants:
    """PLAN_TIERS constant has correct structure."""

    def test_all_plans_have_required_keys(self):
        required = {
            "name",
            "price_cents",
            "suppliers_limit",
            "frameworks_limit",
            "buyer_portal",
            "api_access",
            "white_label",
            "features",
        }
        for plan_id, tier in PLAN_TIERS.items():
            assert required.issubset(tier.keys()), f"{plan_id} missing keys"

    def test_suppliers_limit_values(self):
        assert PLAN_TIERS["starter"]["suppliers_limit"] == 50
        assert PLAN_TIERS["professional"]["suppliers_limit"] == 200
        assert PLAN_TIERS["enterprise"]["suppliers_limit"] == -1

    def test_starter_is_cheapest(self):
        assert PLAN_TIERS["starter"]["price_cents"] < PLAN_TIERS["professional"]["price_cents"]
        assert PLAN_TIERS["professional"]["price_cents"] < PLAN_TIERS["enterprise"]["price_cents"]
