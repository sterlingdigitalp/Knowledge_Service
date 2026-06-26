"""Source Registry entry data model."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class SourceEntry:
    """Source registry metadata persisted by SourceStore implementations."""

    id: str
    name: str
    url: Optional[str]
    type: str
    trust_score: float
    freshness_score: float
    avg_latency_ms: int
    success_rate: float
    topics: List[str]
    cache_policy: Dict[str, Any]
    status: str
    last_acquired_at: Optional[str]
    created_at: str
    updated_at: str
    topic_scores: Dict[str, float] = field(default_factory=dict)
