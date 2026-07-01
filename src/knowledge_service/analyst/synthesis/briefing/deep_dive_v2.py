"""Deep Dive v2 — expand Intelligence Items, not claims."""

from __future__ import annotations

from typing import List, Optional, Sequence

from ...models import Claim, ScoredClaim
from ..models import IntelligenceDeepDive, IntelligenceItem


class IntelligenceDeepDiveGenerator:
    """Research-analyst briefing for a single Intelligence Item."""

    def generate(
        self,
        intelligence_item_id: str,
        items: Sequence[IntelligenceItem],
        scored_claims: Sequence[ScoredClaim],
        all_claims: Sequence[Claim],
    ) -> Optional[IntelligenceDeepDive]:
        item = next((row for row in items if row.item_id == intelligence_item_id), None)
        if item is None:
            return None

        scored_by_id = {row.claim.claim_id: row for row in scored_claims}
        supporting = []
        timeline = []

        for claim_id in item.supporting_claim_ids:
            scored = scored_by_id.get(claim_id)
            claim = scored.claim if scored else next((c for c in all_claims if c.claim_id == claim_id), None)
            if claim is None:
                continue
            supporting.append({
                "claim_id": claim.claim_id,
                "speaker": claim.speaker,
                "source": claim.podcast_name,
                "claim_text": claim.claim_text,
                "evidence": claim.evidence,
                "timestamp_label": claim.timestamp_label,
                "novelty": scored.novelty.to_dict() if scored else None,
                "importance": scored.importance.to_dict() if scored else None,
            })
            timeline.append({
                "timestamp_label": claim.timestamp_label,
                "source": claim.podcast_name,
                "speaker": claim.speaker,
                "event": claim.claim_text[:120],
            })

        timeline.sort(key=lambda row: row.get("timestamp_label") or "")

        corroboration = [
            {
                "source": source,
                "speaker": speaker,
            }
            for source, speaker in zip(item.sources, item.speakers)
        ][:8]

        analyst_briefing = _analyst_briefing(item, supporting, corroboration)

        return IntelligenceDeepDive(
            intelligence_item_id=item.item_id,
            title=item.title,
            analyst_briefing=analyst_briefing,
            executive_summary=item.executive_summary,
            supporting_claims=supporting,
            historical_context=item.historical_developments,
            contradictions=item.contradictions,
            corroboration=corroboration,
            related_transcripts=[
                {
                    "source": citation.get("source"),
                    "speaker": citation.get("speaker"),
                    "timestamp_label": citation.get("timestamp_label"),
                    "url": citation.get("url"),
                }
                for citation in item.timestamped_citations
            ],
            timeline=timeline,
            timestamped_sources=item.timestamped_citations,
            theme_evolution=item.theme_evolution.to_dict() if item.theme_evolution else None,
            explainability={
                "why_surfaced": item.why_surfaced,
                "why_it_matters": item.why_it_matters,
                "novelty_score": item.novelty_score,
                "importance_score": item.importance_score,
                "confidence": item.confidence,
                "corroboration_count": item.corroboration_count,
                "claim_count": item.claim_count,
                "theme_id": item.theme_id,
                "cluster_id": item.cluster_id,
            },
        )


def _analyst_briefing(item: IntelligenceItem, supporting: List, corroboration: List) -> str:
    parts = [
        f"## {item.title}",
        f"{'★' * item.star_rating}{'☆' * (5 - item.star_rating)}",
        "",
        item.executive_summary,
        "",
        f"**Why surfaced:** {item.why_surfaced}",
        f"**Why it matters:** {item.why_it_matters}",
        f"**Confidence:** {item.confidence:.0%} | **Novelty:** {item.novelty_classification} | **Claims synthesized:** {item.claim_count}",
    ]
    if item.corroboration_count:
        parts.append(f"**Corroboration:** {item.corroboration_count} independent source(s).")
    if corroboration:
        names = ", ".join({row.get('speaker') or row.get('source') for row in corroboration if row.get('speaker') or row.get('source')})
        if names:
            parts.append(f"**Independent voices:** {names}.")
    if item.contradictions:
        parts.append(f"**Contradictions:** {len(item.contradictions)} conflicting position(s) require review.")
    if item.theme_evolution:
        parts.append(f"**Theme evolution:** {item.theme_evolution.state.value} — {item.theme_evolution.explanation}")
    parts.append(f"**Evidence base:** {len(supporting)} timestamped transcript citations attached.")
    return "\n".join(parts)