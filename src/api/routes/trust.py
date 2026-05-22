"""
Trust badge verification endpoint — drives TrustBadges component.

Each badge claim is verified against actual data:
  - CSRD Compliant:       CSRD/ESRS framework mappings exist for this org
  - GHG Protocol Source:  GHG Protocol emission factors are in use
  - Audit Ready:          All evidence chain hashes are valid (not tampered)
  - Scope 3 Verified:     Supplier questionnaire responses exist (coverage > 0)
"""

from fastapi import APIRouter, Depends

from src.api.middleware.auth import require_auth
from src.db.database import fetch_trust_badges

router = APIRouter()


@router.get("/badges")
def get_trust_badges(user: dict = Depends(require_auth)):
    """Return data-driven trust badge status for the authenticated org."""
    org_id = user["org_id"]
    badges = fetch_trust_badges(org_id)
    return {"org_id": org_id, "badges": badges}
