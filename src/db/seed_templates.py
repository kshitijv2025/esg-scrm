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
            {"question_id": "T1Q1", "text": "What is your total annual energy consumption (kWh), and what percentage comes from renewable sources?", "text_bn": "আপনার মোট বার্ষিক শক্তি ব্যবহার (kWh) কত এবং নবায়নযোগ্য উৎস থেকে কত শতাংশ আসে?", "text_vi": "Tổng tiêu thụ năng lượng hàng năm của bạn (kWh) là bao nhiêu và bao nhiêu phần trăm đến từ nguồn tái tạo?"},
            {"question_id": "T1Q2", "text": "What are your total annual Scope 1 and Scope 2 greenhouse gas emissions (tonnes CO2e)?", "text_bn": "আপনার মোট বার্ষিক স্কোপ 1 এবং স্কোপ 2 গ্রিনহাউস গ্যাস নির্গমন (টন CO2e) কত?", "text_vi": "Tổng lượng phát thải khí nhà kính Phạm vi 1 và Phạm vi 2 hàng năm của bạn (tấn CO2e) là bao nhiêu?"},
            {"question_id": "T1Q3", "text": "What is your total annual water withdrawal (m3) and what percentage is recycled or reused?", "text_bn": "আপনার মোট বার্ষিক পানি উত্তোলন (m3) কত এবং কত শতাংশ পুনর্ব্যবহৃত বা পুনর্চক্রিত?", "text_vi": "Tổng lượng nước rút ra hàng năm của bạn (m3) là bao nhiêu và bao nhiêu phần trăm được tái chế hoặc sử dụng lại?"},
            {"question_id": "T1Q4", "text": "Describe your labour practices: What policies exist for fair wages, working hours, and freedom of association?", "text_bn": "আপনার শ্রম অনুশীলন বর্ণনা করুন: সুষ্ঠু মজুরি, কাজের সময় এবং সংঘ স্বাধীনতার জন্য কী কী নীতি রয়েছে?", "text_vi": "Mô tả các thực hành lao động của bạn: Những chính sách nào tồn tại về lương công bằng, giờ làm việc và tự do lập hội?"},
            {"question_id": "T1Q5", "text": "What occupational health and safety systems are in place? Provide incident rates for the past 12 months.", "text_bn": "কী ধরনের পেশাদার স্বাস্থ্য ও নিরাপত্তা ব্যবস্থা রয়েছে? বিগত 12 মাসের ঘটনার হার প্রদান করুন।", "text_vi": "Những hệ thống an toàn và sức khỏe nghề nghiệp nào đang được áp dụng? Cung cấp tỷ lệ sự cố trong 12 tháng qua."},
            {"question_id": "T1Q6", "text": "Describe your governance structure: board composition, anti-corruption policies, and whistleblower mechanisms.", "text_bn": "আপনার শাসন কাঠামো বর্ণনা করুন: পরিচালনা পর্ষদের গঠন, দুর্নীতিবিরোধী নীতি এবং প্রতারণা প্রতিরোধমূলক ব্যবস্থা।", "text_vi": "Mô tả cơ cấu quản trị của bạn: thành phần hội đồng quản trị, chính sách chống tham nhũng và cơ chế bảo vệ người tố giác."},
            {"question_id": "T1Q7", "text": "List all environmental and social certifications currently held (e.g., ISO 14001, SA8000, OEKO-TEX).", "text_bn": "বর্তমানে রক্ষণাবেক্ষণকৃত সমস্ত পরিবেশগত এবং সামাজিক সার্টিফিকেশন তালিকাভুক্ত করুন (যেমন, ISO 14001, SA8000, OEKO-TEX)।", "text_vi": "Liệt kê tất cả các chứng nhận môi trường và xã hội hiện có (ví dụ: ISO 14001, SA8000, OEKO-TEX)."},
            {"question_id": "T1Q8", "text": "Describe any corrective actions from prior audits and their current status.", "text_bn": "পূর্ববর্তী অডিট থেকে কোনো সংশোধনী ব্যবস্থা এবং তাদের বর্তমান অবস্থা বর্ণনা করুন।", "text_vi": "Mô tả bất kỳ hành động khắc phục nào từ các cuộc kiểm toán trước đó và tình trạng hiện tại của chúng."},
        ]),
    ),
    (
        "Tier 2 Supplier — Environmental Focus",
        "Focused environmental assessment for medium-priority suppliers.",
        2,
        json.dumps([
            {"question_id": "T2Q1", "text": "What is your total annual energy consumption (kWh)?", "text_bn": "আপনার মোট বার্ষিক শক্তি ব্যবহার (kWh) কত?", "text_vi": "Tổng tiêu thụ năng lượng hàng năm của bạn (kWh) là bao nhiêu?"},
            {"question_id": "T2Q2", "text": "What are your total annual greenhouse gas emissions (tonnes CO2e)?", "text_bn": "আপনার মোট বার্ষিক গ্রিনহাউস গ্যাস নির্গমন (টন CO2e) কত?", "text_vi": "Tổng lượng phát thải khí nhà kính hàng năm của bạn (tấn CO2e) là bao nhiêu?"},
            {"question_id": "T2Q3", "text": "What is your annual water consumption (m3)?", "text_bn": "আপনার বার্ষিক পানি ব্যবহার (m3) কত?", "text_vi": "Lượng nước tiêu thụ hàng năm của bạn (m3) là bao nhiêu?"},
            {"question_id": "T2Q4", "text": "What is your waste generation volume and recycling rate (%)?", "text_bn": "আপনার বর্জ্য উৎপাদন ও পুনর্ব্যবহার হার (%) কত?", "text_vi": "Khối lượng tạo ra chất thải và tỷ lệ tái chế (%) của bạn là bao nhiêu?"},
            {"question_id": "T2Q5", "text": "List any environmental certifications currently held (e.g., ISO 14001, Higg FEM).", "text_bn": "বর্তমানে রক্ষণাবেক্ষণকৃত যেকোনো পরিবেশগত সার্টিফিকেশন তালিকাভুক্ত করুন (যেমন, ISO 14001, Higg FEM)।", "text_vi": "Liệt kê các chứng nhận môi trường hiện có (ví dụ: ISO 14001, Higg FEM)."},
        ]),
    ),
    (
        "Tier 3 Supplier — Quick Screening",
        "Rapid screening questionnaire for lower-priority suppliers.",
        3,
        json.dumps([
            {"question_id": "T3Q1", "text": "List all environmental and social certifications currently held.", "text_bn": "বর্তমানে রক্ষণাবেক্ষণকৃত সমস্ত পরিবেশগত এবং সামাজিক সার্টিফিকেশন তালিকাভুক্ত করুন।", "text_vi": "Liệt kê tất cả các chứng nhận môi trường và xã hội hiện có."},
            {"question_id": "T3Q2", "text": "Have you had any environmental or labour compliance violations in the past 3 years? If yes, describe.", "text_bn": "বিগত 3 বছরে আপনার কোনো পরিবেশগত বা শ্রম সম্মতি লঙ্ঘন হয়েছে কি? যদি হয়ে থাকে, বর্ণনা করুন।", "text_vi": "Bạn có bất kỳ vi phạm tuân thủ môi trường hoặc lao động nào trong 3 năm qua không? Nếu có, hãy mô tả."},
            {"question_id": "T3Q3", "text": "Describe any corrective actions from prior audits and their current status.", "text_bn": "পূর্ববর্তী অডিট থেকে কোনো সংশোধনী ব্যবস্থা এবং তাদের বর্তমান অবস্থা বর্ণনা করুন।", "text_vi": "Mô tả bất kỳ hành động khắc phục nào từ các cuộc kiểm toán trước đó và tình trạng hiện tại của chúng."},
        ]),
    ),
]


def seed_templates() -> None:
    """Insert default questionnaire templates.

    Removes any prior seed data (org_id = '') before inserting so repeated
    development runs stay idempotent. Also populates questionnaire_questions
    (canonical question storage) so template reads work correctly.
    """
    conn = get_connection()

    # Remove prior seed data so repeated runs stay idempotent.
    _execute(
        conn,
        "DELETE FROM questionnaire_templates WHERE org_id = ''",
    )
    # Also clean up orphaned question rows.
    _execute(
        conn,
        """
        DELETE FROM questionnaire_questions
        WHERE template_id IN (SELECT id FROM questionnaire_templates WHERE org_id = '')
        """,
    )

    insert_sql = """
        INSERT INTO questionnaire_templates
            (org_id, name, description, tier, questions)
        VALUES (?, ?, ?, ?, ?)
    """

    count = 0
    for name, description, tier, questions_json in TEMPLATES:
        cur = _execute(conn, insert_sql, ("", name, description, tier, questions_json))
        template_id = cur.lastrowid
        questions = json.loads(questions_json)
        for idx, q in enumerate(questions):
            _execute(
                conn,
                """
                INSERT INTO questionnaire_questions
                    (template_id, question_id, question_text, question_text_bn, question_text_vi, question_type, choices, sort_order, required)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    template_id,
                    q["question_id"],
                    q["text"],
                    q.get("text_bn"),
                    q.get("text_vi"),
                    q.get("question_type", "text"),
                    json.dumps(q["choices"]) if q.get("choices") else None,
                    idx + 1,
                    1 if q.get("required", True) else 0,
                ),
            )
        count += 1

    release_connection(conn)
    print(f"Seeded {count} questionnaire templates into the database.")


if __name__ == "__main__":
    seed_templates()
