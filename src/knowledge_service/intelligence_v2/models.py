"""Data models for Intelligence Layer 2.0."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AnalystBriefCard:
    """Publication-ready intelligence card produced by IL2."""

    title: str
    executive_summary: str
    what_happened: str
    why_it_matters: str
    evidence: List[Dict[str, Any]]
    confidence: float
    confidence_explanation: str
    contradictions: List[Dict[str, Any]]
    what_to_watch: str
    suggested_action: str
    supporting_sources: List[str]
    canonical_topic: str
    original_title: str = ""
    cluster_id: Optional[str] = None
    quality_score: float = 0.0
    accepted: bool = True
    rejection_reason: Optional[str] = None
    failure_modes: List[str] = field(default_factory=list)
    item_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "executive_summary": self.executive_summary,
            "what_happened": self.what_happened,
            "why_it_matters": self.why_it_matters,
            "evidence": list(self.evidence),
            "confidence": self.confidence,
            "confidence_explanation": self.confidence_explanation,
            "contradictions": list(self.contradictions),
            "what_to_watch": self.what_to_watch,
            "suggested_action": self.suggested_action,
            "supporting_sources": list(self.supporting_sources),
            "canonical_topic": self.canonical_topic,
            "original_title": self.original_title,
            "cluster_id": self.cluster_id,
            "quality_score": self.quality_score,
            "accepted": self.accepted,
            "rejection_reason": self.rejection_reason,
            "failure_modes": list(self.failure_modes),
            "item_id": self.item_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalystBriefCard":
        return cls(
            title=str(data.get("title") or ""),
            executive_summary=str(data.get("executive_summary") or ""),
            what_happened=str(data.get("what_happened") or ""),
            why_it_matters=str(data.get("why_it_matters") or ""),
            evidence=list(data.get("evidence") or []),
            confidence=float(data.get("confidence") or 0.0),
            confidence_explanation=str(data.get("confidence_explanation") or ""),
            contradictions=list(data.get("contradictions") or []),
            what_to_watch=str(data.get("what_to_watch") or ""),
            suggested_action=str(data.get("suggested_action") or ""),
            supporting_sources=list(data.get("supporting_sources") or []),
            canonical_topic=str(data.get("canonical_topic") or ""),
            original_title=str(data.get("original_title") or ""),
            cluster_id=data.get("cluster_id"),
            quality_score=float(data.get("quality_score") or 0.0),
            accepted=bool(data.get("accepted", True)),
            rejection_reason=data.get("rejection_reason"),
            failure_modes=list(data.get("failure_modes") or []),
            item_id=str(data.get("item_id") or ""),
        )


@dataclass
class IL2Result:
    """Aggregate output from an IL2 pipeline run."""

    cards: List[AnalystBriefCard] = field(default_factory=list)
    accepted_count: int = 0
    rejected_count: int = 0
    clusters_formed: int = 0
    titles_resolved: int = 0
    latency_ms: float = 0.0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cards": [card.to_dict() for card in self.cards],
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "clusters_formed": self.clusters_formed,
            "titles_resolved": self.titles_resolved,
            "latency_ms": self.latency_ms,
            "enabled": self.enabled,
        }


@dataclass
class CorpusSample:
    """Single historical output for evaluation."""

    sample_id: str
    source: str
    captured_at: str
    title: str
    summary: str
    evidence_excerpt: str
    quality_label: str  # good | bad | mixed
    failure_modes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "source": self.source,
            "captured_at": self.captured_at,
            "title": self.title,
            "summary": self.summary,
            "evidence_excerpt": self.evidence_excerpt,
            "quality_label": self.quality_label,
            "failure_modes": list(self.failure_modes),
            "metadata": dict(self.metadata),
        }