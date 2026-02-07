# parse_search.py - Wildberries Search API Parser

## Overview

`parse_search.py` is a standalone CLI script that parses the Wildberries search API and logs every action performed.

## Features

- **Comprehensive logging**: Every action is logged with timestamps and log levels
- **Dual log files**:
  - `logs/parse_search.log` - All actions (DEBUG level)
  - `logs/parse_search_result.log` - Parsing results summary
- **Console output**: Real-time feedback to user
- **Flexible CLI**: Accept custom search queries via `--query` argument
- **Error handling**: Graceful handling of failures with proper exit codes
- **Execution tracking**: Logs total execution duration

## Usage

### Basic usage (default query "тест"):
```bash
python parse_search.py
```

### Custom query:
```bash
python parse_search.py --query "ноутбук"
```

### Help:
```bash
python parse_search.py --help
```

## Output

### Exit Codes
- `0` - Success (query fetched successfully)
- `1` - Failure (API error, network issue, etc.)
- `130` - Interrupted by user (Ctrl+C)

### Log Files

**logs/parse_search.log** (Action logs):
- Every step of the process
- DEBUG level details
- Timestamps for all actions
- Error stack traces if failures occur

**logs/parse_search_result.log** (Result logs):
- Query used
- Status (success/failed)
- Total products found (if successful)
- Error message (if failed)
- Retry count
- First 500 chars of raw API response

### Console Output

Example successful run:
```
INFO: Starting WB search parser
INFO: Query to parse: 'тест'
INFO: Initializing WB API client
INFO: Building request URL
INFO: Request URL: https://www.wildberries.ru/...
INFO: Sending request to WB API
INFO: Received response from WB API
INFO: Query status: success
INFO: Query successful: total=1234
INFO: Parsing complete

================================================================================
PARSING SUMMARY
================================================================================
Query: тест
Status: success
Total products found: 1234
--------------------------------------------------------------------------------
Action logs saved to: logs/parse_search.log
Result logs saved to: logs/parse_search_result.log
================================================================================
```

## Architecture

### Key Components

1. **setup_logging()**: Configures dual loggers (actions + results)
2. **run_parse()**: Main async function that performs the parsing
3. **parse_args()**: CLI argument parser
4. **main()**: Entry point with error handling

### Integration

The script uses the existing `WBAPIClient` from `src.api.client`, which:
- Handles HTTP requests with retry logic
- Manages rate limiting
- Parses API responses
- Returns structured `QueryResult` objects

## Testing

Comprehensive test coverage in `tests/unit/test_parse_search.py`:
- Logging setup tests (4 tests)
- Parsing logic tests (4 tests)
- CLI argument tests (3 tests)

Run tests:
```bash
python -m pytest tests/unit/test_parse_search.py -v
```

## Requirements

- Python 3.10+
- aiohttp >= 3.9.0
- Dependencies from requirements.txt

## Implementation Notes

- Uses asyncio for async operations
- Properly manages WBAPIClient lifecycle with async context manager
- Logs are UTF-8 encoded to support Cyrillic characters
- Action logger has both file and console handlers
- Result logger has only file handler (keeps console clean)
- Loggers don't propagate to root logger (isolated)
