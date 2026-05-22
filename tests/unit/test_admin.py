"""Tests for admin API — D7.1."""

import hashlib
import sys
import uuid

sys.path.insert(0, "src")

from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.jwt import create_token
from src.db.database import get_connection, release_connection

client = TestClient(app)


def _uid():
    return f"usr_{uuid.uuid4().hex[:8]}"


def _org_id():
    return f"org_{uuid.uuid4().hex[:8]}"


def _admin_headers(org_id: str = None, user_id: str = None, role: str = "admin"):
    token = create_token(
        {
            "sub": user_id or "usr_admin_001",
            "org_id": org_id or "org_admin_test",
            "email": "admin@test.com",
            "role": role,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _create_user(
    conn,
    org_id: str,
    user_id: str = None,
    email: str = None,
    role: str = "viewer",
    is_active: int = 1,
):
    uid = user_id or _uid()
    em = email or f"user_{uid}@test.com"
    # Ensure org exists first (FK constraint on users.org_id -> organizations.id)
    conn.execute(
        "INSERT OR IGNORE INTO organizations (id, name) VALUES (?, ?)",
        (org_id, f"Test Org {org_id}"),
    )
    conn.execute(
        """INSERT OR REPLACE INTO users
           (id, org_id, email, password_hash, full_name, role, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (uid, org_id, em, "$2b$12$dummy", uid[:8], role, is_active),
    )
    conn.commit()
    return uid


def _create_api_key(
    conn,
    org_id: str,
    key_id: str = None,
    name: str = "Test Key",
    user_id: str = None,
):
    kid = key_id or f"key_{uuid.uuid4().hex[:8]}"
    key_hash = hashlib.sha256(b"test_key_xyz").hexdigest()
    conn.execute(
        """INSERT OR REPLACE INTO api_keys
           (id, org_id, user_id, key_hash, name)
           VALUES (?, ?, ?, ?, ?)""",
        (kid, org_id, user_id or "usr_admin_001", key_hash, name),
    )
    conn.commit()
    return kid


class TestListUsers:
    """GET /api/admin/users"""

    def test_admin_lists_users(self):
        """Admin can list all users in org."""
        org_id = _org_id()
        conn = get_connection()
        try:
            _create_user(conn, org_id, "usr_list_001", "alice@test.com", "admin")
            _create_user(conn, org_id, "usr_list_002", "bob@test.com", "viewer")
            conn.commit()
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, "usr_list_001")
        resp = client.get("/api/admin/users", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert len(data["users"]) == 2

    def test_non_admin_gets_403(self):
        """Non-admin cannot list users."""
        org_id = _org_id()
        conn = get_connection()
        try:
            _create_user(conn, org_id, "usr_only_viewer", "viewer@test.com", "viewer")
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, "usr_only_viewer", "viewer")
        resp = client.get("/api/admin/users", headers=headers)

        assert resp.status_code == 403


class TestUpdateUserRole:
    """PUT /api/admin/users/{user_id}/role"""

    def test_admin_updates_role(self):
        """Admin can change a user's role."""
        org_id = _org_id()
        conn = get_connection()
        try:
            admin_id = _create_user(conn, org_id, "usr_role_admin", "admin@test.com", "admin")
            target_id = _create_user(conn, org_id, "usr_role_target", "target@test.com", "viewer")
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, admin_id)
        resp = client.put(
            f"/api/admin/users/{target_id}/role",
            json={"role": "editor"},
            headers=headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Role updated"

        # Verify DB
        conn = get_connection()
        try:
            row = conn.execute("SELECT role FROM users WHERE id = ?", (target_id,)).fetchone()
            assert row["role"] == "editor"
        finally:
            release_connection(conn)

    def test_admin_cannot_set_invalid_role(self):
        """Admin cannot set an invalid role."""
        org_id = _org_id()
        conn = get_connection()
        try:
            admin_id = _create_user(conn, org_id, "usr_invalid_admin", "admin2@test.com", "admin")
            target_id = _create_user(
                conn, org_id, "usr_invalid_target", "target2@test.com", "viewer"
            )
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, admin_id)
        resp = client.put(
            f"/api/admin/users/{target_id}/role",
            json={"role": "superadmin"},
            headers=headers,
        )

        assert resp.status_code == 400

    def test_non_admin_cannot_update_role(self):
        """Non-admin cannot update user role."""
        org_id = _org_id()
        conn = get_connection()
        try:
            admin_id = _create_user(conn, org_id, "usr_not_admin", "notadmin@test.com", "editor")
            target_id = _create_user(conn, org_id, "usr_cannot_update", "cannot@test.com", "viewer")
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, admin_id, "editor")
        resp = client.put(
            f"/api/admin/users/{target_id}/role",
            json={"role": "admin"},
            headers=headers,
        )

        assert resp.status_code == 403


class TestDeactivateUser:
    """DELETE /api/admin/users/{user_id}"""

    def test_admin_deactivates_user(self):
        """Admin can deactivate a user."""
        org_id = _org_id()
        conn = get_connection()
        try:
            admin_id = _create_user(conn, org_id, "usr_deact_admin", "dadmin@test.com", "admin")
            target_id = _create_user(conn, org_id, "usr_deact_target", "dtarget@test.com", "viewer")
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, admin_id)
        resp = client.delete(f"/api/admin/users/{target_id}", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "User deactivated"

        # Verify DB
        conn = get_connection()
        try:
            row = conn.execute("SELECT is_active FROM users WHERE id = ?", (target_id,)).fetchone()
            assert row["is_active"] == 0
        finally:
            release_connection(conn)

    def test_cannot_deactivate_self(self):
        """Admin cannot deactivate their own account."""
        org_id = _org_id()
        conn = get_connection()
        try:
            admin_id = _create_user(conn, org_id, "usr_no_self", "noself@test.com", "admin")
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, admin_id)
        resp = client.delete(f"/api/admin/users/{admin_id}", headers=headers)

        assert resp.status_code == 400

    def test_non_admin_cannot_deactivate(self):
        """Non-admin cannot deactivate users."""
        org_id = _org_id()
        conn = get_connection()
        try:
            admin_id = _create_user(conn, org_id, "usr_editor_user", "editor@test.com", "editor")
            target_id = _create_user(conn, org_id, "usr_viewer_user", "viewer@test.com", "viewer")
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, admin_id, "editor")
        resp = client.delete(f"/api/admin/users/{target_id}", headers=headers)

        assert resp.status_code == 403


class TestOrganizationSettings:
    """PUT /api/admin/org"""

    def test_admin_updates_org(self):
        """Admin can update organization settings."""
        org_id = _org_id()
        conn = get_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO organizations (id, name, industry, country) VALUES (?, ?, ?, ?)",
                (org_id, "Old Name", "Old Industry", "BD"),
            )
            admin_id = _create_user(conn, org_id, "usr_org_admin", "orgadmin@test.com", "admin")
            conn.commit()
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, admin_id)
        resp = client.put(
            "/api/admin/org",
            json={"name": "New Name", "industry": "Textile", "country": "Bangladesh"},
            headers=headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Organization updated"

        # Verify DB
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT name, industry, country FROM organizations WHERE id = ?", (org_id,)
            ).fetchone()
            assert row["name"] == "New Name"
            assert row["industry"] == "Textile"
            assert row["country"] == "Bangladesh"
        finally:
            release_connection(conn)

    def test_non_admin_cannot_update_org(self):
        """Non-admin cannot update org settings."""
        org_id = _org_id()
        conn = get_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO organizations (id, name) VALUES (?, ?)",
                (org_id, "Test Org"),
            )
            _create_user(conn, org_id, "usr_no_edit", "noedit@test.com", "viewer")
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, "usr_no_edit", "viewer")
        resp = client.put(
            "/api/admin/org",
            json={"name": "Hacked"},
            headers=headers,
        )

        assert resp.status_code == 403


class TestAPIKeys:
    """GET /api/admin/api-keys, POST /api/admin/api-keys, DELETE /api/admin/api-keys/{key_id}"""

    def test_list_api_keys(self):
        """Admin can list API keys (masked)."""
        org_id = _org_id()
        conn = get_connection()
        try:
            _create_user(conn, org_id, "usr_key_admin", "keyadmin@test.com", "admin")
            _create_api_key(conn, org_id, "key_list_001", "Production Key", "usr_key_admin")
            _create_api_key(conn, org_id, "key_list_002", "Dev Key", "usr_key_admin")
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, "usr_key_admin")
        resp = client.get("/api/admin/api-keys", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert "keys" in data
        assert len(data["keys"]) == 2
        # Key is masked (raw key never returned)
        for key_entry in data["keys"]:
            assert "..." in key_entry["key"]
            # Verify raw key is not present (masked with "..." only)
            # The raw key has format esg_XXXXXXXX... (43 more chars after esg_)
            # Masked key should be prefix + "...", no other characters after prefix
            assert key_entry["key"].endswith("..."), f"Key should be masked: {key_entry['key']}"

    def test_create_api_key(self):
        """Admin can create a new API key; raw key returned once."""
        org_id = _org_id()
        conn = get_connection()
        try:
            _create_user(conn, org_id, "usr_create_key", "createkey@test.com", "admin")
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, "usr_create_key")
        resp = client.post(
            "/api/admin/api-keys",
            json={"name": "My New Key"},
            headers=headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "key" in data
        # Raw key starts with esg_ and is 50+ chars
        assert data["key"].startswith("esg_")
        assert len(data["key"]) >= 40

        # Verify hash stored in DB
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT key_hash FROM api_keys WHERE id = ?", (data["id"],)
            ).fetchone()
            assert row is not None
            # Hash should be hex string (64 chars for sha256)
            assert len(row["key_hash"]) == 64
        finally:
            release_connection(conn)

    def test_revoke_api_key(self):
        """Admin can revoke an API key."""
        org_id = _org_id()
        conn = get_connection()
        try:
            _create_user(conn, org_id, "usr_revoke_key", "revokekey@test.com", "admin")
            _create_api_key(conn, org_id, "key_revoke_001", "Revoke Me", "usr_revoke_key")
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, "usr_revoke_key")
        resp = client.delete("/api/admin/api-keys/key_revoke_001", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "API key revoked"

        # Verify deleted
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT id FROM api_keys WHERE id = ?", ("key_revoke_001",)
            ).fetchone()
            assert row is None
        finally:
            release_connection(conn)

    def test_non_admin_cannot_manage_keys(self):
        """Non-admin cannot create or delete API keys."""
        org_id = _org_id()
        conn = get_connection()
        try:
            _create_user(conn, org_id, "usr_key_viewer", "keyviewer@test.com", "viewer")
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, "usr_key_viewer", "viewer")

        resp = client.post("/api/admin/api-keys", json={"name": "Bad"}, headers=headers)
        assert resp.status_code == 403

        resp = client.delete("/api/admin/api-keys/some_key_id", headers=headers)
        assert resp.status_code == 403


class TestAuditLog:
    """GET /api/admin/audit-log"""

    def test_admin_lists_audit_log(self):
        """Admin can query paginated audit log."""
        org_id = _org_id()
        conn = get_connection()
        try:
            admin_id = _create_user(conn, org_id, "usr_audit_admin", "auditadmin@test.com", "admin")
            conn.execute(
                """INSERT INTO audit_log
                   (org_id, user_id, action, resource_type, resource_id, details)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    org_id,
                    admin_id,
                    "role_change",
                    "user",
                    admin_id,
                    "Changed role from editor to admin",
                ),
            )
            conn.execute(
                """INSERT INTO audit_log
                   (org_id, user_id, action, resource_type, resource_id, details)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (org_id, admin_id, "org_update", "organization", org_id, "Updated org settings"),
            )
            conn.commit()
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, admin_id)
        resp = client.get("/api/admin/audit-log", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data
        assert "total" in data
        assert len(data["logs"]) == 2

    def test_audit_log_pagination(self):
        """Audit log supports pagination parameters."""
        org_id = _org_id()
        conn = get_connection()
        try:
            admin_id = _create_user(conn, org_id, "usr_page_admin", "pageadmin@test.com", "admin")
            for i in range(15):
                conn.execute(
                    """INSERT INTO audit_log
                       (org_id, user_id, action, resource_type, resource_id, details)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (org_id, admin_id, f"action_{i}", "test", f"res_{i}", f"detail {i}"),
                )
            conn.commit()
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, admin_id)
        resp = client.get("/api/admin/audit-log?page=1&page_size=5", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 15
        assert len(data["logs"]) == 5
        assert data["page"] == 1
        assert data["page_size"] == 5

    def test_audit_log_filter_by_action(self):
        """Audit log can be filtered by action type."""
        org_id = _org_id()
        conn = get_connection()
        try:
            admin_id = _create_user(
                conn, org_id, "usr_filter_admin", "filteradmin@test.com", "admin"
            )
            conn.execute(
                """INSERT INTO audit_log
                   (org_id, user_id, action, resource_type, resource_id, details)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (org_id, admin_id, "role_change", "user", "u1", "role changed"),
            )
            conn.execute(
                """INSERT INTO audit_log
                   (org_id, user_id, action, resource_type, resource_id, details)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (org_id, admin_id, "org_update", "org", org_id, "org updated"),
            )
            conn.commit()
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, admin_id)
        resp = client.get("/api/admin/audit-log?action=role_change", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["logs"][0]["action"] == "role_change"

    def test_non_admin_cannot_view_audit_log(self):
        """Non-admin cannot view audit log."""
        org_id = _org_id()
        conn = get_connection()
        try:
            _create_user(conn, org_id, "usr_no_audit", "noaudit@test.com", "editor")
        finally:
            release_connection(conn)

        headers = _admin_headers(org_id, "usr_no_audit", "editor")
        resp = client.get("/api/admin/audit-log", headers=headers)

        assert resp.status_code == 403
