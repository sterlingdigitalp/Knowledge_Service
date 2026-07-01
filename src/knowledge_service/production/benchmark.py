"""Benchmark Phase 5 improvements against Phase 4.1 baseline."""

from __future__ import annotations

import random
from typing import Any, Dict, List, Sequence

from ..retrieval.embedding import cosine_similarity as hash_cosine
from ..retrieval.embedding import embed_text as hash_embed
from .embeddings.registry import configure_embeddings, cosine_similarity as neural_cosine


class PhaseBenchmark:
    """Quantitative comparison of embedding and brief quality improvements."""

    def compare_embeddings(self, texts: Sequence[str], pairs: Sequence[tuple[int, int]] | None = None) -> Dict[str, Any]:
        if len(texts) < 2:
            return {"status": "insufficient_data"}

        neural = configure_embeddings("local_neural", texts)
        hash_vectors = [hash_embed(text) for text in texts]
        neural_vectors = [neural.embed(text) for text in texts]

        if pairs is None:
            pairs = [(0, 1)]
            if len(texts) >= 4:
                pairs = [(0, 1), (2, 3), (0, 2)]

        hash_scores = []
        neural_scores = []
        for left, right in pairs:
            hash_scores.append(hash_cosine(hash_vectors[left], hash_vectors[right]))
            neural_scores.append(neural_cosine(neural_vectors[left], neural_vectors[right]))

        return {
            "pairs_evaluated": len(pairs),
            "hash_similarity_avg": round(sum(hash_scores) / len(hash_scores), 4),
            "neural_similarity_avg": round(sum(neural_scores) / len(neural_scores), 4),
            "neural_dimensions": neural.dimensions,
            "hash_dimensions": 64,
            "improvement_delta": round(
                (sum(neural_scores) / len(neural_scores)) - (sum(hash_scores) / len(hash_scores)),
                4,
            ),
        }

    def compare_briefs(self, phase41_brief: Dict[str, Any] | None, phase5_brief: Dict[str, Any] | None) -> Dict[str, Any]:
        v41 = phase41_brief or {}
        v5 = phase5_brief or {}
        items41 = v41.get("items") or v41.get("total_items") or 0
        if isinstance(items41, list):
            items41 = len(items41)
        items5 = v5.get("total_items") or len(v5.get("items") or [])
        return {
            "phase41_items": items41,
            "phase5_items": items5,
            "phase41_reading_seconds": v41.get("reading_time_seconds", 0),
            "phase5_reading_seconds": v5.get("reading_time_seconds", 0),
            "phase41_compression": v41.get("compression_ratio", 0),
            "phase5_compression": v5.get("compression_ratio", 0),
            "phase5_quality_score": v5.get("quality_score", 0),
            "title_quality_improved": _title_quality(v5) > _title_quality(v41),
            "summary_quality_improved": bool(v5.get("quality_score", 0) >= 0.5),
        }

    def from_claim_texts(self, claim_texts: List[str]) -> Dict[str, Any]:
        sample = claim_texts[:200]
        if len(sample) < 4:
            sample = claim_texts
        pairs = []
        for index in range(min(10, len(sample) - 1)):
            pairs.append((index, index + 1))
        return self.compare_embeddings(sample, pairs)


def _title_quality(brief: Dict[str, Any]) -> float:
    items = brief.get("items") or []
    if not items:
        return 0.0
    good = 0
    for item in items:
        title = str(item.get("title", ""))
        if 3 <= len(title.split()) <= 6 and not title.lower().startswith(("i ", "and ", "the ")):
            good += 1
    return good / len(items)