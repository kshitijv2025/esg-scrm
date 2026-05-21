"""
Seed the database with demo data.
Works with both SQLite (dev/test) and PostgreSQL (production).
Run once: python -m src.db.seed
"""

import uuid
from datetime import datetime, timezone

from src.db.database import reset_database, get_connection, release_connection, _execute
from src.evidence.hash_chain import compute_hash

ORG_ID = "org_bd_001"
FACTORY_ID = "factory_bd_001"


def seed() -> None:
    reset_database()
    conn = get_connection(row_factory=False)

    _seed_org_and_admin(conn)
    _seed_metrics_and_evidence(conn)
    _seed_risk_flags(conn)
    _seed_suppliers(conn)
    _seed_supplier_scope3(conn)
    _seed_questionnaire_responses(conn)

    release_connection(conn)
    print("Seeded database successfully")


def _seed_org_and_admin(conn) -> None:
    """Seed demo organization and admin user."""
    from src.auth.password import hash_password

    _execute(
        conn,
        """
        INSERT INTO organizations (id, name, industry, employee_count, primary_buyer, annual_revenue_usd, connected_since)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "org_bd_001",
            "Bangladesh Export Textiles Ltd.",
            "Garment manufacturing",
            3200,
            "H&M",
            42000000,
            "2024-09-15",
        ),
    )

    _execute(
        conn,
        """
        INSERT INTO users (id, org_id, email, password_hash, full_name, role)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            "usr_admin_001",
            ORG_ID,
            "admin@textilebd.com",
            hash_password("admin123"),
            "System Administrator",
            "admin",
        ),
    )


def _seed_metrics_and_evidence(conn) -> None:
    """Seed metrics with real SHA-256 evidence chain."""
    metrics_data = [
        {
            "cluster": "energy_kwh",
            "value": 2847320,
            "unit": "kWh",
            "confidence": "HIGH",
            "source": "SAP Business One — Utility Invoices",
            "period": "January 2025",
            "recorded_at": "2025-01-31T23:59:00Z",
            "production_volume": 100000,
            "renewable_kwh": 850000,
        },
        {
            "cluster": "emissions_tco2",
            "value": 892.4,
            "unit": "tCO2e",
            "confidence": "HIGH",
            "source": "Calculated — energy × grid factor",
            "period": "January 2025",
            "recorded_at": "2025-01-31T23:59:00Z",
        },
        {
            "cluster": "water_m3",
            "value": 18430,
            "unit": "m³",
            "confidence": "HIGH",
            "source": "SAP Business One — Municipal Water Bills",
            "period": "January 2025",
            "recorded_at": "2025-01-31T23:59:00Z",
            "wastewater_discharge": 4200,
        },
        {
            "cluster": "scope3_category1",
            "value": 4281.7,
            "unit": "tCO2e",
            "confidence": "MEDIUM",
            "source": "Supplier questionnaires + spend-based fallback",
            "period": "Q4 2024",
            "recorded_at": "2024-12-31T23:59:00Z",
        },
        {
            "cluster": "diesel_consumed",
            "value": 49.3,
            "unit": "tCO2e",
            "confidence": "MEDIUM",
            "source": "Manual entry — diesel generator consumption log",
            "period": "Q4 2024",
            "recorded_at": "2024-12-31T23:59:00Z",
        },
        {
            "cluster": "scope3_category6",
            "value": 37.0,
            "unit": "tCO2e",
            "confidence": "LOW",
            "source": "Manual calculation — travel expense claims × GHG emission factors",
            "period": "Q4 2024",
            "recorded_at": "2024-12-31T23:59:00Z",
        },
    ]

    trends = [
        {
            "cluster": "energy_kwh",
            "months": [
                ("2024-09-30T23:59:00Z", 2710400),
                ("2024-10-31T23:59:00Z", 2789200),
                ("2024-11-30T23:59:00Z", 2823600),
                ("2024-12-31T23:59:00Z", 2798100),
                ("2025-01-31T23:59:00Z", 2847320),
            ],
        },
        {
            "cluster": "emissions_tco2",
            "months": [
                ("2024-09-30T23:59:00Z", 1392.4),
                ("2024-10-31T23:59:00Z", 1321.8),
                ("2024-11-30T23:59:00Z", 1056.2),
                ("2024-12-31T23:59:00Z", 998.7),
                ("2025-01-31T23:59:00Z", 892.4),
            ],
        },
        {
            "cluster": "water_m3",
            "months": [
                ("2024-09-30T23:59:00Z", 17820),
                ("2024-10-31T23:59:00Z", 18210),
                ("2024-11-30T23:59:00Z", 18390),
                ("2024-12-31T23:59:00Z", 18295),
                ("2025-01-31T23:59:00Z", 18430),
            ],
        },
    ]

    prev_hash = None
    all_records = []

    for trend in trends:
        for timestamp, value in trend["months"][:-1]:
            all_records.append(
                {
                    "cluster": trend["cluster"],
                    "value": value,
                    "timestamp": timestamp,
                    "unit": "kWh"
                    if trend["cluster"] == "energy_kwh"
                    else "tCO2e"
                    if trend["cluster"] == "emissions_tco2"
                    else "m³",
                    "confidence": "HIGH",
                    "source": "Historical data",
                    "period": timestamp[:7],
                }
            )

    for m in metrics_data:
        all_records.append(
            {
                "cluster": m["cluster"],
                "value": m["value"],
                "timestamp": m["recorded_at"],
                "unit": m["unit"],
                "confidence": m["confidence"],
                "source": m["source"],
                "period": m["period"],
                "production_volume": m.get("production_volume"),
                "renewable_kwh": m.get("renewable_kwh"),
                "wastewater_discharge": m.get("wastewater_discharge"),
            }
        )

    for rec in all_records:
        the_hash = compute_hash(rec["cluster"], rec["value"], rec["timestamp"], prev_hash)

        stored_hash = (
            f"TAMPERED_{the_hash[:32]}" if rec["cluster"] == "diesel_consumed" else the_hash
        )

        production_volume = rec.get("production_volume")
        renewable_kwh = rec.get("renewable_kwh")
        wastewater_discharge = rec.get("wastewater_discharge")
        cur = _execute(
            conn,
            """
            INSERT INTO metrics (org_id, factory_id, cluster, value, unit, confidence, source, period, recorded_at, production_volume, renewable_kwh, wastewater_discharge)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                ORG_ID,
                FACTORY_ID,
                rec["cluster"],
                rec["value"],
                rec["unit"],
                rec["confidence"],
                rec["source"],
                rec["period"],
                rec["timestamp"],
                production_volume,
                renewable_kwh,
                wastewater_discharge,
            ),
        )
        metric_id = cur.lastrowid
        _execute(
            conn,
            """
            INSERT INTO evidence_chain (metric_id, cluster, hash, prev_hash, value, computed_at, source_system)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                metric_id,
                rec["cluster"],
                stored_hash,
                prev_hash,
                rec["value"],
                datetime.now(timezone.utc).isoformat(),
                "seed",
            ),
        )
        prev_hash = the_hash


def _seed_risk_flags(conn) -> None:
    flags = [
        {
            "id": "flag_001",
            "flag_text": "Water consumption 18% above regulatory threshold for Q4 2024",
            "cluster": "G6",
            "severity": "WARNING",
            "days_overdue": 45,
            "priority_score": 3.0,
            "created_at": "2024-10-15T09:00:00Z",
            "acknowledged": 0,
        },
        {
            "id": "flag_002",
            "flag_text": "Supplier financial health score declined below 60 — risk of supply disruption",
            "cluster": "G5",
            "severity": "CRITICAL",
            "days_overdue": 12,
            "priority_score": 3.96,
            "created_at": "2024-12-01T14:30:00Z",
            "acknowledged": 0,
        },
        {
            "id": "flag_003",
            "flag_text": "Scope 3 Category 1 coverage at 64% — below 70% target for H&M reporting",
            "cluster": "G4",
            "severity": "INFO",
            "days_overdue": 0,
            "priority_score": 0.0,
            "created_at": "2025-01-10T10:00:00Z",
            "acknowledged": 0,
        },
        {
            "id": "flag_004",
            "flag_text": "Diesel generator log — evidence chain broken, data integrity concern",
            "cluster": "G1",
            "severity": "CRITICAL",
            "days_overdue": 3,
            "priority_score": 0.9,
            "created_at": "2025-01-27T08:00:00Z",
            "acknowledged": 1,
            "acknowledged_at": "2025-01-28T11:00:00Z",
            "acknowledged_by": "ops@textilebd.com",
        },
        {
            "id": "flag_005",
            "flag_text": "Gender pay gap metric missing for Tier 2 suppliers — compliance gap",
            "cluster": "G3",
            "severity": "WARNING",
            "days_overdue": 30,
            "priority_score": 2.0,
            "created_at": "2024-11-20T09:00:00Z",
            "acknowledged": 0,
        },
    ]
    for f in flags:
        _execute(
            conn,
            """
            INSERT INTO risk_flags (id, org_id, factory_id, flag_text, cluster, severity, days_overdue,
               priority_score, created_at, acknowledged, acknowledged_at, acknowledged_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                f["id"],
                ORG_ID,
                FACTORY_ID,
                f["flag_text"],
                f["cluster"],
                f["severity"],
                f["days_overdue"],
                f["priority_score"],
                f["created_at"],
                f["acknowledged"],
                f.get("acknowledged_at"),
                f.get("acknowledged_by"),
            ),
        )


def _seed_suppliers(conn) -> None:
    suppliers = [
        {
            "id": "sup_001",
            "name": "Gujarat Cotton Traders",
            "country": "IN",
            "industry": "Cotton trading",
            "tier": "tier2",
            "annual_spend_usd": 2400000,
            "phone": "+91-9876543210",
            "preferred_channel": "whatsapp",
            "questionnaire_status": "responded",
            "risk_tier": "A",
            "risk_score": 2.1,
            "active_flags": 0,
            "certifications": "GOTS,OEKO-TEX",
        },
        {
            "id": "sup_002",
            "name": "Vietnam Fabrics Co.",
            "country": "VN",
            "industry": "Fabric manufacturing",
            "tier": "tier2",
            "annual_spend_usd": 3200000,
            "phone": "+84-901234567",
            "preferred_channel": "whatsapp",
            "questionnaire_status": "responded",
            "risk_tier": "B",
            "risk_score": 5.8,
            "active_flags": 2,
            "certifications": "OEKO-TEX,GRS",
        },
        {
            "id": "sup_003",
            "name": "Bangladesh Dye House Ltd.",
            "country": "BD",
            "industry": "Dyeing & finishing",
            "tier": "tier1",
            "annual_spend_usd": 8400000,
            "phone": "+880-171234567",
            "preferred_channel": "whatsapp",
            "questionnaire_status": "pending",
            "risk_tier": "A",
            "risk_score": 3.4,
            "active_flags": 1,
            "certifications": "GOTS,WRAP,SMETA",
        },
        {
            "id": "sup_004",
            "name": "Thai Thread Industries",
            "country": "TH",
            "industry": "Thread manufacturing",
            "tier": "tier2",
            "annual_spend_usd": 1800000,
            "phone": "+66-812345678",
            "preferred_channel": "line",
            "questionnaire_status": "pending",
            "risk_tier": "B",
            "risk_score": 6.2,
            "active_flags": 1,
            "certifications": "GOTS,BCI",
        },
        {
            "id": "sup_005",
            "name": "Myanmar Packaging Co.",
            "country": "MM",
            "industry": "Packaging materials",
            "tier": "tier3",
            "annual_spend_usd": 480000,
            "phone": "+95-912345678",
            "preferred_channel": "email",
            "questionnaire_status": "not_sent",
            "risk_tier": "C",
            "risk_score": 9.1,
            "active_flags": 4,
            "certifications": "",
        },
        {
            "id": "sup_006",
            "name": "Indonesia Synthetic Fibers",
            "country": "ID",
            "industry": "Synthetic fiber manufacturing",
            "tier": "tier2",
            "annual_spend_usd": 4200000,
            "phone": "+62-81234567890",
            "preferred_channel": "whatsapp",
            "questionnaire_status": "responded",
            "risk_tier": "B",
            "risk_score": 7.1,
            "active_flags": 2,
            "certifications": "OEKO-TEX",
        },
        {
            "id": "sup_007",
            "name": "India Zippers & Hardware",
            "country": "IN",
            "industry": "Trims & accessories",
            "tier": "tier3",
            "annual_spend_usd": 620000,
            "phone": "+91-9876501234",
            "preferred_channel": "whatsapp",
            "questionnaire_status": "responded",
            "risk_tier": "C",
            "risk_score": 8.4,
            "active_flags": 3,
            "certifications": "ISO 14001",
        },
    ]
    for s in suppliers:
        _execute(
            conn,
            """
            INSERT INTO suppliers (id, org_id, name, country, industry, tier, annual_spend_usd,
               phone, preferred_channel, questionnaire_status, risk_tier, risk_score, active_flags, certifications)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                s["id"],
                ORG_ID,
                s["name"],
                s["country"],
                s["industry"],
                s["tier"],
                s["annual_spend_usd"],
                s["phone"],
                s["preferred_channel"],
                s["questionnaire_status"],
                s["risk_tier"],
                s["risk_score"],
                s["active_flags"],
                s["certifications"],
            ),
        )


def _seed_supplier_scope3(conn) -> None:
    records = [
        {
            "supplier_id": "sup_001",
            "category": "Purchased Goods",
            "annual_spend_usd": 2400000,
            "scope3_tco2e": 412.8,
            "calculation_method": "spend_based",
            "emission_factor": "GHG Protocol 2022 — cotton, $0.94/kg CO2",
            "confidence": "MEDIUM",
            "data_source": "Questionnaire Q1 2025 — responded Jan 18",
        },
        {
            "supplier_id": "sup_002",
            "category": "Finished fabrics",
            "annual_spend_usd": 3200000,
            "scope3_tco2e": 580.8,
            "calculation_method": "spend_based",
            "emission_factor": "GHG Protocol 2022 — textiles, $0.94/kg CO2",
            "confidence": "MEDIUM",
            "data_source": "Questionnaire Q1 2025 — responded Jan 20",
        },
        {
            "supplier_id": "sup_003",
            "category": "Dyeing & finishing",
            "annual_spend_usd": 8400000,
            "scope3_tco2e": 1848.0,
            "calculation_method": "spend_based",
            "emission_factor": "GHG Protocol 2022 — textiles, $0.94/kg CO2",
            "confidence": "LOW",
            "data_source": "Spend-based estimate — supplier not yet responded",
        },
        {
            "supplier_id": "sup_004",
            "category": "Thread manufacturing",
            "annual_spend_usd": 1800000,
            "scope3_tco2e": 369.0,
            "calculation_method": "spend_based",
            "emission_factor": "GHG Protocol 2022 — industry average",
            "confidence": "LOW",
            "data_source": "Spend-based estimate — supplier not yet responded",
        },
        {
            "supplier_id": "sup_006",
            "category": "Synthetic fibers",
            "annual_spend_usd": 4200000,
            "scope3_tco2e": 1060.9,
            "calculation_method": "spend_based",
            "emission_factor": "GHG Protocol 2022 — synthetics, $0.94/kg CO2",
            "confidence": "MEDIUM",
            "data_source": "Questionnaire Q1 2025 — responded Jan 22",
        },
        {
            "supplier_id": "sup_007",
            "category": "Trims & accessories",
            "annual_spend_usd": 620000,
            "scope3_tco2e": 10.2,
            "calculation_method": "spend_based",
            "emission_factor": "GHG Protocol 2022 — industry average",
            "confidence": "LOW",
            "data_source": "Spend-based estimate",
        },
    ]
    for r in records:
        _execute(
            conn,
            """
            INSERT INTO supplier_scope3 (org_id, supplier_id, category, annual_spend_usd, scope3_tco2e,
               calculation_method, emission_factor, confidence, data_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                ORG_ID,
                r["supplier_id"],
                r["category"],
                r["annual_spend_usd"],
                r["scope3_tco2e"],
                r["calculation_method"],
                r["emission_factor"],
                r["confidence"],
                r["data_source"],
            ),
        )


def _seed_questionnaire_responses(conn) -> None:
    responses = [
        {
            "supplier_id": "sup_001",
            "tier": 1,
            "question_id": "1",
            "response_text": "4,820,000",
            "response_value": 4820000,
            "channel": "whatsapp",
        },
        {
            "supplier_id": "sup_001",
            "tier": 1,
            "question_id": "2",
            "response_text": "12,400",
            "response_value": 12400,
            "channel": "whatsapp",
        },
        {
            "supplier_id": "sup_001",
            "tier": 1,
            "question_id": "3",
            "response_text": "Yes — 850 kW rooftop solar",
            "response_value": None,
            "channel": "whatsapp",
        },
        {
            "supplier_id": "sup_002",
            "tier": 1,
            "question_id": "1",
            "response_text": "3,210,000",
            "response_value": 3210000,
            "channel": "whatsapp",
        },
        {
            "supplier_id": "sup_002",
            "tier": 1,
            "question_id": "2",
            "response_text": "8,900",
            "response_value": 8900,
            "channel": "whatsapp",
        },
        {
            "supplier_id": "sup_006",
            "tier": 1,
            "question_id": "1",
            "response_text": "5,400,000",
            "response_value": 5400000,
            "channel": "whatsapp",
        },
        {
            "supplier_id": "sup_006",
            "tier": 1,
            "question_id": "2",
            "response_text": "15,200",
            "response_value": 15200,
            "channel": "whatsapp",
        },
        {
            "supplier_id": "sup_007",
            "tier": 1,
            "question_id": "1",
            "response_text": "920,000",
            "response_value": 920000,
            "channel": "whatsapp",
        },
    ]
    for r in responses:
        _execute(
            conn,
            """
            INSERT INTO questionnaire_responses (org_id, supplier_id, tier, question_id, response_text, response_value, channel)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                ORG_ID,
                r["supplier_id"],
                r["tier"],
                r["question_id"],
                r["response_text"],
                r["response_value"],
                r["channel"],
            ),
        )


if __name__ == "__main__":
    seed()
