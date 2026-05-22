"""
4-Tier Supplier Questionnaire Engine.
Covers: Tier 1 (Essential/EH&S) → Tier 4 (Financial/Governance).
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Question:
    id: str
    tier: int
    category: str
    text: str
    unit: Optional[str] = None
    required: bool = True


TIER1_QUESTIONS = [
    Question("t1e_01", 1, "Energy", "What is your total annual energy consumption (kWh)?", "kWh"),
    Question(
        "t1e_02", 1, "Energy", "What percentage of your energy comes from renewable sources?", "%"
    ),
    Question("t1w_01", 1, "Water", "What is your total annual water withdrawal (m³)?", "m³"),
    Question("t1w_02", 1, "Water", "Do you have a water recycling program in place?", None),
    Question(
        "t1s_01",
        1,
        "Safety",
        "How many lost-time injuries occurred in the last 12 months?",
        "count",
    ),
    Question("t1s_02", 1, "Safety", "How many fatalities occurred in the last 12 months?", "count"),
    Question("t1s_03", 1, "Safety", "Do you have ISO 45001 certification?", None),
    Question("t1e_03", 1, "Emissions", "Have you measured your Scope 1 emissions (tCO2e)?", None),
    Question("t1e_04", 1, "Emissions", "Have you measured your Scope 2 emissions (tCO2e)?", None),
    Question("t1w_03", 1, "Waste", "What is your total annual waste generated (tonnes)?", "tonnes"),
    Question("t1w_04", 1, "Waste", "What percentage of waste is recycled or reused?", "%"),
]

TIER2_QUESTIONS = [
    Question(
        "t2l_01",
        2,
        "Labour",
        "What is the average hourly wage paid to workers (in local currency)?",
        "LCU",
    ),
    Question(
        "t2l_02", 2, "Labour", "What is the minimum wage as a percentage of living wage?", "%"
    ),
    Question(
        "t2l_03",
        2,
        "Labour",
        "How many workers are covered by collective bargaining agreements?",
        "count",
    ),
    Question(
        "t2l_04",
        2,
        "Labour",
        "What is the average weekly working hours for production staff?",
        "hours",
    ),
    Question(
        "t2l_05",
        2,
        "Labour",
        "Do you have a child labour policy prohibiting workers under 16?",
        None,
    ),
    Question("t2l_06", 2, "Labour", "What is the turnover rate for the past 12 months?", "%"),
    Question(
        "t2l_07", 2, "Labour", "What is the gender pay gap (female vs male average wage)?", "%"
    ),
]

TIER3_QUESTIONS = [
    Question(
        "t3f_01",
        3,
        "Fibre/Sourcing",
        "What percentage of cotton is certified organic or recycled?",
        "%",
    ),
    Question(
        "t3f_02",
        3,
        "Fibre/Sourcing",
        "Do you have a responsible sourcing policy for raw materials?",
        None,
    ),
    Question(
        "t3f_03",
        3,
        "Fibre/Sourcing",
        "What percentage of materials are sourced from certified sustainable sources?",
        "%",
    ),
    Question(
        "t3f_04", 3, "Fibre/Sourcing", "Do you have GOTS, OEKO-TEX, or GRS certification?", None
    ),
    Question(
        "t3f_05",
        3,
        "Fibre/Sourcing",
        "What is the traceability coverage of your supply chain (Tier 1 only)?",
        "%",
    ),
    Question(
        "t3f_06",
        3,
        "Fibre/Sourcing",
        "What percentage of packaging materials are recyclable or compostable?",
        "%",
    ),
]

TIER4_QUESTIONS = [
    Question(
        "t4g_01", 4, "Governance", "What percentage of your board of directors is independent?", "%"
    ),
    Question("t4g_02", 4, "Governance", "What percentage of board members are women?", "%"),
    Question(
        "t4g_03",
        4,
        "Governance",
        "Has your company undergone an independent financial audit in the past 12 months?",
        None,
    ),
    Question(
        "t4g_04",
        4,
        "Governance",
        "Do you have an anti-corruption policy covering all employees?",
        None,
    ),
    Question(
        "t4g_05",
        4,
        "Governance",
        "Have any ethics violations been reported in the past 24 months?",
        None,
    ),
    Question(
        "t4g_06",
        4,
        "Governance",
        "What is your data privacy compliance posture (GDPR or local equivalent)?",
        None,
    ),
    Question(
        "t4g_07",
        4,
        "Governance",
        "Do you maintain a grievance mechanism accessible to all workers?",
        None,
    ),
]

ALL_QUESTIONS = TIER1_QUESTIONS + TIER2_QUESTIONS + TIER3_QUESTIONS + TIER4_QUESTIONS
TIER_NAMES = {
    1: "Essential / EHS",
    2: "Labour Standards",
    3: "Fibre & Sourcing",
    4: "Financial & Governance",
}


@dataclass
class Questionnaire:
    supplier_id: str
    tier: int
    responses: dict[str, Any] = field(default_factory=dict)
    completed_at: Optional[str] = None

    def add_response(self, question_id: str, value: Any) -> None:
        self.responses[question_id] = value

    def completion_pct(self) -> float:
        tier_qs = [q.id for q in ALL_QUESTIONS if q.tier == self.tier]
        if not tier_qs:
            return 0.0
        answered = sum(1 for qid in tier_qs if qid in self.responses)
        return round(answered / len(tier_qs) * 100, 1)

    def to_dict(self) -> "dict[str, Any]":
        return {
            "supplier_id": self.supplier_id,
            "tier": self.tier,
            "tier_name": TIER_NAMES.get(self.tier, ""),
            "completion_pct": self.completion_pct(),
            "responses": self.responses,
            "completed_at": self.completed_at,
        }


def coverage_pct(responding: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(responding / total * 100, 1)


def get_tier_questions(tier: int) -> list[Question]:
    return [q for q in ALL_QUESTIONS if q.tier == tier]


def get_all_tiers() -> dict[int, list[Question]]:
    return {1: TIER1_QUESTIONS, 2: TIER2_QUESTIONS, 3: TIER3_QUESTIONS, 4: TIER4_QUESTIONS}


@dataclass
class QuestionnaireTemplate:
    """Template for a tiered supplier questionnaire."""

    template_id: str
    name: str
    tier: int
    description: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "tier": self.tier,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "active": self.active,
        }


@dataclass
class QuestionnaireQuestion:
    """Association between a template and a question, with ordering."""

    question_id: str
    template_id: str
    sequence: int
    required: bool = True
    weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "template_id": self.template_id,
            "sequence": self.sequence,
            "required": self.required,
            "weight": self.weight,
        }


@dataclass
class SupplierQuestionnaire:
    """Instance of a questionnaire sent to a specific supplier."""

    supplier_id: str
    template_id: str
    tier: int
    responses: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, sent, partially_completed, completed, expired
    sent_at: Optional[str] = None
    last_response_at: Optional[str] = None
    completed_at: Optional[str] = None
    reminder_count: int = 0
    preferred_channel: Optional[str] = None  # whatsapp, email, line, wechat

    def add_response(self, question_id: str, value: Any) -> None:
        self.responses[question_id] = value

    def completion_pct(self) -> float:
        tier_qs = [q.id for q in ALL_QUESTIONS if q.tier == self.tier]
        if not tier_qs:
            return 0.0
        answered = sum(1 for qid in tier_qs if qid in self.responses)
        return round(answered / len(tier_qs) * 100, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "supplier_id": self.supplier_id,
            "template_id": self.template_id,
            "tier": self.tier,
            "responses": self.responses,
            "status": self.status,
            "sent_at": self.sent_at,
            "last_response_at": self.last_response_at,
            "completed_at": self.completed_at,
            "reminder_count": self.reminder_count,
            "preferred_channel": self.preferred_channel,
        }
