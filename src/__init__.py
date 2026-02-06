"""WB Parser - Wildberries ExactMatch Total Parser."""

__version__ = "1.0.0"
__author__ = "WB Parser Team"
__description__ = "Desktop application for parsing Wildberries search data"

from .api import RetryStrategy, WBAPIClient
from .clean import DataCleaner, StopWordsFilter
from .config import ConfigManager, load_default_config
from .core import CheckpointManager, ParserPipeline
from .io import CSVWriter, ExcelReader, SQLiteCache
from .models import CleaningConfig, ParserConfig, QueryResult, QueryStatus, SearchQuery

__all__ = [
    "SearchQuery",
    "QueryResult",
    "QueryStatus",
    "ParserConfig",
    "CleaningConfig",
    "ExcelReader",
    "CSVWriter",
    "SQLiteCache",
    "DataCleaner",
    "StopWordsFilter",
    "WBAPIClient",
    "RetryStrategy",
    "ParserPipeline",
    "CheckpointManager",
    "ConfigManager",
    "load_default_config",
]
