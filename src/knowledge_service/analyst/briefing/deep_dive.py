"""Interactive Deep Dive — evidence-backed analyst briefing."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from ...retrieval.embedding import cosine_similarity, embed_text
from ..models import Claim, DeepDiveResponse, ScoredClaim


class DeepDiveGenerator:
    """Generate analyst-style deep dives for brief items."""

    def generate(
        self,
        claim_id: str,
        scored_claims: Sequence[ScoredClaim],
        all_claims: Sequence[Claim],
    ) -> Optional[DeepDiveResponse]:
        scored = next((item for item in scored_claims if item.claim.claim_id == claim_id), None)
        if scored is None:
            claim = next((item for item in all_claims if item.claim_id == claim_id), None)
            if claim is None:
                return None
            return self._minimal_response(claim)

        claim = scored.claim
        embedding = claim.embedding or embed_text(claim.claim_text)

        related = []
        for item in all_claims:
            if item.claim_id == claim.claim_id:
                continue
            other_embedding = item.embedding or embed_text(item.claim_text)
            similarity = cosine_similarity(embedding, other_embedding)
            if similarity >= 0.45:
                related.append({
                    "claim_id": item.claim_id,
                    "speaker": item.speaker,
                    "source": item.podcast_name,
                    "similarity": round(similarity, 4),
                    "claim_text": item.claim_text[:240],
                    "timestamp_label": item.timestamp_label,
                })
        related.sort(key=lambda row: row["similarity"], reverse=True)

        corroborating = [
            row for row in related
            if row["source"] != claim.podcast_name and row["similarity"] >= 0.55
        ][:5]

        contradictory = [
            {
                "claim_id": c.prior_claim_id,
                "explanation": c.explanation,
                "prior_claim_text": c.prior_claim_text[:240],
                "similarity": c.similarity,
            }
            for c in scored.contradictions
        ]

        previous = [
            {
                "claim_id": item.claim_id,
                "speaker": item.speaker,
                "source": item.podcast_name,
                "timestamp_label": item.timestamp_label,
                "claim_text": item.claim_text[:200],
            }
            for item in all_claims
            if item.claim_id != claim.claim_id
            and item.speaker == claim.speaker
            and item.topic == claim.topic
        ][:5]

        top_relevance = max(scored.relevance, key=lambda item: item.score) if scored.relevance else None
        analyst_summary = _analyst_summary(scored, top_relevance, corroborating, contradictory)

        return DeepDiveResponse(
            claim_id=claim.claim_id,
            headline=claim.claim_text[:120],
            analyst_summary=analyst_summary,
            transcript_excerpt=claim.evidence,
            surrounding_context=claim.supporting_context,
            previous_appearances=previous,
            related_claims=related[:8],
            corroborating_evidence=corroborating,
            contradictory_evidence=contradictory,
            timestamped_sources=[{
                "source": claim.podcast_name,
                "speaker": claim.speaker,
                "timestamp_label": claim.timestamp_label,
                "url": claim.transcript_reference or claim.source_url,
            }],
            explainability={
                "novelty": scored.novelty.to_dict(),
                "importance": scored.importance.to_dict(),
                "relevance": [item.to_dict() for item in scored.relevance],
                "corroboration_count": scored.corroboration_count,
                "cluster_id": scored.corroboration_cluster_id,
            },
        )

    def _minimal_response(self, claim: Claim) -> DeepDiveResponse:
        return DeepDiveResponse(
            claim_id=claim.claim_id,
            headline=claim.claim_text[:120],
            analyst_summary=f"{claim.speaker} stated: {claim.claim_text}",
            transcript_excerpt=claim.evidence,
            surrounding_context=claim.supporting_context,
            previous_appearances=[],
            related_claims=[],
            corroborating_evidence=[],
            contradictory_evidence=[],
            timestamped_sources=[{
                "source": claim.podcast_name,
                "speaker": claim.speaker,
                "timestamp_label": claim.timestamp_label,
                "url": claim.transcript_reference or claim.source_url,
            }],
            explainability={},
        )


def _analyst_summary(scored, top_relevance, corroborating, contradictory) -> str:
    claim = scored.claim
    parts = [
        f"{claim.speaker} ({claim.podcast_name}, {claim.timestamp_label}) asserts: {claim.claim_text}",
        f"Novelty: {scored.novelty.classification.value} ({scored.novelty.score:.2f}). {scored.novelty.explanation}",
        f"Importance: {scored.importance.band.value} ({scored.importance.score:.2f}).",
    ]
    if top_relevance:
        parts.append(f"Profile relevance ({top_relevance.profile_name}): {top_relevance.explanation}")
    if corroborating:
        sources = ", ".join({row['source'] for row in corroborating})
        parts.append(f"Independent corroboration from: {sources}.")
    if contradictory:
        parts.append("Contradictory prior positions exist — compare evidence before acting.")
    return " ".join(parts)