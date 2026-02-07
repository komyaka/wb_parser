"""Resource path utilities for PyInstaller compatibility."""

import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """
    Get absolute path to resource, works for dev and PyInstaller.

    When running as a PyInstaller bundle, resources are extracted to a temporary
    directory referenced by sys._MEIPASS. In development mode, paths are resolved
    relative to the project root.

    Args:
        relative_path: Path relative to project root (e.g., "data/1stop.txt")

    Returns:
        Absolute Path to the resource
    """
    if getattr(sys, "frozen", False):
        # Running as compiled executable
        base_path = Path(sys._MEIPASS)
    else:
        # Running in development mode - go up from src/core/ to project root
        base_path = Path(__file__).resolve().parent.parent.parent

    return base_path / relative_path
