"""Semantic cluster engine — merge duplicate discussions into coherent topics."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set

from ..analyst.synthesis.models import IntelligenceItem
from ..intelligence.models import stable_id
from .config import IL2Config


@dataclass
class SemanticCluster:
    cluster_id: str
    member_ids: List[str] = field(default_factory=list)
    canonical_member_id: Optional[str] = None
    merged_keywords: Set[str] = field(default_factory=set)
    merged_entities: Set[str] = field(default_factory=set)
    similarity_score: float = 0.0


@dataclass
class ClusterResult:
    clusters: List[SemanticCluster]
    items: List[IntelligenceItem]
    duplicates_merged: int


def cluster_intelligence_items(
    items: Sequence[IntelligenceItem],
    config: Optional[IL2Config] = None,
) -> ClusterResult:
    """Merge near-duplicate intelligence items by title and entity overlap."""
    cfg = config or IL2Config()
    threshold = cfg.cluster_similarity_threshold
    working = list(items)
    clusters: List[SemanticCluster] = []
    assigned: Dict[str, str] = {}
    duplicates_merged = 0

    for index, item in enumerate(working):
        if item.item_id in assigned:
            continue
        cluster = SemanticCluster(
            cluster_id=stable_id("il2-cluster", item.item_id),
            member_ids=[item.item_id],
            canonical_member_id=item.item_id,
            merged_keywords=_tokenize(item.theme_label),
            merged_entities=set(_extract_entities(item)),
        )

        for other in working[index + 1:]:
            if other.item_id in assigned:
                continue
            score = _similarity(item, other)
            if score >= threshold:
                cluster.member_ids.append(other.item_id)
                cluster.merged_keywords.update(_tokenize(other.theme_label))
                cluster.merged_entities.update(_extract_entities(other))
                cluster.similarity_score = max(cluster.similarity_score, score)
                assigned[other.item_id] = cluster.cluster_id
                duplicates_merged += 1
                _merge_into_canonical(item, other)

        assigned[item.item_id] = cluster.cluster_id
        clusters.append(cluster)

    for item in working:
        cluster_id = assigned.get(item.item_id)
        if cluster_id:
            item.cluster_id = cluster_id

    return ClusterResult(clusters=clusters, items=working, duplicates_merged=duplicates_merged)


def _similarity(left: IntelligenceItem, right: IntelligenceItem) -> float:
    title_sim = _jaccard(_tokenize(left.title), _tokenize(right.title))
    theme_sim = _jaccard(_tokenize(left.theme_label), _tokenize(right.theme_label))
    entity_sim = _jaccard(set(_extract_entities(left)), set(_extract_entities(right)))
    source_overlap = 1.0 if set(left.sources) & set(right.sources) else 0.0
    return 0.35 * title_sim + 0.30 * theme_sim + 0.25 * entity_sim + 0.10 * source_overlap


def _merge_into_canonical(canonical: IntelligenceItem, duplicate: IntelligenceItem) -> None:
    """Boost canonical item with duplicate corroboration without changing Runtime 1 scores."""
    canonical.corroboration_count = max(canonical.corroboration_count, duplicate.corroboration_count)
    canonical.claim_count += duplicate.claim_count
    for source in duplicate.sources:
        if source not in canonical.sources:
            canonical.sources.append(source)
    for speaker in duplicate.speakers:
        if speaker not in canonical.speakers:
            canonical.speakers.append(speaker)


def _tokenize(text: str) -> Set[str]:
    tokens = re.findall(r"[a-z0-9]{3,}", text.lower())
    return set(tokens)


def _jaccard(left: Set[str], right: Set[str]) -> float:
    if not left and not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _extract_entities(item: IntelligenceItem) -> List[str]:
    entities: List[str] = []
    for evidence in item.supporting_evidence:
        for key in ("speaker", "source"):
            value = evidence.get(key)
            if value and str(value).lower() != "unknown":
                entities.append(str(value))
    entities.extend(item.speakers)
    entities.extend(item.sources)
    return entities