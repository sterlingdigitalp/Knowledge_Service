"""Profile-specific relevance scoring for claims."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..retrieval.embedding import cosine_similarity, embed_text, tokenize
from .claims import IntelligenceClaim
from .models import IntelligenceProfile, now_iso
from .state import FileStateStore


RELEVANCE_FILE = "claim_relevance.jsonl"


@dataclass
class RelevanceResult:
    claim_id: str
    profile_id: str
    relevance_score: float
    matched_people: List[str] = field(default_factory=list)
    matched_interests: List[str] = field(default_factory=list)
    semantic_score: float = 0.0
    explanation: str = ""
    computed_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "profile_id": self.profile_id,
            "relevance_score": self.relevance_score,
            "matched_people": list(self.matched_people),
            "matched_interests": list(self.matched_interests),
            "semantic_score": self.semantic_score,
            "explanation": self.explanation,
            "computed_at": self.computed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RelevanceResult":
        return cls(
            claim_id=str(data.get("claim_id") or ""),
            profile_id=str(data.get("profile_id") or ""),
            relevance_score=float(data.get("relevance_score", 0.0)),
            matched_people=list(data.get("matched_people") or []),
            matched_interests=list(data.get("matched_interests") or []),
            semantic_score=float(data.get("semantic_score", 0.0)),
            explanation=str(data.get("explanation") or ""),
            computed_at=str(data.get("computed_at") or now_iso()),
        )


class RelevanceEngine:
    def __init__(self, state: FileStateStore):
        self.state = state

    def score(self, claims: List[IntelligenceClaim], profiles: List[IntelligenceProfile]) -> List[RelevanceResult]:
        results: List[RelevanceResult] = []
        for claim in claims:
            claim_tokens = set(tokenize(" ".join([claim.claim_text, claim.topic, " ".join(claim.entities)])))
            for profile in profiles:
                matched_people = _matched_people(claim, profile)
                matched_interests = [interest for interest in profile.interests if interest.lower() in " ".join(claim_tokens)]
                profile_text = " ".join([profile.name, profile.description, *profile.interests, *[entry.display_name for entry in profile.watch_list]])
                semantic = max(0.0, cosine_similarity(embed_text(claim.claim_text), embed_text(profile_text)))
                home_profile_bonus = 0.15 if claim.profile_id == profile.profile_id else 0.0
                score = min(1.0, (0.28 * semantic) + (0.22 * min(1.0, len(matched_interests) / 2)) + (0.30 * min(1.0, len(matched_people))) + home_profile_bonus)
                explanation = _explain(profile, matched_people, matched_interests, semantic, home_profile_bonus)
                results.append(RelevanceResult(
                    claim_id=claim.claim_id,
                    profile_id=profile.profile_id,
                    relevance_score=round(score, 4),
                    matched_people=matched_people,
                    matched_interests=matched_interests,
                    semantic_score=round(semantic, 4),
                    explanation=explanation,
                ))
        self.state.write_jsonl(RELEVANCE_FILE, [result.to_dict() for result in results])
        return results

    def load(self) -> List[RelevanceResult]:
        return [RelevanceResult.from_dict(row) for row in self.state.read_jsonl(RELEVANCE_FILE)]


def _matched_people(claim: IntelligenceClaim, profile: IntelligenceProfile) -> List[str]:
    text = " ".join([claim.claim_text, claim.speaker, " ".join(claim.entities)]).lower()
    matches = []
    for entry in profile.watch_list:
        names = [entry.display_name, *entry.aliases]
        if any(name.lower() in text for name in names if name):
            matches.append(entry.display_name)
    return matches


def _explain(profile: IntelligenceProfile, people: List[str], interests: List[str], semantic: float, home_bonus: float) -> str:
    parts = []
    if people:
        parts.append(f"matched watched people: {', '.join(people)}")
    if interests:
        parts.append(f"matched interests: {', '.join(interests)}")
    if home_bonus:
        parts.append("originated in this profile's corpus")
    parts.append(f"semantic profile similarity {semantic:.2f}")
    return "; ".join(parts) if parts else f"low explicit match to {profile.name}"
