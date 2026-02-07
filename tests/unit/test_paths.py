"""Unit tests for resource path utilities."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.paths import get_resource_path


def test_get_resource_path_development():
    """Test path resolution in development mode."""
    # In development, should resolve relative to project root
    result = get_resource_path("data/1stop.txt")

    assert isinstance(result, Path)
    assert str(result).endswith("1stop.txt")
    # Verify it goes to project root by checking parent structure
    assert result.name == "1stop.txt"
    assert result.parent.name == "data"


def test_get_resource_path_frozen():
    """Test path resolution in frozen (PyInstaller) mode."""
    # Mock PyInstaller frozen state
    with patch.object(sys, "frozen", True, create=True):
        with patch.object(sys, "_MEIPASS", "/tmp/fake_meipass", create=True):
            result = get_resource_path("data/1stop.txt")

            assert isinstance(result, Path)
            assert str(result) == "/tmp/fake_meipass/data/1stop.txt"


def test_get_resource_path_different_files():
    """Test path resolution for different files."""
    files = [
        "data/1stop.txt",
        "data/2stop.txt",
        "config/settings.json",
        "main.py",
    ]

    for file_path in files:
        result = get_resource_path(file_path)
        assert isinstance(result, Path)
        assert str(result).endswith(file_path)
