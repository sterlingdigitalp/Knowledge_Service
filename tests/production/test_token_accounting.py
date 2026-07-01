from knowledge_service.production.llm.accounting import (
    UsageRecord,
    cost_from_xai_usage,
    estimate_token_cost,
    get_llm_accounting,
    reset_llm_accounting,
)


def test_token_accounting_summary_and_cost_estimation():
    reset_llm_accounting()
    accounting = get_llm_accounting()
    accounting.record(UsageRecord(
        provider="xai_responses",
        model="grok-4.3",
        operation="executive_summary",
        prompt_tokens=1000,
        completion_tokens=200,
        total_tokens=1200,
        latency_ms=842.5,
        estimated_cost_usd=estimate_token_cost(1000, 200),
        status="success",
    ))
    accounting.record(UsageRecord(
        provider="xai_responses",
        model="grok-4.3",
        operation="converse",
        status="fallback",
        fallback_used=True,
    ))

    summary = accounting.summary()
    assert summary["requests"] == 2
    assert summary["total_tokens"] == 1200
    assert summary["fallback_events"] == 1
    assert summary["estimated_cost_usd"] > 0
    assert summary["daily_cost_estimate_usd"] == summary["estimated_cost_usd"]
    assert summary["by_operation"]["executive_summary"]["requests"] == 1


def test_cost_from_xai_ticks():
    cost = cost_from_xai_usage({"cost_in_usd_ticks": 10_000_000_000})
    assert cost == 1.0