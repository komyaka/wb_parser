"""Background worker for parsing."""

import asyncio
import logging

from PySide6.QtCore import QObject, Signal

from ..core.pipeline import ParserPipeline
from ..models.config import ParserConfig
from ..models.query import QueryResult

logger = logging.getLogger(__name__)


class ParserWorker(QObject):
    """Worker for running parser in background thread."""

    # Signals
    progress = Signal(dict, object)  # (stats, result)
    finished = Signal(list)  # List of QueryResult
    error = Signal(str)  # Error message

    def __init__(self, config: ParserConfig, queries: list[tuple[str, int]]):
        super().__init__()
        self.config = config
        self.queries = queries
        self.pipeline: ParserPipeline | None = None

    def run(self):
        """Run the parser (called in worker thread)."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Create pipeline
            self.pipeline = ParserPipeline(self.config)
            self.pipeline.set_progress_callback(self._on_progress)

            # Run async processing
            results = loop.run_until_complete(self.pipeline.process_queries(self.queries))

            # Clean up
            loop.close()

            # Emit finished signal
            self.finished.emit(results)

        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            self.error.emit(str(e))

    def _on_progress(self, stats: dict, result: QueryResult | None):
        """Progress callback from pipeline."""
        self.progress.emit(stats, result)

    def pause(self):
        """Pause processing."""
        if self.pipeline:
            self.pipeline.pause()

    def resume(self):
        """Resume processing."""
        if self.pipeline:
            self.pipeline.resume()

    def stop(self):
        """Stop processing."""
        if self.pipeline:
            self.pipeline.stop()
