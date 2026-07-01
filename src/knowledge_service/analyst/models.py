"""Data models for the Personal Intelligence Analyst pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..intelligence.models import now_iso, stable_id


class NoveltyClass(str, Enum):
    NEW = "new"
    REFINEMENT = "refinement"
    REPEAT = "repeat"
    CONTRADICTION = "contradiction"
    UPDATE = "update"


class ImportanceBand(str, Enum):
    IGNORE = "ignore"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class Claim:
    claim_text: str
    speaker: str
    timestamp_start: Optional[float]
    timestamp_end: Optional[float]
    timestamp_label: str
    transcript_reference: str
    evidence: str
    confidence: float
    topic: str
    entities: List[str]
    supporting_context: str
    claim_id: str = ""
    episode_id: str = ""
    event_id: str = ""
    profile_id: str = ""
    source_id: str = ""
    source_url: str = ""
    podcast_name: str = ""
    participants: List[str] = field(default_factory=list)
    route_confidence: Optional[float] = None
    segment_id: str = ""
    knowledge_object_id: str = ""
    published_at: str = ""
    created_at: str = field(default_factory=now_iso)
    embedding: List[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.claim_id:
            self.claim_id = stable_id(
                self.episode_id,
                self.knowledge_object_id,
                self.segment_id,
                self.speaker,
                self.timestamp_start,
                self.claim_text[:200],
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "speaker": self.speaker,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "timestamp_label": self.timestamp_label,
            "transcript_reference": self.transcript_reference,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "topic": self.topic,
            "entities": list(self.entities),
            "supporting_context": self.supporting_context,
            "episode_id": self.episode_id,
            "event_id": self.event_id,
            "profile_id": self.profile_id,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "podcast_name": self.podcast_name,
            "participants": list(self.participants),
            "route_confidence": self.route_confidence,
            "segment_id": self.segment_id,
            "knowledge_object_id": self.knowledge_object_id,
            "published_at": self.published_at,
            "created_at": self.created_at,
            "embedding": list(self.embedding),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Claim":
        return cls(
            claim_id=str(data.get("claim_id") or ""),
            claim_text=str(data.get("claim_text") or ""),
            speaker=str(data.get("speaker") or "unknown"),
            timestamp_start=data.get("timestamp_start"),
            timestamp_end=data.get("timestamp_end"),
            timestamp_label=str(data.get("timestamp_label") or ""),
            transcript_reference=str(data.get("transcript_reference") or ""),
            evidence=str(data.get("evidence") or ""),
            confidence=float(data.get("confidence") or 0.0),
            topic=str(data.get("topic") or ""),
            entities=list(data.get("entities") or []),
            supporting_context=str(data.get("supporting_context") or ""),
            episode_id=str(data.get("episode_id") or ""),
            event_id=str(data.get("event_id") or data.get("episode_id") or ""),
            profile_id=str(data.get("profile_id") or ""),
            source_id=str(data.get("source_id") or ""),
            source_url=str(data.get("source_url") or ""),
            podcast_name=str(data.get("podcast_name") or ""),
            participants=list(data.get("participants") or []),
            route_confidence=data.get("route_confidence"),
            segment_id=str(data.get("segment_id") or ""),
            knowledge_object_id=str(data.get("knowledge_object_id") or ""),
            published_at=str(data.get("published_at") or ""),
            created_at=str(data.get("created_at") or now_iso()),
            embedding=list(data.get("embedding") or []),
        )


@dataclass
class NoveltyResult:
    score: float
    classification: NoveltyClass
    explanation: str
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    prior_claim_id: Optional[str] = None
    prior_similarity: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "classification": self.classification.value,
            "explanation": self.explanation,
            "evidence": list(self.evidence),
            "prior_claim_id": self.prior_claim_id,
            "prior_similarity": self.prior_similarity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NoveltyResult":
        return cls(
            score=float(data.get("score") or 0.0),
            classification=NoveltyClass(data.get("classification") or NoveltyClass.NEW.value),
            explanation=str(data.get("explanation") or ""),
            evidence=list(data.get("evidence") or []),
            prior_claim_id=data.get("prior_claim_id"),
            prior_similarity=data.get("prior_similarity"),
        )


@dataclass
class RelevanceResult:
    profile_id: str
    profile_name: str
    score: float
    matched_interests: List[str] = field(default_factory=list)
    matched_participants: List[str] = field(default_factory=list)
    matched_topics: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "profile_name": self.profile_name,
            "score": self.score,
            "matched_interests": list(self.matched_interests),
            "matched_participants": list(self.matched_participants),
            "matched_topics": list(self.matched_topics),
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RelevanceResult":
        return cls(
            profile_id=str(data.get("profile_id") or ""),
            profile_name=str(data.get("profile_name") or ""),
            score=float(data.get("score") or 0.0),
            matched_interests=list(data.get("matched_interests") or []),
            matched_participants=list(data.get("matched_participants") or []),
            matched_topics=list(data.get("matched_topics") or []),
            explanation=str(data.get("explanation") or ""),
        )


@dataclass
class ImportanceFactors:
    novelty: float = 0.0
    source_credibility: float = 0.0
    corroboration: float = 0.0
    potential_impact: float = 0.0
    profile_relevance: float = 0.0
    freshness: float = 0.0
    evidence_quality: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "novelty": self.novelty,
            "source_credibility": self.source_credibility,
            "corroboration": self.corroboration,
            "potential_impact": self.potential_impact,
            "profile_relevance": self.profile_relevance,
            "freshness": self.freshness,
            "evidence_quality": self.evidence_quality,
        }


@dataclass
class ImportanceResult:
    score: float
    band: ImportanceBand
    factors: ImportanceFactors
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "band": self.band.value,
            "factors": self.factors.to_dict(),
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImportanceResult":
        factors = data.get("factors") or {}
        return cls(
            score=float(data.get("score") or 0.0),
            band=ImportanceBand(data.get("band") or ImportanceBand.LOW.value),
            factors=ImportanceFactors(
                novelty=float(factors.get("novelty") or 0.0),
                source_credibility=float(factors.get("source_credibility") or 0.0),
                corroboration=float(factors.get("corroboration") or 0.0),
                potential_impact=float(factors.get("potential_impact") or 0.0),
                profile_relevance=float(factors.get("profile_relevance") or 0.0),
                freshness=float(factors.get("freshness") or 0.0),
                evidence_quality=float(factors.get("evidence_quality") or 0.0),
            ),
            explanation=str(data.get("explanation") or ""),
        )


@dataclass
class Contradiction:
    claim_id: str
    prior_claim_id: str
    explanation: str
    similarity: float
    claim_text: str = ""
    prior_claim_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "prior_claim_id": self.prior_claim_id,
            "explanation": self.explanation,
            "similarity": self.similarity,
            "claim_text": self.claim_text,
            "prior_claim_text": self.prior_claim_text,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Contradiction":
        return cls(
            claim_id=str(data.get("claim_id") or ""),
            prior_claim_id=str(data.get("prior_claim_id") or ""),
            explanation=str(data.get("explanation") or ""),
            similarity=float(data.get("similarity") or 0.0),
            claim_text=str(data.get("claim_text") or ""),
            prior_claim_text=str(data.get("prior_claim_text") or ""),
        )


@dataclass
class CorroborationCluster:
    cluster_id: str
    topic_label: str
    claim_ids: List[str]
    source_ids: List[str]
    speakers: List[str]
    corroboration_count: int
    confidence: float
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "topic_label": self.topic_label,
            "claim_ids": list(self.claim_ids),
            "source_ids": list(self.source_ids),
            "speakers": list(self.speakers),
            "corroboration_count": self.corroboration_count,
            "confidence": self.confidence,
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CorroborationCluster":
        return cls(
            cluster_id=str(data.get("cluster_id") or ""),
            topic_label=str(data.get("topic_label") or ""),
            claim_ids=list(data.get("claim_ids") or []),
            source_ids=list(data.get("source_ids") or []),
            speakers=list(data.get("speakers") or []),
            corroboration_count=int(data.get("corroboration_count") or 0),
            confidence=float(data.get("confidence") or 0.0),
            explanation=str(data.get("explanation") or ""),
        )


@dataclass
class ScoredClaim:
    claim: Claim
    novelty: NoveltyResult
    relevance: List[RelevanceResult]
    importance: ImportanceResult
    contradictions: List[Contradiction] = field(default_factory=list)
    corroboration_cluster_id: Optional[str] = None
    corroboration_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim.to_dict(),
            "novelty": self.novelty.to_dict(),
            "relevance": [item.to_dict() for item in self.relevance],
            "importance": self.importance.to_dict(),
            "contradictions": [item.to_dict() for item in self.contradictions],
            "corroboration_cluster_id": self.corroboration_cluster_id,
            "corroboration_count": self.corroboration_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScoredClaim":
        return cls(
            claim=Claim.from_dict(data.get("claim") or {}),
            novelty=NoveltyResult.from_dict(data.get("novelty") or {}),
            relevance=[RelevanceResult.from_dict(item) for item in data.get("relevance") or []],
            importance=ImportanceResult.from_dict(data.get("importance") or {}),
            contradictions=[Contradiction.from_dict(item) for item in data.get("contradictions") or []],
            corroboration_cluster_id=data.get("corroboration_cluster_id"),
            corroboration_count=int(data.get("corroboration_count") or 0),
        )


@dataclass
class BriefItem:
    item_id: str
    profile_id: str
    profile_name: str
    headline: str
    what_is_new: str
    why_you_see_this: str
    why_it_matters: str
    evidence_summary: str
    timestamp_label: str
    source: str
    source_url: str
    claim_id: str
    importance_score: float
    importance_band: str
    novelty_score: float
    novelty_classification: str
    matched_interests: List[str]
    matched_participants: List[str]
    corroborated_by: int
    explainability: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "profile_id": self.profile_id,
            "profile_name": self.profile_name,
            "headline": self.headline,
            "what_is_new": self.what_is_new,
            "why_you_see_this": self.why_you_see_this,
            "why_it_matters": self.why_it_matters,
            "evidence_summary": self.evidence_summary,
            "timestamp_label": self.timestamp_label,
            "source": self.source,
            "source_url": self.source_url,
            "claim_id": self.claim_id,
            "importance_score": self.importance_score,
            "importance_band": self.importance_band,
            "novelty_score": self.novelty_score,
            "novelty_classification": self.novelty_classification,
            "matched_interests": list(self.matched_interests),
            "matched_participants": list(self.matched_participants),
            "corroborated_by": self.corroborated_by,
            "explainability": dict(self.explainability),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BriefItem":
        return cls(
            item_id=str(data.get("item_id") or ""),
            profile_id=str(data.get("profile_id") or ""),
            profile_name=str(data.get("profile_name") or ""),
            headline=str(data.get("headline") or ""),
            what_is_new=str(data.get("what_is_new") or ""),
            why_you_see_this=str(data.get("why_you_see_this") or ""),
            why_it_matters=str(data.get("why_it_matters") or ""),
            evidence_summary=str(data.get("evidence_summary") or ""),
            timestamp_label=str(data.get("timestamp_label") or ""),
            source=str(data.get("source") or ""),
            source_url=str(data.get("source_url") or ""),
            claim_id=str(data.get("claim_id") or ""),
            importance_score=float(data.get("importance_score") or 0.0),
            importance_band=str(data.get("importance_band") or ""),
            novelty_score=float(data.get("novelty_score") or 0.0),
            novelty_classification=str(data.get("novelty_classification") or ""),
            matched_interests=list(data.get("matched_interests") or []),
            matched_participants=list(data.get("matched_participants") or []),
            corroborated_by=int(data.get("corroborated_by") or 0),
            explainability=dict(data.get("explainability") or {}),
        )


@dataclass
class MorningBrief:
    brief_id: str
    generated_at: str
    reading_time_seconds: int
    sections: Dict[str, List[BriefItem]]
    total_items: int
    pipeline_run_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brief_id": self.brief_id,
            "generated_at": self.generated_at,
            "reading_time_seconds": self.reading_time_seconds,
            "sections": {
                name: [item.to_dict() for item in items]
                for name, items in self.sections.items()
            },
            "total_items": self.total_items,
            "pipeline_run_id": self.pipeline_run_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MorningBrief":
        sections = {}
        for name, items in (data.get("sections") or {}).items():
            sections[name] = [BriefItem.from_dict(item) for item in items]
        return cls(
            brief_id=str(data.get("brief_id") or ""),
            generated_at=str(data.get("generated_at") or ""),
            reading_time_seconds=int(data.get("reading_time_seconds") or 60),
            sections=sections,
            total_items=int(data.get("total_items") or 0),
            pipeline_run_id=str(data.get("pipeline_run_id") or ""),
        )


@dataclass
class DeepDiveResponse:
    claim_id: str
    headline: str
    analyst_summary: str
    transcript_excerpt: str
    surrounding_context: str
    previous_appearances: List[Dict[str, Any]]
    related_claims: List[Dict[str, Any]]
    corroborating_evidence: List[Dict[str, Any]]
    contradictory_evidence: List[Dict[str, Any]]
    timestamped_sources: List[Dict[str, Any]]
    explainability: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "headline": self.headline,
            "analyst_summary": self.analyst_summary,
            "transcript_excerpt": self.transcript_excerpt,
            "surrounding_context": self.surrounding_context,
            "previous_appearances": list(self.previous_appearances),
            "related_claims": list(self.related_claims),
            "corroborating_evidence": list(self.corroborating_evidence),
            "contradictory_evidence": list(self.contradictory_evidence),
            "timestamped_sources": list(self.timestamped_sources),
            "explainability": dict(self.explainability),
        }