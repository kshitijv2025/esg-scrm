"""EmailClient integration tests — verify demo mode, SMTP dispatch, and audit logging.

Tests cover:
  - Demo mode detection and log-only behavior
  - send_email returns correct status shapes
  - send_alert_email formats severity correctly
  - send_questionnaire dispatches to supplier email + updates supplier record
  - All sends log to outbound_emails table
"""
from __future__ import annotations

import sys
import uuid

sys.path.insert(0, "src")

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.jwt import create_token
from src.connectors.email import EmailClient, get_email_client
from src.db.database import (
    _fetchall,
    _fetchone,
    get_connection,
    release_connection,
    reset_database,
)
from src.db.seed import seed
from src.db.seed_alert_thresholds import seed_alert_thresholds
from src.db.seed_emission_factors import seed_emission_factors

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fresh_db():
    """Reset and seed the database before each test."""
    reset_database()
    seed()
    seed_emission_factors()
    seed_alert_thresholds()
    yield


@pytest.fixture
def client():
    """Unauthenticated test client."""
    return TestClient(app)


@pytest.fixture
def admin_client():
    """TestClient authenticated as admin in org_bd_001."""
    token = create_token(
        {
            "sub": "usr_admin_001",
            "org_id": "org_bd_001",
            "email": "admin@test.com",
            "role": "admin",
        }
    )
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


@pytest.fixture
def ec():
    """Fresh EmailClient instance."""
    return EmailClient()


# ---------------------------------------------------------------------------
# Demo mode detection
# ---------------------------------------------------------------------------


class TestDemoModeDetection:
    """EmailClient operates in demo mode when SMTP credentials are absent."""

    def test_demo_mode_active_when_no_credentials(self, ec):
        """Demo mode is active (no SMTP creds in test env)."""
        assert ec._demo is True, "EmailClient should be in demo mode without SMTP credentials"

    def test_send_email_returns_demo_status(self, ec):
        """send_email returns status='demo' in demo mode."""
        result = ec.send_email(
            to="supplier@example.com",
            subject="Test Subject",
            html_body="<p>Test</p>",
            text_body="Test",
            org_id="org_bd_001",
            supplier_id=None,
        )
        assert result["status"] == "demo"
        assert "smtp_message_id" in result
        assert result["smtp_message_id"].startswith("demo-")

    def test_send_email_does_not_connect_to_smtp(self, ec):
        """send_email completes without SMTP connection in demo mode."""
        # Should not raise — demo mode skips SMTP entirely
        result = ec.send_email(
            to="supplier@example.com",
            subject="No SMTP connection",
            html_body="<p>Should not connect</p>",
            text_body="Should not connect",
            org_id="org_bd_001",
            supplier_id=None,
        )
        assert result["status"] == "demo"


# ---------------------------------------------------------------------------
# Audit trail — outbound_emails logging
# ---------------------------------------------------------------------------


class TestOutboundEmailsAuditTrail:
    """All email sends are logged to outbound_emails table."""

    def _last_email_log(self) -> dict | None:
        conn = get_connection()
        try:
            rows = _fetchall(
                conn,
                "SELECT * FROM outbound_emails ORDER BY id DESC LIMIT 1",
            )
            return rows[0] if rows else None
        finally:
            release_connection(conn)

    def test_send_email_logs_to_outbound_emails(self, ec):
        """send_email inserts a row into outbound_emails."""
        ec.send_email(
            to="audit-test@example.com",
            subject="Audit Trail Test",
            html_body="<p>Test</p>",
            text_body="Test",
            org_id="org_bd_001",
            supplier_id=None,
        )
        row = self._last_email_log()
        assert row is not None, "outbound_emails should have one row after send_email"
        assert row["to_address"] == "audit-test@example.com"
        assert row["subject"] == "Audit Trail Test"
        assert row["org_id"] == "org_bd_001"
        assert row["direction"] == "outbound"
        assert row["channel"] == "email"

    def test_send_alert_email_logs_to_outbound_emails(self, ec):
        """send_alert_email inserts a row into outbound_emails."""
        ec.send_alert_email(
            alert_data={
                "severity": "CRITICAL",
                "flag_text": "Overdue payment",
                "cluster": "Financial Risk",
                "supplier_name": "Test Supplier",
                "days_overdue": 30,
                "priority_score": 92.5,
            },
            org_id="org_bd_001",
        )
        row = self._last_email_log()
        assert row is not None
        assert "CRITICAL" in row["subject"]
        assert row["org_id"] == "org_bd_001"


# ---------------------------------------------------------------------------
# send_alert_email formatting
# ---------------------------------------------------------------------------


class TestSendAlertEmail:
    """send_alert_email formats CRITICAL and WARNING alerts correctly."""

    def test_alert_email_returns_demo_status(self, ec):
        """send_alert_email returns demo status without SMTP credentials."""
        result = ec.send_alert_email(
            alert_data={
                "severity": "WARNING",
                "flag_text": "Mild risk",
                "cluster": "Environmental",
                "supplier_name": "Green Supplies",
                "days_overdue": 5,
                "priority_score": 35.0,
            },
            org_id="org_bd_001",
        )
        assert result["status"] == "demo"
        assert "smtp_message_id" in result

    def test_alert_email_subject_contains_severity(self, ec):
        """Alert subject line includes severity label."""
        result = ec.send_alert_email(
            alert_data={
                "severity": "CRITICAL",
                "flag_text": "Severe violation",
                "cluster": "Labour Rights",
                "supplier_name": "Bad Actor Ltd",
                "days_overdue": 90,
                "priority_score": 98.0,
            },
            org_id="org_bd_001",
        )
        assert "[CRITICAL]" in result.get("smtp_message_id", "") or result["status"] == "demo"
        # Check audit log
        conn = get_connection()
        try:
            rows = _fetchall(
                conn,
                "SELECT subject FROM outbound_emails ORDER BY id DESC LIMIT 1",
            )
            assert rows[0]["subject"] == "[CRITICAL] ESG Risk Alert: Labour Rights"
        finally:
            release_connection(conn)

    def test_alert_email_warning_severity(self, ec):
        """WARNING severity emails include correct label in subject."""
        ec.send_alert_email(
            alert_data={
                "severity": "WARNING",
                "flag_text": "Minor gap",
                "cluster": "Health & Safety",
                "supplier_name": "Safe Corp",
                "days_overdue": 7,
                "priority_score": 55.0,
            },
            org_id="org_bd_001",
        )
        conn = get_connection()
        try:
            rows = _fetchall(
                conn,
                "SELECT subject FROM outbound_emails ORDER BY id DESC LIMIT 1",
            )
            assert rows[0]["subject"] == "[WARNING] ESG Risk Alert: Health & Safety"
        finally:
            release_connection(conn)


# ---------------------------------------------------------------------------
# send_questionnaire integration
# ---------------------------------------------------------------------------


class TestSendQuestionnaire:
    """send_questionnaire dispatches questionnaire emails to suppliers."""

    def _insert_supplier_with_email(
        self,
        supplier_id: str,
        name: str,
        email: str,
        org_id: str = "org_bd_001",
        country: str = "US",
    ) -> None:
        conn = get_connection()
        try:
            from src.db.database import _execute

            _execute(
                conn,
                """INSERT INTO suppliers
                   (id, org_id, name, country, industry, tier, annual_spend_usd,
                    phone, email, preferred_channel, relationship_status, questionnaire_status)
                   VALUES (?, ?, ?, ?, 'Manufacturing', 'tier1', 100000.0, '+1234567890', ?, 'email', 'active', 'not_sent')""",
                (supplier_id, org_id, name, country, email),
            )
        finally:
            release_connection(conn)

    def _insert_questionnaire_template(
        self, template_id: int, name: str, org_id: str, questions: list
    ) -> None:
        import json

        conn = get_connection()
        try:
            from src.db.database import _execute

            _execute(
                conn,
                """INSERT INTO questionnaire_templates (id, name, org_id, questions, is_active)
                   VALUES (?, ?, ?, ?, 1)""",
                (template_id, name, org_id, json.dumps(questions)),
            )
        finally:
            release_connection(conn)

    def test_send_questionnaire_returns_demo_status(self, ec):
        """send_questionnaire returns demo status without SMTP."""
        supplier_id = f"sup_q_{uuid.uuid4().hex[:8]}"
        self._insert_supplier_with_email(supplier_id, "Q Supplier", "qsupplier@example.com")
        self._insert_questionnaire_template(
            template_id=999,
            name="ESG Basic",
            org_id="org_bd_001",
            questions=[
                {"text": "What is your carbon footprint?", "unit": "tCO2e"},
                {"text": "Do you have ISO 14001 certification?", "unit": "yes/no"},
            ],
        )
        result = ec.send_questionnaire(
            supplier_id=supplier_id,
            template_id=999,
            org_id="org_bd_001",
        )
        assert result["status"] == "demo"
        assert result["supplier_name"] == "Q Supplier"
        assert result["question_count"] == 2
        assert result["template_name"] == "ESG Basic"

    def test_send_questionnaire_updates_supplier_status(self, ec):
        """send_questionnaire sets supplier questionnaire_status to 'pending' after send."""
        supplier_id = f"sup_q2_{uuid.uuid4().hex[:8]}"
        self._insert_supplier_with_email(supplier_id, "Status Supplier", "status@example.com")
        self._insert_questionnaire_template(
            template_id=998,
            name="Labour Audit",
            org_id="org_bd_001",
            questions=[{"text": "Any labour violations?", "unit": "yes/no"}],
        )
        ec.send_questionnaire(
            supplier_id=supplier_id,
            template_id=998,
            org_id="org_bd_001",
        )
        conn = get_connection()
        try:
            row = _fetchone(
                conn, "SELECT questionnaire_status FROM suppliers WHERE id = ?", (supplier_id,)
            )
            assert row["questionnaire_status"] == "pending"
        finally:
            release_connection(conn)

    def test_send_questionnaire_logs_to_outbound_emails(self, ec):
        """send_questionnaire inserts into outbound_emails."""
        supplier_id = f"sup_q3_{uuid.uuid4().hex[:8]}"
        self._insert_supplier_with_email(supplier_id, "Log Supplier", "log@example.com")
        self._insert_questionnaire_template(
            template_id=997,
            name="Environmental Survey",
            org_id="org_bd_001",
            questions=[{"text": "Water usage?", "unit": "m3"}],
        )
        ec.send_questionnaire(supplier_id=supplier_id, template_id=997, org_id="org_bd_001")
        conn = get_connection()
        try:
            rows = _fetchall(
                conn,
                "SELECT * FROM outbound_emails WHERE supplier_id = ? ORDER BY id DESC LIMIT 1",
                (supplier_id,),
            )
            assert len(rows) == 1
            assert rows[0]["to_address"] == "log@example.com"
            assert "ESG Questionnaire: Environmental Survey" in rows[0]["subject"]
        finally:
            release_connection(conn)

    def test_send_questionnaire_unknown_supplier(self, ec):
        """send_questionnaire returns error for unknown supplier."""
        result = ec.send_questionnaire(
            supplier_id="nonexistent-supplier-id",
            template_id=1,
            org_id="org_bd_001",
        )
        assert result["status"] == "error"
        assert "not found" in result["detail"]

    def test_send_questionnaire_no_template(self, ec):
        """send_questionnaire returns error when no active template exists."""
        supplier_id = f"sup_q4_{uuid.uuid4().hex[:8]}"
        self._insert_supplier_with_email(supplier_id, "No Template Supplier", "notmpl@example.com")
        # No template inserted — should fail
        result = ec.send_questionnaire(
            supplier_id=supplier_id,
            template_id=0,  # resolve first active
            org_id="org_bd_001",
        )
        assert result["status"] == "error"
        assert "no active questionnaire template" in result["detail"].lower()

    def test_send_questionnaire_supplier_no_email(self, ec):
        """send_questionnaire returns error when supplier has no email."""
        supplier_id = f"sup_q5_{uuid.uuid4().hex[:8]}"
        conn = get_connection()
        try:
            from src.db.database import _execute

            _execute(
                conn,
                """INSERT INTO suppliers
                   (id, org_id, name, country, industry, tier, annual_spend_usd,
                    phone, email, preferred_channel, relationship_status, questionnaire_status)
                   VALUES (?, ?, ?, ?, 'Manufacturing', 'tier1', 50000.0, '+9876543210', '', 'email', 'active', 'not_sent')""",
                (supplier_id, "org_bd_001", "No Email Supplier", "US"),
            )
        finally:
            release_connection(conn)
        result = ec.send_questionnaire(supplier_id=supplier_id, template_id=1, org_id="org_bd_001")
        assert result["status"] == "error"
        assert "no email" in result["detail"].lower()


# ---------------------------------------------------------------------------
# Singleton behavior
# ---------------------------------------------------------------------------


class TestEmailClientSingleton:
    """get_email_client returns the same instance on repeated calls."""

    def test_singleton_returns_same_instance(self):
        """Multiple get_email_client() calls return the same EmailClient."""
        a = get_email_client()
        b = get_email_client()
        assert a is b
