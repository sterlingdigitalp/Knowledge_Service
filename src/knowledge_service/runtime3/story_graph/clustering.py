"""Story clustering utilities."""

from __future__ import annotations

import re
from typing import List, Sequence, Set

from ...retrieval.embedding import cosine_similarity, tokenize
from ..models import DetectedEvent, ResolvedEntity, SemanticClaim

LEXICAL_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "as", "is", "was", "are", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "that", "this", "these", "those", "it", "its", "they", "them", "their", "we", "you",
    "i", "he", "she", "his", "her", "my", "your", "our", "not", "no", "so", "if", "just",
    "like", "about", "into", "than", "then", "there", "when", "what", "which", "who",
    "how", "all", "also", "very", "can", "get", "got", "one", "way", "make", "say", "said",
    "because", "really", "going", "think", "know", "mean", "better", "getting", "through",
})


def shared_entity_score(left: SemanticClaim, right: SemanticClaim) -> float:
    left_set = set(left.resolved_entity_ids)
    right_set = set(right.resolved_entity_ids)
    if not left_set or not right_set:
        return 0.0
    overlap = len(left_set & right_set)
    union = len(left_set | right_set)
    return overlap / union if union else 0.0


def shared_event_score(left: SemanticClaim, right: SemanticClaim) -> float:
    left_set = set(left.event_references)
    right_set = set(right.event_references)
    if not left_set or not right_set:
        return 0.0
    overlap = len(left_set & right_set)
    return 1.0 if overlap else 0.0


def lexical_overlap_score(left: SemanticClaim, right: SemanticClaim) -> float:
    left_tokens = {token for token in tokenize(left.claim_text) if token not in LEXICAL_STOPWORDS and len(token) > 2}
    right_tokens = {token for token in tokenize(right.claim_text) if token not in LEXICAL_STOPWORDS and len(token) > 2}
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return overlap / union if union else 0.0


def shared_phrase_score(left: SemanticClaim, right: SemanticClaim) -> float:
    phrases = [
        "coding agents", "dark matter", "roman empire", "east roman", "byzantine",
        "california", "attorney general", "enterprise ai", "rlvr", "glm-5", "huawei",
        "swalwell", "porter", "becerra", "constantine", "election", "workplace knowledge",
    ]
    left_lower = left.claim_text.lower()
    right_lower = right.claim_text.lower()
    shared = sum(1 for phrase in phrases if phrase in left_lower and phrase in right_lower)
    return min(1.0, shared * 0.35)


def claim_similarity(
    left: SemanticClaim,
    right: SemanticClaim,
    *,
    threshold: float,
) -> float:
    embedding_sim = cosine_similarity(left.embedding, right.embedding)
    entity_sim = shared_entity_score(left, right)
    event_sim = shared_event_score(left, right)
    lexical_sim = lexical_overlap_score(left, right)
    phrase_sim = shared_phrase_score(left, right)
    same_episode = 0.12 if left.episode_id and left.episode_id == right.episode_id else 0.0
    same_podcast = 0.05 if left.podcast_name and left.podcast_name == right.podcast_name else 0.0
    score = (
        0.20 * embedding_sim
        + 0.22 * entity_sim
        + 0.12 * event_sim
        + 0.28 * lexical_sim
        + 0.18 * phrase_sim
        + same_episode
        + same_podcast
    )
    return score if score >= threshold else 0.0


def _candidate_clusters(claim: SemanticClaim, clusters: Sequence[List[SemanticClaim]]) -> List[int]:
    """Limit comparisons using shared entities and episodes."""
    if not clusters:
        return []
    claim_entities = set(claim.resolved_entity_ids)
    candidates: List[int] = []
    for index, cluster in enumerate(clusters):
        rep = cluster[0]
        if claim.episode_id and rep.episode_id == claim.episode_id:
            candidates.append(index)
            continue
        rep_entities = set(rep.resolved_entity_ids)
        if claim_entities and rep_entities and (claim_entities & rep_entities):
            candidates.append(index)
            continue
        if claim.podcast_name and rep.podcast_name == claim.podcast_name:
            candidates.append(index)
    return candidates or list(range(min(len(clusters), 24)))


def cluster_claims(
    claims: Sequence[SemanticClaim],
    *,
    threshold: float = 0.38,
    min_cluster_size: int = 2,
    max_claims: int = 800,
) -> List[List[SemanticClaim]]:
    """Greedy clustering of claims into story candidates."""
    if not claims:
        return []

    sorted_claims = sorted(claims, key=lambda claim: claim.confidence, reverse=True)
    if len(sorted_claims) > max_claims:
        sorted_claims = sorted_claims[:max_claims]

    clusters: List[List[SemanticClaim]] = []

    for claim in sorted_claims:
        best_index = None
        best_score = 0.0
        for index in _candidate_clusters(claim, clusters):
            rep = clusters[index][0]
            score = claim_similarity(claim, rep, threshold=threshold)
            if score > best_score:
                best_score = score
                best_index = index
        if best_index is not None and best_score >= threshold:
            clusters[best_index].append(claim)
        else:
            clusters.append([claim])

    return [cluster for cluster in clusters if len(cluster) >= min_cluster_size]


def collect_story_entities(
    claims: Sequence[SemanticClaim],
    entity_index: dict[str, ResolvedEntity],
) -> List[ResolvedEntity]:
    seen: Set[str] = set()
    entities: List[ResolvedEntity] = []
    for claim in claims:
        for entity_id in claim.resolved_entity_ids:
            if entity_id in seen:
                continue
            entity = entity_index.get(entity_id)
            if entity:
                seen.add(entity_id)
                entities.append(entity)
    return entities


def collect_story_events(
    claims: Sequence[SemanticClaim],
    event_index: dict[str, DetectedEvent],
) -> List[DetectedEvent]:
    seen: Set[str] = set()
    events: List[DetectedEvent] = []
    for claim in claims:
        for event_id in claim.event_references:
            if event_id in seen:
                continue
            event = event_index.get(event_id)
            if event:
                seen.add(event_id)
                events.append(event)
    return events