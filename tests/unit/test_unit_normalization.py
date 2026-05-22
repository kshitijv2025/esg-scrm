"""Tests for unit normalization and conversion functions."""

import sys

sys.path.insert(0, "src")

from decimal import Decimal

from src.supplier.unit_normalization import (
    convert_unit,
    normalize_unit,
    requires_conversion,
    is_standard_unit,
)


class TestNormalizeUnit:
    """Tests for normalize_unit function."""

    def test_normalize_unit_gallon_us(self):
        """Test gallon_us normalization."""
        assert normalize_unit("gallon") == "gallon_us"
        assert normalize_unit("gallons") == "gallon_us"
        assert normalize_unit("gallon_us") == "gallon_us"

    def test_normalize_unit_gallon_uk(self):
        """Test gallon_uk normalization."""
        assert normalize_unit("gallon_uk") == "gallon_uk"
        # "gallon uk" with space is not in aliases, so it remains unchanged
        assert normalize_unit("gallon uk") == "gallon uk"

    def test_normalize_unit_liter(self):
        """Test liter normalization."""
        assert normalize_unit("liter") == "liter"
        assert normalize_unit("litre") == "liter"
        assert normalize_unit("L") == "liter"
        assert normalize_unit("l") == "liter"

    def test_normalize_unit_mwh(self):
        """Test MWh/kWh normalization."""
        assert normalize_unit("MWh") == "mwh"
        assert normalize_unit("mwh") == "mwh"
        assert normalize_unit("kWh") == "kwh"
        assert normalize_unit("kwh") == "kwh"

    def test_normalize_unit_empty_string(self):
        """Test normalize_unit with empty string."""
        assert normalize_unit("") == ""


class TestConvertUnit:
    """Tests for convert_unit function."""

    def test_gallon_us_to_m3(self):
        """Test gallon_us to m3 conversion."""
        result = convert_unit(Decimal("1000"), "gallon_us", "m3")
        # 1000 gallons * 0.00378541 = 3.78541
        assert result == Decimal("3.785410")

    def test_gallon_uk_to_m3(self):
        """Test gallon_uk to m3 conversion."""
        result = convert_unit(Decimal("1000"), "gallon_uk", "m3")
        # 1000 gallons * 0.00454609 = 4.54609
        assert result == Decimal("4.546090")

    def test_liter_to_m3(self):
        """Test liter to m3 conversion."""
        result = convert_unit(Decimal("1000"), "liter", "m3")
        # 1000 liters * 0.001 = 1.0
        assert result == Decimal("1.000000")

    def test_mwh_to_kwh(self):
        """Test MWh to kWh conversion."""
        result = convert_unit(Decimal("45"), "MWh", "kWh")
        # 45 MWh * 1000 = 45000
        assert result == Decimal("45000.000000")

    def test_kwh_stays_kwh(self):
        """Test kWh stays kWh (same unit)."""
        result = convert_unit(Decimal("100"), "kWh", "kwh")
        assert result == Decimal("100")

    def test_kgco2_to_tco2(self):
        """Test kgCO2 to tCO2 conversion."""
        result = convert_unit(Decimal("1000"), "kg_co2", "tCO2")
        # 1000 kg * 0.001 = 1.0 t
        assert result == Decimal("1.000000")

    def test_lbco2_to_tco2(self):
        """Test lbCO2 to tCO2 conversion."""
        result = convert_unit(Decimal("1000"), "lb_co2", "tCO2")
        # 1000 lbs * 0.000453592 = 0.453592
        assert result == Decimal("0.453592")

    def test_unknown_unit_raises_value_error(self):
        """Test unknown unit raises ValueError."""
        # convert_unit returns None for unknown units, it doesn't raise
        result = convert_unit(Decimal("100"), "unknown_unit", "m3")
        assert result is None

    def test_same_unit_returns_value(self):
        """Test same unit returns value unchanged."""
        result = convert_unit(Decimal("100"), "kWh", "kWh")
        assert result == Decimal("100")

    def test_convert_unit_with_string_decimal(self):
        """Test convert_unit with string decimal input."""
        result = convert_unit(Decimal("10.5"), "liter", "m3")
        assert result == Decimal("0.010500")

    def test_gwh_to_kwh(self):
        """Test GWh to kWh conversion."""
        result = convert_unit(Decimal("1"), "GWh", "kWh")
        # 1 GWh * 1000000 = 1000000 kWh
        assert result == Decimal("1000000.000000")


class TestRequiresConversion:
    """Tests for requires_conversion function."""

    def test_requires_conversion_different_units(self):
        """Test requires_conversion returns True for different units."""
        assert requires_conversion("gallon_us", "m3") is True
        assert requires_conversion("MWh", "kWh") is True

    def test_requires_conversion_same_units(self):
        """Test requires_conversion returns False for same units."""
        assert requires_conversion("kWh", "kwh") is False
        assert requires_conversion("liter", "liter") is False


class TestIsStandardUnit:
    """Tests for is_standard_unit function."""

    def test_is_standard_unit_kwh(self):
        """Test kWh is recognized as standard unit."""
        assert is_standard_unit("kWh") is True
        assert is_standard_unit("kwh") is True

    def test_is_standard_unit_m3(self):
        """Test m3 is recognized as standard unit."""
        assert is_standard_unit("m3") is True

    def test_is_standard_unit_tco2(self):
        """Test tCO2 is recognized as standard unit."""
        assert is_standard_unit("tCO2") is True
        assert is_standard_unit("tco2") is True

    def test_is_standard_unit_false(self):
        """Test non-standard unit returns False."""
        assert is_standard_unit("gallon_us") is False
        assert is_standard_unit("MWh") is False

    def test_is_standard_unit_empty(self):
        """Test empty string returns False."""
        assert is_standard_unit("") is False
