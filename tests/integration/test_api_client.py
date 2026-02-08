"""Integration tests for API client with Playwright."""

import asyncio
from unittest.mock import AsyncMock, patch

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
            # Mock the context.request.get method
            mock_response = AsyncMock()
            mock_response.status = 200
            # URL should match the one built by _build_url()
            mock_response.url = client._build_url("test")
            mock_response.text = AsyncMock(return_value='{"total": 12345}')
            mock_response.headers = {}

            with patch.object(client.context.request, "get", return_value=mock_response):
                result = await client.fetch_total("test")

                assert result.query == "test"
                assert result.total == 12345
                assert result.status == QueryStatus.SUCCESS

    async def test_fetch_total_no_total_field(self):
        """Test response without total field."""
        async with WBAPIClient() as client:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.url = client._build_url("test")
            mock_response.text = AsyncMock(return_value='{"data": []}')
            mock_response.headers = {}

            with patch.object(client.context.request, "get", return_value=mock_response):
                result = await client.fetch_total("test")

                assert result.status == QueryStatus.FAILED
                assert "No 'total' field" in result.error_message

    async def test_fetch_total_invalid_json(self):
        """Test response with invalid JSON."""
        async with WBAPIClient() as client:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.url = client._build_url("test")
            mock_response.text = AsyncMock(return_value="not json")
            mock_response.headers = {}

            with patch.object(client.context.request, "get", return_value=mock_response):
                result = await client.fetch_total("test")

                assert result.status == QueryStatus.FAILED
                assert "Invalid JSON" in result.error_message

    async def test_fetch_total_empty_response(self):
        """Test empty response."""
        async with WBAPIClient() as client:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.url = client._build_url("test")
            mock_response.text = AsyncMock(return_value="")
            mock_response.headers = {}

            with patch.object(client.context.request, "get", return_value=mock_response):
                result = await client.fetch_total("test")

                assert result.status == QueryStatus.FAILED
                assert "Empty response" in result.error_message

    async def test_fetch_total_redirected(self):
        """Test redirected request."""
        async with WBAPIClient() as client:
            mock_response = AsyncMock()
            mock_response.status = 200
            # Different URL indicates redirect
            mock_response.url = "https://www.wildberries.ru/different-page"
            mock_response.headers = {}

            with patch.object(client.context.request, "get", return_value=mock_response):
                result = await client.fetch_total("test")

                assert result.status == QueryStatus.FAILED
                assert "redirected" in result.error_message.lower()

    async def test_fetch_total_http_error(self):
        """Test HTTP error response."""
        async with WBAPIClient() as client:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_response.url = client._build_url("test")
            mock_response.headers = {}

            with patch.object(client.context.request, "get", return_value=mock_response):
                result = await client.fetch_total("test")

                assert result.status == QueryStatus.FAILED
                assert "404" in result.error_message

    async def test_fetch_total_rate_limited_no_retry(self):
        """Test rate limiting without retries."""
        retry_strategy = RetryStrategy(max_retries=0)

        async with WBAPIClient(retry_strategy=retry_strategy) as client:
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_response.url = client._build_url("test")
            mock_response.headers = {}

            with patch.object(client.context.request, "get", return_value=mock_response):
                result = await client.fetch_total("test")

                assert result.status == QueryStatus.FAILED
                assert "429" in result.error_message

    async def test_fetch_total_498_retries(self):
        """Test HTTP 498 triggers retry logic."""
        retry_strategy = RetryStrategy(max_retries=0)

        async with WBAPIClient(retry_strategy=retry_strategy) as client:
            mock_response = AsyncMock()
            mock_response.status = 498
            mock_response.url = client._build_url("test")
            mock_response.headers = {}

            with patch.object(client.context.request, "get", return_value=mock_response):
                result = await client.fetch_total("test")

                assert result.status == QueryStatus.FAILED
                assert "498" in result.error_message

    async def test_fetch_total_timeout(self):
        """Test timeout handling."""
        retry_strategy = RetryStrategy(max_retries=1)
        async with WBAPIClient(timeout=0.001, retry_strategy=retry_strategy) as client:
            # Mock to raise timeout
            with patch.object(client.context.request, "get", side_effect=asyncio.TimeoutError()):
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
            mock_response_498.url = client._build_url("test")
            mock_response_498.headers = {}

            mock_response_200 = AsyncMock()
            mock_response_200.status = 200
            mock_response_200.url = client._build_url("test")
            mock_response_200.text = AsyncMock(return_value='{"total": 100}')
            mock_response_200.headers = {}

            with patch.object(
                client.context.request, "get", side_effect=[mock_response_498, mock_response_200]
            ):
                result = await client.fetch_total("test")

                # Verify rate_limit_wait was called
                assert rate_limit_wait_called, "rate_limit_wait should be called after rate limit"
                assert result.status == QueryStatus.SUCCESS
                assert result.total == 100

    async def test_context_headers_set_correctly(self):
        """Test that browser-like headers are set at context initialization."""
        client = WBAPIClient()

        # Mock playwright, browser, and new_context
        mock_playwright = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()

        with patch("src.api.client.async_playwright") as mock_async_pw:
            mock_pw_manager = AsyncMock()
            mock_pw_manager.start = AsyncMock(return_value=mock_playwright)
            mock_async_pw.return_value = mock_pw_manager

            mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)

            # Enter and exit context to ensure proper cleanup
            await client.__aenter__()
            try:
                # Verify new_context was called with browser headers
                mock_browser.new_context.assert_called_once()
                call_kwargs = mock_browser.new_context.call_args.kwargs

                assert "extra_http_headers" in call_kwargs
                headers = call_kwargs["extra_http_headers"]

                # Verify critical browser-like headers are present
                expected_headers = {
                    "Referer": "https://www.wildberries.ru/",
                    "Origin": "https://www.wildberries.ru",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                    "X-Requested-With": "XMLHttpRequest",
                }
                for key, value in expected_headers.items():
                    assert key in headers, f"Missing header: {key}"
                    assert headers[key] == value, f"Wrong value for {key}"

                # Verify user agent is set
                assert "user_agent" in call_kwargs
                assert "Chrome" in call_kwargs["user_agent"]
            finally:
                await client.__aexit__(None, None, None)

    async def test_fetch_total_sends_browser_headers(self):
        """Test that fetch_total sends proper browser-like headers via context."""
        async with WBAPIClient() as client:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.url = client._build_url("test")
            mock_response.text = AsyncMock(return_value='{"total": 100}')
            mock_response.headers = {}

            # Playwright's context.request automatically includes headers set in new_context
            # So we just need to verify the request was made
            with patch.object(
                client.context.request, "get", return_value=mock_response
            ) as mock_get:
                await client.fetch_total("test")

                # Verify get was called
                mock_get.assert_called_once()
                # Note: Headers are set at context level in __aenter__, not per-request
