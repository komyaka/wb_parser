"""Unit tests for application settings."""

import json
import tempfile
from pathlib import Path

import pytest

from src.config.settings import AppSettings


def test_app_settings_defaults():
    """Test default settings values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / "settings.json"
        settings = AppSettings(str(settings_file))

        assert settings.language == "ru"
        assert settings.show_tooltips is True


def test_app_settings_save_and_load():
    """Test saving and loading settings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / "settings.json"

        # Create and save settings
        settings1 = AppSettings(str(settings_file))
        settings1.language = "en"
        settings1.show_tooltips = False
        settings1.save()

        # Load settings in new instance
        settings2 = AppSettings(str(settings_file))

        assert settings2.language == "en"
        assert settings2.show_tooltips is False


def test_app_settings_json_format():
    """Test that settings are saved in correct JSON format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / "settings.json"

        settings = AppSettings(str(settings_file))
        settings.language = "ru"
        settings.show_tooltips = True
        settings.save()

        # Read and verify JSON
        with open(settings_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["language"] == "ru"
        assert data["show_tooltips"] is True


def test_app_settings_creates_directory():
    """Test that settings save creates directory if needed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / "subdir" / "settings.json"

        settings = AppSettings(str(settings_file))
        settings.save()

        assert settings_file.exists()
        assert settings_file.parent.is_dir()


def test_app_settings_load_missing_file():
    """Test loading when file doesn't exist uses defaults."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / "nonexistent.json"

        settings = AppSettings(str(settings_file))

        assert settings.language == "ru"
        assert settings.show_tooltips is True


def test_app_settings_load_invalid_json():
    """Test loading invalid JSON uses defaults."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / "invalid.json"

        # Write invalid JSON
        with open(settings_file, "w") as f:
            f.write("not valid json {")

        settings = AppSettings(str(settings_file))

        # Should fall back to defaults
        assert settings.language == "ru"
        assert settings.show_tooltips is True


def test_app_settings_partial_data():
    """Test loading partial settings data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / "partial.json"

        # Write partial settings
        with open(settings_file, "w") as f:
            json.dump({"language": "en"}, f)

        settings = AppSettings(str(settings_file))

        assert settings.language == "en"
        assert settings.show_tooltips is True  # Should use default
