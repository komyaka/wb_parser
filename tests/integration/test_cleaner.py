"""Integration tests for data cleaning pipeline."""

import pytest
import pandas as pd
from pathlib import Path

from src.clean.cleaner import DataCleaner
from src.models.config import CleaningConfig


class TestDataCleanerIntegration:
    """Integration tests for data cleaner."""

    def test_clean_with_all_filters(self, tmp_path):
        """Test cleaning with all filters active."""
        # Create stop files
        cat_file = tmp_path / "categories.txt"
        cat_file.write_text("алкоголь\nтабак", encoding="utf-8")

        words_file = tmp_path / "words.txt"
        words_file.write_text("термо\nбио", encoding="utf-8")

        # Create test data
        data = {
            "query": ["кружка", "термокружка", "12345", "биойогурт", "чашка"],
            "category": ["посуда", "посуда", "товары", "еда", "алкоголь"],
            "count": [10, 5, 3, 7, 2],
        }
        df = pd.DataFrame(data)

        # Configure cleaner
        config = CleaningConfig(
            stop_categories_file=str(cat_file),
            stop_words_file=str(words_file),
            remove_numeric_only=True,
            case_sensitive=False,
        )

        cleaner = DataCleaner(config)
        cleaned_df, removed_df = cleaner.clean(df)

        # Check results
        assert len(cleaned_df) == 1  # Only 'кружка' should remain
        assert cleaned_df.iloc[0]["query"] == "кружка"

        assert len(removed_df) == 4
        assert "matched_stop" in removed_df.columns

    def test_extract_unique_queries(self):
        """Test extracting unique queries with counts."""
        data = {
            "query": ["кружка", "чашка", "кружка", "тарелка", "кружка"],
            "count": [1, 2, 1, 3, 1],
        }
        df = pd.DataFrame(data)

        config = CleaningConfig()
        cleaner = DataCleaner(config)

        queries = cleaner.extract_unique_queries(df)

        # Check unique queries
        query_dict = dict(queries)
        assert query_dict["кружка"] == 3  # Sum of counts
        assert query_dict["чашка"] == 2
        assert query_dict["тарелка"] == 3

    def test_clean_empty_dataframe(self):
        """Test cleaning empty DataFrame."""
        df = pd.DataFrame(columns=["query", "category", "count"])

        config = CleaningConfig()
        cleaner = DataCleaner(config)

        cleaned_df, removed_df = cleaner.clean(df)

        assert len(cleaned_df) == 0
        assert len(removed_df) == 0

    def test_clean_with_missing_category_column(self):
        """Test cleaning when category column is missing."""
        data = {"query": ["кружка", "12345", "чашка"], "count": [1, 2, 3]}
        df = pd.DataFrame(data)

        config = CleaningConfig(remove_numeric_only=True)
        cleaner = DataCleaner(config)

        cleaned_df, removed_df = cleaner.clean(df)

        # Should remove numeric-only query
        assert len(cleaned_df) == 2
        assert len(removed_df) == 1

    def test_clean_special_characters(self):
        """Test cleaning with special characters in queries."""
        data = {
            "query": ["кружка-чашка", "термо-бутылка", "обычная/простая"],
            "category": ["посуда", "посуда", "посуда"],
            "count": [1, 2, 3],
        }
        df = pd.DataFrame(data)

        config = CleaningConfig()
        cleaner = DataCleaner(config)

        # Add stop word
        cleaner.filter.stop_words = {"термо"}

        cleaned_df, removed_df = cleaner.clean(df)

        # 'термо-бутылка' should be removed
        assert len(cleaned_df) == 2
        assert "термо-бутылка" not in cleaned_df["query"].values


class TestEndToEndCleaning:
    """End-to-end cleaning tests."""

    def test_realistic_data_cleaning(self, tmp_path):
        """Test with realistic data."""
        # Create stop files
        cat_file = tmp_path / "categories.txt"
        cat_file.write_text("алкоголь\nтабак\nмедикаменты", encoding="utf-8")

        words_file = tmp_path / "words.txt"
        words_file.write_text("авто\nмото\nвело\nтермо", encoding="utf-8")

        # Realistic test data
        data = {
            "Поисковый запрос": [
                "кружка керамическая",
                "термокружка стальная",
                "автозапчасти",
                "1234567",
                "чашка для чая",
                "мотошлем",
                "велосипед",
                "водка",
                "сигареты",
            ],
            "Категория": [
                "Посуда",
                "Посуда",
                "Автотовары",
                "Разное",
                "Посуда",
                "Мототовары",
                "Велосипеды",
                "Алкоголь",
                "Табак",
            ],
            "Количество запросов": [10, 5, 3, 1, 8, 2, 4, 15, 7],
        }
        df = pd.DataFrame(data)

        # Configure with column mapping
        config = CleaningConfig(
            stop_categories_file=str(cat_file),
            stop_words_file=str(words_file),
            remove_numeric_only=True,
            case_sensitive=False,
        )

        cleaner = DataCleaner(config)
        cleaned_df, removed_df = cleaner.clean(df)

        # Should keep only 'кружка керамическая' and 'чашка для чая'
        assert len(cleaned_df) == 2

        # Should remove 7 queries
        assert len(removed_df) == 7

        # Extract unique queries
        queries = cleaner.extract_unique_queries(cleaned_df)
        assert len(queries) == 2

    def test_split_removed_by_reason(self, tmp_path):
        """Test splitting removed rows by reason."""
        # Create stop files
        cat_file = tmp_path / "categories.txt"
        cat_file.write_text("алкоголь\nтабак", encoding="utf-8")

        words_file = tmp_path / "words.txt"
        words_file.write_text("термо\nбио", encoding="utf-8")

        # Create test data
        data = {
            "query": ["нормальный", "термокружка", "12345", "биойогурт", "водка"],
            "category": ["посуда", "посуда", "товары", "еда", "алкоголь"],
            "count": [10, 5, 3, 7, 2],
        }
        df = pd.DataFrame(data)

        # Configure cleaner
        config = CleaningConfig(
            stop_categories_file=str(cat_file),
            stop_words_file=str(words_file),
            remove_numeric_only=True,
            case_sensitive=False,
        )

        cleaner = DataCleaner(config)
        cleaned_df, removed_df = cleaner.clean(df)

        # Split removed by reason
        by_categories, by_stop_words = cleaner.split_removed_by_reason(removed_df)

        # Check split results
        assert len(by_categories) == 1  # водка (категория алкоголь)
        assert len(by_stop_words) == 2  # термокружка, биойогурт

        # Verify queries
        assert "водка" in by_categories["query"].values
        assert "термокружка" in by_stop_words["query"].values
        assert "биойогурт" in by_stop_words["query"].values

        # Numeric-only not in either
        assert "12345" not in by_categories["query"].values
        assert "12345" not in by_stop_words["query"].values

    def test_split_removed_empty_dataframe(self):
        """Test split_removed_by_reason with empty DataFrame."""
        config = CleaningConfig()
        cleaner = DataCleaner(config)

        empty_df = pd.DataFrame(columns=["query", "category", "matched_stop"])
        by_cat, by_words = cleaner.split_removed_by_reason(empty_df)

        assert len(by_cat) == 0
        assert len(by_words) == 0
