"""
Tests for corrective actions API endpoints.
Covers CRUD operations, org isolation, RBAC, and escalation.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.db.database import get_connection, release_connection, reset_database


@pytest.fixture(autouse=True)
def _fresh_db():
    """Reset and seed database before each test."""
    reset_database()
    from src.db.seed import seed

    seed()


@pytest.fixture
def admin_client():
    """Admin user client."""
    from src.auth.jwt import create_token

    token = create_token(
        {
            "sub": "usr_admin_001",
            "org_id": "org_bd_001",
            "email": "admin@textilebd.com",
            "role": "admin",
        }
    )
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


@pytest.fixture
def editor_client():
    """Editor user client."""
    from src.auth.jwt import create_token

    token = create_token(
        {
            "sub": "usr_editor_001",
            "org_id": "org_bd_001",
            "email": "editor@textilebd.com",
            "role": "editor",
        }
    )
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


@pytest.fixture
def viewer_client():
    """Viewer user client."""
    from src.auth.jwt import create_token

    token = create_token(
        {
            "sub": "usr_viewer_001",
            "org_id": "org_bd_001",
            "email": "viewer@textilebd.com",
            "role": "viewer",
        }
    )
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


@pytest.fixture
def other_org_client():
    """Client for a different org (for isolation tests)."""
    from src.auth.jwt import create_token

    token = create_token(
        {
            "sub": "usr_other_001",
            "org_id": "org_other_001",
            "email": "other@other.com",
            "role": "admin",
        }
    )
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


@pytest.fixture
def _seed_risk_flag():
    """Seed a risk flag to link a corrective action to."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO risk_flags
               (id, org_id, factory_id, flag_text, cluster, severity, days_overdue, priority_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "flag_test_001",
                "org_bd_001",
                "factory_bd_001",
                "Test risk flag for escalation",
                "G2",
                "WARNING",
                5,
                15.0,
            ),
        )
        conn.commit()
    finally:
        release_connection(conn)


# --- List actions ---


class TestListCorrectiveActions:
    def test_list_empty(self, admin_client):
        """Returns empty list when no actions exist."""
        resp = admin_client.get("/api/corrective-actions")
        assert resp.status_code == 200
        data = resp.json()
        assert "actions" in data
        assert data["actions"] == []
        assert data["total"] == 0

    def test_list_returns_actions(self, admin_client, editor_client, _seed_risk_flag):
        """Returns corrective actions for the org."""
        # Create an action as editor
        resp = editor_client.post(
            "/api/corrective-actions",
            json={
                "title": "Fix the issue",
                "description": "Root cause analysis required",
                "flag_id": "flag_test_001",
                "priority": "high",
                "status": "open",
                "deadline": "2026-12-31",
            },
        )
        assert resp.status_code == 200

        # List as admin
        resp = admin_client.get("/api/corrective-actions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["actions"]) == 1
        assert data["actions"][0]["title"] == "Fix the issue"
        assert data["actions"][0]["status"] == "open"

    def test_list_filter_by_status(self, admin_client, editor_client, _seed_risk_flag):
        """Status filter returns only matching actions."""
        editor_client.post(
            "/api/corrective-actions",
            json={"title": "Action 1", "flag_id": "flag_test_001", "status": "open"},
        )
        editor_client.post(
            "/api/corrective-actions",
            json={"title": "Action 2", "flag_id": "flag_test_001", "status": "completed"},
        )

        resp = admin_client.get("/api/corrective-actions?status=open")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["actions"][0]["title"] == "Action 1"

    def test_list_org_isolation(
        self, admin_client, other_org_client, editor_client, _seed_risk_flag
    ):
        """Each org only sees its own actions."""
        editor_client.post(
            "/api/corrective-actions",
            json={"title": "My org action", "flag_id": "flag_test_001"},
        )

        resp = other_org_client.get("/api/corrective-actions")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_requires_auth(self):
        """Unauthenticated request returns 401."""
        client = TestClient(app)
        resp = client.get("/api/corrective-actions")
        assert resp.status_code == 401


# --- Create action ---


class TestCreateCorrectiveAction:
    def test_create_requires_editor_role(self, viewer_client):
        """Viewer cannot create actions."""
        resp = viewer_client.post(
            "/api/corrective-actions",
            json={"title": "Test action", "flag_id": "flag_test_001"},
        )
        assert resp.status_code == 403

    def test_create_action(self, editor_client, _seed_risk_flag):
        """Editor can create a corrective action."""
        resp = editor_client.post(
            "/api/corrective-actions",
            json={
                "title": "Address labour audit",
                "description": "Complete Higg FEM audit",
                "flag_id": "flag_test_001",
                "priority": "critical",
                "status": "open",
                "deadline": "2026-06-01",
                "assigned_to": "compliance@textilebd.com",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["id"].startswith("ca_")

    def test_create_action_minimal(self, editor_client):
        """Can create with just a title."""
        resp = editor_client.post(
            "/api/corrective-actions",
            json={"title": "Minimal action"},
        )
        assert resp.status_code == 200

    def test_create_action_sets_default_status(self, editor_client):
        """Default status is 'open' when not provided."""
        resp = editor_client.post(
            "/api/corrective-actions",
            json={"title": "Test action"},
        )
        assert resp.status_code == 200

        # Fetch and verify
        action_id = resp.json()["id"]
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT status FROM corrective_actions WHERE id = ?",
                (action_id,),
            ).fetchone()
            assert row["status"] == "open"
        finally:
            release_connection(conn)


# --- Get action ---


class TestGetCorrectiveAction:
    def test_get_action(self, admin_client, editor_client, _seed_risk_flag):
        """Can retrieve a single action by ID."""
        create_resp = editor_client.post(
            "/api/corrective-actions",
            json={"title": "Get me", "flag_id": "flag_test_001"},
        )
        action_id = create_resp.json()["id"]

        resp = admin_client.get(f"/api/corrective-actions/{action_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Get me"

    def test_get_action_not_found(self, admin_client):
        """Returns 404 for non-existent action."""
        resp = admin_client.get("/api/corrective-actions/ca_does_not_exist")
        assert resp.status_code == 404

    def test_get_action_org_isolation(
        self, admin_client, other_org_client, editor_client, _seed_risk_flag
    ):
        """Cannot get another org's action."""
        create_resp = editor_client.post(
            "/api/corrective-actions",
            json={"title": "Private action", "flag_id": "flag_test_001"},
        )
        action_id = create_resp.json()["id"]

        resp = other_org_client.get(f"/api/corrective-actions/{action_id}")
        assert resp.status_code == 404


# --- Update action ---


class TestUpdateCorrectiveAction:
    def test_update_action(self, admin_client, editor_client, _seed_risk_flag):
        """Can update an action's fields."""
        create_resp = editor_client.post(
            "/api/corrective-actions",
            json={"title": "Original", "flag_id": "flag_test_001", "status": "open"},
        )
        action_id = create_resp.json()["id"]

        resp = editor_client.put(
            f"/api/corrective-actions/{action_id}",
            json={"title": "Updated", "status": "in_progress"},
        )
        assert resp.status_code == 200

        get_resp = admin_client.get(f"/api/corrective-actions/{action_id}")
        assert get_resp.json()["title"] == "Updated"
        assert get_resp.json()["status"] == "in_progress"

    def test_update_status_completed_sets_completed_at(
        self, admin_client, editor_client, _seed_risk_flag
    ):
        """Setting status to completed populates completed_at."""
        create_resp = editor_client.post(
            "/api/corrective-actions",
            json={"title": "Will complete", "flag_id": "flag_test_001"},
        )
        action_id = create_resp.json()["id"]

        editor_client.put(
            f"/api/corrective-actions/{action_id}",
            json={"status": "completed"},
        )

        get_resp = admin_client.get(f"/api/corrective-actions/{action_id}")
        assert get_resp.json()["status"] == "completed"
        assert get_resp.json()["completed_at"] is not None

    def test_update_requires_editor_role(self, viewer_client, editor_client, _seed_risk_flag):
        """Viewer cannot update actions."""
        create_resp = editor_client.post(
            "/api/corrective-actions",
            json={"title": "Locked", "flag_id": "flag_test_001"},
        )
        action_id = create_resp.json()["id"]

        resp = viewer_client.put(
            f"/api/corrective-actions/{action_id}",
            json={"title": "Hacked"},
        )
        assert resp.status_code == 403

    def test_update_not_found(self, editor_client):
        """Updating non-existent action returns 404."""
        resp = editor_client.put(
            "/api/corrective-actions/ca_does_not_exist",
            json={"title": "Nope"},
        )
        assert resp.status_code == 404


# --- Delete action ---


class TestDeleteCorrectiveAction:
    def test_delete_requires_admin(self, editor_client, viewer_client, _seed_risk_flag):
        """Editor and viewer cannot delete actions."""
        # Create as editor first
        create_resp = editor_client.post(
            "/api/corrective-actions",
            json={"title": "To delete", "flag_id": "flag_test_001"},
        )
        action_id = create_resp.json()["id"]

        resp = viewer_client.delete(f"/api/corrective-actions/{action_id}")
        assert resp.status_code == 403

        resp = editor_client.delete(f"/api/corrective-actions/{action_id}")
        assert resp.status_code == 403

    def test_delete_action(self, admin_client, editor_client, _seed_risk_flag):
        """Admin can delete an action."""
        create_resp = editor_client.post(
            "/api/corrective-actions",
            json={"title": "To delete", "flag_id": "flag_test_001"},
        )
        action_id = create_resp.json()["id"]

        resp = admin_client.delete(f"/api/corrective-actions/{action_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

        # Verify gone
        get_resp = admin_client.get(f"/api/corrective-actions/{action_id}")
        assert get_resp.status_code == 404

    def test_delete_not_found(self, admin_client):
        """Deleting non-existent action returns 404."""
        resp = admin_client.delete("/api/corrective-actions/ca_does_not_exist")
        assert resp.status_code == 404

    def test_delete_org_isolation(
        self, admin_client, other_org_client, editor_client, _seed_risk_flag
    ):
        """Cannot delete another org's action."""
        create_resp = editor_client.post(
            "/api/corrective-actions",
            json={"title": "Your action", "flag_id": "flag_test_001"},
        )
        action_id = create_resp.json()["id"]

        resp = other_org_client.delete(f"/api/corrective-actions/{action_id}")
        assert resp.status_code == 404


# --- Escalate action ---


class TestEscalateCorrectiveAction:
    def test_escalate_not_overdue_returns_400(self, admin_client, editor_client, _seed_risk_flag):
        """Escalating a non-overdue action returns 400."""
        create_resp = editor_client.post(
            "/api/corrective-actions",
            json={
                "title": "Not overdue",
                "flag_id": "flag_test_001",
                "deadline": "2099-12-31",  # Far future
            },
        )
        action_id = create_resp.json()["id"]

        resp = editor_client.post(f"/api/corrective-actions/{action_id}/escalate")
        assert resp.status_code == 400
        assert "not overdue" in resp.json()["detail"].lower()

    def test_escalate_creates_risk_flag(self, admin_client, editor_client, _seed_risk_flag):
        """Escalating an overdue action creates a new risk flag."""
        create_resp = editor_client.post(
            "/api/corrective-actions",
            json={
                "title": "Overdue action",
                "flag_id": "flag_test_001",
                "deadline": "2020-01-01",  # In the past
                "status": "open",
            },
        )
        action_id = create_resp.json()["id"]

        resp = editor_client.post(f"/api/corrective-actions/{action_id}/escalate")
        assert resp.status_code == 200
        data = resp.json()
        assert "escalated" in data["message"].lower()
        assert "flag_id" in data
        new_flag_id = data["flag_id"]

        # Verify the new risk flag exists
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM risk_flags WHERE id = ?",
                (new_flag_id,),
            ).fetchone()
            assert row is not None
            assert row["org_id"] == "org_bd_001"
        finally:
            release_connection(conn)

    def test_escalate_action_not_found(self, editor_client):
        """Escalating non-existent action returns 404."""
        resp = editor_client.post("/api/corrective-actions/ca_does_not_exist/escalate")
        assert resp.status_code == 404

    def test_escalate_org_isolation(
        self, admin_client, other_org_client, editor_client, _seed_risk_flag
    ):
        """Cannot escalate another org's action."""
        # Create action in org_bd_001
        create_resp = editor_client.post(
            "/api/corrective-actions",
            json={
                "title": "Your overdue action",
                "flag_id": "flag_test_001",
                "deadline": "2020-01-01",
            },
        )
        action_id = create_resp.json()["id"]

        # Try to escalate from other org
        resp = other_org_client.post(f"/api/corrective-actions/{action_id}/escalate")
        assert resp.status_code == 404
