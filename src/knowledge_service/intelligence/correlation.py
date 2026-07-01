"""Cross-source claim correlation and contradiction surfacing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..retrieval.embedding import cosine_similarity, embed_text, tokenize
from .claims import IntelligenceClaim
from .models import now_iso, stable_id
from .novelty import NoveltyResult
from .state import FileStateStore


CORRELATION_FILE = "cross_source_clusters.jsonl"


@dataclass
class CrossSourceCluster:
    cluster_id: str
    topic: str
    claim_ids: List[str]
    sources: List[str]
    participants: List[str]
    source_diversity_score: float
    corroboration_count: int
    contradictions: List[str] = field(default_factory=list)
    evidence_matrix: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "topic": self.topic,
            "claim_ids": list(self.claim_ids),
            "sources": list(self.sources),
            "participants": list(self.participants),
            "source_diversity_score": self.source_diversity_score,
            "corroboration_count": self.corroboration_count,
            "contradictions": list(self.contradictions),
            "evidence_matrix": list(self.evidence_matrix),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrossSourceCluster":
        return cls(
            cluster_id=str(data.get("cluster_id") or ""),
            topic=str(data.get("topic") or "general"),
            claim_ids=list(data.get("claim_ids") or []),
            sources=list(data.get("sources") or []),
            participants=list(data.get("participants") or []),
            source_diversity_score=float(data.get("source_diversity_score", 0.0)),
            corroboration_count=int(data.get("corroboration_count", 0)),
            contradictions=list(data.get("contradictions") or []),
            evidence_matrix=list(data.get("evidence_matrix") or []),
            created_at=str(data.get("created_at") or now_iso()),
        )


class CrossSourceIntelligenceEngine:
    def __init__(self, state: FileStateStore):
        self.state = state

    def correlate(self, claims: List[IntelligenceClaim], novelty: List[NoveltyResult]) -> List[CrossSourceCluster]:
        novelty_by_id = {item.claim_id: item for item in novelty}
        buckets: Dict[str, List[IntelligenceClaim]] = {}
        for claim in claims:
            buckets.setdefault(_cluster_topic(claim), []).append(claim)
        clusters: List[CrossSourceCluster] = []
        for topic, topic_claims in buckets.items():
            sources = sorted({claim.source_id or claim.source_name for claim in topic_claims if claim.source_id or claim.source_name})
            if len(sources) < 2:
                continue
            representatives = _representative_claims(topic_claims)
            if len({claim.source_id or claim.source_name for claim in representatives}) < 2:
                continue
            contradictions = [claim.claim_id for claim in representatives if novelty_by_id.get(claim.claim_id) and novelty_by_id[claim.claim_id].novelty_label == "contradiction_candidate"]
            participants = sorted({entity for claim in representatives for entity in claim.entities})[:12]
            clusters.append(CrossSourceCluster(
                cluster_id=stable_id("cluster", topic, *[claim.claim_id for claim in representatives[:8]]),
                topic=topic,
                claim_ids=[claim.claim_id for claim in representatives],
                sources=sorted({claim.source_id or claim.source_name for claim in representatives}),
                participants=participants,
                source_diversity_score=round(min(1.0, len(sources) / 4), 4),
                corroboration_count=max(0, len(sources) - 1),
                contradictions=contradictions,
                evidence_matrix=[
                    {"claim_id": claim.claim_id, "source": claim.source_name, "speaker": claim.speaker, "timestamped_source_url": claim.timestamped_source_url}
                    for claim in representatives[:12]
                ],
            ))
        self.state.write_jsonl(CORRELATION_FILE, [cluster.to_dict() for cluster in clusters])
        return clusters

    def load(self) -> List[CrossSourceCluster]:
        return [CrossSourceCluster.from_dict(row) for row in self.state.read_jsonl(CORRELATION_FILE)]


def _cluster_topic(claim: IntelligenceClaim) -> str:
    tokens = set(tokenize(claim.claim_text))
    if {"ai", "model", "models", "agent", "agents", "inference", "compute", "coding"} & tokens:
        return "ai"
    if {"market", "markets", "investing", "tariff", "china", "capital"} & tokens:
        return "markets"
    if {"founder", "company", "business", "build", "built"} & tokens:
        return "founders"
    if {"muscle", "weight", "health", "glp", "bone", "strength"} & tokens:
        return "longevity"
    return claim.topic or "general"


def _representative_claims(claims: List[IntelligenceClaim]) -> List[IntelligenceClaim]:
    selected: List[IntelligenceClaim] = []
    for claim in sorted(claims, key=lambda item: (item.source_id, item.claim_id)):
        if not selected:
            selected.append(claim)
            continue
        if any(cosine_similarity(claim.embedding or embed_text(claim.claim_text), other.embedding or embed_text(other.claim_text)) >= 0.38 for other in selected):
            selected.append(claim)
        elif len({item.source_id for item in selected}) < 2:
            selected.append(claim)
    return selected[:20]
