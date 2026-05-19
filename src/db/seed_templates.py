"""Seed the questionnaire_templates table with three default ESG assessment templates.

Templates cover three supplier tiers commonly used in garment/textile supply chains:
  - Tier 1: Full ESG Assessment (8 questions)
  - Tier 2: Environmental Focus (5 questions)
  - Tier 3: Quick Screening (3 questions)

Run:  python -m src.db.seed_templates
"""
import json

from src.db.database import get_connection, release_connection, _execute

# ---------------------------------------------------------------------------
# Default templates: (name, description, tier, questions_json)
# ---------------------------------------------------------------------------

TEMPLATES: list[tuple[str, str, int, str]] = [
    (
        "Tier 1 Supplier — Full ESG Assessment",
        "Comprehensive environmental, social, and governance assessment for highest-priority suppliers.",
        1,
        json.dumps([
            {"question_id": "T1Q1", "text": "What is your total annual energy consumption (kWh), and what percentage comes from renewable sources?"},
            {"question_id": "T1Q2", "text": "What are your total annual Scope 1 and Scope 2 greenhouse gas emissions (tonnes CO2e)?"},
            {"question_id": "T1Q3", "text": "What is your total annual water withdrawal (m3) and what percentage is recycled or reused?"},
            {"question_id": "T1Q4", "text": "Describe your labour practices: What policies exist for fair wages, working hours, and freedom of association?"},
            {"question_id": "T1Q5", "text": "What occupational health and safety systems are in place? Provide incident rates for the past 12 months."},
            {"question_id": "T1Q6", "text": "Describe your governance structure: board composition, anti-corruption policies, and whistleblower mechanisms."},
            {"question_id": "T1Q7", "text": "List all environmental and social certifications currently held (e.g., ISO 14001, SA8000, OEKO-TEX)."},
            {"question_id": "T1Q8", "text": "Describe any corrective actions from prior audits and their current status."},
        ]),
    ),
    (
        "Tier 2 Supplier — Environmental Focus",
        "Focused environmental assessment for medium-priority suppliers.",
        2,
        json.dumps([
            {"question_id": "T2Q1", "text": "What is your total annual energy consumption (kWh)?"},
            {"question_id": "T2Q2", "text": "What are your total annual greenhouse gas emissions (tonnes CO2e)?"},
            {"question_id": "T2Q3", "text": "What is your annual water consumption (m3)?"},
            {"question_id": "T2Q4", "text": "What is your waste generation volume and recycling rate (%)?"},
            {"question_id": "T2Q5", "text": "List any environmental certifications currently held (e.g., ISO 14001, Higg FEM)."},
        ]),
    ),
    (
        "Tier 3 Supplier — Quick Screening",
        "Rapid screening questionnaire for lower-priority suppliers.",
        3,
        json.dumps([
            {"question_id": "T3Q1", "text": "List all environmental and social certifications currently held."},
            {"question_id": "T3Q2", "text": "Have you had any environmental or labour compliance violations in the past 3 years? If yes, describe."},
            {"question_id": "T3Q3", "text": "Describe any corrective actions from prior audits and their current status."},
        ]),
    ),
]


def seed_templates() -> None:
    """Insert default questionnaire templates.

    Removes any prior seed data (org_id = '') before inserting so repeated
    development runs stay idempotent.
    """
    conn = get_connection()

    # Remove prior seed data so repeated runs stay idempotent.
    _execute(
        conn,
        "DELETE FROM questionnaire_templates WHERE org_id = ''",
    )

    insert_sql = """
        INSERT INTO questionnaire_templates
            (org_id, name, description, tier, questions)
        VALUES (?, ?, ?, ?, ?)
    """

    count = 0
    for name, description, tier, questions_json in TEMPLATES:
        _execute(conn, insert_sql, ("", name, description, tier, questions_json))
        count += 1

    release_connection(conn)
    print(f"Seeded {count} questionnaire templates into the database.")


if __name__ == "__main__":
    seed_templates()
