---
name: risk-bad-404-returns
description: HTTPException must be raised, not returned as tuple
type: RISK
---

# RISK: `return {"error": "not found"}, 404` silently returns HTTP 200

## What

All 404 "not found" paths in `risk.py` and `suppliers.py` used `return {"error": "not found"}, 404`. FastAPI ignores the tuple second element unless you `raise HTTPException(status_code=404, ...)` — the endpoint returns 200 with `{"error": "not found"}` body. A consumer checking `response.ok` would incorrectly treat "not found" as success.

## Why

FastAPI route handlers treat `return value, status_code` only when the second element is an integer and FastAPI knows how to handle it. For plain dict returns, the tuple form doesn't set the status code — only `raise HTTPException` does.

## How found

Red team `/redteam` — test `test_acknowledge_flag_not_found` and `test_get_supplier_profile_not_found` both asserted 404 but got 200, failing the test.

## Fix

All 404 returns in `risk.py` and `suppliers.py` changed to `raise HTTPException(status_code=404, detail="not found")`.

## Status

Fixed in this session. 13 tests now pass.
