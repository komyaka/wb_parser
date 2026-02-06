"""Main application window."""

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..clean.cleaner import DataCleaner
from ..io.csv_writer import CSVWriter
from ..io.excel_reader import ExcelReader
from ..models.config import CleaningConfig, ParserConfig
from ..models.query import QueryResult, QueryStatus
from .worker import ParserWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.parser_config = ParserConfig()
        self.cleaning_config = CleaningConfig()

        self.excel_file = ""
        self.cleaned_data = None
        self.removed_data = None
        self.unique_queries = []
        self.results = []

        self.worker: ParserWorker | None = None
        self.worker_thread: QThread | None = None

        self.init_ui()
        self.setup_logging()

    def init_ui(self):
        """Initialize user interface."""
        self.setWindowTitle("WB ExactMatch Total Parser")
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)

        # Create sections
        main_layout.addWidget(self._create_file_section())
        main_layout.addWidget(self._create_settings_section())
        main_layout.addWidget(self._create_controls_section())
        main_layout.addWidget(self._create_progress_section())

        # Create splitter for data preview and log
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self._create_preview_section())
        splitter.addWidget(self._create_log_section())
        main_layout.addWidget(splitter)

        self.log_message("Application started", "INFO")

    def _create_file_section(self) -> QGroupBox:
        """Create file selection section."""
        group = QGroupBox("File Selection")
        layout = QVBoxLayout()

        # Excel file
        excel_layout = QHBoxLayout()
        excel_layout.addWidget(QLabel("Excel File:"))
        self.excel_input = QLineEdit()
        self.excel_input.setPlaceholderText("Select Excel file (.xlsx)")
        excel_layout.addWidget(self.excel_input)
        self.excel_btn = QPushButton("Browse...")
        self.excel_btn.clicked.connect(self.browse_excel)
        excel_layout.addWidget(self.excel_btn)
        layout.addLayout(excel_layout)

        # Stop categories file
        cat_layout = QHBoxLayout()
        cat_layout.addWidget(QLabel("Stop Categories (1stop.txt):"))
        self.cat_input = QLineEdit()
        self.cat_input.setText(self.cleaning_config.stop_categories_file)
        cat_layout.addWidget(self.cat_input)
        self.cat_btn = QPushButton("Browse...")
        self.cat_btn.clicked.connect(self.browse_stop_categories)
        cat_layout.addWidget(self.cat_btn)
        layout.addLayout(cat_layout)

        # Stop words file
        words_layout = QHBoxLayout()
        words_layout.addWidget(QLabel("Stop Words (2stop.txt):"))
        self.words_input = QLineEdit()
        self.words_input.setText(self.cleaning_config.stop_words_file)
        words_layout.addWidget(self.words_input)
        self.words_btn = QPushButton("Browse...")
        self.words_btn.clicked.connect(self.browse_stop_words)
        words_layout.addWidget(self.words_btn)
        layout.addLayout(words_layout)

        # Load button
        self.load_btn = QPushButton("Load and Clean Data")
        self.load_btn.clicked.connect(self.load_and_clean)
        layout.addWidget(self.load_btn)

        group.setLayout(layout)
        return group

    def _create_settings_section(self) -> QGroupBox:
        """Create parser settings section."""
        group = QGroupBox("Parser Settings")
        layout = QVBoxLayout()

        # Concurrency
        conc_layout = QHBoxLayout()
        conc_layout.addWidget(QLabel("Concurrency:"))
        self.concurrency_spin = QSpinBox()
        self.concurrency_spin.setRange(
            self.parser_config.min_concurrency, self.parser_config.max_concurrency
        )
        self.concurrency_spin.setValue(self.parser_config.concurrency)
        conc_layout.addWidget(self.concurrency_spin)
        conc_layout.addStretch()
        layout.addLayout(conc_layout)

        # Delays
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Min Delay (s):"))
        self.min_delay_spin = QDoubleSpinBox()
        self.min_delay_spin.setRange(0, 10)
        self.min_delay_spin.setSingleStep(0.1)
        self.min_delay_spin.setValue(self.parser_config.min_delay)
        delay_layout.addWidget(self.min_delay_spin)

        delay_layout.addWidget(QLabel("Max Delay (s):"))
        self.max_delay_spin = QDoubleSpinBox()
        self.max_delay_spin.setRange(0, 10)
        self.max_delay_spin.setSingleStep(0.1)
        self.max_delay_spin.setValue(self.parser_config.max_delay)
        delay_layout.addWidget(self.max_delay_spin)
        delay_layout.addStretch()
        layout.addLayout(delay_layout)

        # Timeout and retry
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (s):"))
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setSingleStep(5)
        self.timeout_spin.setValue(self.parser_config.timeout)
        timeout_layout.addWidget(self.timeout_spin)

        timeout_layout.addWidget(QLabel("Max Retries:"))
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 10)
        self.retry_spin.setValue(self.parser_config.retry_max)
        timeout_layout.addWidget(self.retry_spin)
        timeout_layout.addStretch()
        layout.addLayout(timeout_layout)

        # Options
        options_layout = QHBoxLayout()
        self.cache_check = QCheckBox("Use Cache")
        self.cache_check.setChecked(self.parser_config.use_cache)
        options_layout.addWidget(self.cache_check)

        self.force_refresh_check = QCheckBox("Force Refresh")
        self.force_refresh_check.setChecked(self.parser_config.force_refresh)
        options_layout.addWidget(self.force_refresh_check)

        self.checkpoint_check = QCheckBox("Enable Checkpoints")
        self.checkpoint_check.setChecked(self.parser_config.enable_checkpoints)
        options_layout.addWidget(self.checkpoint_check)

        options_layout.addStretch()
        layout.addLayout(options_layout)

        group.setLayout(layout)
        return group

    def _create_controls_section(self) -> QGroupBox:
        """Create control buttons section."""
        group = QGroupBox("Controls")
        layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Parsing")
        self.start_btn.clicked.connect(self.start_parsing)
        self.start_btn.setEnabled(False)
        layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.pause_parsing)
        self.pause_btn.setEnabled(False)
        layout.addWidget(self.pause_btn)

        self.resume_btn = QPushButton("Resume")
        self.resume_btn.clicked.connect(self.resume_parsing)
        self.resume_btn.setEnabled(False)
        layout.addWidget(self.resume_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_parsing)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)

        self.export_btn = QPushButton("Export CSV")
        self.export_btn.clicked.connect(self.export_csv)
        self.export_btn.setEnabled(False)
        layout.addWidget(self.export_btn)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def _create_progress_section(self) -> QGroupBox:
        """Create progress section."""
        group = QGroupBox("Progress")
        layout = QVBoxLayout()

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Statistics
        stats_layout = QHBoxLayout()

        self.total_label = QLabel("Total: 0")
        stats_layout.addWidget(self.total_label)

        self.completed_label = QLabel("Completed: 0")
        stats_layout.addWidget(self.completed_label)

        self.success_label = QLabel("Success: 0")
        stats_layout.addWidget(self.success_label)

        self.failed_label = QLabel("Failed: 0")
        stats_layout.addWidget(self.failed_label)

        self.cached_label = QLabel("Cached: 0")
        stats_layout.addWidget(self.cached_label)

        self.speed_label = QLabel("Speed: 0 q/s")
        stats_layout.addWidget(self.speed_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        group.setLayout(layout)
        return group

    def _create_preview_section(self) -> QGroupBox:
        """Create data preview section."""
        group = QGroupBox("Data Preview")
        layout = QVBoxLayout()

        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(["Query", "Count", "Status"])
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.preview_table)

        group.setLayout(layout)
        return group

    def _create_log_section(self) -> QGroupBox:
        """Create log window section."""
        group = QGroupBox("Log")
        layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        layout.addWidget(self.log_text)

        group.setLayout(layout)
        return group

    def setup_logging(self):
        """Setup logging to GUI."""
        # This will be enhanced with a QTextEdit handler
        pass

    def log_message(self, message: str, level: str = "INFO"):
        """Add message to log window."""
        timestamp = QTimer()
        color = {"INFO": "black", "WARNING": "orange", "ERROR": "red", "SUCCESS": "green"}.get(
            level, "black"
        )

        self.log_text.append(f'<span style="color:{color}">[{level}] {message}</span>')
        self.log_text.moveCursor(QTextCursor.End)

    def browse_excel(self):
        """Browse for Excel file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel File", "", "Excel Files (*.xlsx *.xls)"
        )
        if file_path:
            self.excel_input.setText(file_path)
            self.excel_file = file_path

    def browse_stop_categories(self):
        """Browse for stop categories file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Stop Categories File", "", "Text Files (*.txt)"
        )
        if file_path:
            self.cat_input.setText(file_path)
            self.cleaning_config.stop_categories_file = file_path

    def browse_stop_words(self):
        """Browse for stop words file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Stop Words File", "", "Text Files (*.txt)"
        )
        if file_path:
            self.words_input.setText(file_path)
            self.cleaning_config.stop_words_file = file_path

    def load_and_clean(self):
        """Load Excel file and clean data."""
        try:
            if not self.excel_input.text():
                QMessageBox.warning(self, "Error", "Please select an Excel file")
                return

            self.log_message("Loading Excel file...")

            # Update configs
            self.cleaning_config.stop_categories_file = self.cat_input.text()
            self.cleaning_config.stop_words_file = self.words_input.text()

            # Load Excel
            reader = ExcelReader(self.excel_input.text())
            df = reader.load(self.cleaning_config.user_column_map)

            self.log_message(f"Loaded {len(df)} rows", "SUCCESS")

            # Clean data
            self.log_message("Cleaning data...")
            cleaner = DataCleaner(self.cleaning_config)
            self.cleaned_data, self.removed_data = cleaner.clean(df)

            self.log_message(
                f"Cleaned: {len(self.cleaned_data)} kept, {len(self.removed_data)} removed",
                "SUCCESS",
            )

            # Extract unique queries
            self.unique_queries = cleaner.extract_unique_queries(self.cleaned_data)
            self.log_message(f"Found {len(self.unique_queries)} unique queries", "SUCCESS")

            # Update preview
            self._update_preview()

            # Enable start button
            self.start_btn.setEnabled(True)

        except Exception as e:
            logger.error(f"Error loading data: {e}", exc_info=True)
            self.log_message(f"Error: {str(e)}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to load data:\n{str(e)}")

    def _update_preview(self):
        """Update data preview table."""
        self.preview_table.setRowCount(min(100, len(self.unique_queries)))

        for i, (query, count) in enumerate(self.unique_queries[:100]):
            self.preview_table.setItem(i, 0, QTableWidgetItem(query))
            self.preview_table.setItem(i, 1, QTableWidgetItem(str(count)))
            self.preview_table.setItem(i, 2, QTableWidgetItem("Pending"))

    def start_parsing(self):
        """Start parsing process."""
        try:
            if not self.unique_queries:
                QMessageBox.warning(self, "Error", "No queries to process")
                return

            # Update config from UI
            self._update_config_from_ui()

            # Validate config
            errors = self.parser_config.validate()
            if errors:
                QMessageBox.warning(self, "Configuration Error", "\n".join(errors))
                return

            self.log_message("Starting parsing...")

            # Create worker
            self.worker = ParserWorker(self.parser_config, self.unique_queries)
            self.worker_thread = QThread()

            # Connect signals
            self.worker.progress.connect(self._on_progress)
            self.worker.finished.connect(self._on_finished)
            self.worker.error.connect(self._on_error)

            # Move to thread
            self.worker.moveToThread(self.worker_thread)
            self.worker_thread.started.connect(self.worker.run)

            # Update UI
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.load_btn.setEnabled(False)

            # Start thread
            self.worker_thread.start()

        except Exception as e:
            logger.error(f"Error starting parser: {e}", exc_info=True)
            self.log_message(f"Error: {str(e)}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to start parser:\n{str(e)}")

    def pause_parsing(self):
        """Pause parsing."""
        if self.worker:
            self.worker.pause()
            self.log_message("Paused", "WARNING")
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(True)

    def resume_parsing(self):
        """Resume parsing."""
        if self.worker:
            self.worker.resume()
            self.log_message("Resumed", "SUCCESS")
            self.pause_btn.setEnabled(True)
            self.resume_btn.setEnabled(False)

    def stop_parsing(self):
        """Stop parsing."""
        if self.worker:
            self.worker.stop()
            self.log_message("Stopping...", "WARNING")
            self.stop_btn.setEnabled(False)

    def _update_config_from_ui(self):
        """Update configuration from UI inputs."""
        self.parser_config.concurrency = self.concurrency_spin.value()
        self.parser_config.min_delay = self.min_delay_spin.value()
        self.parser_config.max_delay = self.max_delay_spin.value()
        self.parser_config.timeout = self.timeout_spin.value()
        self.parser_config.retry_max = self.retry_spin.value()
        self.parser_config.use_cache = self.cache_check.isChecked()
        self.parser_config.force_refresh = self.force_refresh_check.isChecked()
        self.parser_config.enable_checkpoints = self.checkpoint_check.isChecked()

    def _on_progress(self, stats: dict, result: QueryResult | None):
        """Handle progress update."""
        # Update progress bar
        if stats["total"] > 0:
            progress = int((stats["completed"] / stats["total"]) * 100)
            self.progress_bar.setValue(progress)

        # Update labels
        self.total_label.setText(f"Total: {stats['total']}")
        self.completed_label.setText(f"Completed: {stats['completed']}")
        self.success_label.setText(f"Success: {stats['success']}")
        self.failed_label.setText(f"Failed: {stats['failed']}")
        self.cached_label.setText(f"Cached: {stats['cached']}")

        # Calculate speed
        # TODO: Implement speed calculation

        # Update preview with result
        if result:
            # Find row with matching query
            for i in range(self.preview_table.rowCount()):
                item = self.preview_table.item(i, 0)
                if item and item.text() == result.query:
                    status_item = QTableWidgetItem(result.status.value)
                    if result.status == QueryStatus.SUCCESS:
                        status_item.setForeground(Qt.green)
                    elif result.status == QueryStatus.FAILED:
                        status_item.setForeground(Qt.red)
                    elif result.status == QueryStatus.CACHED:
                        status_item.setForeground(Qt.blue)
                    self.preview_table.setItem(i, 2, status_item)
                    break

    def _on_finished(self, results: list):
        """Handle parsing completion."""
        self.results = results
        self.log_message(f"Parsing complete: {len(results)} results", "SUCCESS")

        # Update UI
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.load_btn.setEnabled(True)
        self.export_btn.setEnabled(True)

        # Clean up thread
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None

        self.worker = None

        QMessageBox.information(
            self,
            "Complete",
            f"Parsing complete!\n\nTotal: {len(results)}\n"
            f"Success: {sum(1 for r in results if r.status == QueryStatus.SUCCESS)}\n"
            f"Failed: {sum(1 for r in results if r.status == QueryStatus.FAILED)}",
        )

    def _on_error(self, error_msg: str):
        """Handle error."""
        self.log_message(f"Error: {error_msg}", "ERROR")
        QMessageBox.critical(self, "Error", f"Parser error:\n{error_msg}")

        # Reset UI
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.load_btn.setEnabled(True)

    def export_csv(self):
        """Export results to CSV."""
        try:
            if not self.results:
                QMessageBox.warning(self, "Error", "No results to export")
                return

            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save CSV File", "wb_results.csv", "CSV Files (*.csv)"
            )

            if file_path:
                self.log_message("Exporting results...")

                # Prepare data
                data = []
                for result in self.results:
                    # Find count from unique_queries
                    count = next((c for q, c in self.unique_queries if q == result.query), 1)

                    row = {
                        "Поисковый запрос": result.query,
                        "Количество запросов": count,
                        "total": result.total if result.total is not None else "",
                        "status": result.status.value,
                        "fetched_at": result.fetched_at.isoformat() if result.fetched_at else "",
                        "error_message": result.error_message or "",
                    }

                    if self.parser_config.save_raw_response:
                        row["raw_response"] = result.raw_response or ""

                    data.append(row)

                # Write CSV
                fieldnames = [
                    "Поисковый запрос",
                    "Количество запросов",
                    "total",
                    "status",
                    "fetched_at",
                    "error_message",
                ]
                if self.parser_config.save_raw_response:
                    fieldnames.append("raw_response")

                writer = CSVWriter(file_path, encoding=self.parser_config.output_encoding)
                writer.write(data, fieldnames)

                self.log_message(f"Exported to {file_path}", "SUCCESS")

                # Export removed rows if any
                if self.removed_data is not None and len(self.removed_data) > 0:
                    removed_path = str(
                        Path(file_path).with_name(Path(file_path).stem + "_removed.csv")
                    )

                    removed_writer = CSVWriter(
                        removed_path, encoding=self.parser_config.output_encoding
                    )
                    removed_data_list = self.removed_data.to_dict("records")
                    removed_fieldnames = list(self.removed_data.columns)
                    removed_writer.write(removed_data_list, removed_fieldnames)

                    self.log_message(f"Exported removed rows to {removed_path}", "SUCCESS")

                QMessageBox.information(self, "Success", "Results exported successfully!")

        except Exception as e:
            logger.error(f"Error exporting CSV: {e}", exc_info=True)
            self.log_message(f"Export error: {str(e)}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to export:\n{str(e)}")
