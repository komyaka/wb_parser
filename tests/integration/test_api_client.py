"""Integration tests for API client."""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from aiohttp import ClientSession, ClientResponse

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
        assert "query=тест+запрос" in url or "query=%D1%82%D0%B5%D1%81%D1%82" in url
        assert "appType=1" in url

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
