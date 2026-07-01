import time

from knowledge_service.production.llm.budget import LLMBudgetConfig, LLMRuntimeBudget


def test_budget_limits_calls_and_items():
    budget = LLMRuntimeBudget(config=LLMBudgetConfig(
        max_live_llm_items=5,
        max_live_llm_calls_per_run=20,
        maximum_live_llm_runtime_seconds=300,
    ))
    for _ in range(5):
        assert budget.can_enhance_live_item()
        budget.record_live_call()
        budget.record_live_item()
    assert not budget.can_enhance_live_item()
    assert budget.remaining_items == 0


def test_budget_hard_stops_at_max_calls():
    budget = LLMRuntimeBudget(config=LLMBudgetConfig(max_live_llm_calls_per_run=3, max_live_llm_items=10))
    for _ in range(3):
        budget.record_live_call()
    assert not budget.can_make_live_call()
    assert budget.budget_exhausted


def test_budget_timeout():
    budget = LLMRuntimeBudget(config=LLMBudgetConfig(maximum_live_llm_runtime_seconds=0.01))
    time.sleep(0.02)
    assert budget.runtime_exceeded()
    budget.mark_timed_out()
    assert not budget.can_make_live_call()


def test_budget_summary_tracks_cache():
    budget = LLMRuntimeBudget()
    budget.record_cache_hit()
    budget.record_cache_miss()
    budget.record_skipped()
    summary = budget.summary()
    assert summary["cache_hits"] == 1
    assert summary["cache_misses"] == 1
    assert summary["items_skipped"] == 1
    assert summary["cache_hit_rate"] == 0.5