"""CSV writer for results export."""

import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class CSVWriter:
    """Write results to CSV file."""

    def __init__(self, filepath: str, encoding: str = "utf-8-sig"):
        self.filepath = Path(filepath)
        self.encoding = encoding

    def write(self, data: list[dict[str, any]], fieldnames: list[str]) -> None:
        """
        Write data to CSV file.

        Args:
            data: List of dictionaries with row data
            fieldnames: Ordered list of field names for CSV header
        """
        logger.info(f"Writing {len(data)} rows to {self.filepath}")

        # Ensure directory exists
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(self.filepath, "w", newline="", encoding=self.encoding) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(data)

        logger.info(f"Successfully wrote CSV: {self.filepath}")

    def append(self, data: list[dict[str, any]], fieldnames: list[str]) -> None:
        """
        Append data to existing CSV file.

        Args:
            data: List of dictionaries with row data
            fieldnames: Ordered list of field names
        """
        mode = "a" if self.filepath.exists() else "w"
        write_header = not self.filepath.exists()

        logger.info(f"Appending {len(data)} rows to {self.filepath}")

        self.filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(self.filepath, mode, newline="", encoding=self.encoding) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            if write_header:
                writer.writeheader()
            writer.writerows(data)

    def read(self) -> list[dict[str, str]]:
        """Read CSV file and return list of dictionaries."""
        if not self.filepath.exists():
            return []

        with open(self.filepath, encoding=self.encoding) as f:
            reader = csv.DictReader(f)
            return list(reader)
