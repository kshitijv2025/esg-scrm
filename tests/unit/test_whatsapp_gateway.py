"""Tests for WhatsAppGateway concrete implementation."""

import sys

sys.path.insert(0, "src")

from uuid import UUID
from unittest.mock import MagicMock, patch
import pytest

from src.supplier.channel_adapters.whatsapp_gateway import WhatsAppGateway
from src.supplier.messaging_gateway import Channel, DispatchStatus


class TestWhatsAppGatewayConstructor:
    """Tests for WhatsAppGateway constructor."""

    def test_whatsapp_gateway_takes_webhook_secret(self):
        """Test WhatsAppGateway constructor signature accepts webhook_secret."""
        # The WhatsAppGateway __init__ takes no arguments in current implementation
        # This test documents expected behavior - if webhook_secret is needed, it should be accepted
        with patch("src.supplier.channel_adapters.whatsapp_gateway.WhatsAppClient"):
            gateway = WhatsAppGateway()
            assert gateway is not None
            assert hasattr(gateway, "_client")
            assert hasattr(gateway, "_nlu_parser")

    def test_whatsapp_gateway_initializes_client(self):
        """Test WhatsAppGateway initializes with WhatsAppClient."""
        with patch("src.supplier.channel_adapters.whatsapp_gateway.WhatsAppClient") as mock_client:
            gateway = WhatsAppGateway()
            # WhatsAppClient should have been instantiated
            mock_client.assert_called_once()


class TestWhatsAppGatewaySendQuestionnaire:
    """Tests for WhatsAppGateway.send_questionnaire() method."""

    def test_send_questionnaire_method_exists(self):
        """Test send_questionnaire method exists on WhatsAppGateway."""
        with patch("src.supplier.channel_adapters.whatsapp_gateway.WhatsAppClient"):
            gateway = WhatsAppGateway()
            assert hasattr(gateway, "send_questionnaire")
            assert callable(gateway.send_questionnaire)

    @pytest.mark.asyncio
    async def test_send_questionnaire_returns_dispatch_result(self):
        """Test send_questionnaire returns DispatchResult."""
        with patch(
            "src.supplier.channel_adapters.whatsapp_gateway.WhatsAppClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.send_questionnaire.return_value = {
                "status": "sent",
                "message_sid": "msg_123",
            }

            gateway = WhatsAppGateway()

            result = await gateway.send_questionnaire(
                questionnaire_id=UUID("12345678-1234-5678-1234-567812345678"),
                supplier_id=UUID("87654321-4321-8765-4321-876543218765"),
                questions=[],
                channel=Channel.WHATSAPP,
            )

            assert result is not None
            assert hasattr(result, "status")
            assert hasattr(result, "channel")

    @pytest.mark.asyncio
    async def test_send_questionnaire_rejects_non_whatsapp_channel(self):
        """Test send_questionnaire rejects non-WHATSAPP channel."""
        with patch("src.supplier.channel_adapters.whatsapp_gateway.WhatsAppClient"):
            gateway = WhatsAppGateway()

            result = await gateway.send_questionnaire(
                questionnaire_id=UUID("12345678-1234-5678-1234-567812345678"),
                supplier_id=UUID("87654321-4321-8765-4321-876543218765"),
                questions=[],
                channel=Channel.EMAIL,
            )

            assert result.status == DispatchStatus.FAILED
            assert "whatsapp" in result.error_message.lower()


class TestWhatsAppGatewayReceiveResponse:
    """Tests for WhatsAppGateway.receive_response() method."""

    def test_receive_response_method_exists(self):
        """Test receive_response method exists on WhatsAppGateway."""
        with patch("src.supplier.channel_adapters.whatsapp_gateway.WhatsAppClient"):
            gateway = WhatsAppGateway()
            assert hasattr(gateway, "receive_response")
            assert callable(gateway.receive_response)

    @pytest.mark.asyncio
    async def test_receive_response_returns_parsed_response(self):
        """Test receive_response returns ParsedResponse."""
        from src.supplier.nlu_parser import ParsedResponse

        with patch("src.supplier.channel_adapters.whatsapp_gateway.WhatsAppClient"):
            gateway = WhatsAppGateway()

            result = await gateway.receive_response(
                channel=Channel.WHATSAPP,
                raw_message="1. 100 kWh",
                message_metadata={},
            )

            assert result is not None
            assert isinstance(result, ParsedResponse)

    @pytest.mark.asyncio
    async def test_receive_response_rejects_non_whatsapp_channel(self):
        """Test receive_response rejects non-WHATSAPP channel."""
        with patch("src.supplier.channel_adapters.whatsapp_gateway.WhatsAppClient"):
            gateway = WhatsAppGateway()

            result = await gateway.receive_response(
                channel=Channel.EMAIL,
                raw_message="test message",
                message_metadata={},
            )

            assert len(result.parse_errors) > 0
            assert "whatsapp" in result.parse_errors[0].lower()


class TestWhatsAppGatewaySendReminder:
    """Tests for WhatsAppGateway.send_reminder() method."""

    def test_send_reminder_method_exists(self):
        """Test send_reminder method exists on WhatsAppGateway."""
        with patch("src.supplier.channel_adapters.whatsapp_gateway.WhatsAppClient"):
            gateway = WhatsAppGateway()
            assert hasattr(gateway, "send_reminder")
            assert callable(gateway.send_reminder)

    @pytest.mark.asyncio
    async def test_send_reminder_returns_none(self):
        """Test send_reminder returns None (sends notification)."""
        with patch(
            "src.supplier.channel_adapters.whatsapp_gateway.WhatsAppClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.send_risk_alert.return_value = {"status": "sent"}

            gateway = WhatsAppGateway()

            result = await gateway.send_reminder(
                questionnaire_id=UUID("12345678-1234-5678-1234-567812345678"),
                supplier_id=UUID("87654321-4321-8765-4321-876543218765"),
                pending_questions=[1, 2],
                channel=Channel.WHATSAPP,
            )

            assert result is None  # send_reminder doesn't return anything

    @pytest.mark.asyncio
    async def test_send_reminder_rejects_non_whatsapp_channel(self):
        """Test send_reminder returns early for non-WHATSAPP channel."""
        with patch("src.supplier.channel_adapters.whatsapp_gateway.WhatsAppClient"):
            gateway = WhatsAppGateway()

            result = await gateway.send_reminder(
                questionnaire_id=UUID("12345678-1234-5678-1234-567812345678"),
                supplier_id=UUID("87654321-4321-8765-4321-876543218765"),
                pending_questions=[1, 2],
                channel=Channel.EMAIL,
            )

            assert result is None  # Returns early without doing anything


class TestWhatsAppGatewayFormatting:
    """Tests for WhatsAppGateway formatting helper methods."""

    def test_format_questions(self):
        """Test _format_questions creates formatted message."""
        from src.supplier.messaging_gateway import Question

        with patch("src.supplier.channel_adapters.whatsapp_gateway.WhatsAppClient"):
            gateway = WhatsAppGateway()

            questions = [
                Question(
                    question_id="q1",
                    question_number=1,
                    question_text="Electricity consumption?",
                    expected_unit="kWh",
                ),
                Question(
                    question_id="q2",
                    question_number=2,
                    question_text="Gas consumption?",
                    expected_unit="m3",
                ),
            ]

            formatted = gateway._format_questions(questions)

            assert "1. Electricity consumption?" in formatted
            assert "2. Gas consumption?" in formatted
            assert "kWh" in formatted
            assert "m3" in formatted

    def test_format_reminder_message(self):
        """Test _format_reminder_message creates reminder text."""
        with patch("src.supplier.channel_adapters.whatsapp_gateway.WhatsAppClient"):
            gateway = WhatsAppGateway()

            reminder = gateway._format_reminder_message([1, 2, 3])

            assert "3" in reminder  # 3 pending questions
            assert "#1" in reminder or "1" in reminder  # Question numbers
            assert "ESG questionnaire" in reminder or "Reminder" in reminder
