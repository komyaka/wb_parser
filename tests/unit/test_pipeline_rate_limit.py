"""Unit tests for pipeline rate limit handling."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.pipeline import ParserPipeline
from src.models.config import ParserConfig


@pytest.mark.asyncio
class TestPipelineRateLimit:
    """Unit tests for rate limit handling in pipeline."""

    async def test_thundering_herd_stagger(self):
        """Test that after rate limit backoff, tasks have staggered delays."""
        config = ParserConfig(concurrency=5)
        pipeline = ParserPipeline(config)

        # Simulate a rate limit condition
        pipeline._consecutive_rate_limits = 2

        # Mock client and semaphore
        mock_client = AsyncMock()
        mock_client.fetch_total = AsyncMock(return_value=MagicMock(status="SUCCESS", query="test"))

        semaphore = asyncio.Semaphore(config.concurrency)

        # Track sleep calls
        sleep_calls = []
        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            sleep_calls.append(delay)
            # Speed up test by not actually sleeping
            await original_sleep(0.001)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            # Process multiple queries with different indices
            tasks = []
            for idx in range(5):
                task = pipeline._process_query_with_semaphore(
                    mock_client, semaphore, f"query_{idx}", idx
                )
                tasks.append(task)

            await asyncio.gather(*tasks, return_exceptions=True)

        # Verify that stagger delays were applied
        # We should see stagger delays based on index % concurrency
        stagger_delays = [
            delay for delay in sleep_calls if 0.0 < delay <= 0.5 * (config.concurrency - 1)
        ]

        # At least some tasks should have had stagger delays
        assert len(stagger_delays) > 0, "Expected stagger delays when consecutive_rate_limits > 0"

        # Verify delays follow expected pattern (index % concurrency) * random(0.1, 0.5)
        # Index 0: 0 * random(0.1, 0.5) = 0
        # Index 1: 1 * random(0.1, 0.5) = 0.1-0.5
        # Index 2: 2 * random(0.1, 0.5) = 0.2-1.0
        # etc.

    async def test_no_stagger_when_no_rate_limits(self):
        """Test that no stagger delay is applied when consecutive_rate_limits is 0."""
        config = ParserConfig(concurrency=5)
        pipeline = ParserPipeline(config)

        # No rate limit condition (consecutive_rate_limits = 0)
        pipeline._consecutive_rate_limits = 0

        # Mock client and semaphore
        mock_client = AsyncMock()
        mock_client.fetch_total = AsyncMock(return_value=MagicMock(status="SUCCESS", query="test"))

        semaphore = asyncio.Semaphore(config.concurrency)

        # Track sleep calls
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)
            await asyncio.sleep(0.001)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            # Process a single query
            await pipeline._process_query_with_semaphore(mock_client, semaphore, "test_query", 1)

        # When consecutive_rate_limits is 0, the stagger logic should not trigger
        # The stagger delay would be in range [0.0, 2.5] for index 1 with concurrency 5
        # Since consecutive_rate_limits is 0, there should be no sleep calls from stagger
        # (any sleep calls would be from other parts of the code, not the stagger logic)

        # Verify: if there are any sleep calls, they should NOT be stagger delays
        # Stagger delays for index 1 would be: random(0.1, 0.5) * 1 = 0.1-0.5
        # Since consecutive_rate_limits is 0, no such delays should appear
        stagger_range_delays = [d for d in sleep_calls if 0.1 <= d <= 0.5]
        assert (
            len(stagger_range_delays) == 0
        ), "No stagger delays should occur when consecutive_rate_limits is 0"

    async def test_rate_limit_wait_passed_to_client(self):
        """Test that the pipeline passes rate_limit_wait to the WBAPIClient."""
        config = ParserConfig()
        pipeline = ParserPipeline(config)

        queries = [("test_query", 1)]

        # Mock WBAPIClient to capture constructor arguments
        captured_kwargs = {}

        class MockWBAPIClient:
            def __init__(self, **kwargs):
                captured_kwargs.update(kwargs)
                self.session = None

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

            async def fetch_total(self, query):
                return MagicMock(status="SUCCESS", query=query)

        with patch("src.core.pipeline.WBAPIClient", MockWBAPIClient):
            await pipeline.process_queries(queries)

        # Verify rate_limit_wait was passed
        assert "rate_limit_wait" in captured_kwargs, "rate_limit_wait should be passed to client"
        assert captured_kwargs["rate_limit_wait"] is not None, "rate_limit_wait should not be None"

        # Verify it's the correct method
        assert (
            captured_kwargs["rate_limit_wait"].__name__ == "_wait_for_rate_limit"
        ), "Should pass _wait_for_rate_limit method"

    async def test_wait_for_rate_limit_method(self):
        """Test that _wait_for_rate_limit waits for the event."""
        config = ParserConfig()
        pipeline = ParserPipeline(config)

        # Clear the rate limit event to simulate rate limiting
        pipeline._rate_limit_event.clear()

        # Create a task to wait for rate limit
        wait_task = asyncio.create_task(pipeline._wait_for_rate_limit())

        # Give it a moment to start waiting
        await asyncio.sleep(0.01)

        # Task should not be done yet
        assert not wait_task.done(), "Task should be waiting for event"

        # Set the event to release the wait
        pipeline._rate_limit_event.set()

        # Now the task should complete
        await asyncio.wait_for(wait_task, timeout=0.5)
        assert wait_task.done(), "Task should complete after event is set"
