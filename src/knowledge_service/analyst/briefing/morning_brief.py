"""Morning Intelligence Brief — ~60 second attention filter."""

from __future__ import annotations

from typing import Dict, List, Sequence

from ...intelligence.models import IntelligenceProfile, now_iso, stable_id
from ..models import BriefItem, ImportanceBand, MorningBrief, NoveltyClass, ScoredClaim


MAX_ITEMS_PER_SECTION = 2
WORDS_PER_SECOND = 3.0
MIN_RELEVANCE = 0.2
MIN_IMPORTANCE = 0.35


class MorningBriefGenerator:
    """Generate profile-organized morning intelligence from scored claims."""

    def generate(
        self,
        scored_claims: Sequence[ScoredClaim],
        profiles: Sequence[IntelligenceProfile],
        pipeline_run_id: str = "",
    ) -> MorningBrief:
        profile_order = [profile.name for profile in profiles if profile.enabled]
        if not profile_order:
            profile_order = ["AI", "Investing", "Founders", "Longevity"]

        sections: Dict[str, List[BriefItem]] = {name: [] for name in profile_order}
        used_claims: set[str] = set()

        for profile in profiles:
            if not profile.enabled:
                continue
            candidates = []
            for item in scored_claims:
                if item.claim.claim_id in used_claims:
                    continue
                if item.novelty.classification == NoveltyClass.REPEAT:
                    continue
                if item.importance.band == ImportanceBand.IGNORE:
                    continue
                if item.importance.score < MIN_IMPORTANCE:
                    continue

                profile_relevance = next(
                    (rel for rel in item.relevance if rel.profile_id == profile.profile_id),
                    None,
                )
                if not profile_relevance or profile_relevance.score < MIN_RELEVANCE:
                    continue
                candidates.append((item, profile_relevance))

            candidates.sort(key=lambda pair: pair[0].importance.score, reverse=True)
            for item, profile_relevance in candidates[:MAX_ITEMS_PER_SECTION]:
                brief_item = _to_brief_item(item, profile_relevance)
                sections[profile.name].append(brief_item)
                used_claims.add(item.claim.claim_id)

        total_items = sum(len(items) for items in sections.values())
        word_count = sum(
            len(item.headline.split()) + len(item.what_is_new.split()) + len(item.why_it_matters.split())
            for items in sections.values()
            for item in items
        )
        reading_time = max(30, min(90, int(word_count / WORDS_PER_SECOND)))

        return MorningBrief(
            brief_id=stable_id("brief", now_iso()),
            generated_at=now_iso(),
            reading_time_seconds=reading_time,
            sections=sections,
            total_items=total_items,
            pipeline_run_id=pipeline_run_id,
        )


def _to_brief_item(item: ScoredClaim, profile_relevance) -> BriefItem:
    claim = item.claim
    matched = []
    if profile_relevance.matched_interests:
        matched.extend(profile_relevance.matched_interests)
    if profile_relevance.matched_participants:
        matched.extend(profile_relevance.matched_participants)
    if claim.topic and claim.topic not in matched:
        matched.append(claim.topic)

    corroborated = item.corroboration_count
    headline = _headline(claim)
    what_is_new = _what_is_new(item)
    why_see = f"Matched: {', '.join(matched[:5])}" if matched else profile_relevance.explanation
    why_matters = _why_matters(item)
    evidence = f"{claim.speaker} at {claim.timestamp_label}: \"{claim.evidence[:180]}\""

    return BriefItem(
        item_id=stable_id("brief-item", claim.claim_id, profile_relevance.profile_id),
        profile_id=profile_relevance.profile_id,
        profile_name=profile_relevance.profile_name,
        headline=headline,
        what_is_new=what_is_new,
        why_you_see_this=why_see,
        why_it_matters=why_matters,
        evidence_summary=evidence,
        timestamp_label=claim.timestamp_label,
        source=claim.podcast_name or claim.source_id,
        source_url=claim.transcript_reference or claim.source_url,
        claim_id=claim.claim_id,
        importance_score=item.importance.score,
        importance_band=item.importance.band.value,
        novelty_score=item.novelty.score,
        novelty_classification=item.novelty.classification.value,
        matched_interests=profile_relevance.matched_interests,
        matched_participants=profile_relevance.matched_participants,
        corroborated_by=corroborated,
        explainability={
            "matched": matched,
            "novelty": item.novelty.classification.value,
            "importance": item.importance.band.value,
            "corroborated_by": corroborated,
            "evidence_type": "timestamped_transcript",
            "importance_factors": item.importance.factors.to_dict(),
            "novelty_explanation": item.novelty.explanation,
        },
    )


def _headline(claim) -> str:
    text = claim.claim_text.strip()
    if len(text) <= 90:
        return text
    return text[:87].rsplit(" ", 1)[0] + "..."


def _what_is_new(item: ScoredClaim) -> str:
    classification = item.novelty.classification.value
    if classification == "new":
        return f"New claim from {item.claim.speaker}: {item.novelty.explanation}"
    if classification == "contradiction":
        return f"Conflicting position surfaced: {item.novelty.explanation}"
    return f"{classification.title()} of prior knowledge: {item.novelty.explanation}"


def _why_matters(item: ScoredClaim) -> str:
    parts = [item.importance.explanation]
    if item.corroboration_count:
        parts.append(f"Corroborated by {item.corroboration_count} additional trusted source(s).")
    if item.contradictions:
        parts.append("Contradiction flagged — review both positions.")
    return " ".join(parts)