"""Runtime LLM budget — limits calls, items, and wall-clock time per production run."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict

from ...intelligence.models import now_iso


@dataclass
class LLMBudgetConfig:
    max_live_llm_items: int = 5
    max_live_llm_calls_per_run: int = 20
    maximum_live_llm_runtime_seconds: float = 300.0

    @classmethod
    def from_env(cls) -> "LLMBudgetConfig":
        return cls(
            max_live_llm_items=int(os.environ.get("KNOWLEDGE_LLM_MAX_ITEMS", "5")),
            max_live_llm_calls_per_run=int(os.environ.get("KNOWLEDGE_LLM_MAX_CALLS", "20")),
            maximum_live_llm_runtime_seconds=float(
                os.environ.get("KNOWLEDGE_LLM_MAX_RUNTIME_SECONDS", "300")
            ),
        )

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "max_live_llm_items": self.max_live_llm_items,
            "max_live_llm_calls_per_run": self.max_live_llm_calls_per_run,
            "maximum_live_llm_runtime_seconds": self.maximum_live_llm_runtime_seconds,
        }


@dataclass
class LLMRuntimeBudget:
    """Tracks consumption for a single production run."""

    config: LLMBudgetConfig = field(default_factory=LLMBudgetConfig.from_env)
    calls_used: int = 0
    items_enhanced_live: int = 0
    items_enhanced_cached: int = 0
    items_enhanced_local: int = 0
    items_skipped: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    budget_exhausted: bool = False
    timed_out: bool = False
    started_at: float = field(default_factory=time.perf_counter)
    completed_at: str = ""

    @property
    def items_enhanced(self) -> int:
        return self.items_enhanced_live + self.items_enhanced_cached + self.items_enhanced_local

    @property
    def elapsed_seconds(self) -> float:
        return time.perf_counter() - self.started_at

    @property
    def remaining_calls(self) -> int:
        return max(0, self.config.max_live_llm_calls_per_run - self.calls_used)

    @property
    def remaining_items(self) -> int:
        return max(0, self.config.max_live_llm_items - self.items_enhanced_live)

    def runtime_exceeded(self) -> bool:
        return self.elapsed_seconds >= self.config.maximum_live_llm_runtime_seconds

    def can_make_live_call(self) -> bool:
        if self.budget_exhausted or self.timed_out or self.runtime_exceeded():
            return False
        return self.calls_used < self.config.max_live_llm_calls_per_run

    def can_enhance_live_item(self) -> bool:
        if not self.can_make_live_call():
            return False
        return self.items_enhanced_live < self.config.max_live_llm_items

    def record_cache_hit(self) -> None:
        self.cache_hits += 1
        self.items_enhanced_cached += 1

    def record_cache_miss(self) -> None:
        self.cache_misses += 1

    def record_live_call(self) -> None:
        self.calls_used += 1
        if self.calls_used >= self.config.max_live_llm_calls_per_run:
            self.budget_exhausted = True

    def record_live_item(self) -> None:
        self.items_enhanced_live += 1
        if self.items_enhanced_live >= self.config.max_live_llm_items:
            self.budget_exhausted = True

    def record_local_item(self) -> None:
        self.items_enhanced_local += 1

    def record_skipped(self) -> None:
        self.items_skipped += 1

    def mark_timed_out(self) -> None:
        self.timed_out = True
        self.budget_exhausted = True

    def finalize(self) -> None:
        if self.runtime_exceeded():
            self.timed_out = True
        self.completed_at = now_iso()

    def summary(self) -> Dict[str, Any]:
        total_lookups = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_lookups) if total_lookups else 0.0
        return {
            "config": self.config.to_public_dict(),
            "calls_used": self.calls_used,
            "remaining_calls": self.remaining_calls,
            "items_enhanced_live": self.items_enhanced_live,
            "items_enhanced_cached": self.items_enhanced_cached,
            "items_enhanced_local": self.items_enhanced_local,
            "items_enhanced": self.items_enhanced,
            "items_skipped": self.items_skipped,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(hit_rate, 4),
            "cache_miss_rate": round(1.0 - hit_rate, 4) if total_lookups else 0.0,
            "budget_exhausted": self.budget_exhausted,
            "timed_out": self.timed_out,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "remaining_runtime_seconds": round(
                max(0.0, self.config.maximum_live_llm_runtime_seconds - self.elapsed_seconds),
                3,
            ),
        }