"""Data models for idea-centric intelligence synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ...intelligence.models import now_iso, stable_id


class ThemeEvolutionState(str, Enum):
    NEW = "new"
    STRENGTHENING = "strengthening"
    CONTRADICTING = "contradicting"
    MATERIAL_CHANGE = "material_change"
    FADING = "fading"
    STABLE = "stable"


@dataclass
class Theme:
    theme_id: str
    label: str
    claim_ids: List[str]
    keywords: List[str]
    entities: List[str]
    source_count: int
    speaker_count: int
    centroid_embedding: List[float] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "theme_id": self.theme_id,
            "label": self.label,
            "claim_ids": list(self.claim_ids),
            "keywords": list(self.keywords),
            "entities": list(self.entities),
            "source_count": self.source_count,
            "speaker_count": self.speaker_count,
            "centroid_embedding": list(self.centroid_embedding),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Theme":
        return cls(
            theme_id=str(data.get("theme_id") or ""),
            label=str(data.get("label") or ""),
            claim_ids=list(data.get("claim_ids") or []),
            keywords=list(data.get("keywords") or []),
            entities=list(data.get("entities") or []),
            source_count=int(data.get("source_count") or 0),
            speaker_count=int(data.get("speaker_count") or 0),
            centroid_embedding=list(data.get("centroid_embedding") or []),
            created_at=str(data.get("created_at") or now_iso()),
        )


@dataclass
class ThemeEvolution:
    theme_id: str
    label: str
    state: ThemeEvolutionState
    explanation: str
    prior_theme_id: Optional[str] = None
    similarity_to_prior: Optional[float] = None
    claim_count_delta: int = 0
    source_count_delta: int = 0
    recorded_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "theme_id": self.theme_id,
            "label": self.label,
            "state": self.state.value,
            "explanation": self.explanation,
            "prior_theme_id": self.prior_theme_id,
            "similarity_to_prior": self.similarity_to_prior,
            "claim_count_delta": self.claim_count_delta,
            "source_count_delta": self.source_count_delta,
            "recorded_at": self.recorded_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThemeEvolution":
        return cls(
            theme_id=str(data.get("theme_id") or ""),
            label=str(data.get("label") or ""),
            state=ThemeEvolutionState(data.get("state") or ThemeEvolutionState.NEW.value),
            explanation=str(data.get("explanation") or ""),
            prior_theme_id=data.get("prior_theme_id"),
            similarity_to_prior=data.get("similarity_to_prior"),
            claim_count_delta=int(data.get("claim_count_delta") or 0),
            source_count_delta=int(data.get("source_count_delta") or 0),
            recorded_at=str(data.get("recorded_at") or now_iso()),
        )


@dataclass
class IntelligenceItem:
    item_id: str
    title: str
    executive_summary: str
    why_surfaced: str
    why_it_matters: str
    novelty_score: float
    novelty_classification: str
    importance_score: float
    importance_band: str
    confidence: float
    corroboration_count: int
    contradiction_count: int
    theme_id: str
    theme_label: str
    profile_ids: List[str]
    profile_names: List[str]
    supporting_claim_ids: List[str]
    supporting_evidence: List[Dict[str, Any]]
    timestamped_citations: List[Dict[str, Any]]
    speakers: List[str]
    sources: List[str]
    contradictions: List[Dict[str, Any]]
    historical_developments: List[Dict[str, Any]]
    theme_evolution: Optional[ThemeEvolution] = None
    cluster_id: Optional[str] = None
    star_rating: int = 3
    claim_count: int = 0
    created_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if not self.item_id:
            self.item_id = stable_id("intel-item", self.title, self.theme_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "title": self.title,
            "executive_summary": self.executive_summary,
            "why_surfaced": self.why_surfaced,
            "why_it_matters": self.why_it_matters,
            "novelty_score": self.novelty_score,
            "novelty_classification": self.novelty_classification,
            "importance_score": self.importance_score,
            "importance_band": self.importance_band,
            "confidence": self.confidence,
            "corroboration_count": self.corroboration_count,
            "contradiction_count": self.contradiction_count,
            "theme_id": self.theme_id,
            "theme_label": self.theme_label,
            "profile_ids": list(self.profile_ids),
            "profile_names": list(self.profile_names),
            "supporting_claim_ids": list(self.supporting_claim_ids),
            "supporting_evidence": list(self.supporting_evidence),
            "timestamped_citations": list(self.timestamped_citations),
            "speakers": list(self.speakers),
            "sources": list(self.sources),
            "contradictions": list(self.contradictions),
            "historical_developments": list(self.historical_developments),
            "theme_evolution": self.theme_evolution.to_dict() if self.theme_evolution else None,
            "cluster_id": self.cluster_id,
            "star_rating": self.star_rating,
            "claim_count": self.claim_count,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntelligenceItem":
        evolution = data.get("theme_evolution")
        return cls(
            item_id=str(data.get("item_id") or ""),
            title=str(data.get("title") or ""),
            executive_summary=str(data.get("executive_summary") or ""),
            why_surfaced=str(data.get("why_surfaced") or ""),
            why_it_matters=str(data.get("why_it_matters") or ""),
            novelty_score=float(data.get("novelty_score") or 0.0),
            novelty_classification=str(data.get("novelty_classification") or ""),
            importance_score=float(data.get("importance_score") or 0.0),
            importance_band=str(data.get("importance_band") or ""),
            confidence=float(data.get("confidence") or 0.0),
            corroboration_count=int(data.get("corroboration_count") or 0),
            contradiction_count=int(data.get("contradiction_count") or 0),
            theme_id=str(data.get("theme_id") or ""),
            theme_label=str(data.get("theme_label") or ""),
            profile_ids=list(data.get("profile_ids") or []),
            profile_names=list(data.get("profile_names") or []),
            supporting_claim_ids=list(data.get("supporting_claim_ids") or []),
            supporting_evidence=list(data.get("supporting_evidence") or []),
            timestamped_citations=list(data.get("timestamped_citations") or []),
            speakers=list(data.get("speakers") or []),
            sources=list(data.get("sources") or []),
            contradictions=list(data.get("contradictions") or []),
            historical_developments=list(data.get("historical_developments") or []),
            theme_evolution=ThemeEvolution.from_dict(evolution) if evolution else None,
            cluster_id=data.get("cluster_id"),
            star_rating=int(data.get("star_rating") or 3),
            claim_count=int(data.get("claim_count") or 0),
            created_at=str(data.get("created_at") or now_iso()),
        )


@dataclass
class IntelligenceBriefEntry:
    entry_id: str
    intelligence_item_id: str
    profile_id: str
    profile_name: str
    title: str
    what_changed: str
    why_you_care: str
    why_surfaced: str
    evidence_summary: str
    star_rating: int
    importance_band: str
    corroborated_by: int
    explainability: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "intelligence_item_id": self.intelligence_item_id,
            "profile_id": self.profile_id,
            "profile_name": self.profile_name,
            "title": self.title,
            "what_changed": self.what_changed,
            "why_you_care": self.why_you_care,
            "why_surfaced": self.why_surfaced,
            "evidence_summary": self.evidence_summary,
            "star_rating": self.star_rating,
            "importance_band": self.importance_band,
            "corroborated_by": self.corroborated_by,
            "explainability": dict(self.explainability),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntelligenceBriefEntry":
        return cls(
            entry_id=str(data.get("entry_id") or ""),
            intelligence_item_id=str(data.get("intelligence_item_id") or ""),
            profile_id=str(data.get("profile_id") or ""),
            profile_name=str(data.get("profile_name") or ""),
            title=str(data.get("title") or ""),
            what_changed=str(data.get("what_changed") or ""),
            why_you_care=str(data.get("why_you_care") or ""),
            why_surfaced=str(data.get("why_surfaced") or ""),
            evidence_summary=str(data.get("evidence_summary") or ""),
            star_rating=int(data.get("star_rating") or 3),
            importance_band=str(data.get("importance_band") or ""),
            corroborated_by=int(data.get("corroborated_by") or 0),
            explainability=dict(data.get("explainability") or {}),
        )


@dataclass
class IntelligenceBrief:
    brief_id: str
    generated_at: str
    reading_time_seconds: int
    total_items: int
    items: List[IntelligenceBriefEntry]
    compression_ratio: float
    claims_synthesized: int
    pipeline_run_id: str = ""
    version: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brief_id": self.brief_id,
            "generated_at": self.generated_at,
            "reading_time_seconds": self.reading_time_seconds,
            "total_items": self.total_items,
            "items": [item.to_dict() for item in self.items],
            "compression_ratio": self.compression_ratio,
            "claims_synthesized": self.claims_synthesized,
            "pipeline_run_id": self.pipeline_run_id,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntelligenceBrief":
        return cls(
            brief_id=str(data.get("brief_id") or ""),
            generated_at=str(data.get("generated_at") or ""),
            reading_time_seconds=int(data.get("reading_time_seconds") or 60),
            total_items=int(data.get("total_items") or 0),
            items=[IntelligenceBriefEntry.from_dict(item) for item in data.get("items") or []],
            compression_ratio=float(data.get("compression_ratio") or 0.0),
            claims_synthesized=int(data.get("claims_synthesized") or 0),
            pipeline_run_id=str(data.get("pipeline_run_id") or ""),
            version=str(data.get("version") or "2.0"),
        )


@dataclass
class IntelligenceDeepDive:
    intelligence_item_id: str
    title: str
    analyst_briefing: str
    executive_summary: str
    supporting_claims: List[Dict[str, Any]]
    historical_context: List[Dict[str, Any]]
    contradictions: List[Dict[str, Any]]
    corroboration: List[Dict[str, Any]]
    related_transcripts: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]
    timestamped_sources: List[Dict[str, Any]]
    theme_evolution: Optional[Dict[str, Any]] = None
    explainability: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intelligence_item_id": self.intelligence_item_id,
            "title": self.title,
            "analyst_briefing": self.analyst_briefing,
            "executive_summary": self.executive_summary,
            "supporting_claims": list(self.supporting_claims),
            "historical_context": list(self.historical_context),
            "contradictions": list(self.contradictions),
            "corroboration": list(self.corroboration),
            "related_transcripts": list(self.related_transcripts),
            "timeline": list(self.timeline),
            "timestamped_sources": list(self.timestamped_sources),
            "theme_evolution": self.theme_evolution,
            "explainability": dict(self.explainability),
        }