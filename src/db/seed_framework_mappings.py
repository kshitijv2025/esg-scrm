"""
Seed the framework_mappings table with real ESG disclosure codes across four
major reporting frameworks: GRI, TCFD, CSRD/ESRS, and ISSB (IFRS S1/S2).

Each mapping links a platform KPI cluster to the relevant disclosure requirement
in one or more frameworks, enabling cross-framework gap analysis and automated
report generation.

Sources:
  - GRI Standards 2021 (Global Reporting Initiative)
  - TCFD Final Report: Recommendations of the Task Force on Climate-related
    Financial Disclosures (June 2017, updated June 2021)
  - EU CSRD / European Sustainability Reporting Standards (ESRS), as delegated
    acts adopted by the European Commission (July 2023)
  - ISSB IFRS S1 General Requirements for Disclosure of Sustainability-related
    Financial Information (June 2023)
  - ISSB IFRS S2 Climate-related Disclosures (June 2023)

Run:  python -m src.db.seed_framework_mappings
"""

from src.db.database import get_connection, release_connection, _execute

# ---------------------------------------------------------------------------
# Mapping tuples: (cluster, metric_name, framework, disclosure_code, description)
# ---------------------------------------------------------------------------

MAPPINGS: list[tuple[str, str, str, str, str]] = [
    # ======================================================================
    # energy_kwh — Energy consumption
    # ======================================================================
    # GRI
    (
        "energy_kwh",
        "Energy consumption",
        "GRI",
        "302-1",
        "Energy consumption within the organisation (joules or kWh, by fuel type)",
    ),
    (
        "energy_kwh",
        "Energy consumption",
        "GRI",
        "302-3",
        "Energy intensity (energy per unit of revenue, output, or employee)",
    ),
    (
        "energy_kwh",
        "Energy consumption",
        "GRI",
        "302-4",
        "Reduction of energy consumption (absolute and percentage)",
    ),
    # TCFD
    (
        "energy_kwh",
        "Energy consumption",
        "TCFD",
        "Metrics and Targets a",
        "Disclose the metrics used to assess climate-related risks and opportunities in line with strategy and risk management process",
    ),
    (
        "energy_kwh",
        "Energy consumption",
        "TCFD",
        "Metrics and Targets b",
        "Disclose Scope 1, Scope 2, and, if appropriate, Scope 3 GHG emissions and related risks",
    ),
    # CSRD/ESRS
    (
        "energy_kwh",
        "Energy consumption",
        "CSRD/ESRS",
        "E1-5",
        "Energy consumption and mix (total, from fossil vs renewable sources)",
    ),
    (
        "energy_kwh",
        "Energy consumption",
        "CSRD/ESRS",
        "E1-6",
        "Gross Scopes 1, 2, 3 GHG emissions and GHG removals from operations",
    ),
    (
        "energy_kwh",
        "Energy consumption",
        "CSRD/ESRS",
        "E1-7",
        "GHG removals and storage from operations and value chain",
    ),
    (
        "energy_kwh",
        "Energy consumption",
        "CSRD/ESRS",
        "E1-8",
        "Internal carbon pricing schemes",
    ),
    (
        "energy_kwh",
        "Energy consumption",
        "CSRD/ESRS",
        "E1-9",
        "Anticipated financial effects from climate-related risks and opportunities",
    ),
    # ISSB
    (
        "energy_kwh",
        "Energy consumption",
        "ISSB",
        "IFRS S2.29(a)",
        "Disclose absolute gross Scope 1 and Scope 2 GHG emissions",
    ),
    (
        "energy_kwh",
        "Energy consumption",
        "ISSB",
        "IFRS S2.29(b)",
        "Disclose gross Scope 3 GHG emissions if material",
    ),
    # ======================================================================
    # emissions_tco2 — Total GHG emissions (Scope 1+2+3)
    # ======================================================================
    # GRI
    (
        "emissions_tco2",
        "Total GHG emissions",
        "GRI",
        "305-1",
        "Direct (Scope 1) GHG emissions in tonnes CO2e",
    ),
    (
        "emissions_tco2",
        "Total GHG emissions",
        "GRI",
        "305-2",
        "Energy indirect (Scope 2) GHG emissions in tonnes CO2e (location and market based)",
    ),
    (
        "emissions_tco2",
        "Total GHG emissions",
        "GRI",
        "305-3",
        "Other indirect (Scope 3) GHG emissions by category in tonnes CO2e",
    ),
    (
        "emissions_tco2",
        "Total GHG emissions",
        "GRI",
        "305-4",
        "GHG emissions intensity (tonnes CO2e per unit of revenue, output, or employee)",
    ),
    # TCFD
    (
        "emissions_tco2",
        "Total GHG emissions",
        "TCFD",
        "Metrics and Targets b",
        "Disclose Scope 1, Scope 2, and Scope 3 GHG emissions",
    ),
    (
        "emissions_tco2",
        "Total GHG emissions",
        "TCFD",
        "Metrics and Targets c",
        "Describe the targets used to manage climate-related risks and opportunities and performance against targets",
    ),
    # CSRD/ESRS
    (
        "emissions_tco2",
        "Total GHG emissions",
        "CSRD/ESRS",
        "E1-6",
        "Gross Scopes 1, 2, 3 GHG emissions and GHG removals from operations",
    ),
    (
        "emissions_tco2",
        "Total GHG emissions",
        "CSRD/ESRS",
        "E1-1",
        "Transition plan for climate change mitigation aligned with 1.5C pathway",
    ),
    (
        "emissions_tco2",
        "Total GHG emissions",
        "CSRD/ESRS",
        "E1-2",
        "Policies related to climate change mitigation and adaptation",
    ),
    (
        "emissions_tco2",
        "Total GHG emissions",
        "CSRD/ESRS",
        "E1-3",
        "Actions and resources related to climate change policies",
    ),
    (
        "emissions_tco2",
        "Total GHG emissions",
        "CSRD/ESRS",
        "E1-4",
        "Targets related to climate change mitigation and adaptation",
    ),
    # ISSB
    (
        "emissions_tco2",
        "Total GHG emissions",
        "ISSB",
        "IFRS S2.29(a)",
        "Disclose absolute gross Scope 1 and Scope 2 GHG emissions",
    ),
    (
        "emissions_tco2",
        "Total GHG emissions",
        "ISSB",
        "IFRS S2.29(b)",
        "Disclose gross Scope 3 GHG emissions if material",
    ),
    (
        "emissions_tco2",
        "Total GHG emissions",
        "ISSB",
        "IFRS S2.29(c)",
        "Disclose total GHG emissions (Scope 1 + Scope 2 + Scope 3)",
    ),
    # ======================================================================
    # water_m3 — Water consumption
    # ======================================================================
    # GRI
    (
        "water_m3",
        "Water consumption",
        "GRI",
        "303-3",
        "Water withdrawal by source (megalitres, including surface, ground, seawater, third-party)",
    ),
    (
        "water_m3",
        "Water consumption",
        "GRI",
        "303-4",
        "Water discharge by destination (megalitres)",
    ),
    (
        "water_m3",
        "Water consumption",
        "GRI",
        "303-5",
        "Water consumption (withdrawal minus discharge, megalitres)",
    ),
    # TCFD
    (
        "water_m3",
        "Water consumption",
        "TCFD",
        "Strategy a",
        "Describe the climate-related risks and opportunities over the short, medium, and long term",
    ),
    (
        "water_m3",
        "Water consumption",
        "TCFD",
        "Strategy b",
        "Describe the impact of climate-related risks on business, strategy, and financial planning",
    ),
    # CSRD/ESRS
    (
        "water_m3",
        "Water consumption",
        "CSRD/ESRS",
        "E3-1",
        "Policies related to water and marine resources",
    ),
    (
        "water_m3",
        "Water consumption",
        "CSRD/ESRS",
        "E3-2",
        "Actions and resources related to water and marine resources policies",
    ),
    (
        "water_m3",
        "Water consumption",
        "CSRD/ESRS",
        "E3-3",
        "Targets related to water and marine resources",
    ),
    (
        "water_m3",
        "Water consumption",
        "CSRD/ESRS",
        "E3-4",
        "Water consumption performance (total, in water-stressed areas, by source)",
    ),
    (
        "water_m3",
        "Water consumption",
        "CSRD/ESRS",
        "E3-5",
        "Anticipated financial effects from water and marine resource-related risks",
    ),
    # ISSB
    (
        "water_m3",
        "Water consumption",
        "ISSB",
        "IFRS S1.26",
        "Disclose material sustainability-related risks and opportunities including water stress",
    ),
    # ======================================================================
    # scope3_category1 — Purchased goods & services
    # ======================================================================
    # GRI
    (
        "scope3_category1",
        "Purchased goods & services (Scope 3 Cat 1)",
        "GRI",
        "305-3",
        "Other indirect (Scope 3) GHG emissions — Category 1: Purchased goods and services",
    ),
    (
        "scope3_category1",
        "Purchased goods & services (Scope 3 Cat 1)",
        "GRI",
        "301-1",
        "Materials used by weight or volume (input materials for purchased goods)",
    ),
    (
        "scope3_category1",
        "Purchased goods & services (Scope 3 Cat 1)",
        "GRI",
        "301-3",
        "Reclaimed products and their packaging materials (percentage per product category)",
    ),
    # TCFD
    (
        "scope3_category1",
        "Purchased goods & services (Scope 3 Cat 1)",
        "TCFD",
        "Metrics and Targets b",
        "Disclose Scope 3 GHG emissions including purchased goods and services",
    ),
    (
        "scope3_category1",
        "Purchased goods & services (Scope 3 Cat 1)",
        "TCFD",
        "Risk Management a",
        "Describe processes for identifying and assessing climate-related risks over the value chain",
    ),
    # CSRD/ESRS
    (
        "scope3_category1",
        "Purchased goods & services (Scope 3 Cat 1)",
        "CSRD/ESRS",
        "E1-6",
        "Gross Scope 3 GHG emissions — includes purchased goods and services category",
    ),
    (
        "scope3_category1",
        "Purchased goods & services (Scope 3 Cat 1)",
        "CSRD/ESRS",
        "E2-1",
        "Policies related to pollution prevention and control",
    ),
    (
        "scope3_category1",
        "Purchased goods & services (Scope 3 Cat 1)",
        "CSRD/ESRS",
        "E2-2",
        "Actions and resources related to pollution policies",
    ),
    # ISSB
    (
        "scope3_category1",
        "Purchased goods & services (Scope 3 Cat 1)",
        "ISSB",
        "IFRS S2.29(b)",
        "Disclose gross Scope 3 GHG emissions — purchased goods and services",
    ),
    (
        "scope3_category1",
        "Purchased goods & services (Scope 3 Cat 1)",
        "ISSB",
        "IFRS S2.B14",
        "Scope 3 Category 1: Purchased goods and services (upstream)",
    ),
    # ======================================================================
    # scope3_category6 — Business travel
    # ======================================================================
    # GRI
    (
        "scope3_category6",
        "Business travel (Scope 3 Cat 6)",
        "GRI",
        "305-3",
        "Other indirect (Scope 3) GHG emissions — Category 6: Business travel",
    ),
    # TCFD
    (
        "scope3_category6",
        "Business travel (Scope 3 Cat 6)",
        "TCFD",
        "Metrics and Targets b",
        "Disclose Scope 3 GHG emissions including business travel",
    ),
    (
        "scope3_category6",
        "Business travel (Scope 3 Cat 6)",
        "TCFD",
        "Strategy a",
        "Describe climate-related risks including transition risks from business travel dependence",
    ),
    # CSRD/ESRS
    (
        "scope3_category6",
        "Business travel (Scope 3 Cat 6)",
        "CSRD/ESRS",
        "E1-6",
        "Gross Scope 3 GHG emissions — includes business travel category",
    ),
    # ISSB
    (
        "scope3_category6",
        "Business travel (Scope 3 Cat 6)",
        "ISSB",
        "IFRS S2.29(b)",
        "Disclose gross Scope 3 GHG emissions — business travel",
    ),
    # ======================================================================
    # diesel_consumed — Stationary combustion
    # ======================================================================
    # GRI
    (
        "diesel_consumed",
        "Stationary combustion (diesel)",
        "GRI",
        "302-1",
        "Energy consumption within the organisation — fuel combustion (diesel)",
    ),
    (
        "diesel_consumed",
        "Stationary combustion (diesel)",
        "GRI",
        "305-1",
        "Direct (Scope 1) GHG emissions from stationary combustion of diesel",
    ),
    # TCFD
    (
        "diesel_consumed",
        "Stationary combustion (diesel)",
        "TCFD",
        "Metrics and Targets a",
        "Disclose metrics for climate-related risks including fuel consumption metrics",
    ),
    (
        "diesel_consumed",
        "Stationary combustion (diesel)",
        "TCFD",
        "Metrics and Targets b",
        "Disclose Scope 1 GHG emissions from stationary combustion",
    ),
    # CSRD/ESRS
    (
        "diesel_consumed",
        "Stationary combustion (diesel)",
        "CSRD/ESRS",
        "E1-5",
        "Energy consumption and mix — fossil fuel consumption including diesel",
    ),
    (
        "diesel_consumed",
        "Stationary combustion (diesel)",
        "CSRD/ESRS",
        "E1-6",
        "Gross Scope 1 GHG emissions from stationary combustion",
    ),
    # ISSB
    (
        "diesel_consumed",
        "Stationary combustion (diesel)",
        "ISSB",
        "IFRS S2.29(a)",
        "Disclose absolute gross Scope 1 GHG emissions including stationary combustion",
    ),
    # ======================================================================
    # waste_generated — Waste management
    # ======================================================================
    # GRI
    (
        "waste_generated",
        "Waste management",
        "GRI",
        "306-3",
        "Waste generated (total by weight, hazardous and non-hazardous)",
    ),
    (
        "waste_generated",
        "Waste management",
        "GRI",
        "306-4",
        "Waste diverted from disposal (by recovery operation, hazardous and non-hazardous)",
    ),
    (
        "waste_generated",
        "Waste management",
        "GRI",
        "306-5",
        "Waste directed to disposal (by disposal operation, hazardous and non-hazardous)",
    ),
    # TCFD
    (
        "waste_generated",
        "Waste management",
        "TCFD",
        "Risk Management b",
        "Describe processes for managing climate-related risks including waste-related transition risks",
    ),
    # CSRD/ESRS
    (
        "waste_generated",
        "Waste management",
        "CSRD/ESRS",
        "E5-1",
        "Policies related to resource use and circular economy",
    ),
    (
        "waste_generated",
        "Waste management",
        "CSRD/ESRS",
        "E5-2",
        "Actions and resources related to resource use and circular economy policies",
    ),
    (
        "waste_generated",
        "Waste management",
        "CSRD/ESRS",
        "E5-3",
        "Targets related to resource use and circular economy",
    ),
    (
        "waste_generated",
        "Waste management",
        "CSRD/ESRS",
        "E5-4",
        "Resource inflows (materials used, recycled content share)",
    ),
    (
        "waste_generated",
        "Waste management",
        "CSRD/ESRS",
        "E5-5",
        "Resource outflows (waste generated, by type and disposal method)",
    ),
    # ISSB
    (
        "waste_generated",
        "Waste management",
        "ISSB",
        "IFRS S1.26",
        "Disclose material sustainability-related risks including waste and circular economy risks",
    ),
    # ======================================================================
    # labor_practices — Worker safety / conditions
    # ======================================================================
    # GRI
    (
        "labor_practices",
        "Worker safety and conditions",
        "GRI",
        "403-1",
        "Occupational health and safety management system",
    ),
    (
        "labor_practices",
        "Worker safety and conditions",
        "GRI",
        "403-2",
        "Hazard identification, risk assessment, incident investigation",
    ),
    (
        "labor_practices",
        "Worker safety and conditions",
        "GRI",
        "403-3",
        "Occupational health services",
    ),
    (
        "labor_practices",
        "Worker safety and conditions",
        "GRI",
        "403-4",
        "Worker participation and consultation on OHS",
    ),
    (
        "labor_practices",
        "Worker safety and conditions",
        "GRI",
        "403-5",
        "Worker training on occupational health and safety",
    ),
    (
        "labor_practices",
        "Worker safety and conditions",
        "GRI",
        "403-6",
        "Promotion of worker health",
    ),
    (
        "labor_practices",
        "Worker safety and conditions",
        "GRI",
        "403-7",
        "Prevention and mitigation of OHS impacts directly linked by business relationships",
    ),
    (
        "labor_practices",
        "Worker safety and conditions",
        "GRI",
        "403-8",
        "Workers covered by an OHS management system",
    ),
    (
        "labor_practices",
        "Worker safety and conditions",
        "GRI",
        "403-9",
        "Work-related injuries (type, rate, fatalities)",
    ),
    (
        "labor_practices",
        "Worker safety and conditions",
        "GRI",
        "403-10",
        "Work-related ill health",
    ),
    # CSRD/ESRS
    (
        "labor_practices",
        "Worker safety and conditions",
        "CSRD/ESRS",
        "S1-1",
        "Policies related to own workforce (working conditions, equal treatment, freedom of association, health and safety)",
    ),
    (
        "labor_practices",
        "Worker safety and conditions",
        "CSRD/ESRS",
        "S1-2",
        "Actions and resources related to own workforce policies",
    ),
    (
        "labor_practices",
        "Worker safety and conditions",
        "CSRD/ESRS",
        "S1-3",
        "Targets related to own workforce matters",
    ),
    (
        "labor_practices",
        "Worker safety and conditions",
        "CSRD/ESRS",
        "S1-4",
        "Information on health and safety indicators (fatalities, injuries, incidents)",
    ),
    (
        "labor_practices",
        "Worker safety and conditions",
        "CSRD/ESRS",
        "S1-5",
        "Anticipated financial effects from workforce-related risks",
    ),
    # ISSB
    (
        "labor_practices",
        "Worker safety and conditions",
        "ISSB",
        "IFRS S1.26",
        "Disclose material sustainability-related risks including workforce health and safety risks",
    ),
    # ======================================================================
    # supply_chain — Supplier ESG assessment
    # ======================================================================
    # GRI
    (
        "supply_chain",
        "Supplier ESG assessment",
        "GRI",
        "308-1",
        "New suppliers that were screened using environmental criteria (percentage)",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "GRI",
        "308-2",
        "Significant actual and potential negative environmental impacts in the supply chain and actions taken",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "GRI",
        "414-1",
        "New suppliers that were screened using social criteria (percentage)",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "GRI",
        "414-2",
        "Significant actual and potential negative social impacts in the supply chain and actions taken",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "GRI",
        "204-1",
        "Proportion of spending on local suppliers",
    ),
    # TCFD
    (
        "supply_chain",
        "Supplier ESG assessment",
        "TCFD",
        "Risk Management a",
        "Describe processes for identifying and assessing climate-related risks in the supply chain",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "TCFD",
        "Risk Management b",
        "Describe processes for managing climate-related risks in the supply chain",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "TCFD",
        "Risk Management c",
        "Describe how processes for identifying, assessing, and managing climate risks are integrated into overall risk management",
    ),
    # CSRD/ESRS
    (
        "supply_chain",
        "Supplier ESG assessment",
        "CSRD/ESRS",
        "S2-1",
        "Policies related to value chain workers (working conditions, health and safety in the supply chain)",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "CSRD/ESRS",
        "S2-2",
        "Actions and resources related to value chain worker policies",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "CSRD/ESRS",
        "S2-3",
        "Targets related to value chain workers",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "CSRD/ESRS",
        "S2-4",
        "Information on health and safety in the value chain (supplier incidents, audits)",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "CSRD/ESRS",
        "S2-5",
        "Anticipated financial effects from value chain worker-related risks",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "CSRD/ESRS",
        "G1-1",
        "Policies on business conduct (supplier code of conduct, due diligence)",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "CSRD/ESRS",
        "G1-2",
        "Actions and resources on business conduct (grievance mechanisms, supply chain audits)",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "CSRD/ESRS",
        "G1-3",
        "Targets on business conduct (anti-corruption, supplier screening coverage)",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "CSRD/ESRS",
        "G1-4",
        "Business conduct disclosures (confirmed incidents, penalties, supplier assessments)",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "CSRD/ESRS",
        "G1-5",
        "Anticipated financial effects from business conduct risks",
    ),
    # ISSB
    (
        "supply_chain",
        "Supplier ESG assessment",
        "ISSB",
        "IFRS S2.29(b)",
        "Disclose gross Scope 3 GHG emissions from upstream supply chain (purchased goods, transportation)",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "ISSB",
        "IFRS S2.B14",
        "Scope 3 Category 1: Purchased goods and services from suppliers",
    ),
    (
        "supply_chain",
        "Supplier ESG assessment",
        "ISSB",
        "IFRS S2.13(a)",
        "Describe significant climate-related risks and opportunities in the value chain",
    ),
]


def seed_framework_mappings() -> None:
    """Insert ESG framework disclosure mappings into the framework_mappings table.

    Idempotent: deletes all existing rows before re-inserting so repeated
    development runs produce a clean table.
    """
    conn = get_connection()

    # Remove any prior seed data so repeated runs stay idempotent.
    _execute(conn, "DELETE FROM framework_mappings")

    insert_sql = """
        INSERT INTO framework_mappings
            (org_id, cluster, metric_name, framework, disclosure_code, description)
        VALUES (?, ?, ?, ?, ?, ?)
    """

    count = 0
    for cluster, metric_name, framework, disclosure_code, description in MAPPINGS:
        _execute(
            conn,
            insert_sql,
            ("", cluster, metric_name, framework, disclosure_code, description),
        )
        count += 1

    release_connection(conn)
    print(f"Seeded {count} framework mappings into the database.")


if __name__ == "__main__":
    seed_framework_mappings()
