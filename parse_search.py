#!/usr/bin/env python3
"""
Standalone CLI script for parsing Wildberries search API.

This script fetches product totals from the Wildberries search API for a given query
and logs every action to log files.

Usage:
    python parse_search.py [--query "search term"]

Example:
    python parse_search.py --query "тест"
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from src.api.client import WBAPIClient
from src.models.query import QueryResult, QueryStatus


def setup_logging(log_dir: Path = Path("logs")) -> tuple[logging.Logger, logging.Logger]:
    """
    Set up logging configuration with two separate log files and console output.

    Args:
        log_dir: Directory to store log files (default: logs/)

    Returns:
        Tuple of (action_logger, result_logger)
    """
    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    # Define log file paths
    action_log_path = log_dir / "parse_search.log"
    result_log_path = log_dir / "parse_search_result.log"

    # Create action logger (logs every action)
    action_logger = logging.getLogger("parse_search_actions")
    action_logger.setLevel(logging.DEBUG)

    # Clear existing handlers to avoid duplicates
    action_logger.handlers.clear()

    # File handler for action logs
    action_file_handler = logging.FileHandler(action_log_path, mode="w", encoding="utf-8")
    action_file_handler.setLevel(logging.DEBUG)
    action_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    action_file_handler.setFormatter(action_formatter)
    action_logger.addHandler(action_file_handler)

    # Console handler for action logs
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    action_logger.addHandler(console_handler)

    # Create result logger (logs parsing results)
    result_logger = logging.getLogger("parse_search_results")
    result_logger.setLevel(logging.INFO)

    # Clear existing handlers
    result_logger.handlers.clear()

    # File handler for result logs
    result_file_handler = logging.FileHandler(result_log_path, mode="w", encoding="utf-8")
    result_file_handler.setLevel(logging.INFO)
    result_formatter = logging.Formatter(
        "%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    result_file_handler.setFormatter(result_formatter)
    result_logger.addHandler(result_file_handler)

    # Prevent propagation to root logger
    action_logger.propagate = False
    result_logger.propagate = False

    return action_logger, result_logger


async def run_parse(
    query: str, action_logger: logging.Logger, result_logger: logging.Logger
) -> QueryResult:
    """
    Run the WB API parsing for the given query.

    Args:
        query: Search query string
        action_logger: Logger for action logs
        result_logger: Logger for result logs

    Returns:
        QueryResult with parsing results
    """
    action_logger.info("Starting WB search parser")
    start_time = datetime.now()
    action_logger.info(f"Query to parse: '{query}'")

    # Initialize API client
    action_logger.info("Initializing WB API client")
    action_logger.debug("Creating WBAPIClient with default settings")

    try:
        async with WBAPIClient() as client:
            action_logger.debug("API client initialized successfully")
            action_logger.info("Building request URL")

            # For logging purposes only: show the URL that will be requested
            # Note: Using _build_url (private method) here for logging transparency.
            # This is acceptable because we're only reading/displaying, not modifying behavior.
            # The actual request is handled by client.fetch_total() below.
            url = client._build_url(query)
            action_logger.info(f"Request URL: {url}")

            action_logger.info("Sending request to WB API")
            action_logger.debug(f"Request parameters: query='{query}'")

            # Fetch data from API
            result = await client.fetch_total(query)

            # Log the result
            action_logger.info("Received response from WB API")
            action_logger.info(f"Query status: {result.status.value}")

            if result.status == QueryStatus.SUCCESS:
                action_logger.info(f"Query successful: total={result.total}")
                action_logger.debug(
                    f"Fetch details: retry_count={result.retry_count}, "
                    f"fetched_at={result.fetched_at}"
                )
            else:
                action_logger.warning(f"Query failed: {result.error_message}")
                action_logger.debug(f"Failure details: retry_count={result.retry_count}")

            # Write detailed result to result log
            result_logger.info("=" * 80)
            result_logger.info("WILDBERRIES SEARCH API PARSING RESULT")
            result_logger.info("=" * 80)
            result_logger.info(f"Query: {result.query}")
            result_logger.info(f"Status: {result.status.value}")
            result_logger.info(f"Total: {result.total if result.total is not None else 'N/A'}")
            result_logger.info(
                f"Fetched At: {result.fetched_at.isoformat() if result.fetched_at else 'N/A'}"
            )
            result_logger.info(f"Retry Count: {result.retry_count}")
            result_logger.info(
                f"Error Message: {result.error_message if result.error_message else 'None'}"
            )
            result_logger.info("-" * 80)
            result_logger.info("Raw Response (first 500 chars):")
            result_logger.info(
                result.raw_response[:500] if result.raw_response else "No raw response"
            )
            result_logger.info("=" * 80)

            action_logger.info("Parsing complete")
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            action_logger.debug(
                f"Execution completed at {end_time.isoformat()} "
                f"(duration: {duration:.2f} seconds)"
            )

            return result

    except Exception as e:
        action_logger.error(f"Unexpected error during parsing: {e}", exc_info=True)
        result_logger.error(f"PARSING FAILED WITH ERROR: {e}")
        raise


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Parse Wildberries search API and log every action",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python parse_search.py
  python parse_search.py --query "ноутбук"
  python parse_search.py --query "тест"
        """,
    )

    parser.add_argument(
        "--query",
        type=str,
        default="тест",
        help='Search query to parse (default: "тест")',
    )

    return parser.parse_args()


def main() -> int:
    """
    Main entry point for the script.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Parse arguments
    args = parse_args()

    # Set up logging
    action_logger, result_logger = setup_logging()

    try:
        # Run the async parsing
        result = asyncio.run(run_parse(args.query, action_logger, result_logger))

        # Print summary to console
        print("\n" + "=" * 80)
        print("PARSING SUMMARY")
        print("=" * 80)
        print(f"Query: {result.query}")
        print(f"Status: {result.status.value}")
        if result.status == QueryStatus.SUCCESS:
            print(f"Total products found: {result.total}")
        else:
            print(f"Error: {result.error_message}")
        print("-" * 80)
        print("Action logs saved to: logs/parse_search.log")
        print("Result logs saved to: logs/parse_search_result.log")
        print("=" * 80)

        return 0 if result.status == QueryStatus.SUCCESS else 1

    except KeyboardInterrupt:
        action_logger.warning("Script interrupted by user")
        print("\nScript interrupted by user")
        return 130

    except Exception as e:
        action_logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\nFatal error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
