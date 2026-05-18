"""Framework mapping API — investor demo"""
from fastapi import APIRouter

router = APIRouter()

FRAMEWORK_OUTPUTS = {
    "energy_kwh_2847320": {
        "csrd_esrs_e1": {
            "field_id": "ESRS E1-13",
            "label": "Energy consumption within the organization",
            "value": "2,847,320 kWh",
            "unit": "kWh",
            "breakdown": {
                "electricity": "2,847,320 kWh",
                "renewable": "312,005 kWh (11%)",
                "non_renewable": "2,535,315 kWh (89%)",
            },
            "methodology": "Direct measurement — SAP Business One utility invoices",
            "confidence": "HIGH",
        },
        "issb_ifrs_s2": {
            "field_id": "IFRS S2-13",
            "label": "Climate-related targets — energy consumption",
            "value": "2,847,320 kWh",
            "unit": "kWh",
            "methodology": "Direct measurement",
            "confidence": "HIGH",
        },
        "gri_302_1": {
            "field_id": "GRI 302-1",
            "label": "Energy consumption within the organization",
            "value": "2,847,320 kWh",
            "unit": "GJ: 10,250 GJ",
            "breakdown": {
                "electricity": "10,250 GJ",
                "diesel": "0 GJ",
            },
            "methodology": "Direct measurement — meter readings",
            "confidence": "HIGH",
        },
        "tcfd_metrics": {
            "field_id": "TCFD-M-4",
            "label": "Amount of energy consumed",
            "value": "2,847,320 kWh",
            "unit": "kWh",
            "methodology": "Direct measurement",
            "confidence": "HIGH",
        },
    },
    "diesel_consumed": {
        "csrd_esrs_e1": {
            "field_id": "ESRS E1-3",
            "label": "Direct GHG emissions — Scope 1",
            "value": "49.3 tCO2e",
            "unit": "tCO2e",
            "breakdown": {
                "diesel_liters": "18,400 L",
                "conversion_factor": "2.68 kg CO2/L (diesel)",
            },
            "methodology": "Manual entry — diesel generator consumption log",
            "confidence": "MEDIUM",
        },
        "issb_ifrs_s2": {
            "field_id": "IFRS S2-14",
            "label": "Scope 1 emissions — fuel combustion",
            "value": "49.3 tCO2e",
            "unit": "tCO2e",
            "methodology": "Activity-based — liters consumed × emission factor",
            "confidence": "MEDIUM",
        },
        "gri_305_1": {
            "field_id": "GRI 305-1",
            "label": "Direct (Scope 1) GHG emissions",
            "value": "49.3 tCO2e",
            "unit": "tCO2e",
            "methodology": "Direct measurement — diesel generator log",
            "confidence": "MEDIUM",
        },
        "tcfd_metrics": {
            "field_id": "TCFD-S1-1",
            "label": "Scope 1 emissions — diesel",
            "value": "49.3 tCO2e",
            "unit": "tCO2e",
            "methodology": "Manual calculation",
            "confidence": "MEDIUM",
        },
    },
    "scope3_cat6_business_travel": {
        "csrd_esrs_e1": {
            "field_id": "ESRS E1-7",
            "label": "Gross Scope 3 GHG emissions — Category 6 (Business Travel)",
            "value": "37.0 tCO2e",
            "unit": "tCO2e",
            "breakdown": {
                "flights_km": "98,400 km",
                "hotels_nights": "840 nights",
                "rental_cars_km": "18,200 km",
            },
            "methodology": "Manual entry — travel expense claims × GHG Protocol emission factors",
            "confidence": "LOW",
        },
        "issb_ifrs_s2": {
            "field_id": "IFRS S2-16",
            "label": "Scope 3 emissions — Category 6 Business Travel",
            "value": "37.0 tCO2e",
            "unit": "tCO2e",
            "methodology": "Activity-based — flight km + hotel nights + car km",
            "confidence": "LOW",
        },
        "gri_305_3": {
            "field_id": "GRI 305-3",
            "label": "Other indirect (Scope 3) GHG emissions — business travel",
            "value": "37.0 tCO2e",
            "unit": "tCO2e",
            "methodology": "Expense report totals × emission factors",
            "confidence": "LOW",
        },
    },
    "scope3_cat1_4281": {
        "csrd_esrs_e1": {
            "field_id": "ESRS E1-6",
            "label": "Gross Scope 3 GHG emissions — Category 1",
            "value": "4,281.7 tCO2e",
            "unit": "tCO2e",
            "breakdown": {
                "purchased_goods": "3,840 tCO2e",
                "transportation": "312 tCO2e",
                "waste": "129.7 tCO2e",
            },
            "methodology": "Activity-based + supplier-specific (47 of 73 suppliers responded)",
            "confidence": "MEDIUM",
            "coverage_note": "64% of procurement spend covered",
        },
        "issb_ifrs_s2": {
            "field_id": "IFRS S2-15",
            "label": "Scope 3 emissions — Category 1 (Purchased goods)",
            "value": "4,281.7 tCO2e",
            "unit": "tCO2e",
            "methodology": "Activity-based",
            "confidence": "MEDIUM",
        },
        "gri_305_3": {
            "field_id": "GRI 305-3",
            "label": "Other indirect (Scope 3) GHG emissions",
            "value": "4,281.7 tCO2e",
            "unit": "tCO2e",
            "methodology": "GHG Protocol Category 1 — spend-based with supplier-specific overrides",
            "confidence": "MEDIUM",
        },
    },
}

# Additional cluster mappings (expanding from 4 to 14)
FRAMEWORK_OUTPUTS["water_m3_18430"] = {
    "csrd_esrs_e3": {
        "field_id": "ESRS E3-1",
        "label": "Water consumption within the organization",
        "value": "18,430 m³",
        "unit": "m³",
        "breakdown": {"municipal_water": "16,200 m³", "groundwater": "2,230 m³"},
        "methodology": "Direct measurement — municipal water bills + borewell meter",
        "confidence": "HIGH",
    },
    "issb_ifrs_s2_water": {
        "field_id": "IFRS S2-17",
        "label": "Water security — consumption",
        "value": "18,430 m³",
        "unit": "m³",
        "methodology": "Direct measurement",
        "confidence": "HIGH",
    },
    "gri_303_3": {
        "field_id": "GRI 303-3",
        "label": "Water withdrawal by source",
        "value": "18,430 m³",
        "unit": "m³",
        "breakdown": {"municipal": "16,200 m³", "groundwater": "2,230 m³"},
        "methodology": "Direct measurement — utility bills",
        "confidence": "HIGH",
    },
    "tcfd_water": {
        "field_id": "TCFD-W-1",
        "label": "Water consumption",
        "value": "18,430 m³",
        "unit": "m³",
        "methodology": "Direct measurement",
        "confidence": "HIGH",
    },
}

FRAMEWORK_OUTPUTS["waste_tonnes"] = {
    "csrd_esrs_e5": {
        "field_id": "ESRS E5-1",
        "label": "Waste generated — hazardous and non-hazardous",
        "value": "842 tonnes",
        "unit": "tonnes",
        "breakdown": {"hazardous": "12 tonnes", "non_hazardous": "830 tonnes"},
        "methodology": "Direct measurement — waste manifests",
        "confidence": "MEDIUM",
    },
    "gri_306_3": {
        "field_id": "GRI 306-3",
        "label": "Waste generated",
        "value": "842 tonnes",
        "unit": "tonnes",
        "methodology": "Waste manifest aggregation",
        "confidence": "MEDIUM",
    },
}

FRAMEWORK_OUTPUTS["scope3_cat2_capital_goods"] = {
    "csrd_esrs_e1": {
        "field_id": "ESRS E1-6",
        "label": "Gross Scope 3 GHG emissions — Category 2 (Capital Goods)",
        "value": "1,240 tCO2e",
        "unit": "tCO2e",
        "methodology": "Spend-based — capital expenditure × emission factor",
        "confidence": "LOW",
    },
    "gri_305_3": {
        "field_id": "GRI 305-3",
        "label": "Other indirect Scope 3 emissions — Category 2",
        "value": "1,240 tCO2e",
        "unit": "tCO2e",
        "methodology": "Spend-based estimate",
        "confidence": "LOW",
    },
}

FRAMEWORK_OUTPUTS["scope3_cat3_energy_related"] = {
    "csrd_esrs_e1": {
        "field_id": "ESRS E1-5",
        "label": "Gross Scope 3 GHG emissions — Category 3 (Energy-related)",
        "value": "2,180 tCO2e",
        "unit": "tCO2e",
        "methodology": "Activity-based — transmission/distribution losses",
        "confidence": "LOW",
    },
    "gri_305_3": {
        "field_id": "GRI 305-3",
        "label": "Other indirect Scope 3 emissions — Category 3",
        "value": "2,180 tCO2e",
        "unit": "tCO2e",
        "confidence": "LOW",
    },
}

FRAMEWORK_OUTPUTS["scope3_cat4_upstream_transport"] = {
    "csrd_esrs_e1": {
        "field_id": "ESRS E1-5",
        "label": "Gross Scope 3 GHG emissions — Category 4 (Upstream Transport)",
        "value": "3,640 tCO2e",
        "unit": "tCO2e",
        "methodology": "Spend-based — logistics spend × emission factor",
        "confidence": "MEDIUM",
    },
    "gri_305_3": {
        "field_id": "GRI 305-3",
        "label": "Other indirect Scope 3 — Category 4 (Upstream Transport)",
        "value": "3,640 tCO2e",
        "unit": "tCO2e",
        "confidence": "MEDIUM",
    },
}

FRAMEWORK_OUTPUTS["scope3_cat5_waste_generated"] = {
    "csrd_esrs_e5": {
        "field_id": "ESRS E5-1",
        "label": "Gross Scope 3 GHG emissions — Category 5 (Waste Generated)",
        "value": "418 tCO2e",
        "unit": "tCO2e",
        "methodology": "Waste-to-landfill × emission factor",
        "confidence": "LOW",
    },
    "gri_306_4": {
        "field_id": "GRI 306-4",
        "label": "Waste diverted from disposal",
        "value": "842 tonnes",
        "unit": "tonnes",
        "confidence": "MEDIUM",
    },
}

FRAMEWORK_OUTPUTS["scope3_cat7_business_travel"] = {
    "csrd_esrs_e1": {
        "field_id": "ESRS E1-7",
        "label": "Gross Scope 3 GHG emissions — Category 7 (Employee Commuting)",
        "value": "892 tCO2e",
        "unit": "tCO2e",
        "methodology": "Employee headcount × average commute distance × mode split",
        "confidence": "LOW",
    },
    "gri_305_3": {
        "field_id": "GRI 305-3",
        "label": "Other indirect Scope 3 — Category 7 (Commuting)",
        "value": "892 tCO2e",
        "unit": "tCO2e",
        "confidence": "LOW",
    },
}

FRAMEWORK_OUTPUTS["scope3_cat8_upstream_leased"] = {
    "csrd_esrs_e1": {
        "field_id": "ESRS E1-6",
        "label": "Gross Scope 3 GHG emissions — Category 8 (Upstream Leased Assets)",
        "value": "240 tCO2e",
        "unit": "tCO2e",
        "methodology": "Leased warehouse energy consumption estimate",
        "confidence": "LOW",
    },
    "gri_305_3": {
        "field_id": "GRI 305-3",
        "label": "Other indirect Scope 3 — Category 8",
        "value": "240 tCO2e",
        "unit": "tCO2e",
        "confidence": "LOW",
    },
}

FRAMEWORK_OUTPUTS["scope3_cat9_downstream_transport"] = {
    "csrd_esrs_e1": {
        "field_id": "ESRS E1-5",
        "label": "Gross Scope 3 GHG emissions — Category 9 (Downstream Transport)",
        "value": "1,820 tCO2e",
        "unit": "tCO2e",
        "methodology": "Finished goods logistics spend × emission factor",
        "confidence": "MEDIUM",
    },
    "gri_305_3": {
        "field_id": "GRI 305-3",
        "label": "Other indirect Scope 3 — Category 9 (Downstream Transport)",
        "value": "1,820 tCO2e",
        "unit": "tCO2e",
        "confidence": "MEDIUM",
    },
}

FRAMEWORK_OUTPUTS["scope3_cat11_sold_products"] = {
    "csrd_esrs_e1": {
        "field_id": "ESRS E1-6",
        "label": "Gross Scope 3 GHG emissions — Category 11 (Use of Sold Products)",
        "value": "0 tCO2e",
        "unit": "tCO2e",
        "methodology": "N/A — garments are not energy-consuming end products",
        "confidence": "HIGH",
    },
    "gri_305_3": {
        "field_id": "GRI 305-3",
        "label": "Other indirect Scope 3 — Category 11",
        "value": "0 tCO2e",
        "unit": "tCO2e",
        "confidence": "HIGH",
    },
}

FRAMEWORK_OUTPUTS["scope3_cat12_eol"] = {
    "csrd_esrs_e5": {
        "field_id": "ESRS E5-1",
        "label": "Gross Scope 3 GHG emissions — Category 12 (EOL of Sold Products)",
        "value": "4,120 tCO2e",
        "unit": "tCO2e",
        "methodology": "Textile waste estimate — garments disposed × emission factor",
        "confidence": "LOW",
    },
    "gri_306_5": {
        "field_id": "GRI 306-5",
        "label": "Waste directed to disposal",
        "value": "4,120 tCO2e",
        "unit": "tCO2e",
        "confidence": "LOW",
    },
}

FRAMEWORK_OUTPUTS["gender_pct_42"] = {
    "csrd_esrs_s1": {
        "field_id": "ESRS S1-1",
        "label": "Gender composition of workforce",
        "value": "42% female",
        "unit": "%",
        "breakdown": {"management": "28% female", "operational": "48% female", "board": "33% female"},
        "methodology": "HRIS data — headcount by gender band",
        "confidence": "HIGH",
    },
    "gri_405_1": {
        "field_id": "GRI 405-1",
        "label": "Diversity of governance bodies and employees",
        "value": "42% female overall",
        "unit": "%",
        "methodology": "HRIS data extraction",
        "confidence": "HIGH",
    },
}

FRAMEWORK_OUTPUTS["safety_incidents_3"] = {
    "csrd_esrs_s1": {
        "field_id": "ESRS S1-3",
        "label": "Work-related ill health and fatalities",
        "value": "3 incidents (minor), 0 fatalities",
        "unit": "count",
        "breakdown": {"lost_time_incidents": "1", "medical_treatment": "2", "first_aid": "0"},
        "methodology": "Safety register — OSHA recordable events",
        "confidence": "HIGH",
    },
    "gri_403_9": {
        "field_id": "GRI 403-9",
        "label": "Work-related injuries",
        "value": "3 incidents",
        "unit": "count",
        "methodology": "Safety register",
        "confidence": "HIGH",
    },
}

FRAMEWORK_OUTPUTS["governance_score_78"] = {
    "csrd_esrs_g1": {
        "field_id": "ESRS G1-1",
        "label": "Corporate governance — board independence and composition",
        "value": "78/100",
        "unit": "score",
        "breakdown": {"board_independence": "67%", "gender_diversity": "33%", "audit_committee": "100% independent"},
        "methodology": "Governance review against CSRD G1 requirements",
        "confidence": "MEDIUM",
    },
    "gri_205_1": {
        "field_id": "GRI 205-1",
        "label": "Operations assessed for anti-corruption risks",
        "value": "100% of sites assessed",
        "unit": "%",
        "methodology": "Annual governance audit",
        "confidence": "HIGH",
    },
}


@router.get("/map/{metric_type}")
def framework_map(metric_type: str):
    """Map a single metric to all framework outputs"""
    mapping = {
        "energy_kwh": ("energy_kwh_2847320", "2,847,320 kWh"),
        "scope3_category_1": ("scope3_cat1_4281", "4,281.7 tCO2e"),
        "diesel_consumed": ("diesel_consumed", "49.3 tCO2e"),
        "scope3_category_6": ("scope3_cat6_business_travel", "37.0 tCO2e"),
        "water_m3": ("water_m3_18430", "18,430 m³"),
        "waste_tonnes": ("waste_tonnes", "842 tonnes"),
        "scope3_cat2": ("scope3_cat2_capital_goods", "1,240 tCO2e"),
        "scope3_cat3": ("scope3_cat3_energy_related", "2,180 tCO2e"),
        "scope3_cat4": ("scope3_cat4_upstream_transport", "3,640 tCO2e"),
        "scope3_cat5": ("scope3_cat5_waste_generated", "418 tCO2e"),
        "scope3_cat7": ("scope3_cat7_business_travel", "892 tCO2e"),
        "scope3_cat8": ("scope3_cat8_upstream_leased", "240 tCO2e"),
        "scope3_cat9": ("scope3_cat9_downstream_transport", "1,820 tCO2e"),
        "scope3_cat11": ("scope3_cat11_sold_products", "0 tCO2e"),
        "scope3_cat12": ("scope3_cat12_eol", "4,120 tCO2e"),
        "gender_pct": ("gender_pct_42", "42% female"),
        "safety_incidents": ("safety_incidents_3", "3 incidents"),
        "governance_score": ("governance_score_78", "78/100"),
    }
    if metric_type not in mapping:
        return {"error": "metric not found"}, 404
    key, source_value = mapping[metric_type]
    if key not in FRAMEWORK_OUTPUTS:
        return {"error": "metric mapping not found"}, 404
    return {
        "source_metric": metric_type,
        "source_value": source_value,
        "frameworks": FRAMEWORK_OUTPUTS[key],
    }


@router.get("/map")
def list_all_mappings():
    """List all available cluster-to-framework mappings"""
    mappings = []
    for key in FRAMEWORK_OUTPUTS:
        # Derive a readable metric name from the key
        metric_name = key.replace("_18430", "").replace("_4281", "").replace("_42", "").replace("_3", "").replace("_78", "").replace("_", " ").title()
        mappings.append({
            "key": key,
            "metric_name": metric_name,
            "frameworks": list(FRAMEWORK_OUTPUTS[key].keys()),
        })
    return {"mappings": mappings, "total": len(mappings)}


@router.get("/compare/{metric_type}")
def compare_frameworks(metric_type: str):
    """Show same metric across all frameworks side by side"""
    COMPARE_DATA = {
        "energy_kwh": {
            "metric": "Energy Consumption",
            "source_value": "2,847,320 kWh",
            "frameworks": [
                {"name": "CSRD / ESRS E1", "field_id": "E1-13", "value": "2,847,320 kWh", "unit": "kWh", "confidence": "HIGH"},
                {"name": "ISSB / IFRS S2", "field_id": "S2-13", "value": "2,847,320 kWh", "unit": "kWh", "confidence": "HIGH"},
                {"name": "GRI 302", "field_id": "302-1", "value": "10,250 GJ", "unit": "GJ", "confidence": "HIGH", "note": "Converted to GJ per GRI guidelines"},
                {"name": "TCFD", "field_id": "M-4", "value": "2,847,320 kWh", "unit": "kWh", "confidence": "HIGH"},
            ],
        },
        "scope3_category_1": {
            "metric": "Scope 3 Category 1 — Purchased Goods",
            "source_value": "4,281.7 tCO2e",
            "frameworks": [
                {"name": "CSRD / ESRS E1", "field_id": "E1-6", "value": "4,281.7 tCO2e", "unit": "tCO2e", "confidence": "MEDIUM", "note": "64% coverage — 47 of 73 suppliers responded"},
                {"name": "ISSB / IFRS S2", "field_id": "S2-15", "value": "4,281.7 tCO2e", "unit": "tCO2e", "confidence": "MEDIUM"},
                {"name": "GRI 305", "field_id": "305-3", "value": "4,281.7 tCO2e", "unit": "tCO2e", "confidence": "MEDIUM", "note": "Activity-based + supplier-specific overrides"},
            ],
        },
        "diesel_consumed": {
            "metric": "Diesel Consumed — Scope 1",
            "source_value": "18,400 L (manual entry from generator log)",
            "frameworks": [
                {"name": "CSRD / ESRS E1", "field_id": "E1-3", "value": "49.3 tCO2e", "unit": "tCO2e", "confidence": "MEDIUM", "note": "18,400 L × 2.68 kg CO2/L"},
                {"name": "ISSB / IFRS S2", "field_id": "S2-14", "value": "49.3 tCO2e", "unit": "tCO2e", "confidence": "MEDIUM"},
                {"name": "GRI 305", "field_id": "305-1", "value": "49.3 tCO2e", "unit": "tCO2e", "confidence": "MEDIUM"},
            ],
        },
        "scope3_category_6": {
            "metric": "Business Travel — Scope 3 Cat 6",
            "source_value": "Manual calculation from expense claims",
            "frameworks": [
                {"name": "CSRD / ESRS E1", "field_id": "E1-7", "value": "37.0 tCO2e", "unit": "tCO2e", "confidence": "LOW", "note": "Flights 98,400 km + hotels 840 nights + cars 18,200 km"},
                {"name": "ISSB / IFRS S2", "field_id": "S2-16", "value": "37.0 tCO2e", "unit": "tCO2e", "confidence": "LOW"},
                {"name": "GRI 305", "field_id": "305-3", "value": "37.0 tCO2e", "unit": "tCO2e", "confidence": "LOW", "note": "Per GHG Protocol Category 6 emission factors"},
            ],
        },
        "water_m3": {
            "metric": "Water Consumption",
            "source_value": "18,430 m³",
            "frameworks": [
                {"name": "CSRD / ESRS E3", "field_id": "E3-1", "value": "18,430 m³", "unit": "m³", "confidence": "HIGH"},
                {"name": "ISSB / IFRS S2", "field_id": "S2-17", "value": "18,430 m³", "unit": "m³", "confidence": "HIGH"},
                {"name": "GRI 303", "field_id": "303-3", "value": "18,430 m³", "unit": "m³", "confidence": "HIGH", "note": "Municipal 16,200 m³ + groundwater 2,230 m³"},
                {"name": "TCFD", "field_id": "W-1", "value": "18,430 m³", "unit": "m³", "confidence": "HIGH"},
            ],
        },
        "waste_tonnes": {
            "metric": "Waste Generated",
            "source_value": "842 tonnes",
            "frameworks": [
                {"name": "CSRD / ESRS E5", "field_id": "E5-1", "value": "842 tonnes", "unit": "tonnes", "confidence": "MEDIUM", "note": "Hazardous 12t + non-hazardous 830t"},
                {"name": "GRI 306", "field_id": "306-3", "value": "842 tonnes", "unit": "tonnes", "confidence": "MEDIUM"},
            ],
        },
        "scope3_cat2": {
            "metric": "Scope 3 Category 2 — Capital Goods",
            "source_value": "1,240 tCO2e (spend-based)",
            "frameworks": [
                {"name": "CSRD / ESRS E1", "field_id": "E1-6", "value": "1,240 tCO2e", "unit": "tCO2e", "confidence": "LOW"},
                {"name": "GRI 305", "field_id": "305-3", "value": "1,240 tCO2e", "unit": "tCO2e", "confidence": "LOW"},
            ],
        },
        "scope3_cat3": {
            "metric": "Scope 3 Category 3 — Energy-related",
            "source_value": "2,180 tCO2e",
            "frameworks": [
                {"name": "CSRD / ESRS E1", "field_id": "E1-5", "value": "2,180 tCO2e", "unit": "tCO2e", "confidence": "LOW"},
                {"name": "GRI 305", "field_id": "305-3", "value": "2,180 tCO2e", "unit": "tCO2e", "confidence": "LOW"},
            ],
        },
        "scope3_cat4": {
            "metric": "Scope 3 Category 4 — Upstream Transport",
            "source_value": "3,640 tCO2e",
            "frameworks": [
                {"name": "CSRD / ESRS E1", "field_id": "E1-5", "value": "3,640 tCO2e", "unit": "tCO2e", "confidence": "MEDIUM"},
                {"name": "GRI 305", "field_id": "305-3", "value": "3,640 tCO2e", "unit": "tCO2e", "confidence": "MEDIUM"},
            ],
        },
        "scope3_cat5": {
            "metric": "Scope 3 Category 5 — Waste Generated",
            "source_value": "418 tCO2e",
            "frameworks": [
                {"name": "CSRD / ESRS E5", "field_id": "E5-1", "value": "418 tCO2e", "unit": "tCO2e", "confidence": "LOW"},
                {"name": "GRI 306", "field_id": "306-4", "value": "842 tonnes", "unit": "tonnes", "confidence": "MEDIUM"},
            ],
        },
        "scope3_cat7": {
            "metric": "Scope 3 Category 7 — Employee Commuting",
            "source_value": "892 tCO2e",
            "frameworks": [
                {"name": "CSRD / ESRS E1", "field_id": "E1-7", "value": "892 tCO2e", "unit": "tCO2e", "confidence": "LOW"},
                {"name": "GRI 305", "field_id": "305-3", "value": "892 tCO2e", "unit": "tCO2e", "confidence": "LOW"},
            ],
        },
        "scope3_cat8": {
            "metric": "Scope 3 Category 8 — Upstream Leased Assets",
            "source_value": "240 tCO2e",
            "frameworks": [
                {"name": "CSRD / ESRS E1", "field_id": "E1-6", "value": "240 tCO2e", "unit": "tCO2e", "confidence": "LOW"},
                {"name": "GRI 305", "field_id": "305-3", "value": "240 tCO2e", "unit": "tCO2e", "confidence": "LOW"},
            ],
        },
        "scope3_cat9": {
            "metric": "Scope 3 Category 9 — Downstream Transport",
            "source_value": "1,820 tCO2e",
            "frameworks": [
                {"name": "CSRD / ESRS E1", "field_id": "E1-5", "value": "1,820 tCO2e", "unit": "tCO2e", "confidence": "MEDIUM"},
                {"name": "GRI 305", "field_id": "305-3", "value": "1,820 tCO2e", "unit": "tCO2e", "confidence": "MEDIUM"},
            ],
        },
        "scope3_cat11": {
            "metric": "Scope 3 Category 11 — Use of Sold Products",
            "source_value": "0 tCO2e (N/A — garments are not energy-consuming)",
            "frameworks": [
                {"name": "CSRD / ESRS E1", "field_id": "E1-6", "value": "0 tCO2e", "unit": "tCO2e", "confidence": "HIGH"},
                {"name": "GRI 305", "field_id": "305-3", "value": "0 tCO2e", "unit": "tCO2e", "confidence": "HIGH"},
            ],
        },
        "scope3_cat12": {
            "metric": "Scope 3 Category 12 — EOL of Sold Products",
            "source_value": "4,120 tCO2e",
            "frameworks": [
                {"name": "CSRD / ESRS E5", "field_id": "E5-1", "value": "4,120 tCO2e", "unit": "tCO2e", "confidence": "LOW"},
                {"name": "GRI 306", "field_id": "306-5", "value": "4,120 tCO2e", "unit": "tCO2e", "confidence": "LOW"},
            ],
        },
        "gender_pct": {
            "metric": "Gender Composition — Workforce",
            "source_value": "42% female overall",
            "frameworks": [
                {"name": "CSRD / ESRS S1", "field_id": "S1-1", "value": "42% female", "unit": "%", "confidence": "HIGH", "note": "Management 28%, operational 48%, board 33%"},
                {"name": "GRI 405", "field_id": "405-1", "value": "42% female overall", "unit": "%", "confidence": "HIGH"},
            ],
        },
        "safety_incidents": {
            "metric": "Work-related Safety Incidents",
            "source_value": "3 incidents (minor), 0 fatalities",
            "frameworks": [
                {"name": "CSRD / ESRS S1", "field_id": "S1-3", "value": "3 incidents", "unit": "count", "confidence": "HIGH", "note": "LTI 1, MTC 2, first aid 0"},
                {"name": "GRI 403", "field_id": "403-9", "value": "3 incidents", "unit": "count", "confidence": "HIGH"},
            ],
        },
        "governance_score": {
            "metric": "Corporate Governance Score",
            "source_value": "78/100",
            "frameworks": [
                {"name": "CSRD / ESRS G1", "field_id": "G1-1", "value": "78/100", "unit": "score", "confidence": "MEDIUM", "note": "Board independence 67%, gender diversity 33%"},
                {"name": "GRI 205", "field_id": "205-1", "value": "100% sites assessed", "unit": "%", "confidence": "HIGH"},
            ],
        },
    }

    if metric_type not in COMPARE_DATA:
        return {"error": "metric not found"}, 404
    return COMPARE_DATA[metric_type]
