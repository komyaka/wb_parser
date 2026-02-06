"""Checkpoint manager for resumable processing."""

import json
import logging
from datetime import datetime
from pathlib import Path

from ..models.query import QueryResult

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages checkpoints for resumable processing."""

    def __init__(self, checkpoint_file: str = "wb_checkpoint.json"):
        self.checkpoint_file = Path(checkpoint_file)
        self.completed_queries: set[str] = set()
        self.pending_queries: list[str] = []
        self.results: list[QueryResult] = []
        self.metadata: dict = {}

    def load(self) -> bool:
        """
        Load checkpoint from file.

        Returns:
            True if checkpoint was loaded, False otherwise
        """
        if not self.checkpoint_file.exists():
            logger.info("No checkpoint file found")
            return False

        try:
            with open(self.checkpoint_file, encoding="utf-8") as f:
                data = json.load(f)

            self.completed_queries = set(data.get("completed_queries", []))
            self.pending_queries = data.get("pending_queries", [])
            self.metadata = data.get("metadata", {})

            # Load results
            self.results = []
            for r_data in data.get("results", []):
                # Reconstruct QueryResult from dict
                from ..models.query import QueryStatus

                result = QueryResult(
                    query=r_data["query"],
                    total=r_data.get("total"),
                    status=QueryStatus(r_data["status"]),
                    fetched_at=(
                        datetime.fromisoformat(r_data["fetched_at"])
                        if r_data.get("fetched_at")
                        else None
                    ),
                    error_message=r_data.get("error_message"),
                    retry_count=r_data.get("retry_count", 0),
                    raw_response=r_data.get("raw_response"),
                )
                self.results.append(result)

            logger.info(
                f"Loaded checkpoint: {len(self.completed_queries)} completed, "
                f"{len(self.pending_queries)} pending"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return False

    def save(self) -> None:
        """Save checkpoint to file."""
        try:
            data = {
                "completed_queries": list(self.completed_queries),
                "pending_queries": self.pending_queries,
                "results": [
                    {
                        "query": r.query,
                        "total": r.total,
                        "status": r.status.value,
                        "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None,
                        "error_message": r.error_message,
                        "retry_count": r.retry_count,
                        "raw_response": r.raw_response,
                    }
                    for r in self.results
                ],
                "metadata": self.metadata,
            }

            # Ensure directory exists
            self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved checkpoint: {len(self.completed_queries)} completed")

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def mark_completed(self, query: str, result: QueryResult) -> None:
        """Mark query as completed and store result."""
        self.completed_queries.add(query)
        self.results.append(result)

        # Remove from pending if present
        if query in self.pending_queries:
            self.pending_queries.remove(query)

    def is_completed(self, query: str) -> bool:
        """Check if query is already completed."""
        return query in self.completed_queries

    def get_pending_queries(self) -> list[str]:
        """Get list of pending queries."""
        return self.pending_queries.copy()

    def set_pending_queries(self, queries: list[str]) -> None:
        """Set list of pending queries."""
        self.pending_queries = queries.copy()

    def get_results(self) -> list[QueryResult]:
        """Get all stored results."""
        return self.results.copy()

    def clear(self) -> None:
        """Clear checkpoint data."""
        self.completed_queries.clear()
        self.pending_queries.clear()
        self.results.clear()
        self.metadata.clear()

        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()

        logger.info("Cleared checkpoint")

    def update_metadata(self, key: str, value) -> None:
        """Update checkpoint metadata."""
        self.metadata[key] = value
