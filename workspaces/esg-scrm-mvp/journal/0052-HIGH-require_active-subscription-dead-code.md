# HIGH: `_require_active_subscription` dead code — FIXED

**Type**: GAP — spec compliance
**Discovered**: 2026-05-21 redteam Round 1
**Fixed**: 2026-05-21 (same session)

## Finding

`specs/billing.md` § "Plan Enforcement Middleware" documents `_require_active_subscription` at `billing.py:119` as the subscription enforcement dependency.

Function was defined but never called — routes performed equivalent inline checks.

## Fix

- Added `_require_auth` as a separate FastAPI dependency for auth-only validation
- Changed `_require_active_subscription` to return `Optional[dict]` (None instead of raising 403)
- Wired `_require_active_subscription` as `Depends()` on `create_customer_portal` — returns 404 when None
- `create_subscription` keeps inline subscription check (required after body parsing for plan validation order)
- `create_customer_portal` uses the dependency (no pre-body checks needed)

## Verification

```bash
$ grep -rn '_require_active_subscription' src/api/routes/billing.py
src/api/routes/billing.py:127:def _require_active_subscription(request: Request) -> Optional[dict]:
src/api/routes/billing.py:162:    sub_info: Optional[dict] = Depends(_require_active_subscription),
$ .venv/bin/python -m pytest tests/unit/test_billing_routes.py -q
26 passed
```
