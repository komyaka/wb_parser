"""Wildberries API client with async support and retry logic."""

import asyncio
import json
import logging
import random
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime
from urllib.parse import urlencode

import aiohttp

from ..models.query import QueryResult, QueryStatus
from .retry import RetryStrategy

logger = logging.getLogger(__name__)


class WBAPIClient:
    """Async client for Wildberries exactmatch API."""

    # API endpoint template
    API_ENDPOINT = "https://www.wildberries.ru/__internal/search/exactmatch/ru/common/v18/search"

    def __init__(
        self,
        timeout: float = 20.0,
        min_delay: float = 0.5,
        max_delay: float = 1.5,
        retry_strategy: RetryStrategy | None = None,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        rate_limit_callback: Callable[[], Awaitable[None]] | None = None,
        rate_limit_wait: Callable[[], Awaitable[None]] | None = None,
    ):
        """
        Initialize WB API client.

        Args:
            timeout: Request timeout in seconds
            min_delay: Minimum delay between requests (seconds)
            max_delay: Maximum delay between requests (seconds)
            retry_strategy: Retry strategy instance
            user_agent: User-Agent header
            rate_limit_callback: Async callback to invoke when rate limited (498/429)
            rate_limit_wait: Async callback to wait for global rate limit to be lifted
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.retry_strategy = retry_strategy or RetryStrategy()
        self.user_agent = user_agent
        self.rate_limit_callback = rate_limit_callback
        self.rate_limit_wait = rate_limit_wait
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    def _build_url(self, query: str) -> str:
        """
        Build API URL with query parameters.

        Args:
            query: Search query string

        Returns:
            Full API URL
        """
        params = {
            "ab_testing": "false",
            "appType": "1",
            "curr": "rub",
            "dest": "-1586361",
            "hide_dtype": "11",
            "inheritFilters": "false",
            "lang": "ru",
            "page": "1",
            "query": query,
            "resultset": "catalog",
            "sort": "popular",
            "spp": "30",
            "suppressSpellcheck": "false",
            "uclusters": "2",
        }

        return f"{self.API_ENDPOINT}?{urlencode(params)}"

    async def _random_delay(self) -> None:
        """Wait for random delay between min_delay and max_delay."""
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)

    def _parse_retry_after(self, headers: Mapping[str, str]) -> float | None:
        """
        Parse Retry-After header.

        Args:
            headers: Response headers

        Returns:
            Retry delay in seconds, or None
        """
        retry_after = headers.get("Retry-After")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass
        return None

    async def fetch_total(self, query: str) -> QueryResult:
        """
        Fetch 'total' field from WB API for a query.

        Args:
            query: Search query string

        Returns:
            QueryResult with total field or error
        """
        if not self.session:
            raise RuntimeError("Client session not initialized. Use async context manager.")

        url = self._build_url(query)
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.wildberries.ru/",
            "Origin": "https://www.wildberries.ru",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="131", "Chromium";v="131"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Connection": "keep-alive",
            "X-Requested-With": "XMLHttpRequest",
        }

        result = QueryResult(query=query)
        attempt = 0

        # Add random delay before request
        await self._random_delay()

        while attempt <= self.retry_strategy.max_retries:
            try:
                logger.debug(f"Fetching query '{query}' (attempt {attempt + 1})")

                async with self.session.get(url, headers=headers) as response:
                    # Debug logging for troubleshooting bot detection issues
                    logger.debug(f"Request to URL: {url}")
                    logger.debug(
                        f"Response status: {response.status}, "
                        f"headers: {dict(response.headers)}"
                    )
                    # Check for redirects (usually means blocked or invalid)
                    if response.history:
                        result.status = QueryStatus.FAILED
                        result.error_message = "Request was redirected"
                        logger.warning(f"Query '{query}' was redirected")
                        return result

                    # Check status code
                    if response.status in (429, 498):
                        # Rate limited - trigger global backoff if callback provided
                        logger.warning(f"Rate limited (HTTP {response.status}) for query '{query}'")

                        if self.rate_limit_callback:
                            await self.rate_limit_callback()

                        if self.retry_strategy.should_retry(attempt):
                            retry_after = self._parse_retry_after(response.headers)
                            await self.retry_strategy.wait(attempt, retry_after)
                            # Wait for global rate limit to be lifted before retrying
                            if self.rate_limit_wait:
                                await self.rate_limit_wait()
                            attempt += 1
                            continue
                        else:
                            result.status = QueryStatus.FAILED
                            result.error_message = f"Rate limited ({response.status})"
                            result.retry_count = attempt
                            return result

                    elif response.status >= 500:
                        # Server error
                        logger.warning(f"Server error {response.status} for query '{query}'")

                        if self.retry_strategy.should_retry(attempt):
                            await self.retry_strategy.wait(attempt)
                            attempt += 1
                            continue
                        else:
                            result.status = QueryStatus.FAILED
                            result.error_message = f"Server error ({response.status})"
                            result.retry_count = attempt
                            return result

                    elif response.status != 200:
                        # Other error
                        result.status = QueryStatus.FAILED
                        result.error_message = f"HTTP {response.status}"
                        logger.warning(f"HTTP {response.status} for query '{query}'")
                        return result

                    # Parse JSON response
                    try:
                        text = await response.text()

                        if not text or text.strip() == "":
                            result.status = QueryStatus.FAILED
                            result.error_message = "Empty response"
                            return result

                        data = json.loads(text)

                        # Extract 'total' field
                        if "total" in data:
                            result.total = int(data["total"])
                            result.status = QueryStatus.SUCCESS
                            result.fetched_at = datetime.now()
                            result.retry_count = attempt
                            logger.info(
                                f"Successfully fetched query '{query}': total={result.total}"
                            )
                        else:
                            result.status = QueryStatus.FAILED
                            result.error_message = "No 'total' field in response"
                            logger.warning(f"No 'total' field for query '{query}'")

                        # Optionally store raw response
                        result.raw_response = text[:500]  # Limit size

                        return result

                    except json.JSONDecodeError as e:
                        result.status = QueryStatus.FAILED
                        result.error_message = f"Invalid JSON: {str(e)}"
                        logger.error(f"JSON decode error for query '{query}': {e}")
                        return result

            except asyncio.TimeoutError:
                logger.warning(f"Timeout for query '{query}' (attempt {attempt + 1})")

                if self.retry_strategy.should_retry(attempt):
                    await self.retry_strategy.wait(attempt)
                    attempt += 1
                    continue
                else:
                    result.status = QueryStatus.FAILED
                    result.error_message = "Timeout"
                    result.retry_count = attempt
                    return result

            except aiohttp.ClientError as e:
                logger.error(f"Client error for query '{query}': {e}")

                if self.retry_strategy.should_retry(attempt):
                    await self.retry_strategy.wait(attempt)
                    attempt += 1
                    continue
                else:
                    result.status = QueryStatus.FAILED
                    result.error_message = f"Client error: {str(e)}"
                    result.retry_count = attempt
                    return result

            except Exception as e:
                logger.error(f"Unexpected error for query '{query}': {e}")
                result.status = QueryStatus.FAILED
                result.error_message = f"Unexpected error: {str(e)}"
                result.retry_count = attempt
                return result

        # Should not reach here
        result.status = QueryStatus.FAILED
        result.error_message = "Max retries exceeded"
        return result
