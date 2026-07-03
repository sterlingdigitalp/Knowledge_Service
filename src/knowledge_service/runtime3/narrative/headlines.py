"""Headline generation for Story Objects."""

from __future__ import annotations

import re
from typing import Sequence

from ..models import DetectedEvent, ResolvedEntity, SemanticClaim, StoryType


TOPIC_HEADLINE_PATTERNS = [
    (re.compile(r"\bbyzantine|east roman|constantine|476\b", re.I), "Byzantine Empire Historical Analysis"),
    (re.compile(r"\bdark\s+matter\b", re.I), "Dark Matter Detection Debate"),
    (re.compile(r"\bcalifornia.*(?:ag|attorney\s+general)|swalwell|porter|becerra\b", re.I), "California AG Race Dynamics"),
    (re.compile(r"\b(?:coding\s+agents|rlvr|enterprise\s+ai|workplace\s+knowledge)\b", re.I), "Enterprise AI Agent Advances"),
    (re.compile(r"\bhuawei|glm[- ]?5\b", re.I), "Huawei GLM-5 Chip Supply Chain"),
    (re.compile(r"\bai\s+(?:agent|model|lab)\b", re.I), "AI Industry Developments"),
    (re.compile(r"\belection|ballot|polls?\b", re.I), "Election and Polling Developments"),
    (re.compile(r"\bnate\s+silver\b", re.I), "Nate Silver Political Forecasting"),
]


def generate_headline(
    entities: Sequence[ResolvedEntity],
    events: Sequence[DetectedEvent],
    claims: Sequence[SemanticClaim],
    story_type: StoryType,
) -> str:
    combined_text = " ".join(claim.claim_text for claim in claims[:5])
    for pattern, headline in TOPIC_HEADLINE_PATTERNS:
        if pattern.search(combined_text):
            return headline

    if events and entities:
        primary = entities[0].canonical_name
        event_word = events[0].event_type.value.replace("_", " ")
        return f"{primary}: {event_word.title()}"

    if len(entities) >= 2:
        return f"{entities[0].canonical_name} and {entities[1].canonical_name}"

    if entities:
        suffix = {
            StoryType.SCIENCE: "Research Update",
            StoryType.POLICY: "Policy Developments",
            StoryType.TECHNOLOGY: "Technology Update",
            StoryType.BUSINESS: "Business Developments",
            StoryType.CULTURE: "Historical Analysis",
        }.get(story_type, "Developments")
        return f"{entities[0].canonical_name} {suffix}"

    lead = max(claims, key=lambda claim: claim.confidence) if claims else None
    if lead:
        words = lead.claim_text.split()
        if len(words) > 8:
            return " ".join(words[:7]) + "…"
        return lead.claim_text[:72]

    return "Emerging Intelligence Signal"