"""Unit tests for stop words filter."""

import pytest
from src.clean.stop_words import StopWordsFilter


class TestNumericDetection:
    """Test numeric-only query detection."""

    def test_numeric_only_simple(self):
        """Test simple numeric query."""
        filter = StopWordsFilter()
        assert filter.is_numeric_only("12345") is True

    def test_numeric_only_with_spaces(self):
        """Test numeric query with spaces."""
        filter = StopWordsFilter()
        assert filter.is_numeric_only("  123  ") is True

    def test_not_numeric_with_letters(self):
        """Test query with letters."""
        filter = StopWordsFilter()
        assert filter.is_numeric_only("abc123") is False

    def test_not_numeric_with_special_chars(self):
        """Test query with special characters."""
        filter = StopWordsFilter()
        assert filter.is_numeric_only("123-456") is False

    def test_empty_string(self):
        """Test empty string."""
        filter = StopWordsFilter()
        assert filter.is_numeric_only("") is False


class TestStopCategoryMatching:
    """Test stop category matching."""

    def test_exact_match(self):
        """Test exact category match."""
        filter = StopWordsFilter()
        filter.stop_categories = {"алкоголь", "табак"}

        assert filter.matches_stop_category("алкоголь") is True
        assert filter.matches_stop_category("табак") is True

    def test_word_boundary_match(self):
        """Test word boundary matching."""
        filter = StopWordsFilter()
        filter.stop_categories = {"алкоголь"}

        # Should match as separate word
        assert filter.matches_stop_category("алкоголь продукты") is True
        assert filter.matches_stop_category("продукты алкоголь") is True

    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        filter = StopWordsFilter(case_sensitive=False)
        filter.stop_categories = {"алкоголь"}

        assert filter.matches_stop_category("АЛКОГОЛЬ") is True
        assert filter.matches_stop_category("Алкоголь") is True

    def test_no_match(self):
        """Test non-matching category."""
        filter = StopWordsFilter()
        filter.stop_categories = {"алкоголь"}

        assert filter.matches_stop_category("безалкогольный") is False
        assert filter.matches_stop_category("другая категория") is False

    def test_empty_category(self):
        """Test empty category."""
        filter = StopWordsFilter()
        filter.stop_categories = {"алкоголь"}

        assert filter.matches_stop_category("") is False
        assert filter.matches_stop_category(None) is False


class TestStopWordMatching:
    """Test stop word matching with token-start rule."""

    def test_token_start_match(self):
        """Test token-start matching."""
        filter = StopWordsFilter()
        filter.stop_words = {"термо"}

        # Should match at start of token
        matches, word = filter.matches_stop_word("термокружка")
        assert matches is True
        assert word == "термо"

    def test_token_start_no_match_middle(self):
        """Test no match when word is in middle of token."""
        filter = StopWordsFilter()
        filter.stop_words = {"термо"}

        # Should NOT match in middle
        matches, word = filter.matches_stop_word("гидротермокружка")
        assert matches is False

    def test_multiple_tokens(self):
        """Test matching in multi-token query."""
        filter = StopWordsFilter()
        filter.stop_words = {"био"}

        # Should match second token
        matches, word = filter.matches_stop_word("купить биопродукты")
        assert matches is True
        assert word == "био"

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        filter = StopWordsFilter(case_sensitive=False)
        filter.stop_words = {"термо"}

        matches, word = filter.matches_stop_word("ТЕРМОКРУЖКА")
        assert matches is True

    def test_no_match(self):
        """Test non-matching query."""
        filter = StopWordsFilter()
        filter.stop_words = {"термо"}

        matches, word = filter.matches_stop_word("кружка обычная")
        assert matches is False
        assert word is None

    def test_special_characters(self):
        """Test with special characters."""
        filter = StopWordsFilter()
        filter.stop_words = {"авто"}

        # Should still match despite special chars
        matches, word = filter.matches_stop_word("авто-запчасти")
        assert matches is True


class TestShouldRemove:
    """Test combined removal logic."""

    def test_remove_numeric(self):
        """Test numeric removal."""
        filter = StopWordsFilter()
        should_remove, reason = filter.should_remove("12345", remove_numeric=True)
        assert should_remove is True
        assert reason == "numeric_only"

    def test_remove_stop_category(self):
        """Test category removal."""
        filter = StopWordsFilter()
        filter.stop_categories = {"алкоголь"}

        should_remove, reason = filter.should_remove("test", "алкоголь")
        assert should_remove is True
        assert reason == "stop_category"

    def test_remove_stop_word(self):
        """Test stop word removal."""
        filter = StopWordsFilter()
        filter.stop_words = {"термо"}

        should_remove, reason = filter.should_remove("термокружка")
        assert should_remove is True
        assert "stop_word" in reason

    def test_keep_normal_query(self):
        """Test keeping normal query."""
        filter = StopWordsFilter()
        filter.stop_categories = {"алкоголь"}
        filter.stop_words = {"термо"}

        should_remove, reason = filter.should_remove("кружка", "посуда")
        assert should_remove is False
        assert reason == ""

    def test_priority_order(self):
        """Test removal priority (numeric > category > word)."""
        filter = StopWordsFilter()
        filter.stop_categories = {"категория"}
        filter.stop_words = {"слово"}

        # Numeric first
        should_remove, reason = filter.should_remove("123", "категория")
        assert reason == "numeric_only"

        # Category before word
        should_remove, reason = filter.should_remove(
            "словоформа", "категория", remove_numeric=False
        )
        assert reason == "stop_category"


class TestLoadFromFiles:
    """Test loading stop words from files."""

    def test_load_stop_categories(self, tmp_path):
        """Test loading categories from file."""
        file_path = tmp_path / "categories.txt"
        file_path.write_text("алкоголь\nтабак\n# comment\n\nсигареты", encoding="utf-8")

        filter = StopWordsFilter()
        filter.load_stop_categories(str(file_path))

        assert len(filter.stop_categories) == 3
        assert "алкоголь" in filter.stop_categories
        assert "табак" in filter.stop_categories
        assert "сигареты" in filter.stop_categories

    def test_load_stop_words(self, tmp_path):
        """Test loading stop words from file."""
        file_path = tmp_path / "words.txt"
        file_path.write_text("термо\nбио\n# comment\n\nэко", encoding="utf-8")

        filter = StopWordsFilter()
        filter.load_stop_words(str(file_path))

        assert len(filter.stop_words) == 3
        assert "термо" in filter.stop_words
        assert "био" in filter.stop_words
        assert "эко" in filter.stop_words

    def test_load_nonexistent_file(self):
        """Test loading from non-existent file."""
        filter = StopWordsFilter()
        filter.load_stop_categories("nonexistent.txt")

        # Should not raise, just log warning
        assert len(filter.stop_categories) == 0
