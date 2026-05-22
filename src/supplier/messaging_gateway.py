"""
Messaging Gateway Abstract Base Class for supplier communication.

Provides a unified interface for sending questionnaires and receiving responses
across multiple channels (WhatsApp, LINE, WeChat, Email).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID

import structlog

from src.supplier.nlu_parser import ParsedResponse

logger = structlog.get_logger(__name__)


class Channel(str, Enum):
    """Supported messaging channels for supplier communication."""

    WHATSAPP = "whatsapp"
    LINE = "line"
    WECHAT = "wechat"
    EMAIL = "email"


class DispatchStatus(str, Enum):
    """Status of a message dispatch operation."""

    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    PENDING = "pending"
    UNKNOWN = "unknown"


@dataclass
class DispatchResult:
    """Result of a message dispatch operation."""

    status: DispatchStatus
    message_id: Optional[str] = None
    channel: Optional[Channel] = None
    supplier_id: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "message_id": self.message_id,
            "channel": self.channel.value
            if self.channel and isinstance(self.channel, Enum)
            else self.channel,
            "supplier_id": self.supplier_id,
            "error_message": self.error_message,
            "raw_response": self.raw_response,
        }


@dataclass
class Question:
    """A questionnaire question with answer expectations."""

    question_id: str
    question_number: int
    question_text: str
    expected_unit: Optional[str] = None


@dataclass
class ReminderSchedule:
    """Schedule for sending reminders."""

    questionnaire_id: UUID
    supplier_id: UUID
    day_3_pending: list[int] = field(default_factory=list)
    day_7_pending: list[int] = field(default_factory=list)
    day_14_pending: list[int] = field(default_factory=list)
    last_reminder_sent: Optional[str] = None
    reminder_count: int = 0


class MessagingGateway(ABC):
    """Abstract base class for messaging gateways.

    Provides a unified interface for sending questionnaires and reminders
    to suppliers and receiving their responses across multiple channels.
    """

    @abstractmethod
    async def send_questionnaire(
        self,
        questionnaire_id: UUID,
        supplier_id: UUID,
        questions: list[Question],
        channel: Channel,
    ) -> DispatchResult:
        """Send a questionnaire to a supplier via the specified channel.

        Args:
            questionnaire_id: Unique identifier for the questionnaire.
            supplier_id: Unique identifier for the supplier.
            questions: List of questions to include in the questionnaire.
            channel: The messaging channel to use (whatsapp, line, wechat, email).

        Returns:
            DispatchResult with the status of the send operation.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """

    @abstractmethod
    async def receive_response(
        self,
        channel: Channel,
        raw_message: str,
        message_metadata: dict,
    ) -> ParsedResponse:
        """Parse a supplier response from any channel.

        Args:
            channel: The messaging channel the response came from.
            raw_message: The raw text content of the supplier's response.
            message_metadata: Additional metadata about the message
                (sender_id, timestamp, message_id, etc.).

        Returns:
            ParsedResponse containing structured answers extracted from the raw message.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """

    @abstractmethod
    async def send_reminder(
        self,
        questionnaire_id: UUID,
        supplier_id: UUID,
        pending_questions: list[int],
        channel: Channel,
    ) -> None:
        """Send a reminder for unanswered questions.

        Reminders are typically sent at Day 3, Day 7, and Day 14 after
        the initial questionnaire was sent.

        Args:
            questionnaire_id: Unique identifier for the questionnaire.
            supplier_id: Unique identifier for the supplier.
            pending_questions: List of question numbers that are still unanswered.
            channel: The messaging channel to use for the reminder.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """

    async def get_reminder_schedule(
        self,
        questionnaire_id: UUID,
        supplier_id: UUID,
        response: Optional[ParsedResponse],
        questions: list[Question],
    ) -> ReminderSchedule:
        """Calculate the reminder schedule based on pending questions.

        Args:
            questionnaire_id: Unique identifier for the questionnaire.
            supplier_id: Unique identifier for the supplier.
            response: The current parsed response (if any) to determine pending questions.
            questions: List of all questions in the questionnaire.

        Returns:
            ReminderSchedule with pending questions categorized by reminder day.
        """
        schedule = ReminderSchedule(
            questionnaire_id=questionnaire_id,
            supplier_id=supplier_id,
        )

        if response is None:
            schedule.day_3_pending = [q.question_number for q in questions]
            schedule.day_7_pending = [q.question_number for q in questions]
            schedule.day_14_pending = [q.question_number for q in questions]
            return schedule

        answered_numbers = {a.question_number for a in response.answers}
        pending = [
            q.question_number for q in questions if q.question_number not in answered_numbers
        ]

        schedule.day_3_pending = pending.copy()
        schedule.day_7_pending = pending.copy()
        schedule.day_14_pending = pending.copy()

        logger.info(
            "reminder.schedule_calculated",
            questionnaire_id=str(questionnaire_id),
            supplier_id=str(supplier_id),
            pending_count=len(pending),
        )

        return schedule

    async def should_send_reminder(
        self,
        schedule: ReminderSchedule,
        day: int,
        pending_count: int,
    ) -> bool:
        """Determine if a reminder should be sent based on schedule and day.

        Args:
            schedule: The reminder schedule to check.
            day: The day number (3, 7, or 14).
            pending_count: Number of questions still pending.

        Returns:
            True if a reminder should be sent, False otherwise.
        """
        if pending_count == 0:
            return False

        if day == 3 and schedule.day_3_pending:
            return True
        if day == 7 and schedule.day_7_pending:
            return True
        if day == 14 and schedule.day_14_pending:
            return True

        return False
