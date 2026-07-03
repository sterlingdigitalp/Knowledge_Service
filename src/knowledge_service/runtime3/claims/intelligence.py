"""Agent B — enriched claim intelligence."""

from __future__ import annotations

from typing import List, Sequence

from ..models import ClaimType, SemanticClaim
from ..thinking.models import EnrichedClaim

PODCAST_QUALITY = {
    "Dwarkesh Podcast": 0.92,
    "Lex Fridman Podcast": 0.90,
    "All-In Podcast": 0.88,
    "Hard Fork": 0.87,
    "The Peter Attia Drive": 0.85,
    "Founders": 0.84,
    "Latent Space": 0.86,
    "No Priors": 0.85,
}

CERTAINTY_BY_TYPE = {
    ClaimType.FACTUAL: 0.82,
    ClaimType.QUOTE: 0.78,
    ClaimType.ANALYSIS: 0.70,
    ClaimType.OPINION: 0.55,
    ClaimType.PREDICTION: 0.48,
    ClaimType.META: 0.20,
    ClaimType.SPONSOR: 0.0,
}


class ClaimIntelligenceEngine:
    """Enrich extracted claims with certainty, source quality, and neighbors."""

    def enrich(self, claims: Sequence[SemanticClaim]) -> List[EnrichedClaim]:
        claim_list = list(claims)
        enriched: List[EnrichedClaim] = []
        for index, claim in enumerate(claim_list):
            neighbors = self._find_neighbors(claim, claim_list, index)
            source_quality = PODCAST_QUALITY.get(claim.podcast_name, 0.72)
            certainty = self._certainty(claim, source_quality)
            enriched.append(EnrichedClaim(
                claim_id=claim.claim_id,
                claim_text=claim.claim_text,
                claim_type=claim.claim_type,
                confidence=claim.confidence,
                segment_type=claim.segment_type,
                speaker=claim.speaker,
                entities=list(claim.entities),
                resolved_entity_ids=list(claim.resolved_entity_ids),
                event_references=list(claim.event_references),
                supporting_sentences=list(claim.supporting_sentences),
                episode_id=claim.episode_id,
                podcast_name=claim.podcast_name,
                source_url=claim.source_url,
                timestamp_start=claim.timestamp_start,
                timestamp_label=claim.timestamp_label,
                segment_id=claim.segment_id,
                embedding=list(claim.embedding),
                certainty=certainty,
                source_quality=source_quality,
                neighbor_claim_ids=[neighbor.claim_id for neighbor in neighbors],
                neighbor_relationship=self._neighbor_relationship(claim, neighbors),
                evidence_strength=round(certainty * source_quality * claim.confidence, 3),
            ))
        return enriched

    def _certainty(self, claim: SemanticClaim, source_quality: float) -> float:
        base = CERTAINTY_BY_TYPE.get(claim.claim_type, 0.60)
        length_bonus = min(0.10, len(claim.claim_text) / 500.0)
        entity_bonus = min(0.08, len(claim.resolved_entity_ids) * 0.02)
        return round(min(0.99, base * 0.7 + source_quality * 0.2 + length_bonus + entity_bonus), 3)

    def _find_neighbors(
        self,
        claim: SemanticClaim,
        claims: Sequence[SemanticClaim],
        index: int,
        window: int = 2,
    ) -> List[SemanticClaim]:
        neighbors: List[SemanticClaim] = []
        for offset in range(1, window + 1):
            if index - offset >= 0:
                candidate = claims[index - offset]
                if candidate.episode_id == claim.episode_id:
                    neighbors.append(candidate)
            if index + offset < len(claims):
                candidate = claims[index + offset]
                if candidate.episode_id == claim.episode_id:
                    neighbors.append(candidate)
        return neighbors

    def _neighbor_relationship(
        self,
        claim: SemanticClaim,
        neighbors: Sequence[SemanticClaim],
    ) -> str:
        if not neighbors:
            return "isolated"
        shared_entities = set(claim.resolved_entity_ids)
        for neighbor in neighbors:
            if shared_entities & set(neighbor.resolved_entity_ids):
                return "supports_same_topic"
        if claim.claim_type == ClaimType.PREDICTION:
            return "speculative_chain"
        return "sequential"