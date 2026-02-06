"""SQLite cache for API results."""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from ..models.query import QueryResult, QueryStatus

logger = logging.getLogger(__name__)


class SQLiteCache:
    """SQLite-based cache for query results."""

    def __init__(self, db_path: str = "wb_cache.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_cache (
                    query TEXT PRIMARY KEY,
                    total INTEGER,
                    status TEXT,
                    fetched_at TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    raw_response TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_fetched_at
                ON query_cache(fetched_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status
                ON query_cache(status)
            """)
            conn.commit()

        logger.info(f"Initialized cache database: {self.db_path}")

    def get(self, query: str) -> QueryResult | None:
        """Get cached result for query."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM query_cache WHERE query = ?", (query,))
            row = cursor.fetchone()

            if row:
                return QueryResult(
                    query=row["query"],
                    total=row["total"],
                    status=QueryStatus(row["status"]),
                    fetched_at=(
                        datetime.fromisoformat(row["fetched_at"]) if row["fetched_at"] else None
                    ),
                    error_message=row["error_message"],
                    retry_count=row["retry_count"],
                    raw_response=row["raw_response"],
                )

            return None

    def set(self, result: QueryResult) -> None:
        """Cache query result."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO query_cache 
                (query, total, status, fetched_at, error_message, retry_count, raw_response)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    result.query,
                    result.total,
                    result.status.value,
                    result.fetched_at.isoformat() if result.fetched_at else None,
                    result.error_message,
                    result.retry_count,
                    result.raw_response,
                ),
            )
            conn.commit()

    def set_batch(self, results: list[QueryResult]) -> None:
        """Cache multiple query results."""
        with sqlite3.connect(self.db_path) as conn:
            data = [
                (
                    r.query,
                    r.total,
                    r.status.value,
                    r.fetched_at.isoformat() if r.fetched_at else None,
                    r.error_message,
                    r.retry_count,
                    r.raw_response,
                )
                for r in results
            ]
            conn.executemany(
                """
                INSERT OR REPLACE INTO query_cache 
                (query, total, status, fetched_at, error_message, retry_count, raw_response)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                data,
            )
            conn.commit()

        logger.info(f"Cached {len(results)} results")

    def exists(self, query: str) -> bool:
        """Check if query exists in cache."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT 1 FROM query_cache WHERE query = ? LIMIT 1", (query,))
            return cursor.fetchone() is not None

    def clear(self) -> None:
        """Clear all cache entries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM query_cache")
            conn.commit()

        logger.info("Cleared cache")

    def get_stats(self) -> dict:
        """Get cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'cached' THEN 1 ELSE 0 END) as cached
                FROM query_cache
            """)
            row = cursor.fetchone()

            return {"total": row[0], "success": row[1], "failed": row[2], "cached": row[3]}

    def get_all_results(self) -> list[QueryResult]:
        """Get all cached results."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM query_cache ORDER BY fetched_at DESC")

            results = []
            for row in cursor:
                results.append(
                    QueryResult(
                        query=row["query"],
                        total=row["total"],
                        status=QueryStatus(row["status"]),
                        fetched_at=(
                            datetime.fromisoformat(row["fetched_at"]) if row["fetched_at"] else None
                        ),
                        error_message=row["error_message"],
                        retry_count=row["retry_count"],
                        raw_response=row["raw_response"],
                    )
                )

            return results
