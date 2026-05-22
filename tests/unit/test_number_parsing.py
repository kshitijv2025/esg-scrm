from src.ml.number_parsing import (
    detect_language,
    parse_bengali_number,
    parse_number,
    parse_vietnamese_number,
)


class TestBengaliNumberParsing:
    def test_bengali_digits(self):
        assert parse_bengali_number("১২৩") == 123.0
        assert parse_bengali_number("১০") == 10.0
        assert parse_bengali_number("১,২৩") == 123.0  # comma separator

    def test_bengali_word_shat(self):
        assert parse_bengali_number("1 shat") == 100.0
        assert parse_bengali_number("5 shat") == 500.0

    def test_bengali_word_hazar(self):
        assert parse_bengali_number("1 hazar") == 1_000.0
        assert parse_bengali_number("2.5 hazar") == 2_500.0

    def test_bengali_word_lakh(self):
        assert parse_bengali_number("1 lakh") == 100_000.0
        assert parse_bengali_number("1.5 lakh") == 150_000.0

    def test_bengali_word_crore(self):
        assert parse_bengali_number("1 crore") == 10_000_000.0
        assert parse_bengali_number("2 crore") == 20_000_000.0

    def test_bengali_mixed(self):
        assert parse_bengali_number("1 lakh 50 hazar") == 150_000.0
        assert parse_bengali_number("১ লক্ষ ৫০ হাজার") == 150_000.0

    def test_bengali_arabic_passthrough(self):
        assert parse_bengali_number("1234567") == 1234567.0
        assert parse_bengali_number("1,500,000") == 1500000.0

    def test_bengali_invalid(self):
        assert parse_bengali_number("") is None
        assert parse_bengali_number("not a number") is None

    def test_bengali_crore_with_decimal(self):
        assert parse_bengali_number("1.25 crore") == 12_500_000.0


class TestVietnameseNumberParsing:
    def test_vietnamese_nghin(self):
        assert parse_vietnamese_number("1 nghìn") == 1_000.0
        assert parse_vietnamese_number("2.5 nghìn") == 2_500.0
        assert parse_vietnamese_number("1 nghin") == 1_000.0  # ASCII variant

    def test_vietnamese_trieu(self):
        assert parse_vietnamese_number("1 triệu") == 1_000_000.0
        assert parse_vietnamese_number("1.5 triệu") == 1_500_000.0
        assert parse_vietnamese_number("1 trieu") == 1_000_000.0  # ASCII variant

    def test_vietnamese_ty(self):
        assert parse_vietnamese_number("1 tỷ") == 1_000_000_000.0
        assert parse_vietnamese_number("1 ty") == 1_000_000_000.0

    def test_vietnamese_dong_suffix_stripped(self):
        assert parse_vietnamese_number("50000 đồng") == 50_000.0
        assert parse_vietnamese_number("50000 dong") == 50_000.0

    def test_vietnamese_comma_decimal(self):
        assert parse_vietnamese_number("1,5 triệu") == 1_500_000.0

    def test_vietnamese_arabic_passthrough(self):
        assert parse_vietnamese_number("1234567") == 1234567.0
        assert parse_vietnamese_number("1.5") == 1.5

    def test_vietnamese_invalid(self):
        assert parse_vietnamese_number("") is None
        assert parse_vietnamese_number("not a number") is None


class TestLanguageDetection:
    def test_detect_bengali_by_country(self):
        assert detect_language("BD") == "bengali"
        assert detect_language("BGD") == "bengali"

    def test_detect_vietnamese_by_country(self):
        assert detect_language("VN") == "vietnamese"
        assert detect_language("VNM") == "vietnamese"

    def test_detect_bengali_by_script(self):
        assert detect_language(None, "১২৩ লক্ষ") == "bengali"
        assert detect_language(None, "কোটি") == "bengali"

    def test_detect_vietnamese_by_content(self):
        assert detect_language(None, "1.5 triệu") == "vietnamese"
        assert detect_language(None, "50000 đồng") == "vietnamese"

    def test_detect_standard_fallback(self):
        assert detect_language("US") == "standard"
        assert detect_language(None, "Hello world") == "standard"


class TestParseNumberDispatch:
    def test_dispatch_bengali(self):
        assert parse_number("১২৩", language="bengali") == 123.0
        assert parse_number("1 lakh", language="bengali") == 100_000.0

    def test_dispatch_vietnamese(self):
        assert parse_number("1.5 triệu", language="vietnamese") == 1_500_000.0
        assert parse_number("50000 đồng", language="vietnamese") == 50_000.0

    def test_dispatch_standard(self):
        assert parse_number("1,500,000", language="standard") == 1500000.0
        assert parse_number("123.45", language="standard") == 123.45

    def test_dispatch_auto_by_country(self):
        assert parse_number("১২৩", country_code="BD") == 123.0
        assert parse_number("1.5 triệu", country_code="VN") == 1_500_000.0
        assert parse_number("12345", country_code="US") == 12345.0
