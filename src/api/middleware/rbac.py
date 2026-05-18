"""Role-based access control helpers."""
from fastapi import HTTPException

ADMIN_ROLES = {"admin"}
EDITOR_ROLES = {"admin", "editor"}
VIEWER_ROLES = {"admin", "editor", "viewer"}


def require_role(user: dict, allowed_roles: set) -> None:
    """Raise 403 if user's role is not in the allowed set."""
    role = user.get("role", "viewer")
    if role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions for this action",
        )
