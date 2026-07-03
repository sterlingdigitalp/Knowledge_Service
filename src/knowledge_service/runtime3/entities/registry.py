"""Agent C — canonical entity registry with aliases."""

from __future__ import annotations

from typing import Dict, List, Sequence, Set

from ...intelligence.models import stable_id
from ..models import EntityType, ResolvedEntity, SemanticClaim
from ..thinking.models import CanonicalEntity, GraphEdge
from .canonical import CANONICAL_ALIASES, infer_entity_type, resolve_canonical
from .resolver import EntityResolver
from .stopwords import ENTITY_FALSE_POSITIVES, ENTITY_STOPWORDS


ENTITY_TYPE_MAP = {
    "person": EntityType.PERSON,
    "organization": EntityType.ORGANIZATION,
    "company": EntityType.COMPANY,
    "product": EntityType.PRODUCT,
    "technology": EntityType.TECHNOLOGY,
    "publication": EntityType.PUBLICATION,
    "place": EntityType.PLACE,
    "government": EntityType.ORGANIZATION,
    "research_lab": EntityType.ORGANIZATION,
    "university": EntityType.ORGANIZATION,
    "podcast": EntityType.PUBLICATION,
}


class EntityRegistry:
    """Build canonical entity graph from resolved mentions."""

    def __init__(self, watch_names: Sequence[str] | None = None):
        self.resolver = EntityResolver(watch_names)
        self._registry: Dict[str, CanonicalEntity] = {}

    def resolve_claims(self, claims: Sequence[SemanticClaim]) -> List[CanonicalEntity]:
        base_entities = self.resolver.resolve_claims(claims)
        for entity in base_entities:
            self._register(entity, claims)
        return list(self._registry.values())

    def _register(self, entity: ResolvedEntity, claims: Sequence[SemanticClaim]) -> CanonicalEntity:
        canonical = resolve_canonical(entity.canonical_name)
        if canonical:
            canonical_name, hinted_type = canonical
            entity_type = hinted_type
        else:
            canonical_name = entity.canonical_name
            entity_type = entity.entity_type

        entity_id = stable_id("centity", entity_type.value, canonical_name.lower())
        existing = self._registry.get(entity_id)
        sources = self._sources_for_entity(entity_id, claims)
        mentions = sum(1 for claim in claims if entity_id in claim.resolved_entity_ids)

        if existing:
            for alias in entity.aliases:
                if alias not in existing.aliases:
                    existing.aliases.append(alias)
            existing.mention_count += mentions
            existing.confidence = min(0.99, existing.confidence + 0.04)
            existing.source_ids = list(dict.fromkeys(existing.source_ids + sources))
            return existing

        record = CanonicalEntity(
            entity_id=entity_id,
            canonical_name=canonical_name,
            entity_type=entity_type,
            aliases=list(dict.fromkeys([entity.canonical_name, *entity.aliases])),
            confidence=entity.confidence,
            mention_count=mentions,
            source_ids=sources,
        )
        self._registry[entity_id] = record
        return record

    def _sources_for_entity(self, entity_id: str, claims: Sequence[SemanticClaim]) -> List[str]:
        sources: List[str] = []
        for claim in claims:
            if entity_id in claim.resolved_entity_ids and claim.podcast_name:
                sources.append(claim.podcast_name)
        return list(dict.fromkeys(sources))

    def build_cooccurrence_edges(self, claims: Sequence[SemanticClaim]) -> List[GraphEdge]:
        edges: List[GraphEdge] = []
        seen: Set[str] = set()
        for claim in claims:
            entity_ids = claim.resolved_entity_ids
            for i in range(len(entity_ids)):
                for j in range(i + 1, len(entity_ids)):
                    left, right = entity_ids[i], entity_ids[j]
                    key = f"{min(left, right)}:{max(left, right)}"
                    if key in seen:
                        continue
                    seen.add(key)
                    edges.append(GraphEdge(
                        source_id=left,
                        target_id=right,
                        edge_type="co_occurrence",
                        confidence=0.65,
                        metadata={"claim_id": claim.claim_id},
                    ))
        return edges

    @staticmethod
    def is_valid_name(name: str) -> bool:
        lower = name.strip().lower()
        if lower in ENTITY_STOPWORDS or lower in ENTITY_FALSE_POSITIVES:
            return False
        if len(name.strip()) < 3:
            return False
        return True