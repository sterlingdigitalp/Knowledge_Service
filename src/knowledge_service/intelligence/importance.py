"""Explainable importance scoring for intelligence claims."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .claims import IntelligenceClaim
from .correlation import CrossSourceCluster
from .models import now_iso
from .novelty import NoveltyResult
from .relevance import RelevanceResult
from .state import FileStateStore


IMPORTANCE_FILE = "claim_importance.jsonl"


@dataclass
class ImportanceResult:
    claim_id: str
    profile_id: str
    importance_score: float
    importance_band: str
    components: Dict[str, float] = field(default_factory=dict)
    explanation: str = ""
    computed_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "profile_id": self.profile_id,
            "importance_score": self.importance_score,
            "importance_band": self.importance_band,
            "components": dict(self.components),
            "explanation": self.explanation,
            "computed_at": self.computed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImportanceResult":
        return cls(
            claim_id=str(data.get("claim_id") or ""),
            profile_id=str(data.get("profile_id") or ""),
            importance_score=float(data.get("importance_score", 0.0)),
            importance_band=str(data.get("importance_band") or "low"),
            components=dict(data.get("components") or {}),
            explanation=str(data.get("explanation") or ""),
            computed_at=str(data.get("computed_at") or now_iso()),
        )


class ImportanceEngine:
    def __init__(self, state: FileStateStore):
        self.state = state

    def score(
        self,
        claims: List[IntelligenceClaim],
        novelty: List[NoveltyResult],
        relevance: List[RelevanceResult],
        clusters: List[CrossSourceCluster],
    ) -> List[ImportanceResult]:
        claims_by_id = {claim.claim_id: claim for claim in claims}
        novelty_by_id = {item.claim_id: item for item in novelty}
        corroboration = _corroboration_by_claim(clusters)
        results: List[ImportanceResult] = []
        for rel in relevance:
            claim = claims_by_id.get(rel.claim_id)
            nov = novelty_by_id.get(rel.claim_id)
            if not claim or not nov:
                continue
            components = {
                "novelty": nov.novelty_score,
                "relevance": rel.relevance_score,
                "source_credibility": float(claim.route_confidence if claim.route_confidence is not None else 0.75),
                "evidence_quality": claim.confidence,
                "corroboration": min(1.0, corroboration.get(claim.claim_id, 0) / 3),
                "freshness": 0.85,
            }
            if nov.novelty_label == "contradiction_candidate":
                components["contradiction_signal"] = 0.85
            score = (
                components["novelty"] * 0.25
                + components["relevance"] * 0.25
                + components["source_credibility"] * 0.15
                + components["evidence_quality"] * 0.15
                + components["corroboration"] * 0.12
                + components["freshness"] * 0.08
                + components.get("contradiction_signal", 0.0) * 0.05
            )
            score = min(1.0, score)
            results.append(ImportanceResult(
                claim_id=rel.claim_id,
                profile_id=rel.profile_id,
                importance_score=round(score, 4),
                importance_band=_band(score),
                components={key: round(value, 4) for key, value in components.items()},
                explanation=_explain(components, nov, rel),
            ))
        self.state.write_jsonl(IMPORTANCE_FILE, [result.to_dict() for result in results])
        return results

    def load(self) -> List[ImportanceResult]:
        return [ImportanceResult.from_dict(row) for row in self.state.read_jsonl(IMPORTANCE_FILE)]


def _corroboration_by_claim(clusters: List[CrossSourceCluster]) -> Dict[str, int]:
    scores: Dict[str, int] = {}
    for cluster in clusters:
        for claim_id in cluster.claim_ids:
            scores[claim_id] = max(scores.get(claim_id, 0), cluster.corroboration_count)
    return scores


def _band(score: float) -> str:
    if score >= 0.78:
        return "very_high"
    if score >= 0.62:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _explain(components: Dict[str, float], novelty: NoveltyResult, relevance: RelevanceResult) -> str:
    return (
        f"{novelty.novelty_label} claim; relevance {relevance.relevance_score:.2f}; "
        f"source credibility {components['source_credibility']:.2f}; evidence {components['evidence_quality']:.2f}; "
        f"corroboration {components['corroboration']:.2f}"
    )
