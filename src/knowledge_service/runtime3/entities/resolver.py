"""Agent C — entity extraction and canonical resolution."""

from __future__ import annotations

import re
from typing import Dict, List, Sequence, Set

from ...intelligence.models import stable_id
from ..models import EntityType, ResolvedEntity, SemanticClaim
from .canonical import infer_entity_type, resolve_canonical
from .stopwords import ENTITY_FALSE_POSITIVES, ENTITY_STOPWORDS

ENTITY_RE = re.compile(
    r"\b("
    r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}"
    r"|(?:GPT|GLM|RLVR|AI|LLM)-?\d*"
    r"|\$[\d,.]+[BMK]?"
    r")\b",
)
PROPER_NOUN_PHRASE_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+(?:of|and|the)\s+)?(?:[A-Z][a-z]+){0,3})\b",
)
KNOWN_MULTI_WORD = [
    "East Roman Empire", "Byzantine Empire", "Roman Empire", "Dark Matter",
    "Coding Agents", "Enterprise AI", "AI Agents", "New York Times",
    "Eric Swalwell", "Katie Porter", "Xavier Becerra", "Nate Silver",
    "Gavin Newsom", "Grant Sanderson", "Lex Fridman", "All-In Podcast",
    "California AG", "International Math Olympiad",
]


class EntityResolver:
    """Extract and resolve entities from semantic claims."""

    def __init__(self, watch_names: Sequence[str] | None = None):
        self.watch_names = list(watch_names or [])

    def resolve_claims(self, claims: Sequence[SemanticClaim]) -> List[ResolvedEntity]:
        registry: Dict[str, ResolvedEntity] = {}
        for claim in claims:
            extracted = self._extract_from_text(claim.claim_text)
            for watch_name in self.watch_names:
                if watch_name.lower() in claim.claim_text.lower():
                    extracted.add(watch_name)
            claim.entities = sorted(extracted)
            claim.resolved_entity_ids = []
            for name in extracted:
                entity = self._resolve_name(name, registry)
                registry[entity.entity_id] = entity
                claim.resolved_entity_ids.append(entity.entity_id)
        return list(registry.values())

    def _extract_from_text(self, text: str) -> Set[str]:
        found: Set[str] = set()
        for phrase in KNOWN_MULTI_WORD:
            if phrase.lower() in text.lower():
                found.add(phrase)
        for match in PROPER_NOUN_PHRASE_RE.findall(text):
            if self._is_valid_entity(match):
                found.add(match.strip())
        for match in ENTITY_RE.findall(text):
            if self._is_valid_entity(match):
                found.add(match.strip())
        return found

    def _is_valid_entity(self, name: str) -> bool:
        cleaned = name.strip()
        if len(cleaned) < 3:
            return False
        lower = cleaned.lower()
        if lower in ENTITY_STOPWORDS:
            return False
        if lower in ENTITY_FALSE_POSITIVES:
            return False
        words = cleaned.split()
        if all(word.lower() in ENTITY_STOPWORDS for word in words):
            return False
        if len(words) == 1 and words[0].lower() in ENTITY_FALSE_POSITIVES:
            return False
        return True

    def _resolve_name(self, name: str, registry: Dict[str, ResolvedEntity]) -> ResolvedEntity:
        canonical = resolve_canonical(name)
        if canonical:
            canonical_name, entity_type = canonical
        else:
            canonical_name = name.strip()
            entity_type = infer_entity_type(canonical_name)

        entity_id = stable_id("entity", entity_type.value, canonical_name.lower())
        existing = registry.get(entity_id)
        if existing:
            if name not in existing.aliases:
                existing.aliases.append(name)
            existing.confidence = min(0.99, existing.confidence + 0.05)
            return existing

        return ResolvedEntity(
            entity_id=entity_id,
            canonical_name=canonical_name,
            entity_type=entity_type,
            aliases=[name] if name != canonical_name else [],
            confidence=0.72,
        )

    @staticmethod
    def group_by_type(entities: Sequence[ResolvedEntity]) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = {
            "people": [],
            "organizations": [],
            "products": [],
            "topics": [],
        }
        for entity in entities:
            if entity.entity_type == EntityType.PERSON:
                groups["people"].append(entity.canonical_name)
            elif entity.entity_type in {EntityType.ORGANIZATION, EntityType.COMPANY}:
                groups["organizations"].append(entity.canonical_name)
            elif entity.entity_type in {EntityType.PRODUCT, EntityType.TECHNOLOGY}:
                if entity.entity_type == EntityType.PRODUCT:
                    groups["products"].append(entity.canonical_name)
                else:
                    groups["topics"].append(entity.canonical_name)
            else:
                groups["topics"].append(entity.canonical_name)
        return groups