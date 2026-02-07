"""Integration tests for API client."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.api.client import WBAPIClient
from src.api.retry import RetryStrategy
from src.models.query import QueryStatus


@pytest.mark.asyncio
class TestWBAPIClient:
    """Integration tests for WB API client."""

    async def test_build_url(self):
        """Test URL building with query parameters."""
        client = WBAPIClient()
        url = client._build_url("тест запрос")

        assert "wildberries.ru" in url
        assert "__internal/search/exactmatch" in url
        assert "query=тест+запрос" in url or "query=%D1%82%D0%B5%D1%81%D1%82" in url
        assert "appType=1" in url
        assert "dest=-1586361" in url
        assert "ab_testing=false" in url
        assert "lang=ru" in url
        assert "page=1" in url
        assert "uclusters=2" in url

    async def test_fetch_total_success(self):
        """Test successful fetch with total field."""
        async with WBAPIClient() as client:
            # Mock the session.get method
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.history = []
            mock_response.text = AsyncMock(return_value='{"total": 12345}')
            mock_response.headers = {}
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            with patch.object(client.session, "get", return_value=mock_response):
                result = await client.fetch_total("test")

                assert result.query == "test"
                assert result.total == 12345
                assert result.status == QueryStatus.SUCCESS

    async def test_fetch_total_no_total_field(self):
        """Test response without total field."""
        async with WBAPIClient() as client:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.history = []
            mock_response.text = AsyncMock(return_value='{"data": []}')
            mock_response.headers = {}
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            with patch.object(client.session, "get", return_value=mock_response):
                result = await client.fetch_total("test")

                assert result.status == QueryStatus.FAILED
                assert "No 'total' field" in result.error_message

    async def test_fetch_total_invalid_json(self):
        """Test response with invalid JSON."""
        async with WBAPIClient() as client:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.history = []
            mock_response.text = AsyncMock(return_value="not json")
            mock_response.headers = {}
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            with patch.object(client.session, "get", return_value=mock_response):
                result = await client.fetch_total("test")

                assert result.status == QueryStatus.FAILED
                assert "Invalid JSON" in result.error_message

    async def test_fetch_total_empty_response(self):
        """Test empty response."""
        async with WBAPIClient() as client:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.history = []
            mock_response.text = AsyncMock(return_value="")
            mock_response.headers = {}
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            with patch.object(client.session, "get", return_value=mock_response):
                result = await client.fetch_total("test")

                assert result.status == QueryStatus.FAILED
                assert "Empty response" in result.error_message

    async def test_fetch_total_redirected(self):
        """Test redirected request."""
        async with WBAPIClient() as client:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.history = [Mock()]  # Non-empty history indicates redirect
            mock_response.headers = {}
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            with patch.object(client.session, "get", return_value=mock_response):
                result = await client.fetch_total("test")

                assert result.status == QueryStatus.FAILED
                assert "redirected" in result.error_message.lower()

    async def test_fetch_total_http_error(self):
        """Test HTTP error response."""
        async with WBAPIClient() as client:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_response.history = []
            mock_response.headers = {}
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            with patch.object(client.session, "get", return_value=mock_response):
                result = await client.fetch_total("test")

                assert result.status == QueryStatus.FAILED
                assert "404" in result.error_message

    async def test_fetch_total_rate_limited_no_retry(self):
        """Test rate limiting without retries."""
        retry_strategy = RetryStrategy(max_retries=0)

        async with WBAPIClient(retry_strategy=retry_strategy) as client:
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_response.history = []
            mock_response.headers = {}
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            with patch.object(client.session, "get", return_value=mock_response):
                result = await client.fetch_total("test")

                assert result.status == QueryStatus.FAILED
                assert "429" in result.error_message

    async def test_fetch_total_498_retries(self):
        """Test HTTP 498 triggers retry logic."""
        retry_strategy = RetryStrategy(max_retries=0)

        async with WBAPIClient(retry_strategy=retry_strategy) as client:
            mock_response = AsyncMock()
            mock_response.status = 498
            mock_response.history = []
            mock_response.headers = {}
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            with patch.object(client.session, "get", return_value=mock_response):
                result = await client.fetch_total("test")

                assert result.status == QueryStatus.FAILED
                assert "498" in result.error_message

    async def test_fetch_total_timeout(self):
        """Test timeout handling."""
        retry_strategy = RetryStrategy(max_retries=1)
        async with WBAPIClient(timeout=0.001, retry_strategy=retry_strategy) as client:
            # Create proper async context manager mock
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_cm.__aexit__ = AsyncMock(return_value=None)

            with patch.object(client.session, "get", return_value=mock_cm):
                result = await client.fetch_total("test")

                assert result.status == QueryStatus.FAILED
                assert "Timeout" in result.error_message or result.retry_count >= 1

    async def test_parse_retry_after_header(self):
        """Test parsing Retry-After header."""
        client = WBAPIClient()

        # Numeric value
        headers = {"Retry-After": "30"}
        delay = client._parse_retry_after(headers)
        assert delay == 30.0

        # No header
        headers = {}
        delay = client._parse_retry_after(headers)
        assert delay is None

        # Invalid value
        headers = {"Retry-After": "invalid"}
        delay = client._parse_retry_after(headers)
        assert delay is None

    async def test_random_delay(self):
        """Test random delay functionality."""
        client = WBAPIClient(min_delay=0.01, max_delay=0.02)

        start = asyncio.get_event_loop().time()
        await client._random_delay()
        elapsed = asyncio.get_event_loop().time() - start

        assert 0.01 <= elapsed <= 0.03  # Allow small margin

    async def test_fetch_total_rate_limited_waits_for_global(self):
        """Test that when rate_limit_wait is provided, it is called during retry after rate limiting."""
        retry_strategy = RetryStrategy(max_retries=1, base_delay=0.01)

        # Track calls
        rate_limit_wait_called = False

        async def mock_rate_limit_wait():
            nonlocal rate_limit_wait_called
            rate_limit_wait_called = True

        async with WBAPIClient(
            retry_strategy=retry_strategy, rate_limit_wait=mock_rate_limit_wait
        ) as client:
            # First response: rate limited (498)
            # Second response: success
            mock_response_498 = AsyncMock()
            mock_response_498.status = 498
            mock_response_498.history = []
            mock_response_498.headers = {}
            mock_response_498.__aenter__ = AsyncMock(return_value=mock_response_498)
            mock_response_498.__aexit__ = AsyncMock(return_value=None)

            mock_response_200 = AsyncMock()
            mock_response_200.status = 200
            mock_response_200.history = []
            mock_response_200.text = AsyncMock(return_value='{"total": 100}')
            mock_response_200.headers = {}
            mock_response_200.__aenter__ = AsyncMock(return_value=mock_response_200)
            mock_response_200.__aexit__ = AsyncMock(return_value=None)

            with patch.object(
                client.session, "get", side_effect=[mock_response_498, mock_response_200]
            ):
                result = await client.fetch_total("test")

                # Verify rate_limit_wait was called
                assert rate_limit_wait_called, "rate_limit_wait should be called after rate limit"
                assert result.status == QueryStatus.SUCCESS
                assert result.total == 100

    async def test_fetch_total_sends_browser_headers(self):
        """Test that fetch_total sends proper browser-like headers."""
        async with WBAPIClient() as client:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.history = []
            mock_response.text = AsyncMock(return_value='{"total": 100}')
            mock_response.headers = {}
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            captured_kwargs = {}

            def capture_get(*args, **kwargs):
                captured_kwargs.update(kwargs)
                return mock_response

            with patch.object(client.session, "get", side_effect=capture_get):
                await client.fetch_total("test")

            # Verify browser-like headers are sent
            sent_headers = captured_kwargs.get("headers", {})
            assert "Referer" in sent_headers, "Referer header should be present"
            assert "Origin" in sent_headers, "Origin header should be present"
            assert "Sec-Fetch-Dest" in sent_headers, "Sec-Fetch-Dest header should be present"
            assert "Sec-Fetch-Mode" in sent_headers, "Sec-Fetch-Mode header should be present"
            assert "Sec-Fetch-Site" in sent_headers, "Sec-Fetch-Site header should be present"
            assert sent_headers["Referer"] == "https://www.wildberries.ru/"
            assert sent_headers["Origin"] == "https://www.wildberries.ru"
