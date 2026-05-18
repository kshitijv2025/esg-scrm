"""
Questionnaire API — backed by SQLite database + questionnaire engine.
"""
from fastapi import APIRouter

from src.db.database import (
    fetch_suppliers, fetch_supplier, fetch_coverage_stats,
    fetch_questionnaire_responses,
)
from src.supplier.questionnaire import (
    get_tier_questions, get_all_tiers, TIER_NAMES, ALL_QUESTIONS,
)

router = APIRouter()


@router.get("/suppliers")
def list_suppliers():
    suppliers = fetch_suppliers()
    return {"suppliers": suppliers, "total": len(suppliers)}


@router.get("/questionnaire/{qnr_id}")
def get_questionnaire(qnr_id: str):
    """Get a questionnaire with responses. For now, returns the demo questionnaire."""
    return {
        "id": "qnr_2025_q1_hmm",
        "buyer": "H&M",
        "template": "H&M ESG Questionnaire Q1 2025",
        "sent_at": "2025-01-15T09:00:00Z",
        "due_at": "2025-04-15T23:59:59Z",
        "language": "English",
        "channel": "whatsapp",
        "status": "partially_responded",
        "questions": [
            {"id": 1, "number": "1", "text": "Annual electricity consumption (kWh)", "response_type": "number", "unit": "kWh", "required": True, "answered": True, "answer": "4,820,000", "confidence": "HIGH", "submitted_at": "2025-01-18T14:22:00Z"},
            {"id": 2, "number": "2", "text": "Annual water withdrawal (m³)", "response_type": "number", "unit": "m³", "required": True, "answered": True, "answer": "12,400", "confidence": "HIGH", "submitted_at": "2025-01-18T14:22:00Z"},
            {"id": 3, "number": "3", "text": "Do you have renewable energy installed?", "response_type": "yes_no", "unit": None, "required": True, "answered": True, "answer": "Yes — 850 kW rooftop solar", "confidence": "HIGH", "submitted_at": "2025-01-18T14:23:00Z"},
            {"id": 4, "number": "4", "text": "Annual spend on raw cotton ($)", "response_type": "number", "unit": "$", "required": True, "answered": False, "answer": None, "confidence": None, "submitted_at": None},
            {"id": 5, "number": "5", "text": "Waste recycling rate (%)", "response_type": "number", "unit": "%", "required": False, "answered": False, "answer": None, "confidence": None, "submitted_at": None},
        ],
        "progress": {"answered": 3, "total": 5, "pending": 2},
    }


@router.get("/whatsapp-preview/{supplier_id}")
def whatsapp_preview(supplier_id: str):
    supplier = fetch_supplier(supplier_id)
    name = supplier["name"] if supplier else "Unknown Supplier"
    return {
        "supplier_name": name,
        "supplier_number": "+91 98765 43210",
        "message_preview": f"""H&M Supplier ESG Update

Dear {name} Team,

Please complete the following ESG data request for Q1 2025.

Reply with the question number followed by your answer.

1. Annual electricity consumption (kWh)
2. Annual water withdrawal (m3)
3. Do you have renewable energy installed?
4. Annual spend on raw cotton ($)
5. Waste recycling rate (%)

Due: April 15, 2025

Questions? Reply to this message.

- ESG Platform (on behalf of Bangladesh Export Textiles)""",
    }


@router.get("/coverage")
def coverage_stats():
    stats = fetch_coverage_stats()
    suppliers = fetch_suppliers()
    pending = [s for s in suppliers if s.get("questionnaire_status") == "pending"]
    return {
        "coverage_rate": stats["coverage_pct"],
        "responding_suppliers": stats["responding_suppliers"],
        "total_suppliers": stats["total_suppliers"],
        "procurement_spend_covered": stats["covered_spend"],
        "total_procurement_spend": stats["total_spend"],
        "pending_suppliers": [
            {"name": s["name"], "spend": s["annual_spend_usd"], "channel": s["preferred_channel"]}
            for s in pending
        ],
    }


@router.get("/coverage-stats")
def coverage_stats_v2():
    stats = fetch_coverage_stats()
    return {
        "total_coverage": stats["spend_coverage_pct"],
        "previous_coverage": 64.0,
        "responding_suppliers": stats["responding_suppliers"],
        "total_suppliers": stats["total_suppliers"],
    }


@router.get("/tiers")
def list_tiers():
    """List all 4 questionnaire tiers from the questionnaire engine."""
    tiers = get_all_tiers()
    return {
        "tiers": [
            {
                "tier": tier_num,
                "name": TIER_NAMES[tier_num],
                "description": f"{TIER_NAMES[tier_num]} questionnaire tier",
                "question_count": len(questions),
            }
            for tier_num, questions in tiers.items()
        ]
    }


@router.get("/tiers/{tier}")
def get_tier(tier: int):
    """Get questions for a specific tier from the questionnaire engine."""
    questions = get_tier_questions(tier)
    if not questions:
        return {"error": "tier not found"}, 404
    return {
        "tier": tier,
        "name": TIER_NAMES.get(tier, ""),
        "description": f"{TIER_NAMES.get(tier, '')} questionnaire tier",
        "questions": [
            {
                "id": q.id,
                "number": str(i + 1),
                "text": q.text,
                "response_type": "number" if q.unit else "yes_no",
                "unit": q.unit,
                "required": q.required,
            }
            for i, q in enumerate(questions)
        ],
    }


@router.get("/whatsapp-template/{tier}")
def get_whatsapp_template(tier: int, supplier_id: str = "sup_001"):
    """Generate WhatsApp message template for a tier + supplier."""
    questions = get_tier_questions(tier)
    if not questions:
        return {"error": "tier not found"}, 404

    supplier = fetch_supplier(supplier_id)
    supplier_name = supplier["name"] if supplier else "Supplier"

    lines = []
    for i, q in enumerate(questions, 1):
        lines.append(f"{i}. {q.text}")
        if q.unit:
            lines.append(f"   Example: {i}. [value in {q.unit}]")
        else:
            lines.append(f"   Example: {i}. Yes/No")

    message = f"""H&M Supplier ESG Update

Dear {supplier_name} Team,

Please complete {TIER_NAMES.get(tier, '')} of the H&M ESG data request for Q1 2025.

Reply with the question number followed by your answer.

{chr(10).join(lines)}

Due: April 15, 2025

Questions? Reply to this message.

- ESG Platform (on behalf of H&M)"""

    return {
        "tier": tier,
        "tier_name": TIER_NAMES.get(tier, ""),
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "channel": "whatsapp",
        "message": message,
    }
