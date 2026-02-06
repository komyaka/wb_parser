"""Search query data models."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class QueryStatus(Enum):
    """Status of API query fetch."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CACHED = "cached"
    RETRY = "retry"


@dataclass
class SearchQuery:
    """Represents a unique search query."""

    query: str
    count: int = 1  # Number of occurrences in original data

    def __hash__(self):
        return hash(self.query)

    def __eq__(self, other):
        if isinstance(other, SearchQuery):
            return self.query == other.query
        return False


@dataclass
class QueryResult:
    """Result of fetching total from WB API."""

    query: str
    total: int | None = None
    status: QueryStatus = QueryStatus.PENDING
    fetched_at: datetime | None = None
    error_message: str | None = None
    retry_count: int = 0
    raw_response: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for CSV export."""
        return {
            "Поисковый запрос": self.query,
            "total": self.total if self.total is not None else "",
            "status": self.status.value,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else "",
            "error_message": self.error_message or "",
            "retry_count": self.retry_count,
            "raw_response": self.raw_response or "",
        }
