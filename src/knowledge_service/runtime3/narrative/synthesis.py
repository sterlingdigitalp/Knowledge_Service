"""Agent F — generate editor-ready Story Objects."""

from __future__ import annotations

from typing import List, Sequence

from ..entities.resolver import EntityResolver
from ..models import StoryObject
from .headlines import generate_headline


class NarrativeSynthesizer:
    """Transform story graph nodes into editor-ready narratives."""

    def synthesize(self, stories: Sequence[StoryObject]) -> List[StoryObject]:
        enriched: List[StoryObject] = []
        for story in stories:
            enriched.append(self._enrich_story(story))
        return enriched

    def _enrich_story(self, story: StoryObject) -> StoryObject:
        groups = EntityResolver.group_by_type(story.entities)
        story.people = groups["people"]
        story.organizations = groups["organizations"]
        story.products = groups["products"]
        story.topics = groups["topics"]

        headline = generate_headline(
            story.entities,
            story.events,
            story.supporting_claims,
            story.story_type,
        )
        story.headline = headline
        story.title = headline

        lead_claims = sorted(story.supporting_claims, key=lambda claim: claim.confidence, reverse=True)
        lead = lead_claims[0] if lead_claims else None

        story.executive_summary = self._executive_summary(story, lead)
        story.what_happened = self._what_happened(story)
        story.why_it_matters = self._why_it_matters(story)
        story.future_watch = self._future_watch(story)
        story.editorial_notes = self._editorial_notes(story)
        story.summary = story.executive_summary
        story.evidence = [claim.claim_text for claim in lead_claims[:5]]
        story.contradictions = self._detect_contradictions(story.supporting_claims)
        return story

    def _executive_summary(self, story: StoryObject, lead) -> str:
        if not lead:
            return story.summary
        sources = ", ".join(story.supporting_sources[:3]) or "monitored sources"
        entity_hint = ""
        if story.people:
            entity_hint = f" involving {story.people[0]}"
        elif story.organizations:
            entity_hint = f" involving {story.organizations[0]}"
        return (
            f"{len(story.supporting_claims)} substantiated claims from {sources}{entity_hint}. "
            f"Lead signal: {lead.claim_text[:220]}"
        )

    def _what_happened(self, story: StoryObject) -> str:
        parts = []
        for claim in sorted(story.supporting_claims, key=lambda row: row.confidence, reverse=True)[:4]:
            source = f" ({claim.podcast_name})" if claim.podcast_name else ""
            parts.append(f"• {claim.claim_text}{source}")
        if story.events:
            parts.append(f"• Detected event: {story.events[0].title}")
        return "\n".join(parts)

    def _why_it_matters(self, story: StoryObject) -> str:
        factors = []
        if len(story.supporting_sources) > 1:
            factors.append(f"corroborated across {len(story.supporting_sources)} sources")
        if story.events:
            factors.append(f"anchored to {story.events[0].event_type.value.replace('_', ' ')} event")
        if story.people or story.organizations:
            names = (story.people + story.organizations)[:2]
            factors.append(f"involves key entities: {', '.join(names)}")
        factors.append(f"confidence {story.confidence:.0%}")
        return "This story matters because it is " + ", ".join(factors) + "."

    def _future_watch(self, story: StoryObject) -> str:
        if story.events:
            event = story.events[0]
            return f"Watch for follow-on {event.event_type.value.replace('_', ' ')} signals involving {event.title}."
        if story.organizations:
            return f"Monitor {story.organizations[0]} for confirming statements or third-source corroboration."
        return "Watch for additional independent sources to confirm this narrative."

    def _editorial_notes(self, story: StoryObject) -> str:
        notes = [f"Story type: {story.story_type.value}", f"Claims: {len(story.supporting_claims)}"]
        if story.contradictions:
            notes.append(f"Contradictions flagged: {len(story.contradictions)}")
        if len(story.episode_ids) > 1:
            notes.append("Multi-episode story — verify cross-source alignment.")
        return "; ".join(notes) + "."

    def _detect_contradictions(self, claims: Sequence) -> List[str]:
        contradictions: List[str] = []
        positives = ("will ", "increase", "grow", "expand", "rise", "bullish")
        negatives = ("won't", "will not", "decline", "fall", "drop", "bearish", "collapse")
        pos_claims = [claim for claim in claims if any(word in claim.claim_text.lower() for word in positives)]
        neg_claims = [claim for claim in claims if any(word in claim.claim_text.lower() for word in negatives)]
        if pos_claims and neg_claims:
            contradictions.append(
                f"Tension between optimistic ({pos_claims[0].claim_text[:80]}…) "
                f"and pessimistic ({neg_claims[0].claim_text[:80]}…) claims."
            )
        return contradictions