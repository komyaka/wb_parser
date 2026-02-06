"""Wildberries API client with async support and retry logic."""

import asyncio
import json
import logging
import random
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
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    ):
        """
        Initialize WB API client.

        Args:
            timeout: Request timeout in seconds
            min_delay: Minimum delay between requests (seconds)
            max_delay: Maximum delay between requests (seconds)
            retry_strategy: Retry strategy instance
            user_agent: User-Agent header
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.retry_strategy = retry_strategy or RetryStrategy()
        self.user_agent = user_agent
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
            "appType": "1",
            "curr": "rub",
            "dest": "-1257786",
            "query": query,
            "resultset": "catalog",
            "sort": "popular",
            "spp": "30",
            "suppressSpellcheck": "false",
        }

        return f"{self.API_ENDPOINT}?{urlencode(params)}"

    async def _random_delay(self) -> None:
        """Wait for random delay between min_delay and max_delay."""
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)

    def _parse_retry_after(self, headers: dict[str, str]) -> float | None:
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
            "Accept": "application/json",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        }

        result = QueryResult(query=query)
        attempt = 0

        # Add random delay before request
        await self._random_delay()

        while attempt <= self.retry_strategy.max_retries:
            try:
                logger.debug(f"Fetching query '{query}' (attempt {attempt + 1})")

                async with self.session.get(url, headers=headers) as response:
                    # Check for redirects (usually means blocked or invalid)
                    if response.history:
                        result.status = QueryStatus.FAILED
                        result.error_message = "Request was redirected"
                        logger.warning(f"Query '{query}' was redirected")
                        return result

                    # Check status code
                    if response.status == 429:
                        # Rate limited
                        logger.warning(f"Rate limited for query '{query}'")

                        if self.retry_strategy.should_retry(attempt):
                            retry_after = self._parse_retry_after(response.headers)
                            await self.retry_strategy.wait(attempt, retry_after)
                            attempt += 1
                            continue
                        else:
                            result.status = QueryStatus.FAILED
                            result.error_message = "Rate limited (429)"
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
