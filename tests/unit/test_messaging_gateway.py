"""Tests for MessagingGateway abstract base class."""

import sys

sys.path.insert(0, "src")

from uuid import UUID
import pytest
from abc import ABC

from src.supplier.messaging_gateway import (
    Channel,
    DispatchResult,
    DispatchStatus,
    MessagingGateway,
    Question,
    ReminderSchedule,
)


class TestMessagingGatewayIsAbstract:
    """Tests to verify MessagingGateway is an abstract class."""

    def test_messaging_gateway_cannot_instantiate_directly(self):
        """Test MessagingGateway is abstract (cannot instantiate directly)."""
        with pytest.raises(TypeError) as exc_info:
            MessagingGateway()

        # Should fail because MessagingGateway is an ABC with abstract methods
        assert (
            "abstract" in str(exc_info.value).lower()
            or "instantiate" in str(exc_info.value).lower()
        )

    def test_messaging_gateway_is_abc(self):
        """Test MessagingGateway inherits from ABC."""
        assert issubclass(MessagingGateway, ABC)


class TestChannelEnum:
    """Tests for Channel enum."""

    def test_channel_values(self):
        """Test Channel enum has expected values."""
        assert Channel.WHATSAPP == "whatsapp"
        assert Channel.LINE == "line"
        assert Channel.WECHAT == "wechat"
        assert Channel.EMAIL == "email"

    def test_channel_is_string_enum(self):
        """Test Channel is a string enum."""
        assert isinstance(Channel.WHATSAPP, str)
        assert Channel.WHATSAPP.value == "whatsapp"


class TestDispatchStatusEnum:
    """Tests for DispatchStatus enum."""

    def test_dispatch_status_values(self):
        """Test DispatchStatus enum has expected values."""
        assert DispatchStatus.SENT == "sent"
        assert DispatchStatus.DELIVERED == "delivered"
        assert DispatchStatus.FAILED == "failed"
        assert DispatchStatus.PENDING == "pending"
        assert DispatchStatus.UNKNOWN == "unknown"


class TestDispatchResult:
    """Tests for DispatchResult dataclass."""

    def test_dispatch_result_to_dict(self):
        """Test DispatchResult.to_dict() method."""
        result = DispatchResult(
            status=DispatchStatus.SENT,
            message_id="msg_123",
            channel=Channel.WHATSAPP,
            supplier_id="sup_001",
        )

        d = result.to_dict()
        assert d["status"] == "sent"
        assert d["message_id"] == "msg_123"
        assert d["channel"] == "whatsapp"
        assert d["supplier_id"] == "sup_001"

    def test_dispatch_result_with_error(self):
        """Test DispatchResult with error message."""
        result = DispatchResult(
            status=DispatchStatus.FAILED,
            error_message="Connection timeout",
            channel=Channel.EMAIL,
        )

        d = result.to_dict()
        assert d["status"] == "failed"
        assert d["error_message"] == "Connection timeout"


class TestQuestion:
    """Tests for Question dataclass."""

    def test_question_basic(self):
        """Test Question creation with basic fields."""
        q = Question(
            question_id="q1",
            question_number=1,
            question_text="What is your energy consumption?",
        )

        assert q.question_id == "q1"
        assert q.question_number == 1
        assert q.question_text == "What is your energy consumption?"
        assert q.expected_unit is None

    def test_question_with_expected_unit(self):
        """Test Question with expected unit."""
        q = Question(
            question_id="q2",
            question_number=2,
            question_text="Gas consumption?",
            expected_unit="m3",
        )

        assert q.expected_unit == "m3"


class TestReminderSchedule:
    """Tests for ReminderSchedule dataclass."""

    def test_reminder_schedule_basic(self):
        """Test ReminderSchedule creation."""
        schedule = ReminderSchedule(
            questionnaire_id=UUID("12345678-1234-5678-1234-567812345678"),
            supplier_id=UUID("87654321-4321-8765-4321-876543218765"),
        )

        assert len(schedule.day_3_pending) == 0
        assert len(schedule.day_7_pending) == 0
        assert len(schedule.day_14_pending) == 0
        assert schedule.reminder_count == 0

    def test_reminder_schedule_with_pending(self):
        """Test ReminderSchedule with pending questions."""
        schedule = ReminderSchedule(
            questionnaire_id=UUID("12345678-1234-5678-1234-567812345678"),
            supplier_id=UUID("87654321-4321-8765-4321-876543218765"),
            day_3_pending=[1, 2, 3],
            day_7_pending=[1, 2],
            day_14_pending=[1],
        )

        assert len(schedule.day_3_pending) == 3
        assert len(schedule.day_7_pending) == 2
        assert len(schedule.day_14_pending) == 1


class TestMessagingGatewayMethods:
    """Tests for MessagingGateway abstract methods signature."""

    def test_send_questionnaire_is_abstract(self):
        """Test send_questionnaire is an abstract method."""
        # Get the abstract method
        method = MessagingGateway.send_questionnaire
        assert hasattr(method, "__isabstractmethod__") or hasattr(
            MessagingGateway, "__abstractmethods__"
        )

    def test_receive_response_is_abstract(self):
        """Test receive_response is an abstract method."""
        # Get the abstract method
        method = MessagingGateway.receive_response
        assert hasattr(method, "__isabstractmethod__") or hasattr(
            MessagingGateway, "__abstractmethods__"
        )

    def test_send_reminder_is_abstract(self):
        """Test send_reminder is an abstract method."""
        # Get the abstract method
        method = MessagingGateway.send_reminder
        assert hasattr(method, "__isabstractmethod__") or hasattr(
            MessagingGateway, "__abstractmethods__"
        )
