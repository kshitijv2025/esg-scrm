# DISCOVERY: FastAPI Router-Level Dependency Override Does Not Override App-Level Dependencies

**Date**: 2026-05-20
**Phase**: C
**Round**: 1 audit
**Type**: DISCOVERY

## Finding

`dependencies=[]` on a FastAPI router or route does NOT override app-level `dependencies=[Depends(require_auth)]` applied at `app.include_router(...)`. FastAPI 0.128.8 aggregates dependencies from all levels — router-level `dependencies=[]` only removes the router's OWN dependencies, not the parent's.

## Technical Detail

```python
# main.py — app-level auth applied to ALL routes including evidence
app.include_router(evidence.router, prefix="/api/evidence", dependencies=[Depends(require_auth)])

# evidence.py — route with empty deps still got 401
@router.get("/auditor/{token}", dependencies=[])
async def auditor_access(token: str, request: Request):
    ...
# Result: 401 — router-level [] does not override app-level [Depends(require_auth)]
```

## Solution

Separate `APIRouter` for auditor endpoints, mounted WITHOUT the global auth dependency:

```python
# evidence.py — separate router for unauthenticated auditor access
auditor_router = APIRouter()

@auditor_router.post("/auditor-link")
async def create_auditor_link(...): ...

@auditor_router.get("/auditor/{token}")
async def auditor_access(token: str, ...): ...

# main.py — mount without global auth
app.include_router(evidence.auditor_router, prefix="/api/evidence")
app.include_router(evidence.router, prefix="/api/evidence", dependencies=[Depends(require_auth)])
```

## Fixes Landed

- `src/api/main.py`: `auditor_router` mounted without `require_auth`
- All other evidence routes stay behind auth via the main `evidence.router`

## Files Changed

- `src/api/main.py`
- `src/api/routes/evidence.py` (auditor_router creation + 3 auditor endpoints moved)

## Related

- Round 1 CRIT/HIGH findings in `04-validate/01-round-1-audit.md`
