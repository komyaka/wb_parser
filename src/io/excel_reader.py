"""Excel file reader with auto-detection."""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class ExcelReader:
    """Read and parse Excel files with automatic sheet/header detection."""

    def __init__(self, filepath: str, sheet_name: str = "Детальная информация"):
        self.filepath = Path(filepath)
        self.sheet_name = sheet_name
        self.df: pd.DataFrame | None = None
        self.header_row: int = 0

    def load(self, column_map: dict[str, str] | None = None) -> pd.DataFrame:
        """
        Load Excel file with auto-detection.

        Args:
            column_map: Mapping from Excel columns to internal names

        Returns:
            Loaded DataFrame

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If sheet not found or data invalid
        """
        if not self.filepath.exists():
            raise FileNotFoundError(f"Excel file not found: {self.filepath}")

        logger.info(f"Loading Excel file: {self.filepath}")

        # Try to load the specific sheet
        try:
            self.df = pd.read_excel(
                self.filepath, sheet_name=self.sheet_name, header=None  # Load without header first
            )
        except ValueError:
            # Sheet not found, try to auto-detect
            logger.warning(f"Sheet '{self.sheet_name}' not found, trying auto-detection")
            self.df = self._auto_detect_sheet()

        # Auto-detect header row
        self.header_row = self._detect_header_row()

        # Reload with proper header
        self.df = pd.read_excel(self.filepath, sheet_name=self.sheet_name, header=self.header_row)

        logger.info(f"Loaded {len(self.df)} rows from sheet '{self.sheet_name}'")

        # Apply column mapping if provided
        if column_map:
            self._apply_column_mapping(column_map)

        return self.df

    def _auto_detect_sheet(self) -> pd.DataFrame:
        """Auto-detect the correct sheet."""
        xl_file = pd.ExcelFile(self.filepath)

        # Priority: sheets containing keywords
        keywords = ["детальная", "информация", "detail", "info", "data"]

        for sheet in xl_file.sheet_names:
            if any(kw in sheet.lower() for kw in keywords):
                logger.info(f"Auto-detected sheet: {sheet}")
                self.sheet_name = sheet
                return pd.read_excel(self.filepath, sheet_name=sheet, header=None)

        # Fall back to first sheet
        self.sheet_name = xl_file.sheet_names[0]
        logger.info(f"Using first sheet: {self.sheet_name}")
        return pd.read_excel(self.filepath, sheet_name=self.sheet_name, header=None)

    def _detect_header_row(self) -> int:
        """
        Detect the header row by looking for expected column names.

        Returns:
            Index of header row (0-based)
        """
        if self.df is None:
            return 0

        # Look for these columns
        expected_columns = ["поисковый запрос", "запрос", "категория", "количество"]

        # Check first 10 rows
        for idx in range(min(10, len(self.df))):
            row_values = [str(v).lower() for v in self.df.iloc[idx] if pd.notna(v)]

            # If at least 2 expected columns found
            matches = sum(1 for col in expected_columns if any(col in val for val in row_values))

            if matches >= 2:
                logger.info(f"Detected header row at index {idx}")
                return idx

        logger.info("Using default header row: 0")
        return 0

    def _apply_column_mapping(self, column_map: dict[str, str]) -> None:
        """Apply column name mapping."""
        # Try to rename columns based on mapping
        rename_dict = {}

        for excel_col, internal_name in column_map.items():
            if excel_col in self.df.columns:
                rename_dict[excel_col] = internal_name

        if rename_dict:
            self.df.rename(columns=rename_dict, inplace=True)
            logger.info(f"Applied column mapping: {rename_dict}")

    def get_column_names(self) -> list[str]:
        """Get list of column names."""
        if self.df is not None:
            return list(self.df.columns)
        return []

    def get_preview(self, n_rows: int = 10) -> pd.DataFrame:
        """Get preview of first n rows."""
        if self.df is not None:
            return self.df.head(n_rows)
        return pd.DataFrame()
