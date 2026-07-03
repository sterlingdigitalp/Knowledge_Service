"""Entity resolution and normalization for IL2."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Set


ENTITY_ALIASES: Dict[str, str] = {
    "open ai": "OpenAI",
    "openai": "OpenAI",
    "gpt": "GPT",
    "nvidia": "NVIDIA",
    "mercury": "Mercury",
    "figure ai": "Figure AI",
    "figure": "Figure AI",
    "anthropic": "Anthropic",
    "karpathy": "Andrej Karpathy",
    "altman": "Sam Altman",
    "roman empire": "Byzantine Empire",
    "east roman empire": "Byzantine Empire",
}

STOP_ENTITIES = frozenset({
    "unknown", "multiple", "monitored", "voices", "speaker", "source", "evidence",
    "speakers", "fork", "hard", "podcast", "test",
})


def normalize_entity(raw: str) -> str:
    cleaned = re.sub(r"\s+", " ", raw.strip())
    if not cleaned:
        return ""
    key = cleaned.lower()
    if key in ENTITY_ALIASES:
        return ENTITY_ALIASES[key]
    if cleaned.isupper() and len(cleaned) <= 6:
        return cleaned
    return cleaned.title() if cleaned.islower() else cleaned


def resolve_entities(
    explicit: Iterable[str],
    evidence_texts: Iterable[str],
) -> List[str]:
    """Merge explicit entities with entities discovered in evidence."""
    found: List[str] = []
    seen: Set[str] = set()

    for entity in explicit:
        normalized = normalize_entity(entity)
        if normalized and normalized.lower() not in STOP_ENTITIES:
            key = normalized.lower()
            if key not in seen:
                seen.add(key)
                found.append(normalized)

    haystack = " ".join(evidence_texts).lower()
    for alias, canonical in ENTITY_ALIASES.items():
        if alias in haystack and canonical.lower() not in seen:
            seen.add(canonical.lower())
            found.append(canonical)

    return found[:8]


def primary_entity(entities: List[str]) -> str:
    return entities[0] if entities else ""