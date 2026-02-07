"""Application settings management."""

import json
import logging
from pathlib import Path

from ..core.paths import get_resource_path

logger = logging.getLogger(__name__)


class AppSettings:
    """Manage application settings with JSON persistence."""

    def __init__(self, settings_file: str | None = None):
        """
        Initialize settings.

        Args:
            settings_file: Path to settings JSON file. If None, uses default location
                          relative to project root (config/settings.json).
        """
        if settings_file is None:
            self.settings_file = get_resource_path("config/settings.json")
        else:
            self.settings_file = Path(settings_file)

        self.language: str = "ru"  # Default language
        self.show_tooltips: bool = True  # Default show tooltips
        self.detailed_logging: bool = False  # Default detailed logging off
        self.load()

    def load(self) -> None:
        """Load settings from JSON file."""
        if not self.settings_file.exists():
            logger.info(f"Settings file not found, using defaults: {self.settings_file}")
            return

        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.language = data.get("language", "ru")
            self.show_tooltips = data.get("show_tooltips", True)
            self.detailed_logging = data.get("detailed_logging", False)

            logger.info(f"Loaded settings from {self.settings_file}")
        except Exception as e:
            logger.warning(f"Failed to load settings: {e}, using defaults")

    def save(self) -> None:
        """Save settings to JSON file."""
        try:
            # Ensure config directory exists
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "language": self.language,
                "show_tooltips": self.show_tooltips,
                "detailed_logging": self.detailed_logging,
            }

            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved settings to {self.settings_file}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}", exc_info=True)
