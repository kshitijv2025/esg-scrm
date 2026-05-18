---
name: gap-zero-test-coverage
description: Three new route modules shipped without any tests
type: GAP
---

# GAP: Three new route modules shipped with zero test coverage

## What

`risk.py`, `scope3.py`, and `suppliers.py` — all added in prior sessions as part of the Phase 1-3 implementation — had zero pytest tests. The test suite had no coverage for these modules at all.

## Why

No test infrastructure was created alongside the route modules. The bug in the 404 returns (`return {"error": "not found"}, 404`) existed from the first commit and would have been caught by a single line of test.

## Fix

Added `tests/unit/test_risk_routes.py`, `tests/unit/test_scope3_routes.py`, and `tests/unit/test_suppliers_routes.py` with 13 tests covering all endpoints, status codes, and field shapes.

## Status

Fixed in this session. 13 tests pass.
