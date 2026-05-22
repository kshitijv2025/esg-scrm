"""
Unit normalization for ESG metrics.

Provides conversion factors between common units used in supplier questionnaires
and standard units for Scope 3 calculations.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

UNIT_CONVERSIONS: dict[tuple[str, str], Decimal] = {
    # Volume conversions -> m3
    ("gallon_us", "m3"): Decimal("0.00378541"),
    ("gallon_uk", "m3"): Decimal("0.00454609"),
    ("liter", "m3"): Decimal("0.001"),
    ("litre", "m3"): Decimal("0.001"),
    ("ml", "m3"): Decimal("0.000001"),
    ("gallons", "m3"): Decimal("0.00378541"),
    # Energy conversions -> kWh
    ("mwh", "kwh"): Decimal("1000"),
    ("mwh", "kWh"): Decimal("1000"),
    ("MWh", "kwh"): Decimal("1000"),
    ("MWh", "kWh"): Decimal("1000"),
    ("gwh", "kwh"): Decimal("1000000"),
    ("gwh", "kWh"): Decimal("1000000"),
    ("GWh", "kwh"): Decimal("1000000"),
    ("GWh", "kWh"): Decimal("1000000"),
    ("wh", "kwh"): Decimal("0.001"),
    ("wh", "kWh"): Decimal("0.001"),
    ("Wh", "kwh"): Decimal("0.001"),
    ("Wh", "kWh"): Decimal("0.001"),
    ("kwh", "mwh"): Decimal("0.001"),
    ("kWh", "mwh"): Decimal("0.001"),
    ("kwh", "MWh"): Decimal("0.001"),
    ("kWh", "MWh"): Decimal("0.001"),
    ("j", "kwh"): Decimal("0.00000027778"),
    ("j", "kWh"): Decimal("0.00000027778"),
    ("J", "kwh"): Decimal("0.00000027778"),
    ("J", "kWh"): Decimal("0.00000027778"),
    ("kj", "kwh"): Decimal("0.00027778"),
    ("kj", "kWh"): Decimal("0.00027778"),
    ("kJ", "kwh"): Decimal("0.00027778"),
    ("kJ", "kWh"): Decimal("0.00027778"),
    ("mj", "kwh"): Decimal("0.27778"),
    ("mj", "kWh"): Decimal("0.27778"),
    ("MJ", "kwh"): Decimal("0.27778"),
    ("MJ", "kWh"): Decimal("0.27778"),
    ("gj", "kwh"): Decimal("277.78"),
    ("gj", "kWh"): Decimal("277.78"),
    ("GJ", "kwh"): Decimal("277.78"),
    ("GJ", "kWh"): Decimal("277.78"),
    # Mass conversions -> kg
    ("t", "kg"): Decimal("1000"),
    ("tonne", "kg"): Decimal("1000"),
    ("tonnes", "kg"): Decimal("1000"),
    ("mt", "kg"): Decimal("1000"),
    ("lb", "kg"): Decimal("0.453592"),
    ("lbs", "kg"): Decimal("0.453592"),
    ("pound", "kg"): Decimal("0.453592"),
    ("pounds", "kg"): Decimal("0.453592"),
    ("oz", "kg"): Decimal("0.0283495"),
    ("ounce", "kg"): Decimal("0.0283495"),
    ("ounces", "kg"): Decimal("0.0283495"),
    # CO2 emissions conversions -> tCO2
    ("kg_co2", "tco2"): Decimal("0.001"),
    ("kg_co2", "tCO2"): Decimal("0.001"),
    ("kgco2", "tco2"): Decimal("0.001"),
    ("kgco2", "tCO2"): Decimal("0.001"),
    ("lb_co2", "tco2"): Decimal("0.000453592"),
    ("lb_co2", "tCO2"): Decimal("0.000453592"),
    ("lbco2", "tco2"): Decimal("0.000453592"),
    ("lbco2", "tCO2"): Decimal("0.000453592"),
    ("g_co2", "tco2"): Decimal("0.000001"),
    ("g_co2", "tCO2"): Decimal("0.000001"),
    ("gco2", "tco2"): Decimal("0.000001"),
    ("gco2", "tCO2"): Decimal("0.000001"),
    ("tco2", "kg_co2"): Decimal("1000"),
    ("tCO2", "kg_co2"): Decimal("1000"),
    # Area conversions -> m2
    ("km2", "m2"): Decimal("1000000"),
    ("km2", "sqm"): Decimal("1000000"),
    ("sqkm", "m2"): Decimal("1000000"),
    ("sqkm", "sqm"): Decimal("1000000"),
    ("hectare", "m2"): Decimal("10000"),
    ("hectares", "m2"): Decimal("10000"),
    ("ha", "m2"): Decimal("10000"),
    ("acre", "m2"): Decimal("4046.86"),
    ("acres", "m2"): Decimal("4046.86"),
    ("sqft", "m2"): Decimal("0.092903"),
    ("sqft", "m^2"): Decimal("0.092903"),
    ("sqm", "m2"): Decimal("1"),
    # Percentage (normalize to decimal)
    ("%", "decimal"): Decimal("0.01"),
    ("percent", "decimal"): Decimal("0.01"),
    ("percentage", "decimal"): Decimal("0.01"),
}

STANDARD_UNITS: list[str] = [
    "kWh",
    "m3",
    "tCO2",
    "kg",
    "USD",
    "count",
    "decimal",
    "m2",
]

UNIT_ALIASES: dict[str, str] = {
    "gallon": "gallon_us",
    "gallons": "gallon_us",
    "gallon_us": "gallon_us",
    "litre": "liter",
    "l": "liter",
    "L": "liter",
    "ml": "ml",
    "mL": "ml",
    "megawatt_hour": "mwh",
    "megawatt_hours": "mwh",
    "MWh": "mwh",
    "gwh": "gwh",
    "GWh": "gwh",
    "kilowatt_hour": "kwh",
    "kilowatt_hours": "kwh",
    "kwh": "kwh",
    "kWh": "kwh",
    "joule": "j",
    "joules": "j",
    "J": "j",
    "kilojoule": "kj",
    "kilojoules": "kj",
    "kJ": "kj",
    "megajoule": "mj",
    "megajoules": "mj",
    "MJ": "mj",
    "gigajoule": "gj",
    "gigajoules": "gj",
    "GJ": "gj",
    "tonne": "t",
    "tonnes": "t",
    "t": "t",
    "metric_ton": "t",
    "metric_tons": "t",
    "lb": "lb",
    "lbs": "lb",
    "pound": "lb",
    "pounds": "lb",
    "ounce": "oz",
    "ounces": "oz",
    "oz": "oz",
    "kilogram": "kg",
    "kilograms": "kg",
    "kg": "kg",
    "kilo": "kg",
    "tco2": "tco2",
    "tCO2": "tco2",
    "tCO2e": "tco2",
    "co2": "tco2",
    "co2e": "tco2",
    "sqm": "m2",
    "sqmeters": "m2",
    "square_meters": "m2",
    "m2": "m2",
    "m^2": "m2",
    "sqft": "sqft",
    "sq_ft": "sqft",
    "square_feet": "sqft",
    "hectare": "hectare",
    "hectares": "hectare",
    "ha": "hectare",
    "acre": "acre",
    "acres": "acre",
    "km2": "km2",
    "sqkm": "km2",
}


def normalize_unit(unit: str) -> str:
    """Normalize a unit string to its canonical form.

    Converts 'kwh', 'KWH', 'Kilowatt Hours' -> 'kwh'
    Returns the input unchanged if no normalization is found.
    """
    if not unit:
        return ""

    unit_lower = unit.lower().strip()

    if unit_lower in UNIT_ALIASES:
        return UNIT_ALIASES[unit_lower]

    normalized = unit_lower.replace(" ", "").replace("-", "").replace("_", "")
    if normalized in UNIT_ALIASES:
        return UNIT_ALIASES[normalized]

    return unit_lower


def convert_unit(
    value: Decimal,
    from_unit: str,
    to_unit: str,
) -> Optional[Decimal]:
    """Convert a value from one unit to another.

    Args:
        value: The numeric value to convert.
        from_unit: The source unit (e.g., 'gallon_us', 'mwh').
        to_unit: The target unit (e.g., 'm3', 'kwh').

    Returns:
        The converted value, or None if conversion is not possible.

    Examples:
        >>> convert_unit(Decimal("1000"), "gallon_us", "m3")
        Decimal('0.378541')
        >>> convert_unit(Decimal("1"), "mwh", "kwh")
        Decimal('1000')
    """
    if from_unit == to_unit:
        return value

    from_norm = normalize_unit(from_unit)
    to_norm = normalize_unit(to_unit)

    if from_norm == to_norm:
        return value

    conversion_key = (from_norm, to_norm)
    if conversion_key in UNIT_CONVERSIONS:
        factor = UNIT_CONVERSIONS[conversion_key]
        converted = value * factor
        return converted.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    reverse_key = (to_norm, from_norm)
    if reverse_key in UNIT_CONVERSIONS:
        factor = UNIT_CONVERSIONS[reverse_key]
        if factor == Decimal("0"):
            return None
        converted = value / factor
        return converted.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    return None


def is_standard_unit(unit: str) -> bool:
    """Check if a unit is one of the standard ESG reporting units."""
    if not unit:
        return False
    normalized = normalize_unit(unit)
    # Check if the normalized form matches any normalized standard unit
    return any(normalize_unit(std) == normalized for std in STANDARD_UNITS)


def requires_conversion(from_unit: str, to_unit: str) -> bool:
    """Check if a conversion is needed between two units."""
    if from_unit == to_unit:
        return False
    from_norm = normalize_unit(from_unit)
    to_norm = normalize_unit(to_unit)
    return from_norm != to_norm
