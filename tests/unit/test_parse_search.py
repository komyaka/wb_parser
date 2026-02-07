"""Unit tests for parse_search.py script."""

import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from parse_search import parse_args, run_parse, setup_logging
from src.models.query import QueryResult, QueryStatus


class TestSetupLogging:
    """Test logging setup functionality."""

    def test_setup_logging_creates_loggers(self, tmp_path):
        """Test that setup_logging creates and configures loggers."""
        log_dir = tmp_path / "test_logs"

        action_logger, result_logger = setup_logging(log_dir)

        # Check loggers exist and have correct names
        assert action_logger.name == "parse_search_actions"
        assert result_logger.name == "parse_search_results"

        # Check log levels
        assert action_logger.level == logging.DEBUG
        assert result_logger.level == logging.INFO

        # Check log directory was created
        assert log_dir.exists()

        # Check log files exist
        assert (log_dir / "parse_search.log").exists()
        assert (log_dir / "parse_search_result.log").exists()

    def test_setup_logging_handlers(self, tmp_path):
        """Test that loggers have correct handlers."""
        log_dir = tmp_path / "test_logs"

        action_logger, result_logger = setup_logging(log_dir)

        # Action logger should have 2 handlers (file + console)
        assert len(action_logger.handlers) == 2

        # Result logger should have 1 handler (file only)
        assert len(result_logger.handlers) == 1

        # Check that handlers are of correct type
        handler_types = [type(h).__name__ for h in action_logger.handlers]
        assert "FileHandler" in handler_types
        assert "StreamHandler" in handler_types

    def test_setup_logging_no_propagation(self, tmp_path):
        """Test that loggers don't propagate to root logger."""
        log_dir = tmp_path / "test_logs"

        action_logger, result_logger = setup_logging(log_dir)

        assert action_logger.propagate is False
        assert result_logger.propagate is False

    def test_setup_logging_writes_to_files(self, tmp_path):
        """Test that loggers actually write to log files."""
        log_dir = tmp_path / "test_logs"

        action_logger, result_logger = setup_logging(log_dir)

        # Write test messages
        action_logger.info("Test action message")
        result_logger.info("Test result message")

        # Flush handlers
        for handler in action_logger.handlers:
            handler.flush()
        for handler in result_logger.handlers:
            handler.flush()

        # Check file contents
        action_log = (log_dir / "parse_search.log").read_text()
        result_log = (log_dir / "parse_search_result.log").read_text()

        assert "Test action message" in action_log
        assert "Test result message" in result_log


class TestRunParse:
    """Test the main parsing function."""

    @pytest.mark.asyncio
    async def test_run_parse_success(self, tmp_path):
        """Test successful parsing."""
        log_dir = tmp_path / "test_logs"
        action_logger, result_logger = setup_logging(log_dir)

        # Create mock result
        mock_result = QueryResult(
            query="test query",
            total=100,
            status=QueryStatus.SUCCESS,
            fetched_at=datetime(2024, 1, 1, 12, 0, 0),
            retry_count=0,
            raw_response='{"total": 100}',
        )

        # Mock WBAPIClient
        with patch("parse_search.WBAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client._build_url = MagicMock(
                return_value="https://www.wildberries.ru/api?query=test"
            )
            mock_client.fetch_total = AsyncMock(return_value=mock_result)
            mock_client_class.return_value = mock_client

            result = await run_parse("test query", action_logger, result_logger)

            # Verify result
            assert result.query == "test query"
            assert result.total == 100
            assert result.status == QueryStatus.SUCCESS

            # Verify client was called
            mock_client.fetch_total.assert_called_once_with("test query")

    @pytest.mark.asyncio
    async def test_run_parse_failure(self, tmp_path):
        """Test parsing with API failure."""
        log_dir = tmp_path / "test_logs"
        action_logger, result_logger = setup_logging(log_dir)

        # Create mock failed result
        mock_result = QueryResult(
            query="test query",
            total=None,
            status=QueryStatus.FAILED,
            error_message="HTTP 500",
            retry_count=3,
        )

        # Mock WBAPIClient
        with patch("parse_search.WBAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client._build_url = MagicMock(
                return_value="https://www.wildberries.ru/api?query=test"
            )
            mock_client.fetch_total = AsyncMock(return_value=mock_result)
            mock_client_class.return_value = mock_client

            result = await run_parse("test query", action_logger, result_logger)

            # Verify result
            assert result.query == "test query"
            assert result.total is None
            assert result.status == QueryStatus.FAILED
            assert result.error_message == "HTTP 500"

    @pytest.mark.asyncio
    async def test_run_parse_logs_actions(self, tmp_path):
        """Test that run_parse logs all actions."""
        log_dir = tmp_path / "test_logs"
        action_logger, result_logger = setup_logging(log_dir)

        mock_result = QueryResult(query="test", total=50, status=QueryStatus.SUCCESS, retry_count=0)

        with patch("parse_search.WBAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client._build_url = MagicMock(return_value="https://example.com")
            mock_client.fetch_total = AsyncMock(return_value=mock_result)
            mock_client_class.return_value = mock_client

            await run_parse("test", action_logger, result_logger)

            # Flush handlers
            for handler in action_logger.handlers:
                handler.flush()

            # Check that actions were logged
            action_log = (log_dir / "parse_search.log").read_text()

            assert "Starting WB search parser" in action_log
            assert "Query to parse: 'test'" in action_log
            assert "Initializing WB API client" in action_log
            assert "Building request URL" in action_log
            assert "Sending request to WB API" in action_log
            assert "Received response from WB API" in action_log
            assert "Parsing complete" in action_log

    @pytest.mark.asyncio
    async def test_run_parse_logs_results(self, tmp_path):
        """Test that run_parse logs results."""
        log_dir = tmp_path / "test_logs"
        action_logger, result_logger = setup_logging(log_dir)

        mock_result = QueryResult(
            query="laptop",
            total=500,
            status=QueryStatus.SUCCESS,
            fetched_at=datetime(2024, 1, 1, 12, 0, 0),
            retry_count=1,
            raw_response='{"total": 500, "products": [...]}',
        )

        with patch("parse_search.WBAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client._build_url = MagicMock(return_value="https://example.com")
            mock_client.fetch_total = AsyncMock(return_value=mock_result)
            mock_client_class.return_value = mock_client

            await run_parse("laptop", action_logger, result_logger)

            # Flush handlers
            for handler in result_logger.handlers:
                handler.flush()

            # Check result log
            result_log = (log_dir / "parse_search_result.log").read_text()

            assert "WILDBERRIES SEARCH API PARSING RESULT" in result_log
            assert "Query: laptop" in result_log
            assert "Status: success" in result_log
            assert "Total: 500" in result_log
            assert "Retry Count: 1" in result_log

    @pytest.mark.asyncio
    async def test_run_parse_uses_custom_retry_strategy(self, tmp_path):
        """Test that run_parse uses custom retry strategy with correct parameters."""
        log_dir = tmp_path / "test_logs"
        action_logger, result_logger = setup_logging(log_dir)

        mock_result = QueryResult(
            query="test query",
            total=100,
            status=QueryStatus.SUCCESS,
            retry_count=0,
        )

        # Mock WBAPIClient and capture the retry_strategy parameter
        with patch("parse_search.WBAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client._build_url = MagicMock(return_value="https://example.com")
            mock_client.fetch_total = AsyncMock(return_value=mock_result)
            mock_client_class.return_value = mock_client

            await run_parse("test query", action_logger, result_logger)

            # Verify WBAPIClient was called with custom retry strategy
            mock_client_class.assert_called_once()
            call_kwargs = mock_client_class.call_args.kwargs

            # Check that retry_strategy parameter was passed
            assert "retry_strategy" in call_kwargs

            # Verify retry_strategy has correct configuration
            retry_strategy = call_kwargs["retry_strategy"]
            assert retry_strategy.max_retries == 7
            assert retry_strategy.base_delay == 3.0


class TestParseArgs:
    """Test command-line argument parsing."""

    def test_parse_args_default(self):
        """Test parsing with default query."""
        with patch("sys.argv", ["parse_search.py"]):
            args = parse_args()
            assert args.query == "тест"

    def test_parse_args_custom_query(self):
        """Test parsing with custom query."""
        with patch("sys.argv", ["parse_search.py", "--query", "ноутбук"]):
            args = parse_args()
            assert args.query == "ноутбук"

    def test_parse_args_with_spaces(self):
        """Test parsing query with spaces."""
        with patch("sys.argv", ["parse_search.py", "--query", "test query"]):
            args = parse_args()
            assert args.query == "test query"
