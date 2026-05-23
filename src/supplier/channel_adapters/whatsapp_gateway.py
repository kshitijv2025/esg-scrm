"""
WhatsApp Gateway implementation for supplier messaging.

Concrete implementation of MessagingGateway for WhatsApp using the existing
WhatsAppClient connector.
"""

import logging
from uuid import UUID


from src.connectors.whatsapp import WhatsAppClient
from src.supplier.messaging_gateway import (
    Channel,
    DispatchResult,
    DispatchStatus,
    MessagingGateway,
    Question,
)
from src.supplier.nlu_parser import NLUParser, ParsedResponse

logger = logging.getLogger(__name__)


class WhatsAppGateway(MessagingGateway):
    """WhatsApp implementation of the MessagingGateway ABC.

    Uses the existing WhatsAppClient from src/connectors/whatsapp.py
    to send and receive messages via WhatsApp.
    """

    def __init__(self) -> None:
        """Initialize the WhatsApp gateway."""
        self._client = WhatsAppClient()
        self._nlu_parser = NLUParser()
        logger.info("whatsapp_gateway.initialized")

    async def send_questionnaire(
        self,
        questionnaire_id: UUID,
        supplier_id: UUID,
        questions: list[Question],
        channel: Channel,
    ) -> DispatchResult:
        """Send a questionnaire to a supplier via WhatsApp.

        Args:
            questionnaire_id: Unique identifier for the questionnaire.
            supplier_id: Unique identifier for the supplier.
            questions: List of questions to include in the questionnaire.
            channel: Must be Channel.WHATSAPP for this implementation.

        Returns:
            DispatchResult with the status of the send operation.
        """
        if channel != Channel.WHATSAPP:
            logger.error(
                "whatsapp_gateway.wrong_channel: expected=%s, got=%s",
                Channel.WHATSAPP,
                channel,
            )
            return DispatchResult(
                status=DispatchStatus.FAILED,
                error_message=f"WhatsAppGateway only supports {Channel.WHATSAPP}, got {channel}",
                channel=channel,
                supplier_id=str(supplier_id),
            )

        logger.info(
            "whatsapp_gateway.send_questionnaire.start: questionnaire_id=%s, supplier_id=%s, question_count=%d",
            str(questionnaire_id),
            str(supplier_id),
            len(questions),
        )

        try:
            formatted_questions = self._format_questions(questions)

            result = self._client.send_questionnaire(
                supplier_id=str(supplier_id),
                template_id=0,
            )

            if result.get("status") == "sent":
                logger.info(
                    "whatsapp_gateway.send_questionnaire.success: questionnaire_id=%s, supplier_id=%s, message_sid=%s",
                    str(questionnaire_id),
                    str(supplier_id),
                    result.get("message_sid"),
                )
                return DispatchResult(
                    status=DispatchStatus.SENT,
                    message_id=result.get("message_sid"),
                    channel=Channel.WHATSAPP,
                    supplier_id=str(supplier_id),
                    raw_response=result,
                )
            elif result.get("status") == "demo":
                logger.info(
                    "whatsapp_gateway.send_questionnaire.demo: questionnaire_id=%s, supplier_id=%s",
                    str(questionnaire_id),
                    str(supplier_id),
                )
                return DispatchResult(
                    status=DispatchStatus.SENT,
                    message_id="demo",
                    channel=Channel.WHATSAPP,
                    supplier_id=str(supplier_id),
                    raw_response=result,
                )
            else:
                logger.error(
                    "whatsapp_gateway.send_questionnaire.failed: questionnaire_id=%s, supplier_id=%s, error=%s",
                    str(questionnaire_id),
                    str(supplier_id),
                    result.get("detail"),
                )
                return DispatchResult(
                    status=DispatchStatus.FAILED,
                    error_message=result.get("detail", "Unknown error"),
                    channel=Channel.WHATSAPP,
                    supplier_id=str(supplier_id),
                    raw_response=result,
                )

        except Exception as e:
            logger.exception(
                "whatsapp_gateway.send_questionnaire.error: questionnaire_id=%s, supplier_id=%s, error=%s",
                str(questionnaire_id),
                str(supplier_id),
                str(e),
            )
            return DispatchResult(
                status=DispatchStatus.FAILED,
                error_message=str(e),
                channel=Channel.WHATSAPP,
                supplier_id=str(supplier_id),
            )

    async def receive_response(
        self,
        channel: Channel,
        raw_message: str,
        message_metadata: dict,
    ) -> ParsedResponse:
        """Parse a supplier response from WhatsApp.

        Args:
            channel: Must be Channel.WHATSAPP for this implementation.
            raw_message: The raw text content of the supplier's response.
            message_metadata: Additional metadata (sender_id, timestamp, etc.).

        Returns:
            ParsedResponse containing structured answers.
        """
        if channel != Channel.WHATSAPP:
            logger.error(
                "whatsapp_gateway.wrong_channel: expected=%s, got=%s",
                Channel.WHATSAPP,
                channel,
            )
            return ParsedResponse(
                raw_message=raw_message,
                parse_errors=[f"WhatsAppGateway only supports {Channel.WHATSAPP}"],
            )

        logger.info(
            "whatsapp_gateway.receive_response: sender_id=%s, message_len=%d",
            message_metadata.get("sender_id", "unknown"),
            len(raw_message),
        )

        questions_for_parsing = self._extract_questions_from_metadata(message_metadata)

        if questions_for_parsing:
            parsed = self._nlu_parser.parse_response(raw_message, questions_for_parsing)
        else:
            parsed = ParsedResponse(
                raw_message=raw_message,
                parse_errors=["No question context available for parsing"],
            )
            logger.warning(
                "whatsapp_gateway.no_question_context: sender_id=%s",
                message_metadata.get("sender_id", "unknown"),
            )

        return parsed

    async def send_reminder(
        self,
        questionnaire_id: UUID,
        supplier_id: UUID,
        pending_questions: list[int],
        channel: Channel,
    ) -> None:
        """Send a reminder for unanswered questions via WhatsApp.

        Args:
            questionnaire_id: Unique identifier for the questionnaire.
            supplier_id: Unique identifier for the supplier.
            pending_questions: List of question numbers that are still unanswered.
            channel: Must be Channel.WHATSAPP for this implementation.
        """
        if channel != Channel.WHATSAPP:
            logger.error(
                "whatsapp_gateway.wrong_channel: expected=%s, got=%s",
                Channel.WHATSAPP,
                channel,
            )
            return

        if not pending_questions:
            logger.info(
                "whatsapp_gateway.send_reminder.no_pending: questionnaire_id=%s, supplier_id=%s",
                str(questionnaire_id),
                str(supplier_id),
            )
            return

        logger.info(
            "whatsapp_gateway.send_reminder.start: questionnaire_id=%s, supplier_id=%s, pending_count=%d, pending_questions=%s",
            str(questionnaire_id),
            str(supplier_id),
            len(pending_questions),
            pending_questions,
        )

        try:
            reminder_text = self._format_reminder_message(pending_questions)

            result = self._client.send_risk_alert(
                supplier_id=str(supplier_id),
                alert_text=reminder_text,
            )

            if result.get("status") == "sent":
                logger.info(
                    "whatsapp_gateway.send_reminder.success: questionnaire_id=%s, supplier_id=%s, pending_count=%d",
                    str(questionnaire_id),
                    str(supplier_id),
                    len(pending_questions),
                )
            elif result.get("status") == "demo":
                logger.info(
                    "whatsapp_gateway.send_reminder.demo: questionnaire_id=%s, supplier_id=%s",
                    str(questionnaire_id),
                    str(supplier_id),
                )
            else:
                logger.error(
                    "whatsapp_gateway.send_reminder.failed: questionnaire_id=%s, supplier_id=%s, error=%s",
                    str(questionnaire_id),
                    str(supplier_id),
                    result.get("detail"),
                )

        except Exception as e:
            logger.exception(
                "whatsapp_gateway.send_reminder.error: questionnaire_id=%s, supplier_id=%s, error=%s",
                str(questionnaire_id),
                str(supplier_id),
                str(e),
            )

    def _format_questions(self, questions: list[Question]) -> str:
        """Format questions for WhatsApp message body.

        Args:
            questions: List of questions to format.

        Returns:
            Formatted message string.
        """
        lines = []
        for q in questions:
            lines.append(f"{q.question_number}. {q.question_text}")
            if q.expected_unit:
                lines.append(f"   Reply: {q.question_number}. [value in {q.expected_unit}]")
            else:
                lines.append(f"   Reply: {q.question_number}. [your answer]")

        return "\n".join(lines)

    def _format_reminder_message(self, pending_questions: list[int]) -> str:
        """Format a reminder message for pending questions.

        Args:
            pending_questions: List of pending question numbers.

        Returns:
            Formatted reminder message.
        """
        question_list = ", ".join(f"#{q}" for q in pending_questions)

        return (
            f"Reminder: You still have {len(pending_questions)} pending question(s) "
            f"in your ESG questionnaire.\n\n"
            f"Pending: {question_list}\n\n"
            f"Please complete your response at your earliest convenience to help "
            f"ensure accurate sustainability reporting."
        )

    def _extract_questions_from_metadata(
        self,
        message_metadata: dict,
    ) -> list[Question]:
        """Extract question context from message metadata.

        Args:
            message_metadata: Metadata dictionary that may contain questions.

        Returns:
            List of questions if found in metadata, empty list otherwise.
        """
        questions = message_metadata.get("questions", [])
        return [Question(**q) if isinstance(q, dict) else q for q in questions]
