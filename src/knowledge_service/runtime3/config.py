"""Configuration for Runtime 3 — Semantic Understanding Engine."""

from __future__ import annotations

import os
from dataclasses import dataclass


def is_runtime3_enabled() -> bool:
    """Runtime 1 remains default; enable Runtime 3 via KNOWLEDGE_RUNTIME3_ENABLED=1."""
    return os.environ.get("KNOWLEDGE_RUNTIME3_ENABLED", "").strip().lower() in {
        "1", "true", "yes", "on",
    }


@dataclass(frozen=True)
class Runtime3Config:
    min_claim_chars: int = 35
    min_story_claims: int = 2
    story_cluster_threshold: float = 0.38
    min_story_confidence: float = 0.45
    max_stories_per_run: int = 15
    max_claims_for_clustering: int = 800
    reject_non_news_segments: bool = True
    output_dir: str = "data/runtime3"

    @classmethod
    def from_env(cls) -> "Runtime3Config":
        return cls(
            min_claim_chars=int(os.environ.get("KNOWLEDGE_R3_MIN_CLAIM_CHARS", "35")),
            story_cluster_threshold=float(os.environ.get("KNOWLEDGE_R3_CLUSTER_SIM", "0.38")),
            min_story_confidence=float(os.environ.get("KNOWLEDGE_R3_MIN_CONFIDENCE", "0.45")),
            max_stories_per_run=int(os.environ.get("KNOWLEDGE_R3_MAX_STORIES", "15")),
        )