"""Novelty Engine — semantic comparison against historical claims."""

from __future__ import annotations

from typing import List, Optional, Sequence

from ...retrieval.embedding import cosine_similarity, embed_text
from ..models import Claim, NoveltyClass, NoveltyResult


REPEAT_THRESHOLD = 0.82
REFINEMENT_THRESHOLD = 0.62
CONTRADICTION_TOPIC_THRESHOLD = 0.55

NEGATION_PAIRS = [
    ("will", "won't"),
    ("will", "will not"),
    ("increase", "decrease"),
    ("grow", "shrink"),
    ("bullish", "bearish"),
    ("support", "oppose"),
    ("agree", "disagree"),
    ("yes", "no"),
    ("can", "cannot"),
    ("should", "should not"),
]


class NoveltyEngine:
    """Score claim novelty against the existing claim corpus."""

    def score(self, claim: Claim, historical: Sequence[Claim]) -> NoveltyResult:
        if not claim.embedding:
            claim.embedding = embed_text(claim.claim_text)

        best_match: Optional[Claim] = None
        best_similarity = 0.0
        for prior in historical:
            if prior.claim_id == claim.claim_id:
                continue
            if prior.episode_id == claim.episode_id:
                continue
            prior_embedding = prior.embedding or embed_text(prior.claim_text)
            similarity = cosine_similarity(claim.embedding, prior_embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = prior

        if best_match is None or best_similarity < REFINEMENT_THRESHOLD:
            return NoveltyResult(
                score=1.0,
                classification=NoveltyClass.NEW,
                explanation="No close semantic match found in historical corpus.",
                evidence=[{"type": "corpus_search", "matches": 0}],
            )

        if _has_contradiction(claim.claim_text, best_match.claim_text) and best_similarity >= CONTRADICTION_TOPIC_THRESHOLD:
            return NoveltyResult(
                score=0.85,
                classification=NoveltyClass.CONTRADICTION,
                explanation=(
                    f"Semantically related prior claim from {best_match.speaker} "
                    f"({best_match.podcast_name}) appears to conflict."
                ),
                evidence=[{
                    "type": "prior_claim",
                    "claim_id": best_match.claim_id,
                    "similarity": round(best_similarity, 4),
                    "speaker": best_match.speaker,
                    "source": best_match.podcast_name,
                }],
                prior_claim_id=best_match.claim_id,
                prior_similarity=round(best_similarity, 4),
            )

        if best_similarity >= REPEAT_THRESHOLD:
            return NoveltyResult(
                score=0.15,
                classification=NoveltyClass.REPEAT,
                explanation=(
                    f"Highly similar claim already recorded from {best_match.speaker} "
                    f"in {best_match.podcast_name}."
                ),
                evidence=[{
                    "type": "prior_claim",
                    "claim_id": best_match.claim_id,
                    "similarity": round(best_similarity, 4),
                }],
                prior_claim_id=best_match.claim_id,
                prior_similarity=round(best_similarity, 4),
            )

        classification = NoveltyClass.REFINEMENT
        novelty_score = round(1.0 - best_similarity + 0.35, 3)
        if _looks_like_update(claim.claim_text, best_match.claim_text):
            classification = NoveltyClass.UPDATE
            novelty_score = max(novelty_score, 0.7)

        return NoveltyResult(
            score=min(1.0, novelty_score),
            classification=classification,
            explanation=(
                f"Related prior discussion from {best_match.speaker} "
                f"({best_match.podcast_name}); this claim adds or refines detail."
            ),
            evidence=[{
                "type": "prior_claim",
                "claim_id": best_match.claim_id,
                "similarity": round(best_similarity, 4),
                "speaker": best_match.speaker,
            }],
            prior_claim_id=best_match.claim_id,
            prior_similarity=round(best_similarity, 4),
        )

    def score_batch(self, claims: List[Claim], historical: Sequence[Claim]) -> List[NoveltyResult]:
        results: List[NoveltyResult] = []
        corpus = list(historical)
        for claim in claims:
            result = self.score(claim, corpus)
            results.append(result)
            if result.classification in {NoveltyClass.NEW, NoveltyClass.REFINEMENT, NoveltyClass.UPDATE, NoveltyClass.CONTRADICTION}:
                corpus.append(claim)
        return results


def _has_contradiction(left: str, right: str) -> bool:
    left_lower = left.lower()
    right_lower = right.lower()
    for positive, negative in NEGATION_PAIRS:
        if (positive in left_lower and negative in right_lower) or (negative in left_lower and positive in right_lower):
            return True
    if ("not " in left_lower) ^ ("not " in right_lower):
        shared_tokens = set(left_lower.split()) & set(right_lower.split())
        if len(shared_tokens) >= 4:
            return True
    return False


def _looks_like_update(left: str, right: str) -> bool:
    markers = ("now", "updated", "revised", "changed", "instead", "no longer", "recently", "latest")
    left_lower = left.lower()
    return any(marker in left_lower for marker in markers)