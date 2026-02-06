#!/usr/bin/env python3
"""Main entry point for WB Parser GUI application."""

import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow


def setup_logging():
    """Setup application logging."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_dir / "wb_parser.log"), logging.StreamHandler()],
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
