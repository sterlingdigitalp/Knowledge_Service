"""Production artifact persistence."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..intelligence.state import FileStateStore
from .briefing.morning_brief_v3 import IntelligenceBriefV3


class ProductionStore:
    BRIEFS_FILE = "production/intelligence_briefs_v3.json"
    TREND_HISTORY_FILE = "production/trend_history.jsonl"
    BENCHMARK_FILE = "production/benchmark_vs_phase41.json"
    BENCHMARK_LLM_FILE = "production/benchmark_llm.json"
    LLM_USAGE_FILE = "production/llm_usage.jsonl"
    LLM_CACHE_FILE = "production/llm_cache.json"
    LLM_BUDGET_FILE = "production/llm_budget.json"
    RUNS_FILE = "production/pipeline_runs.json"

    def __init__(self, state: FileStateStore):
        self.state = state
        (self.state.root / "production").mkdir(parents=True, exist_ok=True)

    def save_brief(self, brief: IntelligenceBriefV3) -> None:
        briefs = self.load_briefs()
        briefs.append(brief)
        self.state.write_json(self.BRIEFS_FILE, {"briefs": [item.to_dict() for item in briefs]})

    def load_briefs(self) -> List[IntelligenceBriefV3]:
        data = self.state.read_json(self.BRIEFS_FILE, {"briefs": []})
        return [IntelligenceBriefV3.from_dict(item) for item in data.get("briefs", [])]

    def latest_brief(self) -> Optional[IntelligenceBriefV3]:
        briefs = self.load_briefs()
        return briefs[-1] if briefs else None

    def append_trend_snapshot(self, snapshot: Dict[str, Any]) -> None:
        rows = self.state.read_jsonl(self.TREND_HISTORY_FILE)
        rows.append(snapshot)
        self.state.write_jsonl(self.TREND_HISTORY_FILE, rows)

    def load_trend_history(self) -> List[Dict[str, Any]]:
        return self.state.read_jsonl(self.TREND_HISTORY_FILE)

    def save_benchmark(self, report: Dict[str, Any]) -> None:
        self.state.write_json(self.BENCHMARK_FILE, report)

    def load_benchmark(self) -> Dict[str, Any]:
        return self.state.read_json(self.BENCHMARK_FILE, {})

    def save_llm_benchmark(self, report: Dict[str, Any]) -> None:
        self.state.write_json(self.BENCHMARK_LLM_FILE, report)

    def load_llm_benchmark(self) -> Dict[str, Any]:
        return self.state.read_json(self.BENCHMARK_LLM_FILE, {})

    def append_llm_usage(self, event: Dict[str, Any]) -> None:
        rows = self.state.read_jsonl(self.LLM_USAGE_FILE)
        rows.append(event)
        self.state.write_jsonl(self.LLM_USAGE_FILE, rows)

    def load_llm_usage(self) -> List[Dict[str, Any]]:
        return self.state.read_jsonl(self.LLM_USAGE_FILE)

    def save_llm_budget(self, report: Dict[str, Any]) -> None:
        self.state.write_json(self.LLM_BUDGET_FILE, report)

    def load_llm_budget(self) -> Dict[str, Any]:
        return self.state.read_json(self.LLM_BUDGET_FILE, {})

    def load_llm_cache_summary(self) -> Dict[str, Any]:
        from .llm.cache import LLMEnhancementCache

        return LLMEnhancementCache(self.state).summary()

    def record_run(self, run: Dict[str, Any]) -> None:
        data = self.state.read_json(self.RUNS_FILE, {"runs": []})
        data["runs"].append(run)
        self.state.write_json(self.RUNS_FILE, data)

    def summary(self) -> Dict[str, Any]:
        brief = self.latest_brief()
        return {
            "briefs": len(self.load_briefs()),
            "latest_brief_id": brief.brief_id if brief else None,
            "latest_items": brief.total_items if brief else 0,
            "reading_time_seconds": brief.reading_time_seconds if brief else 0,
            "quality_score": brief.quality_score if brief else 0.0,
            "trend_snapshots": len(self.load_trend_history()),
            "benchmark_available": bool(self.load_benchmark()),
            "llm_benchmark_available": bool(self.load_llm_benchmark()),
            "llm_usage_events": len(self.load_llm_usage()),
            "llm_cache_entries": self.load_llm_cache_summary().get("entries", 0),
            "llm_budget_available": bool(self.load_llm_budget()),
        }