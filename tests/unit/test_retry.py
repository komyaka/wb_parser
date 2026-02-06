"""Unit tests for retry strategy."""

import pytest
from src.api.retry import RetryStrategy


class TestRetryStrategy:
    """Test retry strategy with exponential backoff."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        strategy = RetryStrategy()
        assert strategy.max_retries == 5
        assert strategy.base_delay == 1.0
        assert strategy.max_delay == 60.0
        assert strategy.exponential_base == 2.0

    def test_init_custom(self):
        """Test initialization with custom values."""
        strategy = RetryStrategy(
            max_retries=3, base_delay=2.0, max_delay=30.0, exponential_base=3.0
        )
        assert strategy.max_retries == 3
        assert strategy.base_delay == 2.0
        assert strategy.max_delay == 30.0
        assert strategy.exponential_base == 3.0

    def test_calculate_delay_first_attempt(self):
        """Test delay calculation for first retry."""
        strategy = RetryStrategy(base_delay=1.0, exponential_base=2.0)
        delay = strategy.calculate_delay(0)

        # First attempt: 1.0 * (2^0) = 1.0, with jitter ±0.25
        assert 0.75 <= delay <= 1.25

    def test_calculate_delay_exponential_growth(self):
        """Test exponential growth of delays."""
        strategy = RetryStrategy(base_delay=1.0, exponential_base=2.0, max_delay=100.0)

        delays = [strategy.calculate_delay(i) for i in range(5)]

        # Check that delays generally increase (accounting for jitter)
        # 0: ~1.0, 1: ~2.0, 2: ~4.0, 3: ~8.0, 4: ~16.0
        assert delays[1] > delays[0] * 0.75  # Allow for jitter
        assert delays[2] > delays[1] * 0.75
        assert delays[3] > delays[2] * 0.75

    def test_calculate_delay_max_cap(self):
        """Test that delay is capped at max_delay."""
        strategy = RetryStrategy(base_delay=1.0, exponential_base=2.0, max_delay=10.0)

        # Large attempt number should hit max_delay
        delay = strategy.calculate_delay(10)
        assert delay <= 10.0 * 1.25  # Max + jitter

    def test_calculate_delay_with_retry_after(self):
        """Test respecting Retry-After header."""
        strategy = RetryStrategy(base_delay=1.0, max_delay=60.0)

        delay = strategy.calculate_delay(0, retry_after=5.0)
        assert delay == 5.0

    def test_calculate_delay_retry_after_capped(self):
        """Test Retry-After is capped by max_delay."""
        strategy = RetryStrategy(base_delay=1.0, max_delay=10.0)

        delay = strategy.calculate_delay(0, retry_after=100.0)
        assert delay == 10.0

    def test_should_retry_within_limit(self):
        """Test should retry within max_retries."""
        strategy = RetryStrategy(max_retries=5)

        assert strategy.should_retry(0) is True
        assert strategy.should_retry(4) is True

    def test_should_retry_at_limit(self):
        """Test should not retry at max_retries."""
        strategy = RetryStrategy(max_retries=5)

        assert strategy.should_retry(5) is False
        assert strategy.should_retry(10) is False

    def test_should_retry_zero_retries(self):
        """Test with zero retries allowed."""
        strategy = RetryStrategy(max_retries=0)

        assert strategy.should_retry(0) is False
        assert strategy.should_retry(1) is False


class TestRetryJitter:
    """Test jitter in retry delays."""

    def test_jitter_randomness(self):
        """Test that jitter produces different values."""
        strategy = RetryStrategy(base_delay=10.0)

        delays = [strategy.calculate_delay(0) for _ in range(20)]

        # Should have some variation due to jitter
        assert len(set(delays)) > 1

        # All should be within expected range (10.0 ±2.5)
        for delay in delays:
            assert 7.5 <= delay <= 12.5

    def test_jitter_never_negative(self):
        """Test that jitter never produces negative delays."""
        strategy = RetryStrategy(base_delay=0.1)

        delays = [strategy.calculate_delay(0) for _ in range(100)]

        # All delays should be non-negative
        assert all(d >= 0 for d in delays)
