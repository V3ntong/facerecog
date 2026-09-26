from app.routes.enroll import normalize_name


class TestNormalizeName:
    def test_trims_and_collapses_whitespace(self):
        assert normalize_name("  Cui   Pendang  ") == "Cui Pendang"

    def test_empty_and_blank_names_rejected(self):
        assert normalize_name("") is None
        assert normalize_name("   ") is None

    def test_invalid_characters_rejected(self):
        assert normalize_name("Cui$%") is None
        assert normalize_name("Cui<3") is None
        assert normalize_name("芒果") is None
        assert normalize_name("Cui; DROP TABLE Person;") is None

    def test_too_long_rejected(self):
        assert normalize_name("A" * 101) is None

    def test_max_length_accepted(self):
        assert normalize_name("A" * 100) == "A" * 100

    def test_letters_digits_dots_apostrophes_hyphens_accepted(self):
        name = "J. B. O'Brien-Test 3"
        assert normalize_name(name) == name

    def test_internal_spacing_preserved_in_order(self):
        assert normalize_name("cristian jim   pogoy") == "cristian jim pogoy"