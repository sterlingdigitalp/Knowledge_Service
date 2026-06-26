"""Source Repository — repository pattern for Source Registry data."""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from .source_entry import SourceEntry
from ..interfaces.source_store import SourceStore


def _normalize_topic(topic: str) -> str:
    """Normalize topic keys for stable matching."""
    return topic.strip().lower()


def _normalize_topics(topics: List[str]) -> List[str]:
    """Normalize topic list, removing blanks and duplicates."""
    normalized = []
    seen = set()
    for topic in topics:
        normalized_topic = _normalize_topic(topic)
        if not normalized_topic or normalized_topic in seen:
            continue
        normalized.append(normalized_topic)
        seen.add(normalized_topic)
    return normalized


def _canonical_url(url: Optional[str]) -> Optional[str]:
    """Canonicalize source URLs for stable lookup and deduplication."""
    if not url:
        return None

    candidate = url.strip()
    if not candidate:
        return None

    parsed = urlparse(candidate)
    if parsed.scheme and parsed.netloc:
        canonical_netloc = parsed.netloc.lower()
        canonical_path = parsed.path or ""
        if canonical_path and canonical_path != "/" and canonical_path.endswith("/"):
            canonical_path = canonical_path.rstrip("/")

        query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
        canonical_query = urlencode(sorted(query_pairs), doseq=True)

        normalized = urlunparse((
            parsed.scheme.lower(),
            canonical_netloc,
            canonical_path,
            "",
            canonical_query,
            "",
        ))
        return normalized

    # Handle URLs provided without scheme (for example, "example.org/path").
    if "/" in candidate or "." in candidate:
        if not candidate.startswith("/") and not candidate.startswith("."):
            normalized_candidate = candidate.lower().strip("/")
            if normalized_candidate:
                return f"https://{normalized_candidate}"

    return candidate.lower()


class SourceRepository:
    """Repository for Source Registry data."""

    DEFAULT_TOPICS = ["general"]

    DEFAULT_CACHE_POLICY = {
        "max_age_seconds": 3600,
        "stale_while_revalidate": 600,
        "cache_key_strategy": "url_exact",
        "invalidate_on_plan": True,
    }

    def __init__(self, store: SourceStore):
        self.store = store

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _coerce_status(self, trust_score: float, success_rate: float, freshness_score: float,
                      current_status: Optional[str] = None) -> str:
        """Compute a health status from metrics."""
        if success_rate < 0.6:
            return "unhealthy"
        if success_rate < 0.8 or freshness_score < 0.5 or trust_score < 0.5:
            return "degraded"
        return current_status or "healthy"

    def register_source(self, source_id: str, name: str, url: Optional[str], source_type: str,
                        trust_score: float = 0.5, freshness_score: float = 1.0,
                        topics: List[str] = None, cache_policy: Dict[str, Any] = None) -> bool:
        """Register a new source in the registry."""
        normalized_url = _canonical_url(url)
        normalized_topics = _normalize_topics(topics or self.DEFAULT_TOPICS)
        cache_policy = cache_policy.copy() if cache_policy else self.DEFAULT_CACHE_POLICY.copy()

        now = self._now_iso()
        topic_scores = {topic: 1.0 for topic in normalized_topics}

        status = self._coerce_status(trust_score, 1.0, freshness_score)

        entry = SourceEntry(
            id=source_id,
            name=name,
            url=normalized_url,
            type=source_type,
            trust_score=trust_score,
            freshness_score=freshness_score,
            avg_latency_ms=0,
            success_rate=1.0,
            topics=normalized_topics,
            cache_policy=cache_policy,
            status=status,
            last_acquired_at=None,
            created_at=now,
            updated_at=now,
            topic_scores=topic_scores,
        )
        return self.store.register_source(entry)

    def get_source(self, source_id: str) -> Optional[SourceEntry]:
        """Retrieve a source entry by ID."""
        return self.store.get_source(source_id)

    def update_source_metrics(self, source_id: str, trust_score: Optional[float] = None,
                               freshness_score: Optional[float] = None, avg_latency_ms: Optional[int] = None,
                               success_rate: Optional[float] = None, last_acquired_at: Optional[str] = None):
        """Update source metrics."""
        if freshness_score is not None and (freshness_score < 0.0 or freshness_score > 1.0):
            raise ValueError("freshness_score must be between 0.0 and 1.0")
        if trust_score is not None and (trust_score < 0.0 or trust_score > 1.0):
            raise ValueError("trust_score must be between 0.0 and 1.0")
        if success_rate is not None and (success_rate < 0.0 or success_rate > 1.0):
            raise ValueError("success_rate must be between 0.0 and 1.0")
        if avg_latency_ms is not None and avg_latency_ms < 0:
            raise ValueError("avg_latency_ms must be >= 0")

        existing = self.store.get_source(source_id)
        if not existing:
            return False

        computed_trust = trust_score if trust_score is not None else existing.trust_score
        computed_freshness = freshness_score if freshness_score is not None else existing.freshness_score
        computed_success = success_rate if success_rate is not None else existing.success_rate
        computed_status = self._coerce_status(computed_trust, computed_success, computed_freshness, existing.status)

        self.store.update_source_metrics(
            source_id,
            trust_score=trust_score,
            freshness_score=freshness_score,
            avg_latency_ms=avg_latency_ms,
            success_rate=success_rate,
            last_acquired_at=last_acquired_at,
            status=computed_status,
        )
        return True

    def list_sources(self, status: Optional[str] = None, limit: int = 100) -> List[SourceEntry]:
        """List source entries, optionally filtered by status."""
        if limit < 0:
            raise ValueError("limit must be >= 0")

        normalized_status = status.lower() if isinstance(status, str) else status
        sources = self.store.list_sources(normalized_status, limit)
        return sources

    def search_by_topic(self, topic: str, min_confidence: float = 0.3) -> List[SourceEntry]:
        """Search sources by topic expertise."""
        if min_confidence < 0.0 or min_confidence > 1.0:
            raise ValueError("min_confidence must be between 0.0 and 1.0")
        normalized_topic = _normalize_topic(topic)
        if not normalized_topic:
            return []

        candidates = self.store.search_by_topic(normalized_topic, min_confidence)
        return [
            source for source in candidates
            if source.topic_scores.get(normalized_topic, 1.0) >= min_confidence
        ]
