"""Phase 5.1.2 production runtime inspector."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ..analyst.inspector import inspect_analyst_runtime
from ..intelligence.state import FileStateStore
from .llm.config import load_llm_config, redact_secrets
from .llm.registry import get_llm_provider, llm_runtime_summary
from .personalization.feedback import UserFeedbackEngine
from .personalization.store import PersonalizationStore
from .scheduler.brief_scheduler import MorningBriefScheduler
from .store import ProductionStore


def inspect_production_runtime(state_dir: str | Path) -> Dict[str, Any]:
    state = FileStateStore(state_dir)
    analyst = inspect_analyst_runtime(state_dir)
    production_store = ProductionStore(state)
    personalization_store = PersonalizationStore(state)
    feedback = UserFeedbackEngine(personalization_store)
    scheduler = MorningBriefScheduler(state)

    brief = production_store.latest_brief()
    benchmark = production_store.load_benchmark()
    llm_benchmark = production_store.load_llm_benchmark()
    llm_usage = production_store.load_llm_usage()
    llm_budget = production_store.load_llm_budget()
    llm_cache = production_store.load_llm_cache_summary()
    trends = production_store.load_trend_history()
    prefs = personalization_store.load_preferences()

    llm_provider = get_llm_provider(state_dir=str(state_dir))
    llm_summary = redact_secrets(llm_runtime_summary(llm_provider))
    config = load_llm_config()
    accounting = llm_summary.get("accounting") or {}
    estimated_daily = float(accounting.get("estimated_cost_usd") or llm_budget.get("estimated_cost_usd") or 0)

    warnings: List[str] = list(analyst.get("warnings") or [])
    if not brief:
        warnings.append("No Phase 5 intelligence brief generated")
    if brief and brief.reading_time_seconds > 60:
        warnings.append(f"Brief reading time {brief.reading_time_seconds}s exceeds target")
    if brief and not (5 <= brief.total_items <= 10):
        warnings.append(f"Brief item count {brief.total_items} outside 5-10 target")
    if config.provider == "xai_responses" and not config.xai_api_key_configured:
        warnings.append("xAI provider selected but XAI_API_KEY is not configured — fallback expected")
    if llm_summary.get("accounting", {}).get("fallback_events", 0) > 0:
        warnings.append(
            f"LLM fallback events detected: {llm_summary['accounting']['fallback_events']}"
        )
    if llm_budget.get("calls_used", 0) > config.max_live_llm_calls_per_run:
        warnings.append("LLM call budget exceeded on last run")

    status = "pass" if brief and analyst.get("status") == "pass" and not any("No Phase 5" in w for w in warnings) else "fail"
    if brief and brief.reading_time_seconds <= 60 and 5 <= brief.total_items <= 10:
        status = "pass"

    return {
        "phase": "5.1.2",
        "status": status,
        "analyst": analyst,
        "production": {
            **production_store.summary(),
            "benchmark": benchmark,
            "llm_benchmark": llm_benchmark,
            "embedding_provider": benchmark.get("neural_dimensions", "local_neural"),
        },
        "llm": {
            "config": config.to_public_dict(),
            "active_provider": llm_provider.name,
            "provider_status": llm_summary.get("metrics", {}).get("status", "ready"),
            "model": config.model,
            "latency_ms": llm_summary.get("metrics", {}).get("last_latency_ms", 0),
            "token_usage": accounting,
            "estimated_cost_usd": accounting.get("estimated_cost_usd", 0.0),
            "estimated_daily_cost_usd": round(estimated_daily, 6),
            "estimated_monthly_cost_usd": round(estimated_daily * 30, 4),
            "fallback_events": accounting.get("fallback_events", 0),
            "retries": accounting.get("retries", 0),
            "failure_count": llm_summary.get("metrics", {}).get("failure_count", 0),
            "quality_comparison": llm_benchmark.get("quality_evaluation", {}),
            "recent_usage_events": llm_usage[-10:],
            "cache": llm_cache,
            "budget": llm_budget,
            "remaining_llm_budget": llm_budget.get("remaining_calls", config.max_live_llm_calls_per_run),
            "items_enhanced": llm_budget.get("items_enhanced", 0),
            "items_enhanced_live": llm_budget.get("items_enhanced_live", 0),
            "items_skipped": llm_budget.get("items_skipped", 0),
            "cache_hit_rate": llm_budget.get("cache_hit_rate", 0.0),
            "cache_miss_rate": llm_budget.get("cache_miss_rate", 0.0),
        },
        "personalization": feedback.summary(),
        "preferences": {
            "topic_weights": prefs.get("topic_weights", {}),
            "profile_weights": prefs.get("profile_weights", {}),
        },
        "scheduler": scheduler.inspect(),
        "trends": {
            "snapshots": len(trends),
            "latest": trends[-1] if trends else None,
        },
        "brief_quality": brief.to_dict() if brief else None,
        "warnings": warnings,
    }