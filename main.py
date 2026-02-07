#!/usr/bin/env python3
"""Main entry point for WB Parser GUI application."""

import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.config.settings import AppSettings


def setup_logging():
    """Setup application logging."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Load settings to check detailed_logging preference
    settings = AppSettings()

    # Set logging level based on settings
    log_level = logging.DEBUG if settings.detailed_logging else logging.INFO

    handlers = [logging.StreamHandler()]

    # Always create the standard log file
    handlers.append(logging.FileHandler(log_dir / "wb_parser.log"))

    # If detailed logging is enabled, also add debug log file
    if settings.detailed_logging:
        debug_handler = logging.FileHandler(log_dir / "wb_parser_debug.log", encoding="utf-8")
        debug_handler.setLevel(logging.DEBUG)
        handlers.append(debug_handler)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


def main():
    """Main application entry point."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting WB Parser application")

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("WB ExactMatch Total Parser")
    app.setOrganizationName("WB Parser")

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
