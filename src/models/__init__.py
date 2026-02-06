"""Data models for WB Parser application."""

from .config import CleaningConfig, ParserConfig
from .query import QueryResult, QueryStatus, SearchQuery

__all__ = [
    "SearchQuery",
    "QueryResult",
    "QueryStatus",
    "ParserConfig",
    "CleaningConfig",
]
