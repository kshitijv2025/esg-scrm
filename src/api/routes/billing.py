"""Billing API routes — Stripe subscription management, plan enforcement, webhooks."""

from __future__ import annotations
from typing import Optional

import json
import os
import time
import uuid

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import timezone, datetime

    UTC = timezone.utc

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request

from src.auth.jwt import decode_token
from src.db.database import get_connection, release_connection

router = APIRouter()

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")

# ---------------------------------------------------------------------------
# Plan tier definitions
# ---------------------------------------------------------------------------

PLAN_TIERS = {
    "starter": {
        "name": "Starter",
        "price_cents": 2000,  # $20/month = $240/year
        "suppliers_limit": 50,
        "frameworks_limit": 1,
        "buyer_portal": False,
        "api_access": False,
        "white_label": False,
        "features": ["Basic ESG reporting", "50 suppliers", "1 framework"],
    },
    "professional": {
        "name": "Professional",
        "price_cents": 4000,  # $40/month = $480/year
        "suppliers_limit": 200,
        "frameworks_limit": -1,  # unlimited
        "buyer_portal": True,
        "api_access": False,
        "white_label": False,
        "features": [
            "Full ESG reporting",
            "200 suppliers",
            "All frameworks",
            "Buyer portal",
            "WhatsApp collection",
        ],
    },
    "enterprise": {
        "name": "Enterprise",
        "price_cents": 5000,  # $50/month = $600/year base
        "suppliers_limit": -1,  # unlimited
        "frameworks_limit": -1,
        "buyer_portal": True,
        "api_access": True,
        "white_label": True,
        "features": [
            "Everything in Professional",
            "Unlimited suppliers",
            "API access",
            "White-label",
            "Priority support",
            "Custom integrations",
        ],
    },
}

DEFAULT_TRIAL_DAYS = 14


# ---------------------------------------------------------------------------
# Helper: get auth payload
# ---------------------------------------------------------------------------


def _get_auth_payload(request: Request) -> Optional[dict]:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    return decode_token(token)


def _require_auth(request: Request) -> dict:
    """FastAPI dependency: require valid JWT auth, return payload with org_id."""
    payload = _get_auth_payload(request)
    if not payload:
        raise HTTPException(401, "Valid token required")
    return payload


# ---------------------------------------------------------------------------
# Plan enforcement middleware
# ---------------------------------------------------------------------------


def _check_plan_limit(conn, org_id: str, plan: str, action: str) -> None:
    """Check if org can perform action within plan limits. Raises HTTPException if blocked."""
    if plan not in PLAN_TIERS:
        return  # unknown plan, allow

    tier = PLAN_TIERS[plan]
    limit = tier.get(f"{action}_limit", -1)
    if limit == -1:
        return  # unlimited

    if action == "suppliers":
        count_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM suppliers WHERE org_id = ?",
            (org_id,),
        ).fetchone()
        current = count_row["cnt"] if count_row else 0
        if current >= limit:
            raise HTTPException(
                403,
                f"Plan limit reached: {plan.title()} plan allows {limit} suppliers. "
                f"Upgrade to Enterprise for unlimited.",
            )


def _require_active_subscription(request: Request) -> Optional[dict]:
    """Return subscription for current org, or None if none exists."""
    payload = _get_auth_payload(request)
    if not payload:
        raise HTTPException(401, "Valid token required")

    org_id = payload["org_id"]
    conn = get_connection()
    try:
        sub = conn.execute(
            "SELECT * FROM subscriptions WHERE org_id = ? AND status IN (?, ?, ?) "
            "ORDER BY created_at DESC LIMIT 1",
            (org_id, "active", "trialing", "past_due"),
        ).fetchone()

        if not sub:
            # Check if org is in trial period
            org = conn.execute(
                "SELECT trial_end, plan FROM organizations WHERE id = ?",
                (org_id,),
            ).fetchone()
            if org and org["trial_end"]:
                from datetime import datetime as dt

                trial_end = dt.fromisoformat(org["trial_end"])
                if dt.utcnow() < trial_end:
                    return {
                        "org_id": org_id,
                        "status": "trialing",
                        "plan": org["plan"],
                        "trial_end": org["trial_end"],
                    }
            return None

        result = dict(sub)
        result["org_id"] = org_id
        return result
    finally:
        release_connection(conn)


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------


@router.get("/plans")
def list_plans(request: Request):
    """Return plan tiers with features. Public — no auth required."""
    result = {}
    for pid, tier in PLAN_TIERS.items():
        result[pid] = {
            "id": pid,
            "name": tier["name"],
            "price_cents_monthly": tier["price_cents"],
            "suppliers_limit": tier["suppliers_limit"],
            "frameworks_limit": tier["frameworks_limit"],
            "buyer_portal": tier["buyer_portal"],
            "api_access": tier["api_access"],
            "white_label": tier["white_label"],
            "features": tier["features"],
        }
    return {"plans": result}


@router.get("/my-plan")
def my_plan(request: Request):
    """Return current org's plan and subscription status."""
    payload = _get_auth_payload(request)
    if not payload:
        raise HTTPException(401, "Valid token required")

    org_id = payload["org_id"]
    conn = get_connection()
    try:
        org = conn.execute(
            "SELECT plan, trial_end FROM organizations WHERE id = ?",
            (org_id,),
        ).fetchone()
        if not org:
            raise HTTPException(404, "Organization not found")

        sub = conn.execute(
            "SELECT status, plan_id, current_period_end, trial_end FROM subscriptions "
            "WHERE org_id = ? ORDER BY created_at DESC LIMIT 1",
            (org_id,),
        ).fetchone()

        from datetime import datetime as dt

        in_trial = False
        trial_expired = False
        if org["trial_end"]:
            trial_end = dt.fromisoformat(org["trial_end"])
            in_trial = dt.utcnow() < trial_end
            trial_expired = not in_trial

        return {
            "plan": org["plan"],
            "subscription_status": sub["status"] if sub else ("trialing" if in_trial else "none"),
            "trial_end": org["trial_end"] if in_trial else None,
            "trial_expired": trial_expired,
            "current_period_end": sub["current_period_end"] if sub else None,
        }
    finally:
        release_connection(conn)


@router.post("/subscribe")
async def create_subscription(
    request: Request,
    payload: dict = Depends(_require_auth),
):
    """Create Stripe checkout session for subscription. Returns checkout URL."""
    body = await request.json()
    plan_id = body.get("plan_id", "professional")
    if plan_id not in PLAN_TIERS:
        raise HTTPException(400, f"Invalid plan_id. Must be one of: {list(PLAN_TIERS.keys())}")

    org_id = payload["org_id"]
    conn = get_connection()
    try:
        org = conn.execute(
            "SELECT name, plan FROM organizations WHERE id = ?",
            (org_id,),
        ).fetchone()
        if not org:
            raise HTTPException(404, "Organization not found")

        # Check if already has active subscription
        existing = conn.execute(
            "SELECT id FROM subscriptions WHERE org_id = ? AND status IN (?, ?)",
            (org_id, "active", "trialing"),
        ).fetchone()
        if existing:
            raise HTTPException(409, "Organization already has an active subscription")

        tier = PLAN_TIERS[plan_id]

        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"ESG SCRM {tier['name']} Plan",
                            "description": (
                                f"ESG Supply Chain Risk Management - {tier['name']} tier"
                            ),
                        },
                        "unit_amount": tier["price_cents"],
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                },
            ],
            success_url="https://app.esg-scrm.com/dashboard?subscription=success",
            cancel_url="https://app.esg-scrm.com/pricing?subscription=cancelled",
            metadata={"org_id": org_id, "plan_id": plan_id},
        )

        return {"checkout_url": checkout_session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(400, f"Stripe error: {str(e)}")
    finally:
        release_connection(conn)


@router.post("/portal")
def create_customer_portal(
    sub_info: Optional[dict] = Depends(_require_active_subscription),
):
    """Create Stripe customer portal session for managing subscription."""
    if sub_info is None:
        raise HTTPException(404, "No active subscription found")
    org_id = sub_info["org_id"]
    conn = get_connection()
    try:
        sub = conn.execute(
            "SELECT stripe_customer_id FROM subscriptions WHERE org_id = ? AND status IN (?, ?, ?)",
            (org_id, "active", "trialing", "past_due"),
        ).fetchone()
        if not sub or not sub["stripe_customer_id"]:
            raise HTTPException(404, "No active subscription found")

        session = stripe.billing_portal.Session.create(
            customer=sub["stripe_customer_id"],
            return_url="https://app.esg-scrm.com/dashboard",
        )
        return {"portal_url": session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(400, f"Stripe error: {str(e)}")
    finally:
        release_connection(conn)


# ---------------------------------------------------------------------------
# Stripe Webhook — must use raw body for signature verification
# ---------------------------------------------------------------------------


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events. Uses raw body for signature verification."""
    body = await request.body()
    sig = request.headers.get("stripe-signature", "")
    event = None

    if STRIPE_WEBHOOK_SECRET and STRIPE_WEBHOOK_SECRET.strip():
        try:
            event = stripe.Webhook.construct_event(body, sig, STRIPE_WEBHOOK_SECRET)
        except stripe.error.SignatureVerificationError:
            raise HTTPException(400, "Invalid webhook signature")
    else:
        # Refuse to process unsigned webhooks in non-dev environments.
        # An empty STRIPE_WEBHOOK_SECRET in production means every caller can
        # forge Stripe events — there is no safe fallback.
        environment = os.environ.get("ENVIRONMENT", "development")
        if environment not in ("development", "dev", "test", "local"):
            raise RuntimeError(
                "STRIPE_WEBHOOK_SECRET is not configured. "
                "Refusing to process unsigned webhook events in production. "
                "Set STRIPE_WEBHOOK_SECRET in your production environment."
            )
        # Development mode — parse without verification
        try:
            event = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid JSON")

    conn = get_connection()
    try:
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            org_id = session["metadata"].get("org_id")
            plan_id = session["metadata"].get("plan_id", "professional")
            customer_id = session.get("customer")
            subscription_id = session.get("subscription")

            if org_id and customer_id:
                # Fetch subscription details
                sub_details = None
                if subscription_id:
                    sub_details = stripe.Subscription.retrieve(subscription_id)

                period_start = datetime.fromtimestamp(
                    sub_details["current_period_start"] if sub_details else time.time(),
                    tz=UTC,
                ).isoformat()
                period_end = datetime.fromtimestamp(
                    sub_details["current_period_end"] if sub_details else time.time() + 30 * 86400,
                    tz=UTC,
                ).isoformat()
                trial_end = (
                    datetime.fromtimestamp(sub_details["trial_end"], tz=UTC).isoformat()
                    if sub_details and sub_details.get("trial_end")
                    else None
                )

                # Upsert subscription record
                existing = conn.execute(
                    "SELECT id FROM subscriptions WHERE org_id = ?",
                    (org_id,),
                ).fetchone()

                sub_id = existing["id"] if existing else f"sub_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """INSERT OR REPLACE INTO subscriptions
                    (id, org_id, stripe_customer_id, stripe_subscription_id, plan_id, status,
                     current_period_start, current_period_end, trial_end,
                     cancel_at_period_end, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                    (
                        sub_id,
                        org_id,
                        customer_id,
                        subscription_id or "",
                        plan_id,
                        "active",
                        period_start,
                        period_end,
                        trial_end,
                        0,
                    ),
                )
                conn.commit()

        elif event["type"] == "customer.subscription.updated":
            sub = event["data"]["object"]
            customer_id = sub.get("customer")
            if customer_id:
                stripe_sub_id = sub.get("id")
                status = _stripe_status_to_internal(sub.get("status", ""))
                period_start = datetime.fromtimestamp(
                    sub["current_period_start"], tz=UTC
                ).isoformat()
                period_end = datetime.fromtimestamp(sub["current_period_end"], tz=UTC).isoformat()
                cancel_at = 1 if sub.get("cancel_at_period_end") else 0

                conn.execute(
                    """UPDATE subscriptions SET
                    status = ?, current_period_start = ?, current_period_end = ?,
                    cancel_at_period_end = ?, updated_at = datetime('now')
                    WHERE stripe_subscription_id = ?""",
                    (status, period_start, period_end, cancel_at, stripe_sub_id),
                )
                conn.commit()

        elif event["type"] == "customer.subscription.deleted":
            sub = event["data"]["object"]
            stripe_sub_id = sub.get("id")
            if stripe_sub_id:
                conn.execute(
                    "UPDATE subscriptions SET status = ?, updated_at = datetime('now') "
                    "WHERE stripe_subscription_id = ?",
                    ("cancelled", stripe_sub_id),
                )
                conn.commit()

        elif event["type"] == "invoice.payment_failed":
            invoice = event["data"]["object"]
            customer_id = invoice.get("customer")
            if customer_id:
                conn.execute(
                    "UPDATE subscriptions SET status = ?, updated_at = datetime('now') "
                    "WHERE stripe_customer_id = ? AND status = ?",
                    ("past_due", customer_id, "active"),
                )
                conn.commit()

    except Exception:
        # Log but don't fail Stripe's webhook delivery
        import logging

        logging.getLogger("billing").exception("stripe.webhook.processing_error")
    finally:
        release_connection(conn)

    return {"received": True}


def _stripe_status_to_internal(status: str) -> str:
    """Map Stripe subscription status to internal status."""
    mapping = {
        "trialing": "trialing",
        "active": "active",
        "past_due": "past_due",
        "canceled": "cancelled",
        "unpaid": "unpaid",
        "incomplete": "past_due",
        "incomplete_expired": "unpaid",
    }
    return mapping.get(status, "active")
