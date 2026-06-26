"""Source Store — Abstract persistence contract for Source Registry entries."""

from typing import Optional, List

from ..repositories.source_entry import SourceEntry


class SourceStore:
    """Abstract interface for source registry persistence."""

    def register_source(self, source: SourceEntry) -> bool:
        """Persist a new source entry. Returns True if inserted."""
        raise NotImplementedError

    def get_source(self, source_id: str) -> Optional[SourceEntry]:
        """Get a source entry by its identifier."""
        raise NotImplementedError

    def update_source_metrics(self, source_id: str, trust_score: Optional[float] = None,
                             freshness_score: Optional[float] = None, avg_latency_ms: Optional[int] = None,
                             success_rate: Optional[float] = None, last_acquired_at: Optional[str] = None,
                             status: Optional[str] = None):
        """Update runtime metrics for a source. Returns True if updated, False if missing."""
        raise NotImplementedError

    def list_sources(self, status: Optional[str] = None, limit: int = 100) -> List[SourceEntry]:
        """List source entries, optionally filtered by status."""
        raise NotImplementedError

    def search_by_topic(self, topic: str, min_confidence: float = 0.3) -> List[SourceEntry]:
        """Find sources with enough confidence for the topic."""
        raise NotImplementedError

    def get_metrics(self) -> dict:
        """Return store metrics."""
        raise NotImplementedError

    def health(self) -> bool:
        """Check if the storage backend is healthy."""
        raise NotImplementedError
