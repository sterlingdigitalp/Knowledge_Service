"""Data models for Runtime 3 Story Objects and pipeline artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..intelligence.models import now_iso, stable_id


class SegmentType(str, Enum):
    NEWS = "news"
    DISCUSSION = "discussion"
    INTERVIEW = "interview"
    SPONSOR = "sponsor"
    ADVERTISEMENT = "advertisement"
    INTRO = "intro"
    OUTRO = "outro"
    HOUSEKEEPING = "housekeeping"
    HOST_BANTER = "host_banter"
    META_REQUEST = "meta_request"
    QA = "qa"
    UNKNOWN = "unknown"


class ClaimType(str, Enum):
    FACTUAL = "factual"
    OPINION = "opinion"
    PREDICTION = "prediction"
    ANALYSIS = "analysis"
    QUOTE = "quote"
    META = "meta"
    SPONSOR = "sponsor"


class EntityType(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    PRODUCT = "product"
    PLACE = "place"
    TECHNOLOGY = "technology"
    PUBLICATION = "publication"
    COMPANY = "company"
    EVENT = "event"
    TOPIC = "topic"


class EventType(str, Enum):
    LAUNCH = "launch"
    ACQUISITION = "acquisition"
    FUNDING = "funding"
    RESEARCH_PAPER = "research_paper"
    POLICY = "policy"
    HIRING = "hiring"
    PARTNERSHIP = "partnership"
    RELEASE = "release"
    SCIENTIFIC_DISCOVERY = "scientific_discovery"
    LEGAL_ACTION = "legal_action"
    SPEECH = "speech"
    INTERVIEW = "interview"
    DEBATE = "debate"
    PRODUCT_ANNOUNCEMENT = "product_announcement"
    ELECTION = "election"
    OTHER = "other"


class StoryType(str, Enum):
    BREAKING = "breaking"
    ANALYSIS = "analysis"
    TREND = "trend"
    PROFILE = "profile"
    SCIENCE = "science"
    POLICY = "policy"
    TECHNOLOGY = "technology"
    BUSINESS = "business"
    CULTURE = "culture"
    GENERAL = "general"


NON_NEWS_SEGMENT_TYPES = frozenset({
    SegmentType.SPONSOR,
    SegmentType.ADVERTISEMENT,
    SegmentType.INTRO,
    SegmentType.OUTRO,
    SegmentType.HOUSEKEEPING,
    SegmentType.HOST_BANTER,
    SegmentType.META_REQUEST,
})


@dataclass
class TranscriptSegment:
    segment_id: str
    text: str
    speaker: str
    start_seconds: Optional[float]
    end_seconds: Optional[float]
    segment_type: SegmentType
    confidence: float
    episode_id: str = ""
    podcast_name: str = ""
    source_url: str = ""
    knowledge_object_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "text": self.text,
            "speaker": self.speaker,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "segment_type": self.segment_type.value,
            "confidence": self.confidence,
            "episode_id": self.episode_id,
            "podcast_name": self.podcast_name,
            "source_url": self.source_url,
            "knowledge_object_id": self.knowledge_object_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptSegment":
        return cls(
            segment_id=str(data.get("segment_id") or ""),
            text=str(data.get("text") or ""),
            speaker=str(data.get("speaker") or "unknown"),
            start_seconds=data.get("start_seconds"),
            end_seconds=data.get("end_seconds"),
            segment_type=SegmentType(data.get("segment_type") or SegmentType.UNKNOWN.value),
            confidence=float(data.get("confidence") or 0.0),
            episode_id=str(data.get("episode_id") or ""),
            podcast_name=str(data.get("podcast_name") or ""),
            source_url=str(data.get("source_url") or ""),
            knowledge_object_id=str(data.get("knowledge_object_id") or ""),
        )


@dataclass
class ResolvedEntity:
    entity_id: str
    canonical_name: str
    entity_type: EntityType
    aliases: List[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "canonical_name": self.canonical_name,
            "entity_type": self.entity_type.value,
            "aliases": list(self.aliases),
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResolvedEntity":
        return cls(
            entity_id=str(data.get("entity_id") or ""),
            canonical_name=str(data.get("canonical_name") or ""),
            entity_type=EntityType(data.get("entity_type") or EntityType.TOPIC.value),
            aliases=list(data.get("aliases") or []),
            confidence=float(data.get("confidence") or 0.0),
        )


@dataclass
class SemanticClaim:
    claim_id: str
    claim_text: str
    claim_type: ClaimType
    confidence: float
    segment_type: SegmentType
    speaker: str
    entities: List[str]
    resolved_entity_ids: List[str]
    event_references: List[str]
    supporting_sentences: List[str]
    episode_id: str = ""
    podcast_name: str = ""
    source_url: str = ""
    timestamp_start: Optional[float] = None
    timestamp_label: str = ""
    segment_id: str = ""
    embedding: List[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.claim_id:
            self.claim_id = stable_id(
                self.episode_id, self.segment_id, self.speaker, self.claim_text[:200],
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "claim_type": self.claim_type.value,
            "confidence": self.confidence,
            "segment_type": self.segment_type.value,
            "speaker": self.speaker,
            "entities": list(self.entities),
            "resolved_entity_ids": list(self.resolved_entity_ids),
            "event_references": list(self.event_references),
            "supporting_sentences": list(self.supporting_sentences),
            "episode_id": self.episode_id,
            "podcast_name": self.podcast_name,
            "source_url": self.source_url,
            "timestamp_start": self.timestamp_start,
            "timestamp_label": self.timestamp_label,
            "segment_id": self.segment_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SemanticClaim":
        return cls(
            claim_id=str(data.get("claim_id") or ""),
            claim_text=str(data.get("claim_text") or ""),
            claim_type=ClaimType(data.get("claim_type") or ClaimType.FACTUAL.value),
            confidence=float(data.get("confidence") or 0.0),
            segment_type=SegmentType(data.get("segment_type") or SegmentType.UNKNOWN.value),
            speaker=str(data.get("speaker") or "unknown"),
            entities=list(data.get("entities") or []),
            resolved_entity_ids=list(data.get("resolved_entity_ids") or []),
            event_references=list(data.get("event_references") or []),
            supporting_sentences=list(data.get("supporting_sentences") or []),
            episode_id=str(data.get("episode_id") or ""),
            podcast_name=str(data.get("podcast_name") or ""),
            source_url=str(data.get("source_url") or ""),
            timestamp_start=data.get("timestamp_start"),
            timestamp_label=str(data.get("timestamp_label") or ""),
            segment_id=str(data.get("segment_id") or ""),
        )


@dataclass
class DetectedEvent:
    event_id: str
    event_type: EventType
    title: str
    description: str
    claim_ids: List[str]
    entity_ids: List[str]
    episode_ids: List[str]
    confidence: float
    timestamp_start: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = stable_id("event", self.event_type.value, self.title)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "title": self.title,
            "description": self.description,
            "claim_ids": list(self.claim_ids),
            "entity_ids": list(self.entity_ids),
            "episode_ids": list(self.episode_ids),
            "confidence": self.confidence,
            "timestamp_start": self.timestamp_start,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DetectedEvent":
        return cls(
            event_id=str(data.get("event_id") or ""),
            event_type=EventType(data.get("event_type") or EventType.OTHER.value),
            title=str(data.get("title") or ""),
            description=str(data.get("description") or ""),
            claim_ids=list(data.get("claim_ids") or []),
            entity_ids=list(data.get("entity_ids") or []),
            episode_ids=list(data.get("episode_ids") or []),
            confidence=float(data.get("confidence") or 0.0),
            timestamp_start=data.get("timestamp_start"),
        )


@dataclass
class StoryRelationship:
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    confidence: float
    evidence_claim_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "relationship_type": self.relationship_type,
            "confidence": self.confidence,
            "evidence_claim_ids": list(self.evidence_claim_ids),
        }


@dataclass
class StoryTimelineEntry:
    timestamp_label: str
    description: str
    claim_id: str = ""
    event_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_label": self.timestamp_label,
            "description": self.description,
            "claim_id": self.claim_id,
            "event_id": self.event_id,
        }


@dataclass
class StoryObject:
    story_id: str
    title: str
    summary: str
    story_type: StoryType
    headline: str = ""
    executive_summary: str = ""
    what_happened: str = ""
    why_it_matters: str = ""
    evidence: List[str] = field(default_factory=list)
    supporting_sources: List[str] = field(default_factory=list)
    future_watch: str = ""
    editorial_notes: str = ""
    entities: List[ResolvedEntity] = field(default_factory=list)
    people: List[str] = field(default_factory=list)
    organizations: List[str] = field(default_factory=list)
    products: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    events: List[DetectedEvent] = field(default_factory=list)
    supporting_claims: List[SemanticClaim] = field(default_factory=list)
    supporting_claim_ids: List[str] = field(default_factory=list)
    episode_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0
    novelty: float = 0.0
    importance: float = 0.0
    contradictions: List[str] = field(default_factory=list)
    relationships: List[StoryRelationship] = field(default_factory=list)
    timeline: List[StoryTimelineEntry] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if not self.story_id:
            self.story_id = stable_id("story", self.title, *self.supporting_claim_ids[:3])
        if not self.headline:
            self.headline = self.title
        if not self.executive_summary:
            self.executive_summary = self.summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "story_id": self.story_id,
            "title": self.title,
            "summary": self.summary,
            "story_type": self.story_type.value,
            "headline": self.headline,
            "executive_summary": self.executive_summary,
            "what_happened": self.what_happened,
            "why_it_matters": self.why_it_matters,
            "evidence": list(self.evidence),
            "supporting_sources": list(self.supporting_sources),
            "future_watch": self.future_watch,
            "editorial_notes": self.editorial_notes,
            "entities": [entity.to_dict() for entity in self.entities],
            "people": list(self.people),
            "organizations": list(self.organizations),
            "products": list(self.products),
            "topics": list(self.topics),
            "events": [event.to_dict() for event in self.events],
            "supporting_claim_ids": list(self.supporting_claim_ids),
            "supporting_claims": [claim.to_dict() for claim in self.supporting_claims],
            "episode_ids": list(self.episode_ids),
            "confidence": self.confidence,
            "novelty": self.novelty,
            "importance": self.importance,
            "contradictions": list(self.contradictions),
            "relationships": [rel.to_dict() for rel in self.relationships],
            "timeline": [entry.to_dict() for entry in self.timeline],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoryObject":
        return cls(
            story_id=str(data.get("story_id") or ""),
            title=str(data.get("title") or ""),
            summary=str(data.get("summary") or ""),
            story_type=StoryType(data.get("story_type") or StoryType.GENERAL.value),
            headline=str(data.get("headline") or data.get("title") or ""),
            executive_summary=str(data.get("executive_summary") or data.get("summary") or ""),
            what_happened=str(data.get("what_happened") or ""),
            why_it_matters=str(data.get("why_it_matters") or ""),
            evidence=list(data.get("evidence") or []),
            supporting_sources=list(data.get("supporting_sources") or []),
            future_watch=str(data.get("future_watch") or ""),
            editorial_notes=str(data.get("editorial_notes") or ""),
            entities=[ResolvedEntity.from_dict(e) for e in data.get("entities") or []],
            people=list(data.get("people") or []),
            organizations=list(data.get("organizations") or []),
            products=list(data.get("products") or []),
            topics=list(data.get("topics") or []),
            events=[DetectedEvent.from_dict(e) for e in data.get("events") or []],
            supporting_claims=[SemanticClaim.from_dict(c) for c in data.get("supporting_claims") or []],
            supporting_claim_ids=list(data.get("supporting_claim_ids") or []),
            episode_ids=list(data.get("episode_ids") or []),
            confidence=float(data.get("confidence") or 0.0),
            novelty=float(data.get("novelty") or 0.0),
            importance=float(data.get("importance") or 0.0),
            contradictions=list(data.get("contradictions") or []),
            relationships=[
                StoryRelationship(**rel) if isinstance(rel, dict) else rel
                for rel in data.get("relationships") or []
            ],
            timeline=[
                StoryTimelineEntry(**entry) if isinstance(entry, dict) else entry
                for entry in data.get("timeline") or []
            ],
            created_at=str(data.get("created_at") or now_iso()),
        )


@dataclass
class StoryGraph:
    stories: List[StoryObject] = field(default_factory=list)
    orphan_claim_ids: List[str] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stories": [story.to_dict() for story in self.stories],
            "orphan_claim_ids": list(self.orphan_claim_ids),
            "edges": list(self.edges),
            "story_count": len(self.stories),
        }


@dataclass
class Runtime3Result:
    segments: List[TranscriptSegment] = field(default_factory=list)
    claims: List[SemanticClaim] = field(default_factory=list)
    entities: List[ResolvedEntity] = field(default_factory=list)
    events: List[DetectedEvent] = field(default_factory=list)
    story_graph: Optional[StoryGraph] = None
    stories: List[StoryObject] = field(default_factory=list)
    episodes_processed: int = 0
    latency_ms: float = 0.0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segments": [segment.to_dict() for segment in self.segments],
            "claims": [claim.to_dict() for claim in self.claims],
            "entities": [entity.to_dict() for entity in self.entities],
            "events": [event.to_dict() for event in self.events],
            "story_graph": self.story_graph.to_dict() if self.story_graph else None,
            "stories": [story.to_dict() for story in self.stories],
            "episodes_processed": self.episodes_processed,
            "latency_ms": self.latency_ms,
            "enabled": self.enabled,
            "story_count": len(self.stories),
            "claim_count": len(self.claims),
            "segment_count": len(self.segments),
            "entity_count": len(self.entities),
            "event_count": len(self.events),
        }