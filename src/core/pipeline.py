"""Main processing pipeline for WB parser."""

import asyncio
import logging
import random
from collections.abc import Callable

from ..api.client import WBAPIClient
from ..api.retry import RetryStrategy
from ..io.sqlite_cache import SQLiteCache
from ..models.config import ParserConfig
from ..models.query import QueryResult, QueryStatus
from .checkpoint import CheckpointManager

logger = logging.getLogger(__name__)

# Rate limiting backoff constants
RATE_LIMIT_BASE_BACKOFF_SECONDS = 5.0
RATE_LIMIT_MAX_BACKOFF_SECONDS = 60.0


class ParserPipeline:
    """Main pipeline for processing queries."""

    def __init__(self, config: ParserConfig):
        self.config = config
        self.cache: SQLiteCache | None = None
        self.checkpoint: CheckpointManager | None = None
        self.is_running = False
        self.is_paused = False
        self._stop_event = asyncio.Event()
        self._pause_event = asyncio.Event()

        # Global rate limiting coordination
        self._rate_limit_event = asyncio.Event()
        self._rate_limit_event.set()  # Initially allow requests
        self._rate_limit_lock = asyncio.Lock()
        self._consecutive_rate_limits = 0

        # Statistics
        self.stats = {
            "total": 0,
            "completed": 0,
            "success": 0,
            "failed": 0,
            "cached": 0,
            "in_progress": 0,
        }

        # Progress callback
        self.progress_callback: Callable | None = None

    def set_progress_callback(self, callback: Callable) -> None:
        """Set callback for progress updates."""
        self.progress_callback = callback

    def _notify_progress(self, result: QueryResult | None = None) -> None:
        """Notify progress callback."""
        if self.progress_callback:
            self.progress_callback(self.stats, result)

    async def _on_rate_limited(self) -> None:
        """
        Handle global rate limit backoff.

        This method implements exponential backoff when rate limiting occurs.
        It ensures only one backoff happens at a time using a lock, and blocks
        all concurrent requests until the backoff period completes.
        """
        async with self._rate_limit_lock:
            # Check if already backing off
            if not self._rate_limit_event.is_set():
                return  # Another task is already handling backoff

            # Clear event to block all concurrent requests
            self._rate_limit_event.clear()
            self._consecutive_rate_limits += 1

            # Calculate exponential backoff with constants
            backoff = min(
                RATE_LIMIT_BASE_BACKOFF_SECONDS * (2 ** (self._consecutive_rate_limits - 1)),
                RATE_LIMIT_MAX_BACKOFF_SECONDS,
            )
            logger.warning(
                f"Global rate limit backoff: {backoff:.1f}s "
                f"(consecutive rate limits: {self._consecutive_rate_limits})"
            )

        # Sleep outside the lock to allow other tasks to check the event
        await asyncio.sleep(backoff)

        # Re-enable requests
        self._rate_limit_event.set()

    async def _wait_for_rate_limit(self) -> None:
        """Wait until the global rate limit backoff is over."""
        await self._rate_limit_event.wait()

    async def process_queries(self, queries: list[tuple[str, int]]) -> list[QueryResult]:
        """
        Process list of queries with API calls.

        Args:
            queries: List of (query_string, count) tuples

        Returns:
            List of QueryResult objects
        """
        self.is_running = True
        self._stop_event.clear()
        self._pause_event.clear()

        # Initialize cache
        if self.config.use_cache:
            self.cache = SQLiteCache(self.config.cache_db_path)

        # Initialize checkpoint
        if self.config.enable_checkpoints:
            self.checkpoint = CheckpointManager(self.config.checkpoint_file)

            # Try to load existing checkpoint
            if self.checkpoint.load():
                logger.info("Resuming from checkpoint")

        # Prepare query list
        query_strings = [q[0] for q in queries]

        # Filter out completed queries if resuming
        if self.checkpoint:
            query_strings = [q for q in query_strings if not self.checkpoint.is_completed(q)]
            logger.info(f"After checkpoint filtering: {len(query_strings)} queries remaining")

        # Update stats
        self.stats["total"] = len(query_strings)
        self.stats["completed"] = 0
        self.stats["success"] = 0
        self.stats["failed"] = 0
        self.stats["cached"] = 0
        self.stats["in_progress"] = 0

        if not query_strings:
            logger.info("All queries already completed")
            return self.checkpoint.get_results() if self.checkpoint else []

        # Create retry strategy
        retry_strategy = RetryStrategy(
            max_retries=self.config.retry_max,
            base_delay=self.config.retry_base_delay,
            max_delay=self.config.retry_max_delay,
            exponential_base=self.config.retry_exponential_base,
        )

        # Process queries with concurrency control
        results = []

        async with WBAPIClient(
            timeout=self.config.timeout,
            min_delay=self.config.min_delay,
            max_delay=self.config.max_delay,
            retry_strategy=retry_strategy,
            user_agent=self.config.user_agent,
            rate_limit_callback=self._on_rate_limited,
            rate_limit_wait=self._wait_for_rate_limit,
        ) as client:
            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(self.config.concurrency)

            # Create tasks
            tasks = [
                self._process_query_with_semaphore(client, semaphore, query, idx)
                for idx, query in enumerate(query_strings)
            ]

            # Execute tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = [r for r in results if isinstance(r, QueryResult)]

        # Add checkpoint results if resuming
        if self.checkpoint:
            checkpoint_results = self.checkpoint.get_results()
            valid_results = checkpoint_results + valid_results

        logger.info(f"Processing complete: {len(valid_results)} results")

        self.is_running = False

        return valid_results

    async def _process_query_with_semaphore(
        self, client: WBAPIClient, semaphore: asyncio.Semaphore, query: str, index: int
    ) -> QueryResult:
        """Process single query with semaphore control."""
        async with semaphore:
            # Wait if globally rate-limited
            await self._rate_limit_event.wait()

            # Stagger requests to avoid thundering herd after rate limit backoff
            if self._consecutive_rate_limits > 0:
                stagger_delay = random.uniform(0.1, 0.5) * (index % self.config.concurrency)
                await asyncio.sleep(stagger_delay)

            # Check for stop signal
            if self._stop_event.is_set():
                logger.info("Stop signal received")
                result = QueryResult(
                    query=query, status=QueryStatus.FAILED, error_message="Stopped by user"
                )
                return result

            # Check for pause signal
            while self.is_paused and not self._stop_event.is_set():
                await asyncio.sleep(0.5)

            if self._stop_event.is_set():
                result = QueryResult(
                    query=query, status=QueryStatus.FAILED, error_message="Stopped by user"
                )
                return result

            self.stats["in_progress"] += 1
            self._notify_progress()

            try:
                result = await self._process_single_query(client, query)

                # Update stats
                self.stats["completed"] += 1
                self.stats["in_progress"] -= 1

                if result.status == QueryStatus.SUCCESS:
                    self.stats["success"] += 1
                    # Reset consecutive rate limits on success
                    self._consecutive_rate_limits = 0
                elif result.status == QueryStatus.CACHED:
                    self.stats["cached"] += 1
                    # Reset consecutive rate limits on cached (successful) result
                    self._consecutive_rate_limits = 0
                else:
                    self.stats["failed"] += 1

                # Save to checkpoint periodically
                if self.checkpoint:
                    self.checkpoint.mark_completed(query, result)

                    if self.stats["completed"] % self.config.checkpoint_interval == 0:
                        self.checkpoint.save()
                        logger.info(f"Checkpoint saved at {self.stats['completed']} queries")

                self._notify_progress(result)

                return result

            except Exception as e:
                logger.error(f"Error processing query '{query}': {e}")
                self.stats["completed"] += 1
                self.stats["in_progress"] -= 1
                self.stats["failed"] += 1

                result = QueryResult(
                    query=query,
                    status=QueryStatus.FAILED,
                    error_message=f"Processing error: {str(e)}",
                )

                self._notify_progress(result)

                return result

    async def _process_single_query(self, client: WBAPIClient, query: str) -> QueryResult:
        """Process a single query with caching."""
        # Check cache first (unless force refresh)
        if self.cache and not self.config.force_refresh:
            cached_result = self.cache.get(query)
            if cached_result:
                logger.debug(f"Cache hit for query '{query}'")
                cached_result.status = QueryStatus.CACHED
                return cached_result

        # Fetch from API
        result = await client.fetch_total(query)

        # Save to cache
        if self.cache and result.status == QueryStatus.SUCCESS:
            self.cache.set(result)

        return result

    def pause(self) -> None:
        """Pause processing."""
        self.is_paused = True
        logger.info("Pipeline paused")

    def resume(self) -> None:
        """Resume processing."""
        self.is_paused = False
        logger.info("Pipeline resumed")

    def stop(self) -> None:
        """Stop processing."""
        self._stop_event.set()
        self.is_paused = False
        logger.info("Pipeline stop signal sent")

    def get_stats(self) -> dict:
        """Get current statistics."""
        return self.stats.copy()
