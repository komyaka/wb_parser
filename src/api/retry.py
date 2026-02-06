"""Retry strategy with exponential backoff and jitter."""

import asyncio
import logging
import random

logger = logging.getLogger(__name__)


class RetryStrategy:
    """Exponential backoff retry strategy with jitter."""

    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ):
        """
        Initialize retry strategy.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def calculate_delay(self, attempt: int, retry_after: float | None = None) -> float:
        """
        Calculate delay for retry attempt with exponential backoff and jitter.

        Args:
            attempt: Current retry attempt number (0-based)
            retry_after: Optional Retry-After header value in seconds

        Returns:
            Delay in seconds
        """
        # Respect Retry-After header if provided
        if retry_after is not None:
            delay = min(retry_after, self.max_delay)
            logger.debug(f"Using Retry-After: {delay}s")
            return delay

        # Exponential backoff: base_delay * (exponential_base ** attempt)
        delay = self.base_delay * (self.exponential_base**attempt)

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter (±25%)
        jitter_range = delay * 0.25
        jitter = random.uniform(-jitter_range, jitter_range)
        delay = max(0, delay + jitter)

        logger.debug(f"Calculated retry delay for attempt {attempt}: {delay:.2f}s")

        return delay

    async def wait(self, attempt: int, retry_after: float | None = None) -> None:
        """
        Wait for the calculated delay period.

        Args:
            attempt: Current retry attempt number
            retry_after: Optional Retry-After header value
        """
        delay = self.calculate_delay(attempt, retry_after)
        await asyncio.sleep(delay)

    def should_retry(self, attempt: int) -> bool:
        """
        Check if should retry based on attempt number.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            True if should retry
        """
        return attempt < self.max_retries
