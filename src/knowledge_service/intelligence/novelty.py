"""Novelty and contradiction scoring for extracted claims."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..retrieval.embedding import cosine_similarity, embed_text, tokenize
from .claims import IntelligenceClaim
from .models import now_iso
from .state import FileStateStore


NOVELTY_FILE = "claim_novelty.jsonl"

CONTRADICTION_MARKERS = {"not", "never", "no", "without", "can't", "cannot", "won't", "less", "decline", "risk", "wrong"}
UPDATE_MARKERS = {"now", "new", "changed", "updated", "different", "emerging", "next", "future", "recent"}


@dataclass
class NoveltyResult:
    claim_id: str
    novelty_score: float
    novelty_label: str
    explanation: str
    nearest_prior_claim_ids: List[str] = field(default_factory=list)
    novelty_evidence: List[Dict[str, Any]] = field(default_factory=list)
    computed_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "novelty_score": self.novelty_score,
            "novelty_label": self.novelty_label,
            "explanation": self.explanation,
            "nearest_prior_claim_ids": list(self.nearest_prior_claim_ids),
            "novelty_evidence": list(self.novelty_evidence),
            "computed_at": self.computed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NoveltyResult":
        return cls(
            claim_id=str(data.get("claim_id") or ""),
            novelty_score=float(data.get("novelty_score", 0.0)),
            novelty_label=str(data.get("novelty_label") or "unknown"),
            explanation=str(data.get("explanation") or ""),
            nearest_prior_claim_ids=list(data.get("nearest_prior_claim_ids") or []),
            novelty_evidence=list(data.get("novelty_evidence") or []),
            computed_at=str(data.get("computed_at") or now_iso()),
        )


class NoveltyEngine:
    def __init__(self, state: FileStateStore):
        self.state = state

    def score(self, claims: List[IntelligenceClaim]) -> List[NoveltyResult]:
        results: List[NoveltyResult] = []
        prior: List[IntelligenceClaim] = []
        for claim in claims:
            nearest = _nearest_claims(claim, prior)
            max_similarity = nearest[0][1] if nearest else 0.0
            label = "new"
            score = 1.0 - max_similarity
            explanation = "No substantially similar prior claim found."
            if nearest and max_similarity >= 0.9:
                label = "repeated"
                score = 0.08
                explanation = "Claim closely repeats prior corpus language."
            elif nearest and max_similarity >= 0.72:
                label = "refinement"
                score = 0.45
                explanation = "Claim appears to refine or restate a related prior claim."
            if nearest and _possible_contradiction(claim, nearest[0][0]):
                label = "contradiction_candidate"
                score = max(score, 0.7)
                explanation = "Claim uses opposing language relative to a semantically related prior claim."
            elif any(token in UPDATE_MARKERS for token in tokenize(claim.claim_text)) and nearest:
                label = "significant_update" if max_similarity >= 0.55 else label
                score = max(score, 0.62)
                explanation = "Claim contains update language and relates to earlier corpus material."
            results.append(NoveltyResult(
                claim_id=claim.claim_id,
                novelty_score=round(max(0.0, min(1.0, score)), 4),
                novelty_label=label,
                explanation=explanation,
                nearest_prior_claim_ids=[item[0].claim_id for item in nearest[:3]],
                novelty_evidence=[
                    {"claim_id": item[0].claim_id, "similarity": round(item[1], 4), "claim_text": item[0].claim_text[:240]}
                    for item in nearest[:3]
                ],
            ))
            prior.append(claim)
        self.state.write_jsonl(NOVELTY_FILE, [result.to_dict() for result in results])
        return results

    def load(self) -> List[NoveltyResult]:
        return [NoveltyResult.from_dict(row) for row in self.state.read_jsonl(NOVELTY_FILE)]


def _nearest_claims(claim: IntelligenceClaim, prior: List[IntelligenceClaim]) -> List[tuple[IntelligenceClaim, float]]:
    if not prior:
        return []
    claim_embedding = claim.embedding or embed_text(claim.claim_text)
    scored = []
    claim_tokens = set(tokenize(claim.claim_text))
    for candidate in prior:
        semantic = cosine_similarity(claim_embedding, candidate.embedding or embed_text(candidate.claim_text))
        overlap = _token_overlap(claim_tokens, set(tokenize(candidate.claim_text)))
        score = (semantic * 0.65) + (overlap * 0.35)
        if score >= 0.35:
            scored.append((candidate, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:5]


def _token_overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    important_left = {token for token in left if len(token) > 3}
    important_right = {token for token in right if len(token) > 3}
    if not important_left or not important_right:
        return 0.0
    return len(important_left & important_right) / len(important_left | important_right)


def _possible_contradiction(claim: IntelligenceClaim, prior: IntelligenceClaim) -> bool:
    claim_markers = CONTRADICTION_MARKERS & set(tokenize(claim.claim_text))
    prior_markers = CONTRADICTION_MARKERS & set(tokenize(prior.claim_text))
    return bool(claim_markers ^ prior_markers)
