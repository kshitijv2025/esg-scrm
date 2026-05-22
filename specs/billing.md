# Billing Specification

## Overview

Stripe-powered subscription management with three plan tiers. All billing endpoints require authentication except `GET /plans`. Plan enforcement middleware blocks supplier creation when a plan's supplier limit is reached.

## Plan Tiers

Implemented at `src/api/routes/billing.py:28-72` (`PLAN_TIERS` dict).

| Tier         | ID             | Price (cents/mo) | Suppliers | Frameworks | Buyer Portal | API Access | White Label |
| ------------ | -------------- | ---------------- | --------- | ---------- | ------------ | ---------- | ----------- |
| Starter      | `starter`      | 2000 ($20)       | 50        | 1          | No           | No         | No          |
| Professional | `professional` | 4000 ($40)       | 200       | unlimited  | Yes          | No         | No          |
| Enterprise   | `enterprise`   | 5000 ($50)       | unlimited | unlimited  | Yes          | Yes        | Yes         |

Supplier limit enforcement: `src/api/routes/billing.py:95-116` (`_check_plan_limit`).

## Endpoints

### `GET /api/billing/plans`

**Auth**: None (public).

**Response** (200):

```json
{
  "plans": {
    "starter": {
      "id": "starter",
      "name": "Starter",
      "price_cents_monthly": 2000,
      "suppliers_limit": 50,
      "frameworks_limit": 1,
      "buyer_portal": false,
      "api_access": false,
      "white_label": false,
      "features": ["Basic ESG reporting", "50 suppliers", "1 framework"]
    }
  }
}
```

---

### `GET /api/billing/my-plan`

**Auth**: Required.

**Response** (200):

```json
{
  "plan": "professional",
  "subscription_status": "active",
  "trial_end": null,
  "trial_expired": false,
  "current_period_end": "2026-06-21T00:00:00Z"
}
```

`subscription_status` values: `active`, `trialing`, `past_due`, `none`. Implemented at `src/api/routes/billing.py:184-224`.

---

### `POST /api/billing/subscribe`

**Auth**: Required.

**Request**:

```json
{ "plan_id": "professional" }
```

**Response** (200):

```json
{ "checkout_url": "https://checkout.stripe.com/..." }
```

**Errors**:

- 400: `Invalid plan_id. Must be one of: ['starter', 'professional', 'enterprise']`
- 401: `Valid token required`
- 409: `Organization already has an active subscription`

Implemented at `src/api/routes/billing.py:227-286`. Creates a Stripe Checkout Session with `mode="subscription"` and `metadata={org_id, plan_id}`.

---

### `POST /api/billing/portal`

**Auth**: Required.

**Response** (200):

```json
{ "portal_url": "https://billing.stripe.com/..." }
```

**Errors**:

- 401: `Valid token required`
- 404: `No active subscription found`

Implemented at `src/api/routes/billing.py:289-314`. Creates a Stripe Customer Portal session for subscription management.

---

### `POST /api/billing/webhook`

**Auth**: Stripe signature verification (or development bypass when `STRIPE_WEBHOOK_SECRET` is empty).

**Handled events** at `src/api/routes/billing.py:322-448`:

| Event                           | Effect                                                                                                                         |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `checkout.session.completed`    | Upsert `subscriptions` row with status=`active`, store `stripe_customer_id`, `stripe_subscription_id`, `plan_id`, period dates |
| `customer.subscription.updated` | Update `subscriptions.status`, `current_period_start`, `current_period_end`, `cancel_at_period_end`                            |
| `customer.subscription.deleted` | Set `subscriptions.status` = `cancelled`                                                                                       |
| `invoice.payment_failed`        | Set `subscriptions.status` = `past_due`                                                                                        |

Webhook signature verification at line 331: `stripe.Webhook.construct_event(body, sig, STRIPE_WEBHOOK_SECRET)`. Development mode (no secret configured) parses JSON directly.

## Plan Enforcement Middleware

`_require_active_subscription(request)` at `src/api/routes/billing.py:119-157` checks:

1. Row in `subscriptions` table with `status IN ('active', 'trialing', 'past_due')` for the org.
2. Falls back to `organizations.trial_end` for trialing orgs.

`_check_plan_limit(conn, org_id, plan, action)` at `src/api/routes/billing.py:95-116`:

- Counts current rows in `suppliers` table for the org.
- Raises HTTP 403 with upgrade message when limit is reached.

## Security Measures

- Stripe signature verification on webhook (`stripe.Webhook.construct_event`) — prevents spoofed events.
- `STRIPE_WEBHOOK_SECRET` env var required for production; development mode bypasses verification.
- No auth token exposed in webhook response.
- Stripe error handling returns 400 with sanitized message.

## Data Model

`subscriptions` table columns used by billing: `id`, `org_id`, `stripe_customer_id`, `stripe_subscription_id`, `plan_id`, `status`, `current_period_start`, `current_period_end`, `trial_end`, `cancel_at_period_end`, `updated_at`.
