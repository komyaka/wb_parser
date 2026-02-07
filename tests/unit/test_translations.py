"""Unit tests for translations."""

import importlib.util
from pathlib import Path

import pytest

# Import translations module directly to avoid PySide6 dependency
spec = importlib.util.spec_from_file_location(
    "translations",
    Path(__file__).parent.parent.parent / "src" / "ui" / "translations.py"
)
translations_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(translations_module)

TRANSLATIONS = translations_module.TRANSLATIONS
get_text = translations_module.get_text


def test_translations_structure():
    """Test that translations dictionary has correct structure."""
    assert "en" in TRANSLATIONS
    assert "ru" in TRANSLATIONS
    assert isinstance(TRANSLATIONS["en"], dict)
    assert isinstance(TRANSLATIONS["ru"], dict)


def test_translations_keys_match():
    """Test that English and Russian have same keys."""
    en_keys = set(TRANSLATIONS["en"].keys())
    ru_keys = set(TRANSLATIONS["ru"].keys())

    missing_in_ru = en_keys - ru_keys
    missing_in_en = ru_keys - en_keys

    assert not missing_in_ru, f"Keys missing in Russian: {missing_in_ru}"
    assert not missing_in_en, f"Keys missing in English: {missing_in_en}"


def test_get_text_english():
    """Test getting text in English."""
    text = get_text("app_title", "en")
    assert text == "WB ExactMatch Total Parser"


def test_get_text_russian():
    """Test getting text in Russian."""
    text = get_text("load_and_clean", "ru")
    assert text == "Загрузить и очистить данные"


def test_get_text_default_language():
    """Test default language is Russian."""
    text = get_text("load_and_clean")
    assert text == "Загрузить и очистить данные"


def test_get_text_with_kwargs():
    """Test text formatting with kwargs."""
    text = get_text("msg_loaded", "en", count=42)
    assert "42" in text


def test_get_text_missing_key():
    """Test behavior with missing key."""
    text = get_text("nonexistent_key", "en")
    assert text == "nonexistent_key"


def test_all_keys_nonempty():
    """Test that all translation values are non-empty."""
    for lang, translations in TRANSLATIONS.items():
        for key, value in translations.items():
            assert value, f"Empty translation for key '{key}' in language '{lang}'"


def test_essential_keys_exist():
    """Test that essential UI keys exist."""
    essential_keys = [
        "app_title",
        "file_selection",
        "parser_settings",
        "controls",
        "progress",
        "data_preview",
        "log",
        "tab_parsing",
        "tab_settings",
        "language",
        "show_tooltips",
    ]

    for key in essential_keys:
        assert key in TRANSLATIONS["en"], f"Missing essential key '{key}' in English"
        assert key in TRANSLATIONS["ru"], f"Missing essential key '{key}' in Russian"
