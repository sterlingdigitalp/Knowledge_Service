"""Contradiction detection — surface conflicts instead of hiding them."""

from __future__ import annotations

from typing import List, Sequence

from ..models import Claim, Contradiction, NoveltyClass, NoveltyResult
from ..novelty.engine import _has_contradiction
from ...retrieval.embedding import cosine_similarity, embed_text


class ContradictionDetector:
    """Identify conflicting, updated, or reversed claims."""

    def detect(self, claim: Claim, novelty: NoveltyResult, historical: Sequence[Claim]) -> List[Contradiction]:
        if novelty.classification != NoveltyClass.CONTRADICTION or not novelty.prior_claim_id:
            return []

        prior = next((item for item in historical if item.claim_id == novelty.prior_claim_id), None)
        if prior is None:
            return []

        return [Contradiction(
            claim_id=claim.claim_id,
            prior_claim_id=prior.claim_id,
            explanation=(
                f"{claim.speaker} ({claim.podcast_name}) appears to contradict "
                f"prior statement by {prior.speaker} ({prior.podcast_name})."
            ),
            similarity=novelty.prior_similarity or 0.0,
            claim_text=claim.claim_text,
            prior_claim_text=prior.claim_text,
        )]

    def scan_corpus(self, claims: Sequence[Claim]) -> List[Contradiction]:
        contradictions: List[Contradiction] = []
        for index, claim in enumerate(claims):
            embedding = claim.embedding or embed_text(claim.claim_text)
            for prior in claims[:index]:
                if prior.episode_id == claim.episode_id:
                    continue
                prior_embedding = prior.embedding or embed_text(prior.claim_text)
                similarity = cosine_similarity(embedding, prior_embedding)
                if similarity >= 0.55 and _has_contradiction(claim.claim_text, prior.claim_text):
                    contradictions.append(Contradiction(
                        claim_id=claim.claim_id,
                        prior_claim_id=prior.claim_id,
                        explanation=(
                            f"Potential contradiction between {claim.speaker} and {prior.speaker} "
                            f"on related topic ({claim.topic})."
                        ),
                        similarity=round(similarity, 4),
                        claim_text=claim.claim_text,
                        prior_claim_text=prior.claim_text,
                    ))
        return contradictions