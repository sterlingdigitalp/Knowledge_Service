"""Token usage, latency, and cost accounting for LLM providers."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ...intelligence.models import now_iso


TICKS_PER_USD = 10_000_000_000
DEFAULT_COST_PER_1K_INPUT = 0.003
DEFAULT_COST_PER_1K_OUTPUT = 0.015


@dataclass
class UsageRecord:
    provider: str
    model: str
    operation: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    actual_cost_usd: Optional[float] = None
    status: str = "success"
    fallback_used: bool = False
    retries: int = 0
    error_type: str = ""
    timestamp: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "operation": self.operation,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": round(self.latency_ms, 2),
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "actual_cost_usd": round(self.actual_cost_usd, 6) if self.actual_cost_usd is not None else None,
            "status": self.status,
            "fallback_used": self.fallback_used,
            "retries": self.retries,
            "error_type": self.error_type,
            "timestamp": self.timestamp,
        }


class LLMUsageAccounting:
    """In-memory accounting with optional JSONL persistence."""

    def __init__(self) -> None:
        self._records: List[UsageRecord] = []
        self._persist_hook: Optional[Any] = None

    def bind_persistence(self, hook: Any) -> None:
        self._persist_hook = hook

    def record(self, record: UsageRecord) -> None:
        self._records.append(record)
        if self._persist_hook is not None:
            self._persist_hook(record.to_dict())

    def summary(self) -> Dict[str, Any]:
        if not self._records:
            return {
                "requests": 0,
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "estimated_cost_usd": 0.0,
                "actual_cost_usd": 0.0,
                "fallback_events": 0,
                "failures": 0,
                "retries": 0,
                "avg_latency_ms": 0.0,
                "by_operation": {},
                "daily_cost_estimate_usd": 0.0,
            }

        total_tokens = sum(record.total_tokens for record in self._records)
        prompt_tokens = sum(record.prompt_tokens for record in self._records)
        completion_tokens = sum(record.completion_tokens for record in self._records)
        estimated = sum(record.estimated_cost_usd for record in self._records)
        actual_values = [record.actual_cost_usd for record in self._records if record.actual_cost_usd is not None]
        actual = sum(actual_values)
        fallback_events = sum(1 for record in self._records if record.fallback_used)
        failures = sum(1 for record in self._records if record.status != "success")
        retries = sum(record.retries for record in self._records)
        latencies = [record.latency_ms for record in self._records if record.latency_ms > 0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        by_operation: Dict[str, Dict[str, Any]] = {}
        for record in self._records:
            bucket = by_operation.setdefault(record.operation, {
                "requests": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
                "fallback_events": 0,
            })
            bucket["requests"] += 1
            bucket["total_tokens"] += record.total_tokens
            bucket["estimated_cost_usd"] += record.estimated_cost_usd
            bucket["fallback_events"] += int(record.fallback_used)

        return {
            "requests": len(self._records),
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated_cost_usd": round(estimated, 6),
            "actual_cost_usd": round(actual, 6) if actual_values else None,
            "fallback_events": fallback_events,
            "failures": failures,
            "retries": retries,
            "avg_latency_ms": round(avg_latency, 2),
            "by_operation": {
                key: {
                    **value,
                    "estimated_cost_usd": round(value["estimated_cost_usd"], 6),
                }
                for key, value in by_operation.items()
            },
            "daily_cost_estimate_usd": round(estimated, 6),
        }

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [record.to_dict() for record in self._records[-limit:]]

    def reset(self) -> None:
        self._records.clear()


_accounting = LLMUsageAccounting()


def get_llm_accounting() -> LLMUsageAccounting:
    return _accounting


def reset_llm_accounting() -> None:
    _accounting.reset()


def cost_from_xai_usage(usage: Dict[str, Any]) -> Optional[float]:
    if not usage:
        return None
    ticks = usage.get("cost_in_usd_ticks")
    if ticks is not None:
        return float(ticks) / TICKS_PER_USD
    nano = usage.get("cost_in_nano_usd")
    if nano is not None:
        return float(nano) / 1_000_000_000
    return None


def estimate_token_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return (
        (prompt_tokens / 1000.0) * DEFAULT_COST_PER_1K_INPUT
        + (completion_tokens / 1000.0) * DEFAULT_COST_PER_1K_OUTPUT
    )


class RequestTimer:
    def __init__(self) -> None:
        self._started = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._started) * 1000.0