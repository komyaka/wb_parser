"""Integration tests for API client with Playwright."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from src.api.client import WBAPIClient
from src.api.retry import RetryStrategy
from src.models.query import QueryStatus


@pytest_asyncio.fixture
async def mock_client():
    """Create a WBAPIClient with mocked Playwright."""
    with patch("src.api.client.async_playwright") as mock_pw:
        mock_playwright = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_pw_cm = AsyncMock()
        mock_pw_cm.start = AsyncMock(return_value=mock_playwright)
        mock_pw.return_value = mock_pw_cm

        mock_playwright.chromium.launch_persistent_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock()
        mock_context.close = AsyncMock()
        mock_page.close = AsyncMock()

        client = WBAPIClient()
        await client.__aenter__()
        yield client
        await client.__aexit__(None, None, None)


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

    async def test_fetch_total_success(self, mock_client):
        """Test successful fetch with total field."""
        client = mock_client
        url = client._build_url("test")

        # Mock page.evaluate to return successful response
        mock_client.page.evaluate = AsyncMock(
            return_value={"status": 200, "url": url, "text": '{"total": 12345}', "headers": {}}
        )

        result = await client.fetch_total("test")

        assert result.query == "test"
        assert result.total == 12345
        assert result.status == QueryStatus.SUCCESS

    async def test_fetch_total_no_total_field(self, mock_client):
        """Test response without total field."""
        client = mock_client
        url = client._build_url("test")

        mock_client.page.evaluate = AsyncMock(
            return_value={"status": 200, "url": url, "text": '{"data": []}', "headers": {}}
        )

        result = await client.fetch_total("test")

        assert result.status == QueryStatus.FAILED
        assert "No 'total' field" in result.error_message

    async def test_fetch_total_invalid_json(self, mock_client):
        """Test response with invalid JSON."""
        client = mock_client
        url = client._build_url("test")

        mock_client.page.evaluate = AsyncMock(
            return_value={"status": 200, "url": url, "text": "not json", "headers": {}}
        )

        result = await client.fetch_total("test")

        assert result.status == QueryStatus.FAILED
        assert "Invalid JSON" in result.error_message

    async def test_fetch_total_empty_response(self, mock_client):
        """Test empty response."""
        client = mock_client
        url = client._build_url("test")

        mock_client.page.evaluate = AsyncMock(
            return_value={"status": 200, "url": url, "text": "", "headers": {}}
        )

        result = await client.fetch_total("test")

        assert result.status == QueryStatus.FAILED
        assert "Empty response" in result.error_message

    async def test_fetch_total_redirected(self, mock_client):
        """Test redirected request."""
        client = mock_client

        mock_client.page.evaluate = AsyncMock(
            return_value={
                "status": 200,
                "url": "https://www.wildberries.ru/different-page",
                "text": '{"total": 100}',
                "headers": {},
            }
        )

        result = await client.fetch_total("test")

        assert result.status == QueryStatus.FAILED
        assert "redirected" in result.error_message.lower()

    async def test_fetch_total_http_error(self, mock_client):
        """Test HTTP error response."""
        client = mock_client
        url = client._build_url("test")

        mock_client.page.evaluate = AsyncMock(
            return_value={"status": 404, "url": url, "text": "", "headers": {}}
        )

        result = await client.fetch_total("test")

        assert result.status == QueryStatus.FAILED
        assert "404" in result.error_message

    async def test_fetch_total_rate_limited_no_retry(self, mock_client):
        """Test rate limiting without retries."""
        client = mock_client
        client.retry_strategy = RetryStrategy(max_retries=0)
        url = client._build_url("test")

        mock_client.page.evaluate = AsyncMock(
            return_value={"status": 429, "url": url, "text": "", "headers": {}}
        )

        result = await client.fetch_total("test")

        assert result.status == QueryStatus.FAILED
        assert "429" in result.error_message

    async def test_fetch_total_498_retries(self, mock_client):
        """Test HTTP 498 triggers retry logic."""
        client = mock_client
        client.retry_strategy = RetryStrategy(max_retries=0)
        url = client._build_url("test")

        mock_client.page.evaluate = AsyncMock(
            return_value={"status": 498, "url": url, "text": "", "headers": {}}
        )

        result = await client.fetch_total("test")

        assert result.status == QueryStatus.FAILED
        assert "498" in result.error_message

    async def test_fetch_total_timeout(self, mock_client):
        """Test timeout handling."""
        client = mock_client
        client.retry_strategy = RetryStrategy(max_retries=1)

        # Mock page.evaluate to raise TimeoutError
        mock_client.page.evaluate = AsyncMock(side_effect=asyncio.TimeoutError())

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

    async def test_fetch_total_rate_limited_waits_for_global(self, mock_client):
        """Test that when rate_limit_wait is provided, it is called during retry after rate limiting."""
        client = mock_client
        client.retry_strategy = RetryStrategy(max_retries=1, base_delay=0.01)

        # Track calls
        rate_limit_wait_called = False

        async def mock_rate_limit_wait():
            nonlocal rate_limit_wait_called
            rate_limit_wait_called = True

        client.rate_limit_wait = mock_rate_limit_wait

        url = client._build_url("test")

        # First response: rate limited (498)
        # Second response: success
        response_498 = {"status": 498, "url": url, "text": "", "headers": {}}

        response_200 = {"status": 200, "url": url, "text": '{"total": 100}', "headers": {}}

        mock_client.page.evaluate = AsyncMock(side_effect=[response_498, response_200])

        result = await client.fetch_total("test")

        # Verify rate_limit_wait was called
        assert rate_limit_wait_called, "rate_limit_wait should be called after rate limit"
        assert result.status == QueryStatus.SUCCESS
        assert result.total == 100

    async def test_context_headers_set_correctly(self):
        """Test that browser-like headers are set at context initialization."""
        client = WBAPIClient()

        # Mock playwright and launch_persistent_context
        mock_playwright = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        with patch("src.api.client.async_playwright") as mock_async_pw:
            mock_pw_manager = AsyncMock()
            mock_pw_manager.start = AsyncMock(return_value=mock_playwright)
            mock_async_pw.return_value = mock_pw_manager

            mock_playwright.chromium.launch_persistent_context = AsyncMock(
                return_value=mock_context
            )
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_page.goto = AsyncMock()
            mock_context.close = AsyncMock()
            mock_page.close = AsyncMock()

            # Enter and exit context to ensure proper cleanup
            await client.__aenter__()
            try:
                # Verify launch_persistent_context was called with browser headers
                mock_playwright.chromium.launch_persistent_context.assert_called_once()
                call_args = mock_playwright.chromium.launch_persistent_context.call_args

                # First positional arg should be profile_dir
                assert len(call_args.args) > 0

                call_kwargs = call_args.kwargs

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

    async def test_fetch_total_sends_browser_headers(self, mock_client):
        """Test that fetch_total uses in-page fetch (page.evaluate)."""
        client = mock_client
        url = client._build_url("test")

        mock_client.page.evaluate = AsyncMock(
            return_value={"status": 200, "url": url, "text": '{"total": 100}', "headers": {}}
        )

        await client.fetch_total("test")

        # Verify evaluate was called (in-page fetch)
        mock_client.page.evaluate.assert_called()
        # Verify it was called with JavaScript code and URL
        call_args = mock_client.page.evaluate.call_args
        assert len(call_args.args) == 2  # js_code and url
        assert "fetch" in call_args.args[0]  # JavaScript contains fetch call
        assert call_args.args[1] == url  # URL is passed as second parameter
