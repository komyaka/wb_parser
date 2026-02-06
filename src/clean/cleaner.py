"""Main data cleaner that orchestrates cleaning operations."""

import logging

import pandas as pd

from ..models.config import CleaningConfig
from .stop_words import StopWordsFilter

logger = logging.getLogger(__name__)


class DataCleaner:
    """Main data cleaner for Excel data."""

    def __init__(self, config: CleaningConfig):
        self.config = config
        self.filter = StopWordsFilter(
            stop_categories_file=config.stop_categories_file,
            stop_words_file=config.stop_words_file,
            case_sensitive=config.case_sensitive,
        )
        self.removed_rows: list[dict] = []

    def clean(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Clean DataFrame by removing stop categories and stop words.

        Args:
            df: Input DataFrame with columns from USER_COLUMN_MAP

        Returns:
            Tuple of (cleaned_df, removed_df)
        """
        logger.info(f"Starting cleaning on {len(df)} rows")

        # Detect query column
        query_col = self._detect_column(df, ["query", "Поисковый запрос", "запрос"])
        category_col = self._detect_column(df, ["category", "Категория"])

        if not query_col:
            raise ValueError("Could not find query column in DataFrame")

        logger.info(f"Using query column: {query_col}")
        if category_col:
            logger.info(f"Using category column: {category_col}")

        # Lists to track removal
        keep_indices = []
        remove_indices = []
        removal_reasons = []

        # Process each row
        for idx, row in df.iterrows():
            query = str(row[query_col]) if pd.notna(row[query_col]) else ""
            category = (
                str(row[category_col]) if category_col and pd.notna(row[category_col]) else None
            )

            should_remove, reason = self.filter.should_remove(
                query, category, remove_numeric=self.config.remove_numeric_only
            )

            if should_remove:
                remove_indices.append(idx)
                removal_reasons.append(reason)
            else:
                keep_indices.append(idx)

        # Create cleaned and removed DataFrames
        cleaned_df = (
            df.loc[keep_indices].copy() if keep_indices else pd.DataFrame(columns=df.columns)
        )
        removed_df = (
            df.loc[remove_indices].copy() if remove_indices else pd.DataFrame(columns=df.columns)
        )

        # Add removal reason to removed_df
        if len(removed_df) > 0:
            removed_df["matched_stop"] = removal_reasons

        logger.info(
            f"Cleaning complete: {len(cleaned_df)} rows kept, {len(removed_df)} rows removed"
        )

        # Store removed rows for later export
        self.removed_rows = removed_df.to_dict("records") if len(removed_df) > 0 else []

        return cleaned_df, removed_df

    def _detect_column(self, df: pd.DataFrame, possible_names: list[str]) -> str:
        """Detect column name from list of possibilities."""
        for name in possible_names:
            if name in df.columns:
                return name

        # Try case-insensitive match
        lower_cols = {col.lower(): col for col in df.columns}
        for name in possible_names:
            if name.lower() in lower_cols:
                return lower_cols[name.lower()]

        return ""

    def extract_unique_queries(self, df: pd.DataFrame) -> list[tuple[str, int]]:
        """
        Extract unique search queries with their counts.

        Args:
            df: Cleaned DataFrame

        Returns:
            List of (query, count) tuples
        """
        query_col = self._detect_column(df, ["query", "Поисковый запрос", "запрос"])
        count_col = self._detect_column(df, ["count", "Количество запросов", "количество"])

        if not query_col:
            raise ValueError("Could not find query column in DataFrame")

        # Group by query and sum counts
        if count_col and count_col in df.columns:
            # Use existing count column
            grouped = df.groupby(query_col)[count_col].sum().reset_index()
            queries = list(zip(grouped[query_col], grouped[count_col]))
        else:
            # Count occurrences
            value_counts = df[query_col].value_counts()
            queries = list(value_counts.items())

        logger.info(f"Extracted {len(queries)} unique queries")

        return queries

    def get_removed_rows(self) -> list[dict]:
        """Get list of removed rows with reasons."""
        return self.removed_rows
