"""Configuration for Intelligence Layer 2.0."""

from __future__ import annotations

import os
from dataclasses import dataclass


def is_il2_enabled() -> bool:
    """Runtime 1 remains default; enable IL2 via KNOWLEDGE_IL2_ENABLED=1."""
    return os.environ.get("KNOWLEDGE_IL2_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class IL2Config:
    min_title_quality: float = 0.62
    min_summary_quality: float = 0.55
    cluster_similarity_threshold: float = 0.62
    reject_sponsor_ctas: bool = True
    reject_fragment_titles: bool = True
    reject_boilerplate_summaries: bool = True
    max_cards_per_run: int = 12
    corpus_dir: str = "data/intelligence_v2/evaluation_corpus"

    @classmethod
    def from_env(cls) -> "IL2Config":
        return cls(
            min_title_quality=float(os.environ.get("KNOWLEDGE_IL2_MIN_TITLE", "0.55")),
            min_summary_quality=float(os.environ.get("KNOWLEDGE_IL2_MIN_SUMMARY", "0.50")),
            cluster_similarity_threshold=float(os.environ.get("KNOWLEDGE_IL2_CLUSTER_SIM", "0.62")),
        )