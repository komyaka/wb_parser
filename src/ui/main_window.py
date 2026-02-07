"""Main application window."""

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..clean.cleaner import DataCleaner
from ..config.settings import AppSettings
from ..io.csv_writer import CSVWriter
from ..io.excel_reader import ExcelReader
from ..models.config import CleaningConfig, ParserConfig
from ..models.query import QueryResult, QueryStatus
from .translations import get_text
from .worker import ParserWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.settings = AppSettings()
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
        self.setWindowTitle(self.tr("app_title"))
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)

        # Create tab widget
        # Note: Tab labels are set at creation time. For full language change effect,
        # application restart is required (user is informed via dialog).
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_parsing_tab(), self.tr("tab_parsing"))
        self.tabs.addTab(self._create_settings_tab(), self.tr("tab_settings"))
        main_layout.addWidget(self.tabs)

        self.log_message("Application started", "INFO")

    def _create_parsing_tab(self) -> QWidget:
        """Create main parsing tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Create sections
        layout.addWidget(self._create_file_section())
        layout.addWidget(self._create_parser_settings_section())
        layout.addWidget(self._create_controls_section())
        layout.addWidget(self._create_progress_section())

        # Create splitter for data preview and log
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self._create_preview_section())
        splitter.addWidget(self._create_log_section())
        layout.addWidget(splitter)

        return tab

    def _create_settings_tab(self) -> QWidget:
        """Create settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Settings group
        group = QGroupBox(self.tr("app_settings"))
        settings_layout = QVBoxLayout()

        # Language selection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel(self.tr("language")))
        self.language_combo = QComboBox()
        self.language_combo.addItem(self.tr("language_ru"), "ru")
        self.language_combo.addItem(self.tr("language_en"), "en")
        # Set current language
        index = 0 if self.settings.language == "ru" else 1
        self.language_combo.setCurrentIndex(index)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_layout.addWidget(self.language_combo)
        lang_layout.addStretch()
        settings_layout.addLayout(lang_layout)

        # Tooltips toggle
        tooltip_layout = QHBoxLayout()
        self.tooltip_check = QCheckBox(self.tr("show_tooltips"))
        self.tooltip_check.setChecked(self.settings.show_tooltips)
        self.tooltip_check.stateChanged.connect(self._on_tooltips_changed)
        if self.settings.show_tooltips:
            self.tooltip_check.setToolTip(self.tr("tooltip_show_tooltips"))
        tooltip_layout.addWidget(self.tooltip_check)
        tooltip_layout.addStretch()
        settings_layout.addLayout(tooltip_layout)

        settings_layout.addStretch()
        group.setLayout(settings_layout)
        layout.addWidget(group)
        layout.addStretch()

        return tab

    def tr(self, key: str, **kwargs) -> str:
        """Translate text using current language."""
        return get_text(key, self.settings.language, **kwargs)

    def _on_language_changed(self, index: int):
        """Handle language change."""
        language = self.language_combo.itemData(index)
        if language != self.settings.language:
            self.settings.language = language
            self.settings.save()
            # Show restart message in both languages for clarity
            en_msg = "Language changed. Please restart the application for full effect."
            ru_msg = "Язык изменён. Пожалуйста, перезапустите приложение для полного применения."
            QMessageBox.information(
                self,
                self.tr("dialog_success"),
                f"{en_msg}\n\n{ru_msg}",
            )

    def _on_tooltips_changed(self, state: int):
        """Handle tooltips toggle."""
        self.settings.show_tooltips = bool(state)
        self.settings.save()
        self._update_tooltips()

    def _create_file_section(self) -> QGroupBox:
        """Create file selection section."""
        group = QGroupBox(self.tr("file_selection"))
        layout = QVBoxLayout()

        # Excel file
        excel_layout = QHBoxLayout()
        excel_layout.addWidget(QLabel(self.tr("excel_file")))
        self.excel_input = QLineEdit()
        self.excel_input.setPlaceholderText(self.tr("excel_placeholder"))
        excel_layout.addWidget(self.excel_input)
        self.excel_btn = QPushButton(self.tr("browse"))
        self.excel_btn.clicked.connect(self.browse_excel)
        excel_layout.addWidget(self.excel_btn)
        layout.addLayout(excel_layout)

        # Stop categories file
        cat_layout = QHBoxLayout()
        cat_layout.addWidget(QLabel(self.tr("stop_categories")))
        self.cat_input = QLineEdit()
        self.cat_input.setText(self.cleaning_config.stop_categories_file)
        cat_layout.addWidget(self.cat_input)
        self.cat_btn = QPushButton(self.tr("browse"))
        self.cat_btn.clicked.connect(self.browse_stop_categories)
        cat_layout.addWidget(self.cat_btn)
        layout.addLayout(cat_layout)

        # Stop words file
        words_layout = QHBoxLayout()
        words_layout.addWidget(QLabel(self.tr("stop_words")))
        self.words_input = QLineEdit()
        self.words_input.setText(self.cleaning_config.stop_words_file)
        words_layout.addWidget(self.words_input)
        self.words_btn = QPushButton(self.tr("browse"))
        self.words_btn.clicked.connect(self.browse_stop_words)
        words_layout.addWidget(self.words_btn)
        layout.addLayout(words_layout)

        # Load button
        self.load_btn = QPushButton(self.tr("load_and_clean"))
        self.load_btn.clicked.connect(self.load_and_clean)
        layout.addWidget(self.load_btn)

        group.setLayout(layout)
        return group

    def _create_parser_settings_section(self) -> QGroupBox:
        """Create parser settings section."""
        group = QGroupBox(self.tr("parser_settings"))
        layout = QVBoxLayout()

        # Concurrency
        conc_layout = QHBoxLayout()
        conc_layout.addWidget(QLabel(self.tr("concurrency")))
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
        delay_layout.addWidget(QLabel(self.tr("min_delay")))
        self.min_delay_spin = QDoubleSpinBox()
        self.min_delay_spin.setRange(0, 10)
        self.min_delay_spin.setSingleStep(0.1)
        self.min_delay_spin.setValue(self.parser_config.min_delay)
        delay_layout.addWidget(self.min_delay_spin)

        delay_layout.addWidget(QLabel(self.tr("max_delay")))
        self.max_delay_spin = QDoubleSpinBox()
        self.max_delay_spin.setRange(0, 10)
        self.max_delay_spin.setSingleStep(0.1)
        self.max_delay_spin.setValue(self.parser_config.max_delay)
        delay_layout.addWidget(self.max_delay_spin)
        delay_layout.addStretch()
        layout.addLayout(delay_layout)

        # Timeout and retry
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel(self.tr("timeout")))
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setSingleStep(5)
        self.timeout_spin.setValue(self.parser_config.timeout)
        timeout_layout.addWidget(self.timeout_spin)

        timeout_layout.addWidget(QLabel(self.tr("max_retries")))
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 10)
        self.retry_spin.setValue(self.parser_config.retry_max)
        timeout_layout.addWidget(self.retry_spin)
        timeout_layout.addStretch()
        layout.addLayout(timeout_layout)

        # Options
        options_layout = QHBoxLayout()
        self.cache_check = QCheckBox(self.tr("use_cache"))
        self.cache_check.setChecked(self.parser_config.use_cache)
        options_layout.addWidget(self.cache_check)

        self.force_refresh_check = QCheckBox(self.tr("force_refresh"))
        self.force_refresh_check.setChecked(self.parser_config.force_refresh)
        options_layout.addWidget(self.force_refresh_check)

        self.checkpoint_check = QCheckBox(self.tr("enable_checkpoints"))
        self.checkpoint_check.setChecked(self.parser_config.enable_checkpoints)
        options_layout.addWidget(self.checkpoint_check)

        options_layout.addStretch()
        layout.addLayout(options_layout)

        group.setLayout(layout)

        # Set tooltips after creating widgets
        self._update_tooltips()

        return group

    def _update_tooltips(self):
        """Update tooltips based on settings."""
        if self.settings.show_tooltips:
            self.concurrency_spin.setToolTip(self.tr("tooltip_concurrency"))
            self.min_delay_spin.setToolTip(self.tr("tooltip_min_delay"))
            self.max_delay_spin.setToolTip(self.tr("tooltip_max_delay"))
            self.timeout_spin.setToolTip(self.tr("tooltip_timeout"))
            self.retry_spin.setToolTip(self.tr("tooltip_max_retries"))
            self.cache_check.setToolTip(self.tr("tooltip_use_cache"))
            self.force_refresh_check.setToolTip(self.tr("tooltip_force_refresh"))
            self.checkpoint_check.setToolTip(self.tr("tooltip_enable_checkpoints"))
            if hasattr(self, "tooltip_check"):
                self.tooltip_check.setToolTip(self.tr("tooltip_show_tooltips"))
        else:
            # Clear tooltips
            self.concurrency_spin.setToolTip("")
            self.min_delay_spin.setToolTip("")
            self.max_delay_spin.setToolTip("")
            self.timeout_spin.setToolTip("")
            self.retry_spin.setToolTip("")
            self.cache_check.setToolTip("")
            self.force_refresh_check.setToolTip("")
            self.checkpoint_check.setToolTip("")
            if hasattr(self, "tooltip_check"):
                self.tooltip_check.setToolTip("")

    def _create_controls_section(self) -> QGroupBox:
        """Create control buttons section."""
        group = QGroupBox(self.tr("controls"))
        layout = QHBoxLayout()

        self.start_btn = QPushButton(self.tr("start_parsing"))
        self.start_btn.clicked.connect(self.start_parsing)
        self.start_btn.setEnabled(False)
        layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton(self.tr("pause"))
        self.pause_btn.clicked.connect(self.pause_parsing)
        self.pause_btn.setEnabled(False)
        layout.addWidget(self.pause_btn)

        self.resume_btn = QPushButton(self.tr("resume"))
        self.resume_btn.clicked.connect(self.resume_parsing)
        self.resume_btn.setEnabled(False)
        layout.addWidget(self.resume_btn)

        self.stop_btn = QPushButton(self.tr("stop"))
        self.stop_btn.clicked.connect(self.stop_parsing)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)

        self.export_btn = QPushButton(self.tr("export_csv"))
        self.export_btn.clicked.connect(self.export_csv)
        self.export_btn.setEnabled(False)
        layout.addWidget(self.export_btn)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def _create_progress_section(self) -> QGroupBox:
        """Create progress section."""
        group = QGroupBox(self.tr("progress"))
        layout = QVBoxLayout()

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Statistics
        stats_layout = QHBoxLayout()

        self.total_label = QLabel(f"{self.tr('total')}: 0")
        stats_layout.addWidget(self.total_label)

        self.completed_label = QLabel(f"{self.tr('completed')}: 0")
        stats_layout.addWidget(self.completed_label)

        self.success_label = QLabel(f"{self.tr('success')}: 0")
        stats_layout.addWidget(self.success_label)

        self.failed_label = QLabel(f"{self.tr('failed')}: 0")
        stats_layout.addWidget(self.failed_label)

        self.cached_label = QLabel(f"{self.tr('cached')}: 0")
        stats_layout.addWidget(self.cached_label)

        self.speed_label = QLabel(f"{self.tr('speed')}: 0 q/s")
        stats_layout.addWidget(self.speed_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        group.setLayout(layout)
        return group

    def _create_preview_section(self) -> QGroupBox:
        """Create data preview section."""
        group = QGroupBox(self.tr("data_preview"))
        layout = QVBoxLayout()

        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(
            [self.tr("preview_query"), self.tr("preview_count"), self.tr("preview_status")]
        )
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.preview_table)

        group.setLayout(layout)
        return group

    def _create_log_section(self) -> QGroupBox:
        """Create log window section."""
        group = QGroupBox(self.tr("log"))
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
            self,
            self.tr("dialog_select_excel_title"),
            "",
            self.tr("dialog_excel_filter"),
        )
        if file_path:
            self.excel_input.setText(file_path)
            self.excel_file = file_path

    def browse_stop_categories(self):
        """Browse for stop categories file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("dialog_select_stop_cat_title"),
            "",
            self.tr("dialog_text_filter"),
        )
        if file_path:
            self.cat_input.setText(file_path)
            self.cleaning_config.stop_categories_file = file_path

    def browse_stop_words(self):
        """Browse for stop words file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("dialog_select_stop_words_title"),
            "",
            self.tr("dialog_text_filter"),
        )
        if file_path:
            self.words_input.setText(file_path)
            self.cleaning_config.stop_words_file = file_path

    def load_and_clean(self):
        """Load Excel file and clean data."""
        try:
            if not self.excel_input.text():
                QMessageBox.warning(self, self.tr("dialog_error"), self.tr("msg_select_excel"))
                return

            self.log_message(self.tr("msg_loading"))

            # Update configs
            self.cleaning_config.stop_categories_file = self.cat_input.text()
            self.cleaning_config.stop_words_file = self.words_input.text()

            # Load Excel
            reader = ExcelReader(self.excel_input.text())
            df = reader.load(self.cleaning_config.user_column_map)

            self.log_message(self.tr("msg_loaded", count=len(df)), "SUCCESS")

            # Clean data
            self.log_message(self.tr("msg_cleaning"))
            cleaner = DataCleaner(self.cleaning_config)
            self.cleaned_data, self.removed_data = cleaner.clean(df)

            self.log_message(
                self.tr(
                    "msg_cleaned",
                    kept=len(self.cleaned_data),
                    removed=len(self.removed_data),
                ),
                "SUCCESS",
            )

            # Save removed rows to separate files
            if len(self.removed_data) > 0:
                removed_by_categories, removed_by_stop_words = cleaner.split_removed_by_reason(
                    self.removed_data
                )

                # Save categories file
                if len(removed_by_categories) > 0:
                    cat_path = Path("data/removed_by_categories.csv")
                    cat_path.parent.mkdir(parents=True, exist_ok=True)
                    cat_writer = CSVWriter(str(cat_path), encoding="utf-8-sig")
                    cat_writer.write(
                        removed_by_categories.to_dict("records"),
                        list(removed_by_categories.columns),
                    )
                    self.log_message(
                        self.tr("msg_saved_categories", path=str(cat_path)), "SUCCESS"
                    )

                # Save stop words file
                if len(removed_by_stop_words) > 0:
                    words_path = Path("data/removed_by_stop_words.csv")
                    words_path.parent.mkdir(parents=True, exist_ok=True)
                    words_writer = CSVWriter(str(words_path), encoding="utf-8-sig")
                    words_writer.write(
                        removed_by_stop_words.to_dict("records"),
                        list(removed_by_stop_words.columns),
                    )
                    self.log_message(
                        self.tr("msg_saved_stop_words", path=str(words_path)), "SUCCESS"
                    )

            # Extract unique queries
            self.unique_queries = cleaner.extract_unique_queries(self.cleaned_data)
            self.log_message(
                self.tr("msg_unique_queries", count=len(self.unique_queries)), "SUCCESS"
            )

            # Update preview
            self._update_preview()

            # Enable start button
            self.start_btn.setEnabled(True)

        except Exception as e:
            logger.error(f"Error loading data: {e}", exc_info=True)
            self.log_message(f"Error: {str(e)}", "ERROR")
            QMessageBox.critical(
                self, self.tr("dialog_error"), f"Failed to load data:\n{str(e)}"
            )

    def _update_preview(self):
        """Update data preview table."""
        self.preview_table.setRowCount(min(100, len(self.unique_queries)))

        for i, (query, count) in enumerate(self.unique_queries[:100]):
            self.preview_table.setItem(i, 0, QTableWidgetItem(query))
            self.preview_table.setItem(i, 1, QTableWidgetItem(str(count)))
            self.preview_table.setItem(i, 2, QTableWidgetItem(self.tr("preview_pending")))

    def start_parsing(self):
        """Start parsing process."""
        try:
            if not self.unique_queries:
                QMessageBox.warning(self, self.tr("dialog_error"), self.tr("msg_no_queries"))
                return

            # Update config from UI
            self._update_config_from_ui()

            # Validate config
            errors = self.parser_config.validate()
            if errors:
                QMessageBox.warning(
                    self, self.tr("dialog_config_error"), "\n".join(errors)
                )
                return

            self.log_message(self.tr("msg_starting"))

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
            QMessageBox.critical(
                self, self.tr("dialog_error"), f"Failed to start parser:\n{str(e)}"
            )

    def pause_parsing(self):
        """Pause parsing."""
        if self.worker:
            self.worker.pause()
            self.log_message(self.tr("msg_paused"), "WARNING")
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(True)

    def resume_parsing(self):
        """Resume parsing."""
        if self.worker:
            self.worker.resume()
            self.log_message(self.tr("msg_resumed"), "SUCCESS")
            self.pause_btn.setEnabled(True)
            self.resume_btn.setEnabled(False)

    def stop_parsing(self):
        """Stop parsing."""
        if self.worker:
            self.worker.stop()
            self.log_message(self.tr("msg_stopping"), "WARNING")
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
        self.total_label.setText(f"{self.tr('total')}: {stats['total']}")
        self.completed_label.setText(f"{self.tr('completed')}: {stats['completed']}")
        self.success_label.setText(f"{self.tr('success')}: {stats['success']}")
        self.failed_label.setText(f"{self.tr('failed')}: {stats['failed']}")
        self.cached_label.setText(f"{self.tr('cached')}: {stats['cached']}")

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
        self.log_message(self.tr("msg_complete", count=len(results)), "SUCCESS")

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

        success_count = sum(1 for r in results if r.status == QueryStatus.SUCCESS)
        failed_count = sum(1 for r in results if r.status == QueryStatus.FAILED)

        QMessageBox.information(
            self,
            self.tr("dialog_complete"),
            self.tr(
                "dialog_complete_msg",
                total=len(results),
                success=success_count,
                failed=failed_count,
            ),
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
                QMessageBox.warning(self, self.tr("dialog_error"), self.tr("msg_no_results"))
                return

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                self.tr("dialog_save_csv_title"),
                "wb_results.csv",
                self.tr("dialog_csv_filter"),
            )

            if file_path:
                self.log_message(self.tr("msg_exporting"))

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

                self.log_message(self.tr("msg_exported", path=file_path), "SUCCESS")

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

                    self.log_message(
                        self.tr("msg_exported_removed", path=removed_path), "SUCCESS"
                    )

                QMessageBox.information(
                    self, self.tr("dialog_success"), self.tr("dialog_export_success")
                )

        except Exception as e:
            logger.error(f"Error exporting CSV: {e}", exc_info=True)
            self.log_message(self.tr("msg_export_error", error=str(e)), "ERROR")
            QMessageBox.critical(
                self, self.tr("dialog_error"), f"Failed to export:\n{str(e)}"
            )
