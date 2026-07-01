"""Theme Discovery — emergent topic clustering from claims."""

from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List, Sequence, Set

from ....intelligence.models import stable_id
from ....retrieval.embedding import cosine_similarity, embed_text, tokenize
from ...models import ImportanceBand, NoveltyClass, ScoredClaim
from ..models import Theme


THEME_CLUSTER_THRESHOLD = 0.50
MIN_THEME_CLAIMS = 3
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "as", "is", "was", "are", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "that", "this", "these", "those", "it", "its", "they", "them", "their", "we", "you",
    "i", "he", "she", "his", "her", "my", "your", "our", "not", "no", "so", "if", "just",
    "like", "about", "into", "than", "then", "there", "when", "what", "which", "who",
    "how", "all", "also", "very", "can", "know", "think", "mean", "really", "going",
    "get", "got", "one", "two", "way", "make", "made", "say", "said", "because",
}


class ThemeDiscoveryEngine:
    """Cluster related claims into emergent themes — no hardcoded topic list."""

    def discover(self, scored_claims: Sequence[ScoredClaim]) -> List[Theme]:
        candidates = [
            item for item in scored_claims
            if item.novelty.classification != NoveltyClass.REPEAT
            and item.importance.band != ImportanceBand.IGNORE
            and item.importance.score >= 0.35
        ]
        if not candidates:
            return []

        groups: List[List[ScoredClaim]] = []
        for item in candidates:
            embedding = item.claim.embedding or embed_text(item.claim.claim_text)
            matched_index = None
            for index, group in enumerate(groups):
                rep = group[0]
                rep_embedding = rep.claim.embedding or embed_text(rep.claim.claim_text)
                if cosine_similarity(embedding, rep_embedding) >= THEME_CLUSTER_THRESHOLD:
                    matched_index = index
                    break
            if matched_index is None:
                groups.append([item])
            else:
                groups[matched_index].append(item)

        themes: List[Theme] = []
        for members in groups:
            if len(members) < MIN_THEME_CLAIMS:
                continue
            claims = [item.claim for item in members]
            label, keywords, entities = _emergent_label(claims)
            sources = {claim.episode_id for claim in claims}
            speakers = {claim.speaker for claim in claims if claim.speaker and claim.speaker != "unknown"}
            centroid = _centroid([item.claim.embedding or embed_text(item.claim.claim_text) for item in members])
            theme_id = stable_id("theme", label, *sorted(sources)[:3])
            themes.append(Theme(
                theme_id=theme_id,
                label=label,
                claim_ids=[claim.claim_id for claim in claims],
                keywords=keywords,
                entities=entities,
                source_count=len(sources),
                speaker_count=len(speakers) or 1,
                centroid_embedding=centroid,
            ))
        return sorted(themes, key=lambda theme: len(theme.claim_ids), reverse=True)


def _emergent_label(claims: Sequence) -> tuple[str, List[str], List[str]]:
    token_counts: Counter[str] = Counter()
    entities: Counter[str] = Counter()
    topics: Counter[str] = Counter()

    for claim in claims:
        for token in tokenize(claim.claim_text):
            if token not in STOPWORDS and len(token) > 2:
                token_counts[token] += 1
        for entity in claim.entities:
            if entity and entity != "general":
                entities[entity] += 1
        if claim.topic and claim.topic != "general":
            topics[claim.topic] += 1

    keywords = [word for word, _ in token_counts.most_common(6)]
    top_entities = [name for name, _ in entities.most_common(4)]
    top_topics = [topic for topic, _ in topics.most_common(2)]

    label_parts: List[str] = []
    if top_topics:
        label_parts.append(top_topics[0])
    elif top_entities:
        label_parts.append(top_entities[0])
    if keywords:
        secondary = keywords[0].title() if keywords[0] not in {p.lower() for p in label_parts} else (
            keywords[1].title() if len(keywords) > 1 else ""
        )
        if secondary:
            label_parts.append(secondary)

    label = " ".join(label_parts)[:60].strip() or _title_from_keywords(keywords)
    if _is_fragment_label(label):
        if top_entities:
            label = top_entities[0]
        elif top_topics:
            label = top_topics[0]
        else:
            label = _title_from_keywords([k for k in keywords if k not in FRAGMENT_STARTERS])
    return label, keywords[:8], top_entities[:6]


FRAGMENT_STARTERS = {"i", "and", "but", "so", "well", "yeah", "okay", "the", "a", "we", "you"}


def _is_fragment_label(label: str) -> bool:
    if not label:
        return True
    words = label.split()
    if len(words) <= 1 and words[0][0].islower():
        return True
    if words[0].lower() in FRAGMENT_STARTERS:
        return True
    if len(label) > 50:
        return True
    return False


def _title_from_keywords(keywords: List[str]) -> str:
    if not keywords:
        return "Emerging Development"
    return " ".join(word.title() for word in keywords[:3])


def _centroid(embeddings: List[List[float]]) -> List[float]:
    if not embeddings:
        return []
    size = len(embeddings[0])
    vector = [0.0] * size
    for embedding in embeddings:
        for index, value in enumerate(embedding[:size]):
            vector[index] += value
    count = float(len(embeddings))
    return [value / count for value in vector]