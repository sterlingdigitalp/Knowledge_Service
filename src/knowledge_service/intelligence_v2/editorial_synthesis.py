"""Editorial synthesis — analyst brief cards from evidence."""

from __future__ import annotations

import re
from typing import List, Sequence

from ..analyst.synthesis.models import IntelligenceItem
from .canonical_resolver import UNRESOLVED, ResolutionResult, resolve_canonical_title
from .models import AnalystBriefCard


def synthesize_brief_card(
    item: IntelligenceItem,
    resolution: ResolutionResult,
) -> AnalystBriefCard:
    """Generate a full analyst brief card from an intelligence item."""
    excerpts = [row.get("excerpt", "") for row in item.supporting_evidence if row.get("excerpt")]
    keywords = _extract_keywords(item)
    speakers = [s for s in item.speakers if s and s.lower() != "unknown"]
    sources = list(item.sources[:3])

    what_happened = _what_happened(item, excerpts, speakers, sources)
    why_matters = _why_it_matters(item, excerpts)
    confidence_explanation = _confidence_explanation(item, speakers, sources)
    what_to_watch = _what_to_watch(item)
    suggested_action = _suggested_action(item, resolution.canonical_topic)
    executive = _executive_summary(resolution, what_happened, why_matters)

    return AnalystBriefCard(
        title=resolution.canonical_title,
        executive_summary=executive,
        what_happened=what_happened,
        why_it_matters=why_matters,
        evidence=list(item.supporting_evidence[:6]),
        confidence=item.confidence,
        confidence_explanation=confidence_explanation,
        contradictions=list(item.contradictions[:5]),
        what_to_watch=what_to_watch,
        suggested_action=suggested_action,
        supporting_sources=list(item.sources[:8]),
        canonical_topic=resolution.canonical_topic,
        original_title=item.title,
        cluster_id=item.cluster_id,
        failure_modes=list(resolution.failure_modes),
        item_id=item.item_id,
    )


def synthesize_from_item(item: IntelligenceItem) -> AnalystBriefCard:
    """End-to-end card synthesis including canonical resolution."""
    excerpts = [row.get("excerpt", "") for row in item.supporting_evidence if row.get("excerpt")]
    keywords = _extract_keywords(item)
    resolution = resolve_canonical_title(
        raw_title=item.title,
        keywords=keywords,
        entities=[s for s in item.speakers if s],
        claim_excerpts=excerpts or [item.executive_summary],
        sources=item.sources,
    )
    card = synthesize_brief_card(item, resolution)
    card.confidence = resolution.confidence if resolution.publishable else item.confidence
    return card


def apply_card_to_item(item: IntelligenceItem, card: AnalystBriefCard) -> IntelligenceItem:
    """Write IL2 editorial output back onto Runtime 1 intelligence item."""
    if card.title == UNRESOLVED:
        return item
    item.title = card.title
    item.theme_label = card.canonical_topic
    item.executive_summary = card.executive_summary
    item.why_it_matters = card.why_it_matters
    item.why_surfaced = (
        f"IL2: {card.canonical_topic}. "
        f"{card.what_happened[:160]}"
    )
    return item


def _extract_keywords(item: IntelligenceItem) -> List[str]:
    tokens: List[str] = []
    for part in (item.theme_label, item.why_surfaced):
        for word in part.replace(",", " ").split():
            cleaned = word.strip(".")
            if len(cleaned) >= 4:
                tokens.append(cleaned)
    return tokens[:12]


def _what_happened(
    item: IntelligenceItem,
    excerpts: Sequence[str],
    speakers: Sequence[str],
    sources: Sequence[str],
) -> str:
    lead = _clean_excerpt(excerpts[0]) if excerpts else ""
    if not lead:
        return "No substantive transcript evidence available for this signal."

    source_line = ", ".join(sources) if sources else "monitored podcasts"
    speaker_line = ", ".join(speakers[:2]) if speakers else "multiple voices"
    return (
        f"{speaker_line} on {source_line} discussed: {lead[:240]}"
    )


def _why_it_matters(item: IntelligenceItem, excerpts: Sequence[str]) -> str:
    parts: List[str] = []
    if item.contradiction_count:
        parts.append("Competing viewpoints surfaced — compare sources before acting.")
    elif item.corroboration_count >= 2:
        parts.append("Several monitored sources raised the same theme.")
    elif excerpts:
        parts.append("A new angle appeared in the monitored corpus.")

    if item.profile_names:
        parts.append(f"Relevant to {item.profile_names[0]} monitoring.")
    return " ".join(parts) if parts else "Track for follow-on commentary."


def _confidence_explanation(
    item: IntelligenceItem,
    speakers: Sequence[str],
    sources: Sequence[str],
) -> str:
    return (
        f"Based on {item.claim_count} claims across {len(sources) or 1} source(s)"
        f"{f' with {len(speakers)} named speaker(s)' if speakers else ''}."
    )


def _what_to_watch(item: IntelligenceItem) -> str:
    if item.contradictions:
        return "Watch whether leading voices reconcile or harden opposing positions."
    if item.corroboration_count >= 2:
        return "Watch for policy, product, or funding follow-through."
    return "Watch for a second independent source to confirm the thesis."


def _suggested_action(item: IntelligenceItem, topic: str) -> str:
    profile = item.profile_names[0] if item.profile_names else "your monitored domain"
    if item.contradiction_count:
        return f"Compare primary sources on {topic} before updating {profile} assumptions."
    if item.importance_band in {"very_high", "high"}:
        return f"Add {topic} to this week's {profile} review queue."
    return f"Monitor {topic}; no immediate action required."


def _executive_summary(
    resolution: ResolutionResult,
    what_happened: str,
    why_matters: str,
) -> str:
    if not resolution.publishable:
        return what_happened
    return f"{resolution.canonical_title}: {what_happened} {why_matters}"


def _clean_excerpt(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    return cleaned