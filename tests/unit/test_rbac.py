"""Tests for role-based access control — require_role helper."""
import sys

sys.path.insert(0, "src")

import pytest
from fastapi import HTTPException

from src.api.middleware.rbac import (
    ADMIN_ROLES,
    EDITOR_ROLES,
    VIEWER_ROLES,
    require_role,
)


class TestRequireRoleAdmin:
    """require_role with ADMIN_ROLES = {'admin'}."""

    def test_admin_allowed(self):
        """Admin user passes the admin-only gate."""
        user = {"role": "admin", "org_id": "org_bd_001"}
        # Should not raise — admin is in ADMIN_ROLES
        require_role(user, ADMIN_ROLES)

    def test_editor_rejected(self):
        """Editor cannot perform admin-only actions."""
        user = {"role": "editor"}
        with pytest.raises(HTTPException) as exc_info:
            require_role(user, ADMIN_ROLES)
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail

    def test_viewer_rejected(self):
        """Viewer cannot perform admin-only actions."""
        user = {"role": "viewer"}
        with pytest.raises(HTTPException) as exc_info:
            require_role(user, ADMIN_ROLES)
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail


class TestRequireRoleEditor:
    """require_role with EDITOR_ROLES = {'admin', 'editor'}."""

    def test_admin_allowed(self):
        """Admin inherits editor permissions."""
        user = {"role": "admin"}
        require_role(user, EDITOR_ROLES)

    def test_editor_allowed(self):
        """Editor passes the editor gate."""
        user = {"role": "editor"}
        require_role(user, EDITOR_ROLES)

    def test_viewer_rejected(self):
        """Viewer cannot perform editor-level actions."""
        user = {"role": "viewer"}
        with pytest.raises(HTTPException) as exc_info:
            require_role(user, EDITOR_ROLES)
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail


class TestRequireRoleViewer:
    """require_role with VIEWER_ROLES = {'admin', 'editor', 'viewer'}."""

    def test_admin_allowed(self):
        user = {"role": "admin"}
        require_role(user, VIEWER_ROLES)

    def test_editor_allowed(self):
        user = {"role": "editor"}
        require_role(user, VIEWER_ROLES)

    def test_viewer_allowed(self):
        user = {"role": "viewer"}
        require_role(user, VIEWER_ROLES)


class TestRequireRoleMissingRole:
    """When user dict has no 'role' key, it defaults to 'viewer'."""

    def test_missing_role_defaults_to_viewer_in_viewer_roles(self):
        """No role key — defaults to viewer, which is in VIEWER_ROLES."""
        user = {"org_id": "org_bd_001"}
        require_role(user, VIEWER_ROLES)

    def test_missing_role_defaults_to_viewer_rejected_by_editor_roles(self):
        """No role key — defaults to viewer, which is NOT in EDITOR_ROLES."""
        user = {"org_id": "org_bd_001"}
        with pytest.raises(HTTPException) as exc_info:
            require_role(user, EDITOR_ROLES)
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail

    def test_missing_role_defaults_to_viewer_rejected_by_admin_roles(self):
        """No role key — defaults to viewer, which is NOT in ADMIN_ROLES."""
        user = {"org_id": "org_bd_001"}
        with pytest.raises(HTTPException) as exc_info:
            require_role(user, ADMIN_ROLES)
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail

    def test_empty_role_string_rejected(self):
        """Empty string for role is not in any allowed set."""
        user = {"role": ""}
        with pytest.raises(HTTPException) as exc_info:
            require_role(user, ADMIN_ROLES)
        assert exc_info.value.status_code == 403


class TestRequireRoleUnknownRole:
    """Roles not in any predefined set are rejected."""

    def test_unknown_role_rejected_by_admin_roles(self):
        user = {"role": "superuser"}
        with pytest.raises(HTTPException) as exc_info:
            require_role(user, ADMIN_ROLES)
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail

    def test_unknown_role_rejected_by_editor_roles(self):
        user = {"role": "manager"}
        with pytest.raises(HTTPException) as exc_info:
            require_role(user, EDITOR_ROLES)
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail

    def test_unknown_role_rejected_by_viewer_roles(self):
        user = {"role": "guest"}
        with pytest.raises(HTTPException) as exc_info:
            require_role(user, VIEWER_ROLES)
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail


class TestRequireRoleErrorDetail:
    """Verify the 403 error message is generic (no role/permission leak)."""

    def test_error_detail_is_generic(self):
        user = {"role": "viewer"}
        with pytest.raises(HTTPException) as exc_info:
            require_role(user, ADMIN_ROLES)
        detail = exc_info.value.detail
        assert "Insufficient permissions" in detail

    def test_error_detail_does_not_leak_roles(self):
        user = {"role": "viewer"}
        with pytest.raises(HTTPException) as exc_info:
            require_role(user, ADMIN_ROLES)
        detail = exc_info.value.detail
        assert "viewer" not in detail
        assert "admin" not in detail


class TestRoleSetDefinitions:
    """Verify the role hierarchy invariants."""

    def test_admin_roles_is_subset_of_editor_roles(self):
        assert ADMIN_ROLES.issubset(EDITOR_ROLES)

    def test_editor_roles_is_subset_of_viewer_roles(self):
        assert EDITOR_ROLES.issubset(VIEWER_ROLES)

    def test_admin_roles_contains_only_admin(self):
        assert ADMIN_ROLES == {"admin"}

    def test_viewer_roles_contains_all_three(self):
        assert VIEWER_ROLES == {"admin", "editor", "viewer"}
