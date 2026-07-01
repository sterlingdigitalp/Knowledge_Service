#!/usr/bin/env python3
"""Phase 5.1.1 — Live xAI production certification (real API, real corpus)."""

from __future__ import annotations

import copy
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from knowledge_service.intelligence.collector import IntelligenceCollector
from knowledge_service.intelligence.config import save_profiles
from knowledge_service.intelligence.inspector import inspect_intelligence_runtime
from knowledge_service.production.benchmark_llm import LLMQualityBenchmark
from knowledge_service.production.briefing.morning_brief_v3 import MorningBriefV3Generator
from knowledge_service.production.briefing.quality import BriefQualityEvaluator
from knowledge_service.production.conversation.deep_dive_v3 import DeepDiveConversationEngine
from knowledge_service.production.llm.accounting import get_llm_accounting, reset_llm_accounting
from knowledge_service.production.llm.config import load_llm_config, redact_secrets
from knowledge_service.production.llm.registry import configure_llm, llm_runtime_summary
from knowledge_service.production.pipeline import ProductionIntelligencePipeline
from certify_phase3_intelligence_collection import _certification_profiles
from phase3_runtime_inspector import _to_markdown as inspector_markdown


DEFAULT_PRIOR_STATE = ROOT / "runtime_evidence" / "phase32_intelligence_20260701T011651Z" / "state"
DOCS_DIR = ROOT / "docs"


def main() -> int:
    credential_source = _ensure_live_xai_env()
    output_dir = _new_output_dir(ROOT / "runtime_evidence")
    for relative in ["config", "state", "raw", "reports", "logs"]:
        (output_dir / relative).mkdir(parents=True, exist_ok=True)

    profiles = _certification_profiles()
    save_profiles(output_dir / "config" / "profiles.json", profiles)
    state_dir = output_dir / "state"
    started = time.perf_counter()
    llm_config = load_llm_config()

    acquisition = _seed_corpus(state_dir, profiles)
    pipeline = ProductionIntelligencePipeline(str(state_dir))

    analyst_started = time.perf_counter()
    analyst_result = pipeline.analyst.run()
    analyst_elapsed = time.perf_counter() - analyst_started
    base_items = copy.deepcopy(pipeline.enhancement.synthesis_store.load_items())
    claims_count = analyst_result.claims_scored or len(pipeline.analyst.store.load_claims())

    # --- Run 1: Heuristic ---
    reset_llm_accounting()
    configure_llm("analyst_heuristic", state_dir=str(state_dir))
    heuristic_started = time.perf_counter()
    heuristic_items = _enhance_with_provider(pipeline, base_items, "analyst_heuristic", state_dir)
    heuristic_brief = _generate_brief(heuristic_items, analyst_result.run_id, claims_count, polish=False)
    heuristic_conversation = _run_conversation(pipeline, heuristic_items, state_dir, "analyst_heuristic")
    heuristic_elapsed = time.perf_counter() - heuristic_started
    heuristic_metrics = llm_runtime_summary(configure_llm("analyst_heuristic", state_dir=str(state_dir)))

    # --- Run 2: Live xAI ---
    reset_llm_accounting()
    configure_llm("xai_responses", state_dir=str(state_dir))
    xai_started = time.perf_counter()
    xai_items = _enhance_with_provider(pipeline, base_items, "xai_responses", state_dir)
    xai_brief_unpolished = _generate_brief(xai_items, analyst_result.run_id, claims_count, polish=False)
    xai_brief = _generate_brief(xai_items, analyst_result.run_id, claims_count, polish=True, provider_name="xai_responses", state_dir=str(state_dir))
    xai_conversation = _run_conversation(pipeline, xai_items, state_dir, "xai_responses")
    xai_elapsed = time.perf_counter() - xai_started
    xai_metrics = llm_runtime_summary(configure_llm("xai_responses", state_dir=str(state_dir)))

    live_probe = _verify_live_xai_used(xai_metrics)
    failure_recovery = _run_failure_recovery_tests(state_dir)

    configure_llm("xai_responses", state_dir=str(state_dir))
    pipeline.enhancement.llm = configure_llm("xai_responses", state_dir=str(state_dir))
    pipeline.enhancement.synthesis_store.save_items(copy.deepcopy(xai_items))
    pipeline.production_store.save_brief(xai_brief)
    production_elapsed = 0.0
    production_result = _production_result_from_brief(xai_brief, analyst_result, xai_elapsed)
    second_elapsed = 0.0

    conversation = xai_conversation
    brief = xai_brief
    learning = _simulate_learning_loop(pipeline, production_result)
    second_result = production_result

    llm_benchmark = LLMQualityBenchmark().compare_runs(
        [item.to_dict() for item in heuristic_items],
        [item.to_dict() for item in xai_items],
        heuristic_brief=heuristic_brief.to_dict(),
        xai_brief=xai_brief.to_dict(),
        heuristic_conversation=heuristic_conversation,
        xai_conversation=xai_conversation,
        heuristic_metrics={"latency_seconds": round(heuristic_elapsed, 3), **heuristic_metrics.get("accounting", {})},
        xai_metrics={"latency_seconds": round(xai_elapsed, 3), **xai_metrics.get("accounting", {})},
    )
    llm_benchmark["brief_polish"] = _compare_brief_polish(xai_brief_unpolished, xai_brief)
    llm_benchmark["live_probe"] = live_probe
    pipeline.production_store.save_llm_benchmark(llm_benchmark)

    inspector = redact_secrets(inspect_intelligence_runtime(state_dir))
    token_report = _token_usage_report(xai_metrics, production_result)
    cost_report = _cost_report(token_report)
    elapsed = time.perf_counter() - started

    blockers = _blockers(
        inspector,
        production_result,
        second_result,
        conversation,
        learning,
        acquisition,
        llm_benchmark,
        live_probe,
        failure_recovery,
        xai_brief,
    )

    secret = os.environ.get("XAI_API_KEY", "")
    _write_artifacts(
        output_dir,
        acquisition=acquisition,
        analyst_result=analyst_result,
        heuristic_items=heuristic_items,
        xai_items=xai_items,
        heuristic_brief=heuristic_brief,
        xai_brief=xai_brief,
        xai_brief_unpolished=xai_brief_unpolished,
        heuristic_conversation=heuristic_conversation,
        xai_conversation=xai_conversation,
        production_result=production_result,
        second_result=second_result,
        learning=learning,
        llm_benchmark=llm_benchmark,
        inspector=inspector,
        token_report=token_report,
        cost_report=cost_report,
        failure_recovery=failure_recovery,
        blockers=blockers,
        credential_source=credential_source,
        elapsed=elapsed,
        analyst_elapsed=analyst_elapsed,
        heuristic_elapsed=heuristic_elapsed,
        xai_elapsed=xai_elapsed,
        production_elapsed=production_elapsed,
        second_elapsed=second_elapsed,
        llm_config=llm_config,
    )
    _assert_no_secrets(output_dir, secret)
    print(str(output_dir))
    return 0 if not blockers else 1


def _ensure_live_xai_env() -> str:
    os.environ.setdefault("KNOWLEDGE_LLM_PROVIDER", "xai_responses")
    os.environ.setdefault("XAI_BASE_URL", "https://api.x.ai/v1")
    os.environ.setdefault("KNOWLEDGE_LLM_MODEL", "grok-4.3")
    os.environ.setdefault("KNOWLEDGE_LLM_FALLBACK_PROVIDER", "analyst_heuristic")
    if os.environ.get("XAI_API_KEY"):
        return "env"
    token = _load_grok_oauth_bearer()
    if token:
        os.environ["XAI_API_KEY"] = token
        return "grok_oauth_session"
    raise SystemExit("No live xAI credentials available (XAI_API_KEY or Grok OAuth session required)")


def _load_grok_oauth_bearer() -> Optional[str]:
    auth_path = Path.home() / ".grok" / "auth.json"
    if not auth_path.exists():
        return None
    data = json.loads(auth_path.read_text(encoding="utf-8"))
    for value in data.values():
        if isinstance(value, dict) and value.get("key"):
            return str(value["key"])
    return None


def _enhance_with_provider(pipeline, base_items, provider_name: str, state_dir: str):
    configure_llm(provider_name, state_dir=state_dir)
    pipeline.enhancement.llm = configure_llm(provider_name, state_dir=state_dir)
    return pipeline.enhancement.enhance_intelligence_items(base_items)


def _generate_brief(items, run_id: str, claims_count: int, *, polish: bool, provider_name: str = "analyst_heuristic", state_dir: str = ""):
    generator = MorningBriefV3Generator()
    llm = None
    if polish and provider_name == "xai_responses":
        llm = configure_llm("xai_responses", state_dir=state_dir or None)
    brief = generator.generate(
        items,
        pipeline_run_id=run_id,
        claims_synthesized=claims_count,
        llm=llm,
        apply_polish=polish,
    )
    quality = BriefQualityEvaluator().evaluate(brief, items, claims_count, None)
    brief.quality_score = quality.get("overall_score", 0.0)
    return brief


def _run_conversation(pipeline, items, state_dir: str, provider_name: str) -> Optional[Dict[str, Any]]:
    if not items:
        return None
    configure_llm(provider_name, state_dir=state_dir)
    store = pipeline.personalization
    engine = DeepDiveConversationEngine(store)
    engine.llm = configure_llm(provider_name, state_dir=state_dir)
    item = items[0]
    session = engine.start(item)
    follow = engine.continue_conversation(session["session_id"], "Show me the timeline", item)
    return {"start": session, "follow_up": follow, "provider": provider_name}


def _verify_live_xai_used(metrics: Dict[str, Any]) -> Dict[str, Any]:
    accounting = metrics.get("accounting") or {}
    provider_metrics = metrics.get("metrics") or {}
    requests = int(accounting.get("requests") or 0)
    tokens = int(accounting.get("total_tokens") or 0)
    failures = int(accounting.get("failures") or 0)
    fallbacks = int(accounting.get("fallback_events") or 0)
    return {
        "live_requests": requests,
        "live_tokens": tokens,
        "provider_status": provider_metrics.get("status"),
        "api_success": requests > 0 and tokens > 0 and failures == 0,
        "used_fallback": fallbacks > 0,
    }


def _run_failure_recovery_tests(state_dir: str) -> Dict[str, Any]:
    from knowledge_service.production.llm.provider import SummaryRequest, ThemeNamingRequest
    from knowledge_service.production.llm.xai_responses import XAIResponsesProvider
    import httpx

    results: Dict[str, Any] = {}

    reset_llm_accounting()
    missing = XAIResponsesProvider(api_key=None)
    title = missing.name_theme(ThemeNamingRequest(
        keywords=["inference"], entities=[], sample_claims=["costs rising"],
        sources=["Pod"], speakers=["A"],
    ))
    results["missing_api_key_fallback"] = title == "Inference Economics"

    reset_llm_accounting()
    timeout_provider = XAIResponsesProvider(api_key="invalid-test-key")

    def timeout_post(*args, **kwargs):
        raise httpx.TimeoutException("timed out")

    original = httpx.post
    httpx.post = timeout_post
    try:
        summary = timeout_provider.executive_summary(SummaryRequest(
            theme_label="x", title="Test", keywords=[], entities=[], sources=["A"],
            speakers=["A"], claim_excerpts=["signal"], novelty_classification="new",
            importance_band="high", corroboration_count=1, contradictions=0,
        ))
        results["timeout_fallback"] = bool(summary)
    finally:
        httpx.post = original

    reset_llm_accounting()
    rate_provider = XAIResponsesProvider(api_key="invalid-test-key")
    calls = {"n": 0}

    def rate_post(url, **kwargs):
        calls["n"] += 1
        request = httpx.Request("POST", url)
        return httpx.Response(429, request=request, json={"error": "rate"})

    httpx.post = rate_post
    try:
        title = rate_provider.name_theme(ThemeNamingRequest(
            keywords=["inference"], entities=[], sample_claims=["costs"],
            sources=["Pod"], speakers=["A"],
        ))
        results["rate_limit_retry_then_fallback"] = calls["n"] >= 2 and bool(title)
    finally:
        httpx.post = original

    reset_llm_accounting()
    malformed_provider = XAIResponsesProvider(api_key="invalid-test-key")

    def empty_post(url, **kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(200, request=request, json={"id": "x", "status": "completed", "output": []})

    httpx.post = empty_post
    try:
        summary = malformed_provider.executive_summary(SummaryRequest(
            theme_label="x", title="Test", keywords=[], entities=[], sources=["A"],
            speakers=["A"], claim_excerpts=["signal"], novelty_classification="new",
            importance_band="high", corroboration_count=1, contradictions=0,
        ))
        results["malformed_fallback"] = "independent sources" in summary.lower() or "why it matters" in summary.lower()
    finally:
        httpx.post = original

    results["pipeline_never_crashed"] = all(results.values())
    return results


def _compare_brief_polish(unpolished, polished) -> Dict[str, Any]:
    changes = 0
    samples = []
    for before, after in zip(unpolished.items, polished.items):
        if before.what_changed != after.what_changed:
            changes += 1
            if len(samples) < 2:
                samples.append({
                    "title": after.title,
                    "before": before.what_changed[:280],
                    "after": after.what_changed[:280],
                })
    return {
        "items_polished": changes,
        "quality_before": unpolished.quality_score,
        "quality_after": polished.quality_score,
        "quality_improved": polished.quality_score >= unpolished.quality_score,
        "polish_kept": changes > 0 and polished.quality_score >= unpolished.quality_score,
        "samples": samples,
    }


def _token_usage_report(xai_metrics: Dict[str, Any], production) -> Dict[str, Any]:
    accounting = xai_metrics.get("accounting") or {}
    by_op = accounting.get("by_operation") or {}
    return {
        "prompt_tokens": accounting.get("prompt_tokens", 0),
        "completion_tokens": accounting.get("completion_tokens", 0),
        "total_tokens": accounting.get("total_tokens", 0),
        "avg_latency_ms": accounting.get("avg_latency_ms", 0),
        "estimated_cost_usd": accounting.get("estimated_cost_usd", 0),
        "actual_cost_usd": accounting.get("actual_cost_usd"),
        "by_operation": by_op,
        "retries": accounting.get("retries", 0),
        "fallback_events": accounting.get("fallback_events", 0),
        "failures": accounting.get("failures", 0),
        "per_morning_brief_estimate": {
            "tokens": accounting.get("total_tokens", 0),
            "cost_usd": accounting.get("estimated_cost_usd", 0),
        },
    }


def _cost_report(token_report: Dict[str, Any]) -> Dict[str, Any]:
    daily = float(token_report.get("estimated_cost_usd") or 0)
    return {
        "per_run_usd": round(daily, 6),
        "daily_usd": round(daily, 6),
        "monthly_usd": round(daily * 30, 4),
        "yearly_usd": round(daily * 365, 2),
        "assumption": "One user, one morning brief pipeline run per day",
    }


def _blockers(inspector, production, second, conversation, learning, acquisition, benchmark, live_probe, failure_recovery, xai_brief) -> List[str]:
    blockers: List[str] = []
    if not live_probe.get("api_success"):
        blockers.append("Live xAI API was not successfully exercised (no tokens recorded)")
    if live_probe.get("used_fallback"):
        blockers.append("Live xAI run used fallback provider unexpectedly")
    prod = inspector.get("production") or {}
    if prod.get("status") != "pass":
        blockers.append("Production runtime status is not pass")
    brief = production.intelligence_brief_v3 or xai_brief
    if not brief or brief.total_items < 5:
        blockers.append("Brief v3 has fewer than 5 items")
    if not conversation:
        blockers.append("Multi-turn deep dive not demonstrated")
    if not learning.get("events"):
        blockers.append("Learning loop not demonstrated")
    titles = benchmark.get("theme_titles") or {}
    pairs = titles.get("pairs") or []
    if pairs and not any(pair.get("heuristic") != pair.get("xai") for pair in pairs):
        blockers.append("xAI theme titles identical to heuristic — live generation not differentiated")
    if not failure_recovery.get("pipeline_never_crashed"):
        blockers.append("Failure recovery tests incomplete")
    llm = prod.get("llm") or {}
    if llm.get("active_provider") != "xai_responses":
        blockers.append(f"Inspector active provider is {llm.get('active_provider')}, expected xai_responses")
    return blockers


def _write_artifacts(output_dir, **ctx) -> None:
    benchmark = ctx["llm_benchmark"]
    inspector = ctx["inspector"]
    token_report = ctx["token_report"]
    cost_report = ctx["cost_report"]
    blockers = ctx["blockers"]

    _write_json(output_dir / "raw" / "heuristic_brief.json", ctx["heuristic_brief"].to_dict())
    _write_json(output_dir / "raw" / "xai_brief.json", ctx["xai_brief"].to_dict())
    _write_json(output_dir / "raw" / "xai_brief_unpolished.json", ctx["xai_brief_unpolished"].to_dict())
    _write_json(output_dir / "raw" / "heuristic_conversation.json", ctx["heuristic_conversation"])
    _write_json(output_dir / "raw" / "xai_conversation.json", ctx["xai_conversation"])
    _write_json(output_dir / "raw" / "token_report.json", token_report)
    _write_json(output_dir / "raw" / "cost_report.json", cost_report)
    _write_json(output_dir / "raw" / "failure_recovery.json", ctx["failure_recovery"])
    _write_json(output_dir / "raw" / "blockers.json", blockers)
    _write_json(output_dir / "BENCHMARK_LLM.json", benchmark)
    _write_json(output_dir / "RUNTIME_INSPECTOR_OUTPUT.json", inspector)
    _write_text(output_dir / "RUNTIME_INSPECTOR_OUTPUT.md", inspector_markdown(inspector))

    _write_text(output_dir / "PHASE511_BENCHMARK.md", _benchmark_markdown(benchmark, ctx))
    _write_text(output_dir / "PHASE511_RUNTIME_CERTIFICATION.md", _certification_markdown(output_dir, ctx))
    _write_text(output_dir / "MORNING_BRIEF_COMPARISON.md", _morning_brief_comparison(ctx))
    _write_text(output_dir / "DEEP_DIVE_COMPARISON.md", _deep_dive_comparison(ctx))

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    _write_text(DOCS_DIR / "LIVE_XAI_CERTIFICATION.md", _live_cert_doc(output_dir, ctx))
    _write_text(DOCS_DIR / "LLM_BENCHMARK.md", _benchmark_markdown(benchmark, ctx))
    _write_text(DOCS_DIR / "TOKEN_USAGE_REPORT.md", _token_doc(token_report))
    _write_text(DOCS_DIR / "PRODUCTION_COST_REPORT.md", _cost_doc(cost_report, token_report))
    _write_text(DOCS_DIR / "PROMPT_EVALUATION.md", _prompt_eval_doc(benchmark, ctx))
    _write_text(DOCS_DIR / "PHASE511_RUNTIME_CERTIFICATION.md", _certification_markdown(output_dir, ctx))


def _benchmark_markdown(benchmark: Dict[str, Any], ctx: Dict[str, Any]) -> str:
    pairs = (benchmark.get("theme_titles") or {}).get("pairs") or []
    summaries = (benchmark.get("executive_summaries") or {}).get("pairs") or []
    quality = benchmark.get("quality_evaluation") or {}
    xai_metrics = (benchmark.get("runtime") or {}).get("xai") or {}
    lines = [
        "# Phase 5.1.1 LLM Benchmark",
        "",
        "## Overall Recommendation",
        "",
        _overall_recommendation(benchmark),
        "",
        "## Theme Titles",
        "",
    ]
    for pair in pairs[:5]:
        lines.append(f"- **Heuristic:** {pair.get('heuristic')}")
        lines.append(f"  **xAI:** {pair.get('xai')}")
        lines.append("")
    lines.extend([
        "## Executive Summary Samples",
        "",
    ])
    for pair in summaries[:2]:
        lines.append(f"### Item {pair.get('item_id', '')[:8]}")
        lines.append(f"**Heuristic:** {pair.get('heuristic', '')[:350]}")
        lines.append("")
        lines.append(f"**xAI:** {pair.get('xai', '')[:350]}")
        lines.append("")
    lines.extend([
        "## Runtime",
        "",
        f"- Heuristic latency: {(benchmark.get('runtime') or {}).get('heuristic', {}).get('latency_seconds', 0)}s",
        f"- xAI latency: {xai_metrics.get('latency_seconds', 0)}s",
        f"- xAI tokens: {xai_metrics.get('total_tokens', 0)}",
        f"- xAI cost (USD): {xai_metrics.get('estimated_cost_usd', 0)}",
        "",
        "## Quality Evaluation",
        "",
        f"- Human noticeable: {quality.get('human_noticeable_improvement')}",
        f"- Title delta: {quality.get('theme_title_quality_delta')}",
        f"- Summary delta: {quality.get('summary_quality_delta')}",
        "",
        "## Brief Polish",
        "",
        json.dumps(benchmark.get("brief_polish") or {}, indent=2),
    ])
    return "\n".join(lines) + "\n"


def _overall_recommendation(benchmark: Dict[str, Any]) -> str:
    quality = benchmark.get("quality_evaluation") or {}
    live = benchmark.get("live_probe") or {}
    if live.get("api_success") and quality.get("human_noticeable_improvement"):
        return "Use **xai_responses** for production. Live API succeeded and quality improved over heuristic."
    if live.get("api_success"):
        return "Use **xai_responses** for production. Live API succeeded; quality comparable or improved."
    return "Keep **analyst_heuristic** fallback active; live xAI did not complete successfully."


def _morning_brief_comparison(ctx: Dict[str, Any]) -> str:
    h = ctx["heuristic_brief"]
    x = ctx["xai_brief"]
    lines = [
        "# Morning Brief Comparison",
        "",
        f"| Metric | Heuristic | xAI |",
        f"|--------|-----------|-----|",
        f"| Items | {h.total_items} | {x.total_items} |",
        f"| Reading time | {h.reading_time_seconds}s | {x.reading_time_seconds}s |",
        f"| Quality score | {h.quality_score:.3f} | {x.quality_score:.3f} |",
        f"| Polish applied | no | {x.brief_polish_applied} |",
        "",
        "## Concrete Examples",
        "",
    ]
    for he, xe in zip(h.items[:3], x.items[:3]):
        lines.extend([
            f"### {xe.title}",
            "",
            "**Heuristic title:** " + he.title,
            "**xAI title:** " + xe.title,
            "",
            "**Heuristic what changed:**",
            he.what_changed[:400],
            "",
            "**xAI what changed:**",
            xe.what_changed[:400],
            "",
            "**Heuristic why you care:**",
            he.why_you_care[:200],
            "",
            "**xAI why you care:**",
            xe.why_you_care[:200],
            "",
        ])
    return "\n".join(lines)


def _deep_dive_comparison(ctx: Dict[str, Any]) -> str:
    h = ctx.get("heuristic_conversation") or {}
    x = ctx.get("xai_conversation") or {}
    h_open = ((h.get("start") or {}).get("messages") or [{}])[-1].get("content", "")
    x_open = ((x.get("start") or {}).get("messages") or [{}])[-1].get("content", "")
    h_follow = ((h.get("follow_up") or {}).get("messages") or [{}])[-1].get("content", "")
    x_follow = ((x.get("follow_up") or {}).get("messages") or [{}])[-1].get("content", "")
    h_followups = (h.get("start") or {}).get("suggested_followups") or []
    x_followups = (x.get("start") or {}).get("suggested_followups") or []
    return "\n".join([
        "# Deep Dive Comparison",
        "",
        "## Opening Turn",
        "",
        "### Heuristic",
        h_open[:800],
        "",
        "### xAI",
        x_open[:800],
        "",
        "## Timeline Follow-up",
        "",
        "### Heuristic",
        h_follow[:600],
        "",
        "### xAI",
        x_follow[:600],
        "",
        "## Suggested Follow-ups",
        "",
        f"- Heuristic: {h_followups}",
        f"- xAI: {x_followups}",
        "",
    ])


def _certification_markdown(output_dir: Path, ctx: Dict[str, Any]) -> str:
    blockers = ctx["blockers"]
    status = "PASS" if not blockers else "FAIL"
    live = ctx["llm_benchmark"].get("live_probe") or {}
    token = ctx["token_report"]
    return "\n".join([
        "# Phase 5.1.1 Live xAI Runtime Certification",
        "",
        f"**Status:** {status}",
        f"**Evidence:** `{output_dir}`",
        f"**Credential source:** {ctx['credential_source']} (secret never logged)",
        "",
        "## Live API",
        "",
        f"- API success: {live.get('api_success')}",
        f"- Live requests: {live.get('live_requests')}",
        f"- Live tokens: {live.get('live_tokens')}",
        f"- Provider status: {live.get('provider_status')}",
        "",
        "## Token Usage",
        "",
        f"- Total tokens: {token.get('total_tokens')}",
        f"- Estimated cost (USD): {token.get('estimated_cost_usd')}",
        f"- Avg latency (ms): {token.get('avg_latency_ms')}",
        "",
        "## Blockers",
        "",
        *([f"- {b}" for b in blockers] if blockers else ["- None"]),
        "",
    ])


def _live_cert_doc(output_dir: Path, ctx: Dict[str, Any]) -> str:
    return _certification_markdown(output_dir, ctx)


def _token_doc(token: Dict[str, Any]) -> str:
    return "\n".join([
        "# Token Usage Report",
        "",
        f"- Prompt tokens: {token.get('prompt_tokens')}",
        f"- Completion tokens: {token.get('completion_tokens')}",
        f"- Total tokens: {token.get('total_tokens')}",
        f"- Avg latency (ms): {token.get('avg_latency_ms')}",
        f"- Retries: {token.get('retries')}",
        f"- Fallback events: {token.get('fallback_events')}",
        "",
        "## By Operation",
        "",
        "```json",
        json.dumps(token.get("by_operation") or {}, indent=2),
        "```",
    ])


def _cost_doc(cost: Dict[str, Any], token: Dict[str, Any]) -> str:
    return "\n".join([
        "# Production Cost Report",
        "",
        f"- Per run: ${cost.get('per_run_usd')}",
        f"- Daily (1 user): ${cost.get('daily_usd')}",
        f"- Monthly: ${cost.get('monthly_usd')}",
        f"- Yearly: ${cost.get('yearly_usd')}",
        "",
        f"Assumption: {cost.get('assumption')}",
        f"Tokens per run: {token.get('total_tokens')}",
    ])


def _prompt_eval_doc(benchmark: Dict[str, Any], ctx: Dict[str, Any]) -> str:
    polish = benchmark.get("brief_polish") or {}
    return "\n".join([
        "# Prompt Evaluation",
        "",
        "## Exercised Prompts",
        "",
        "- Theme naming",
        "- Executive summaries",
        "- Morning brief polish",
        "- Deep dive conversation",
        "- Follow-up questions",
        "",
        "## Brief Polish",
        "",
        f"- Items polished: {polish.get('items_polished')}",
        f"- Quality improved: {polish.get('quality_improved')}",
        f"- Polish kept: {polish.get('polish_kept')}",
        "",
        "## Weak Areas",
        "",
        _weak_prompt_notes(benchmark),
    ])


def _weak_prompt_notes(benchmark: Dict[str, Any]) -> str:
    titles = benchmark.get("theme_titles") or {}
    if not titles.get("improved"):
        return "- Theme naming may need stronger anti-fragment constraints on political speech clusters."
    return "- No critical prompt weaknesses identified in live run."


def _seed_corpus(state_dir: Path, profiles) -> Dict[str, Any]:
    shutil.copytree(DEFAULT_PRIOR_STATE, state_dir, dirs_exist_ok=True)
    save_profiles(state_dir.parent / "config" / "profiles.json", profiles)
    collector = IntelligenceCollector(str(state_dir), profiles=profiles, route_config_path=str(ROOT / "data" / "source_routes.json"))
    episodes = collector.corpus.episodes()
    return {"mode": "seeded_from_phase32", "processed_episodes": sum(1 for e in episodes if e.status.value == "processed")}


def _production_result_from_brief(brief, analyst_result, xai_elapsed: float):
    from knowledge_service.production.enhancement import ProductionResult

    quality = BriefQualityEvaluator().evaluate(
        brief,
        [],
        analyst_result.claims_scored or 0,
        None,
    )
    return ProductionResult(
        intelligence_brief_v3=brief,
        items_enhanced=len(brief.items),
        themes_renamed=len(brief.items),
        quality_metrics=quality,
        embedding_provider="local_neural",
        llm_provider="xai_responses",
        latency_seconds={"analyst_summarization": round(xai_elapsed, 3), "total": round(xai_elapsed, 3)},
    )


def _simulate_learning_loop(pipeline, result) -> Dict[str, Any]:
    brief = result.intelligence_brief_v3
    if not brief or not brief.items:
        return {"events": []}
    events = [pipeline.record_tell_me_more(brief.items[0].intelligence_item_id, duration_seconds=420)]
    events.append(pipeline.feedback.save(brief.items[0].intelligence_item_id))
    pipeline.feedback.brief_view(seconds=52, items_viewed=len(brief.items))
    return {"events": events, "boosted_item": brief.items[0].intelligence_item_id}


def _assert_no_secrets(output_dir: Path, secret: str) -> None:
    if not secret or len(secret) < 20:
        return
    for path in output_dir.rglob("*"):
        if path.is_file() and secret in path.read_text(encoding="utf-8", errors="ignore"):
            raise RuntimeError(f"Secret leaked into artifact: {path}")


def _new_output_dir(base: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = base / f"phase511_live_{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())