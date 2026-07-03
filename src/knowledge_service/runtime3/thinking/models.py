"""Extended models for the FEGOS Thinking Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ...intelligence.models import now_iso, stable_id
from ..models import (
    DetectedEvent,
    ResolvedEntity,
    SemanticClaim,
    StoryObject,
    StoryType,
    TranscriptSegment,
)


class RichSegmentType(str, Enum):
    """Extended transcript segment taxonomy."""
    SPONSOR = "sponsor"
    ADVERTISEMENT = "advertisement"
    HOUSEKEEPING = "housekeeping"
    META_DISCUSSION = "meta_discussion"
    INTRO = "intro"
    OUTRO = "outro"
    INTERVIEW = "interview"
    DEBATE = "debate"
    NEWS = "news"
    RESEARCH = "research"
    OPINION = "opinion"
    PREDICTION = "prediction"
    SPECULATION = "speculation"
    HISTORICAL_CONTEXT = "historical_context"
    BACKGROUND = "background"
    QA = "qa"
    DISCUSSION = "discussion"
    UNKNOWN = "unknown"


class StoryEvolutionState(str, Enum):
    FIRST_SEEN = "first_seen"
    STRENGTHENED = "strengthened"
    WEAKENED = "weakened"
    CONTRADICTED = "contradicted"
    RESOLVED = "resolved"
    RETIRED = "retired"
    STABLE = "stable"


class MemoryMatchAction(str, Enum):
    EXTEND = "extend"
    CREATE = "create"
    RETIRE = "retire"


NON_SUBSTANTIVE_SEGMENTS = frozenset({
    RichSegmentType.SPONSOR,
    RichSegmentType.ADVERTISEMENT,
    RichSegmentType.HOUSEKEEPING,
    RichSegmentType.META_DISCUSSION,
    RichSegmentType.INTRO,
    RichSegmentType.OUTRO,
})


@dataclass
class StoryBoundary:
    """Where a substantive narrative begins/ends in a transcript."""
    boundary_id: str
    episode_id: str
    start_seconds: float
    end_seconds: float
    boundary_type: str  # story_start | story_end | topic_shift
    segment_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "boundary_id": self.boundary_id,
            "episode_id": self.episode_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "boundary_type": self.boundary_type,
            "segment_ids": list(self.segment_ids),
            "confidence": self.confidence,
            "label": self.label,
        }


@dataclass
class EnrichedSegment(TranscriptSegment):
    """Segment with rich classification and boundary hints."""
    rich_type: str = "unknown"
    is_substantive: bool = True
    story_boundary_id: str = ""
    topic_label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "rich_type": self.rich_type,
            "is_substantive": self.is_substantive,
            "story_boundary_id": self.story_boundary_id,
            "topic_label": self.topic_label,
        })
        return base


@dataclass
class EnrichedClaim(SemanticClaim):
    """Claim with full intelligence metadata."""
    certainty: float = 0.0
    source_quality: float = 0.0
    neighbor_claim_ids: List[str] = field(default_factory=list)
    neighbor_relationship: str = ""
    evidence_strength: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "certainty": self.certainty,
            "source_quality": self.source_quality,
            "neighbor_claim_ids": list(self.neighbor_claim_ids),
            "neighbor_relationship": self.neighbor_relationship,
            "evidence_strength": self.evidence_strength,
        })
        return base


@dataclass
class CanonicalEntity(ResolvedEntity):
    """Fully resolved entity with alias graph."""
    wikipedia_hint: str = ""
    external_ids: Dict[str, str] = field(default_factory=dict)
    mention_count: int = 0
    source_ids: List[str] = field(default_factory=list)
    related_entity_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "wikipedia_hint": self.wikipedia_hint,
            "external_ids": dict(self.external_ids),
            "mention_count": self.mention_count,
            "source_ids": list(self.source_ids),
            "related_entity_ids": list(self.related_entity_ids),
        })
        return base


@dataclass
class EventObject:
    """First-class event with participants and temporal grounding."""
    event_id: str
    event_type: str
    title: str
    description: str
    participants: List[str]
    participant_entity_ids: List[str]
    claim_ids: List[str]
    episode_ids: List[str]
    confidence: float
    time_label: str = ""
    timestamp_start: Optional[float] = None
    first_seen: str = field(default_factory=now_iso)
    last_seen: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = stable_id("evt", self.event_type, self.title)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "participants": list(self.participants),
            "participant_entity_ids": list(self.participant_entity_ids),
            "claim_ids": list(self.claim_ids),
            "episode_ids": list(self.episode_ids),
            "confidence": self.confidence,
            "time_label": self.time_label,
            "timestamp_start": self.timestamp_start,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_detected(cls, event: DetectedEvent, entities: List[ResolvedEntity]) -> "EventObject":
        entity_index = {entity.entity_id: entity for entity in entities}
        participants = [
            entity_index[eid].canonical_name
            for eid in event.entity_ids
            if eid in entity_index
        ]
        return cls(
            event_id=event.event_id,
            event_type=event.event_type.value,
            title=event.title,
            description=event.description,
            participants=participants,
            participant_entity_ids=list(event.entity_ids),
            claim_ids=list(event.claim_ids),
            episode_ids=list(event.episode_ids),
            confidence=event.confidence,
            timestamp_start=event.timestamp_start,
        )


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    edge_type: str
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }


@dataclass
class EntityGraph:
    entities: List[CanonicalEntity] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [entity.to_dict() for entity in self.entities],
            "edges": [edge.to_dict() for edge in self.edges],
            "entity_count": len(self.entities),
            "edge_count": len(self.edges),
        }


@dataclass
class EventGraph:
    events: List[EventObject] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": [event.to_dict() for event in self.events],
            "edges": [edge.to_dict() for edge in self.edges],
            "event_count": len(self.events),
            "edge_count": len(self.edges),
        }


@dataclass
class RelationshipGraph:
    """Cross-entity, cross-story, cross-event relationships."""
    edges: List[GraphEdge] = field(default_factory=list)
    story_links: List[Dict[str, Any]] = field(default_factory=list)
    contradictions: List[Dict[str, Any]] = field(default_factory=list)
    follow_ups: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edges": [edge.to_dict() for edge in self.edges],
            "story_links": list(self.story_links),
            "contradictions": list(self.contradictions),
            "follow_ups": list(self.follow_ups),
            "edge_count": len(self.edges),
        }


@dataclass
class StoryEvolution:
    state: StoryEvolutionState
    explanation: str
    prior_confidence: float = 0.0
    new_confidence: float = 0.0
    recorded_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "explanation": self.explanation,
            "prior_confidence": self.prior_confidence,
            "new_confidence": self.new_confidence,
            "recorded_at": self.recorded_at,
        }


@dataclass
class PersistentStoryRecord:
    """Cross-day story memory entry."""
    persistent_story_id: str
    headline: str
    story_type: str
    entity_signature: List[str]
    event_signature: List[str]
    first_seen_date: str
    last_seen_date: str
    evolution_state: StoryEvolutionState
    confidence: float
    importance: float
    claim_count: int = 0
    source_count: int = 0
    episode_ids: List[str] = field(default_factory=list)
    daily_story_ids: Dict[str, str] = field(default_factory=dict)
    evolution_history: List[StoryEvolution] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "persistent_story_id": self.persistent_story_id,
            "headline": self.headline,
            "story_type": self.story_type,
            "entity_signature": list(self.entity_signature),
            "event_signature": list(self.event_signature),
            "first_seen_date": self.first_seen_date,
            "last_seen_date": self.last_seen_date,
            "evolution_state": self.evolution_state.value,
            "confidence": self.confidence,
            "importance": self.importance,
            "claim_count": self.claim_count,
            "source_count": self.source_count,
            "episode_ids": list(self.episode_ids),
            "daily_story_ids": dict(self.daily_story_ids),
            "evolution_history": [entry.to_dict() for entry in self.evolution_history],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersistentStoryRecord":
        return cls(
            persistent_story_id=str(data.get("persistent_story_id") or ""),
            headline=str(data.get("headline") or ""),
            story_type=str(data.get("story_type") or ""),
            entity_signature=list(data.get("entity_signature") or []),
            event_signature=list(data.get("event_signature") or []),
            first_seen_date=str(data.get("first_seen_date") or ""),
            last_seen_date=str(data.get("last_seen_date") or ""),
            evolution_state=StoryEvolutionState(data.get("evolution_state") or "first_seen"),
            confidence=float(data.get("confidence") or 0.0),
            importance=float(data.get("importance") or 0.0),
            claim_count=int(data.get("claim_count") or 0),
            source_count=int(data.get("source_count") or 0),
            episode_ids=list(data.get("episode_ids") or []),
            daily_story_ids=dict(data.get("daily_story_ids") or {}),
            evolution_history=[
                StoryEvolution(
                    state=StoryEvolutionState(entry.get("state", "stable")),
                    explanation=str(entry.get("explanation") or ""),
                    prior_confidence=float(entry.get("prior_confidence") or 0.0),
                    new_confidence=float(entry.get("new_confidence") or 0.0),
                    recorded_at=str(entry.get("recorded_at") or now_iso()),
                )
                for entry in data.get("evolution_history") or []
            ],
        )


@dataclass
class StoryMemory:
    """Persistent cross-day story store."""
    version: str = "1.0"
    updated_at: str = field(default_factory=now_iso)
    records: List[PersistentStoryRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "updated_at": self.updated_at,
            "records": [record.to_dict() for record in self.records],
            "record_count": len(self.records),
        }


@dataclass
class RankedStory:
    story: StoryObject
    rank_score: float
    importance_score: float
    novelty_score: float
    editorial_opportunity: float
    recency_score: float
    evidence_quality: float
    source_diversity: float
    corroboration_score: float
    persistent_story_id: str = ""
    evolution_state: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank_score": self.rank_score,
            "importance_score": self.importance_score,
            "novelty_score": self.novelty_score,
            "editorial_opportunity": self.editorial_opportunity,
            "recency_score": self.recency_score,
            "evidence_quality": self.evidence_quality,
            "source_diversity": self.source_diversity,
            "corroboration_score": self.corroboration_score,
            "persistent_story_id": self.persistent_story_id,
            "evolution_state": self.evolution_state,
            "story": self.story.to_dict(),
        }


@dataclass
class ThinkingResult:
    """Complete output of the Thinking Engine."""
    date: str = ""
    segments: List[EnrichedSegment] = field(default_factory=list)
    boundaries: List[StoryBoundary] = field(default_factory=list)
    claims: List[EnrichedClaim] = field(default_factory=list)
    entities: List[CanonicalEntity] = field(default_factory=list)
    events: List[EventObject] = field(default_factory=list)
    stories: List[StoryObject] = field(default_factory=list)
    ranked_stories: List[RankedStory] = field(default_factory=list)
    entity_graph: Optional[EntityGraph] = None
    event_graph: Optional[EventGraph] = None
    relationship_graph: Optional[RelationshipGraph] = None
    story_graph: Optional[Dict[str, Any]] = None
    story_memory: Optional[StoryMemory] = None
    memory_actions: List[Dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "segment_count": len(self.segments),
            "boundary_count": len(self.boundaries),
            "claim_count": len(self.claims),
            "entity_count": len(self.entities),
            "event_count": len(self.events),
            "story_count": len(self.stories),
            "ranked_story_count": len(self.ranked_stories),
            "entity_graph": self.entity_graph.to_dict() if self.entity_graph else None,
            "event_graph": self.event_graph.to_dict() if self.event_graph else None,
            "relationship_graph": self.relationship_graph.to_dict() if self.relationship_graph else None,
            "story_graph": self.story_graph,
            "story_memory": self.story_memory.to_dict() if self.story_memory else None,
            "memory_actions": list(self.memory_actions),
            "latency_ms": self.latency_ms,
        }