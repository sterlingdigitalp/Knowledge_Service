#!/usr/bin/env python3
"""Phase 5.1 xAI production integration runtime certification."""

import copy
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from knowledge_service.intelligence.collector import IntelligenceCollector
from knowledge_service.intelligence.config import save_profiles
from knowledge_service.intelligence.inspector import inspect_intelligence_runtime
from knowledge_service.production.benchmark_llm import LLMQualityBenchmark
from knowledge_service.production.llm.config import load_llm_config, redact_secrets
from knowledge_service.production.llm.registry import configure_llm, llm_runtime_summary
from knowledge_service.production.pipeline import ProductionIntelligencePipeline
from certify_phase3_intelligence_collection import _certification_profiles
from phase3_runtime_inspector import _to_markdown as inspector_markdown


DEFAULT_PRIOR_STATE = ROOT / "runtime_evidence" / "phase32_intelligence_20260701T011651Z" / "state"


def main() -> int:
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

    heuristic_started = time.perf_counter()
    configure_llm("analyst_heuristic", state_dir=str(state_dir))
    pipeline.enhancement.llm = configure_llm("analyst_heuristic", state_dir=str(state_dir))
    heuristic_items = pipeline.enhancement.enhance_intelligence_items(base_items)
    heuristic_elapsed = time.perf_counter() - heuristic_started

    xai_started = time.perf_counter()
    configure_llm("xai_responses", state_dir=str(state_dir))
    pipeline.enhancement.llm = configure_llm("xai_responses", state_dir=str(state_dir))
    xai_items = pipeline.enhancement.enhance_intelligence_items(base_items)
    xai_elapsed = time.perf_counter() - xai_started

    active_provider = llm_config.provider if llm_config.xai_api_key_configured else "analyst_heuristic"
    configure_llm(active_provider, state_dir=str(state_dir))
    pipeline.enhancement.llm = configure_llm(active_provider, state_dir=str(state_dir))
    pipeline.enhancement.synthesis_store.save_items(copy.deepcopy(xai_items if active_provider == "xai_responses" else heuristic_items))

    production_started = time.perf_counter()
    production_result = pipeline.enhancement.enhance(analyst_result)
    production_elapsed = time.perf_counter() - production_started

    conversation = None
    brief = production_result.intelligence_brief_v3
    if brief and brief.items:
        item_id = brief.items[0].intelligence_item_id
        item = next(
            (entry for entry in pipeline.enhancement.synthesis_store.load_items() if entry.item_id == item_id),
            None,
        )
        if item:
            session = pipeline.conversation.start(item)
            conversation = {
                "start": session,
                "follow_up": pipeline.continue_conversation(session["session_id"], "Show me the timeline"),
            }

    learning = _simulate_learning_loop(pipeline, production_result)
    second_started = time.perf_counter()
    second_result = pipeline.rerun_with_learning()
    second_elapsed = time.perf_counter() - second_started

    llm_benchmark = LLMQualityBenchmark().compare_runs(
        [item.to_dict() for item in heuristic_items],
        [item.to_dict() for item in xai_items],
        heuristic_brief=_brief_dict_from_items(heuristic_items, analyst_result),
        xai_brief=brief.to_dict() if brief else _brief_dict_from_items(xai_items, analyst_result),
        heuristic_metrics={"latency_seconds": round(heuristic_elapsed, 3), "provider": "analyst_heuristic"},
        xai_metrics={
            "latency_seconds": round(xai_elapsed, 3),
            "provider": "xai_responses",
            **llm_runtime_summary(pipeline.enhancement.llm).get("accounting", {}),
        },
    )
    pipeline.production_store.save_llm_benchmark(llm_benchmark)

    inspector = redact_secrets(inspect_intelligence_runtime(state_dir))
    elapsed = time.perf_counter() - started
    blockers = _blockers(
        inspector,
        production_result,
        second_result,
        conversation,
        learning,
        acquisition,
        llm_benchmark,
        llm_config,
        active_provider,
    )

    _write_json(output_dir / "raw" / "acquisition.json", acquisition)
    _write_json(output_dir / "raw" / "analyst_result.json", analyst_result.to_dict())
    _write_json(output_dir / "raw" / "heuristic_items.json", [item.to_dict() for item in heuristic_items])
    _write_json(output_dir / "raw" / "xai_items.json", [item.to_dict() for item in xai_items])
    _write_json(output_dir / "raw" / "production_result.json", production_result.to_dict())
    _write_json(output_dir / "raw" / "second_pipeline_result.json", second_result.to_dict())
    _write_json(output_dir / "raw" / "learning_loop.json", learning)
    _write_json(output_dir / "raw" / "conversation.json", conversation)
    _write_json(output_dir / "raw" / "llm_runtime.json", redact_secrets(llm_runtime_summary(pipeline.enhancement.llm)))
    _write_json(output_dir / "raw" / "blockers.json", blockers)
    _write_json(output_dir / "BENCHMARK_LLM.json", llm_benchmark)
    _write_json(output_dir / "RUNTIME_INSPECTOR_OUTPUT.json", inspector)
    _write_text(output_dir / "RUNTIME_INSPECTOR_OUTPUT.md", inspector_markdown(inspector))
    _write_text(output_dir / "PHASE51_RUNTIME_CERTIFICATION.md", _certification_report(
        output_dir,
        inspector,
        production_result,
        second_result,
        conversation,
        learning,
        llm_benchmark,
        blockers,
        elapsed,
        analyst_elapsed,
        heuristic_elapsed,
        xai_elapsed,
        production_elapsed,
        second_elapsed,
        active_provider,
        llm_config,
    ))
    if brief:
        _write_json(output_dir / "MORNING_INTELLIGENCE_BRIEF.json", brief.to_dict())
        _write_text(output_dir / "MORNING_INTELLIGENCE_BRIEF.md", _brief_markdown(brief))
        _write_text(output_dir / "DEEP_DIVE_COMPARISON.md", _deep_dive_comparison(heuristic_items, xai_items, conversation))

    _assert_no_secrets(output_dir, os.environ.get("XAI_API_KEY", ""))
    print(str(output_dir))
    return 0 if not blockers else 1


def _seed_corpus(state_dir: Path, profiles) -> Dict[str, Any]:
    shutil.copytree(DEFAULT_PRIOR_STATE, state_dir, dirs_exist_ok=True)
    save_profiles(state_dir.parent / "config" / "profiles.json", profiles)
    collector = IntelligenceCollector(
        str(state_dir),
        profiles=profiles,
        route_config_path=str(ROOT / "data" / "source_routes.json"),
    )
    episodes = collector.corpus.episodes()
    return {
        "mode": "seeded_from_phase32",
        "processed_episodes": sum(1 for episode in episodes if episode.status.value == "processed"),
    }


def _simulate_learning_loop(pipeline: ProductionIntelligencePipeline, result) -> Dict[str, Any]:
    brief = result.intelligence_brief_v3
    if not brief or not brief.items:
        return {"events": []}
    events = []
    lead = brief.items[0]
    events.append(pipeline.record_tell_me_more(lead.intelligence_item_id, duration_seconds=420))
    events.append(pipeline.feedback.save(lead.intelligence_item_id))
    if len(brief.items) > 2:
        events.append(pipeline.feedback.dismiss(brief.items[2].intelligence_item_id))
    pipeline.feedback.brief_view(seconds=52, items_viewed=len(brief.items))
    return {
        "events": events,
        "boosted_item": lead.intelligence_item_id,
        "dismissed_item": brief.items[2].intelligence_item_id if len(brief.items) > 2 else None,
    }


def _brief_dict_from_items(items, analyst_result) -> Dict[str, Any]:
    return {
        "total_items": len(items),
        "reading_time_seconds": 55,
        "quality_score": 0.5,
        "items": [item.to_dict() for item in items[:8]],
        "claims_synthesized": analyst_result.claims_scored or 0,
    }


def _blockers(
    inspector,
    production,
    second,
    conversation,
    learning,
    acquisition,
    llm_benchmark,
    llm_config,
    active_provider,
) -> List[str]:
    blockers: List[str] = []
    prod = inspector.get("production") or {}
    if prod.get("status") != "pass":
        blockers.append("Production runtime status is not pass")
    brief = production.intelligence_brief_v3
    if not brief or brief.total_items < 5:
        blockers.append("Brief v3 has fewer than 5 items")
    if brief and brief.total_items > 10:
        blockers.append("Brief v3 has more than 10 items")
    if brief and brief.reading_time_seconds > 60:
        blockers.append(f"Reading time {brief.reading_time_seconds}s exceeds 60s")
    if not conversation:
        blockers.append("Multi-turn deep dive not demonstrated")
    if not learning.get("events"):
        blockers.append("Learning loop not demonstrated")
    if production.embedding_provider == "hash":
        blockers.append("Neural embeddings not active")
    if acquisition.get("processed_episodes", 0) <= 0:
        blockers.append("No processed episodes")
    llm = prod.get("llm") or {}
    if not llm.get("active_provider"):
        blockers.append("Runtime inspector missing LLM provider section")
    if llm_config.provider == "xai_responses" and llm_config.xai_api_key_configured:
        if production.llm_provider != "xai_responses" and llm.get("fallback_events", 0) == 0:
            blockers.append("xAI configured but active production provider is not xai_responses")
    if not llm_benchmark.get("theme_titles", {}).get("pairs"):
        blockers.append("LLM benchmark missing theme title pairs")
    return blockers


def _certification_report(
    output_dir,
    inspector,
    production,
    second,
    conversation,
    learning,
    llm_benchmark,
    blockers,
    elapsed,
    analyst_elapsed,
    heuristic_elapsed,
    xai_elapsed,
    production_elapsed,
    second_elapsed,
    active_provider,
    llm_config,
) -> str:
    brief = production.intelligence_brief_v3
    llm = (inspector.get("production") or {}).get("llm") or {}
    status = "PASS" if not blockers else "FAIL"
    lines = [
        "# Phase 5.1 Runtime Certification",
        "",
        f"**Status:** {status}",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Evidence Directory:** `{output_dir}`",
        "",
        "## Pipeline Demonstration",
        "",
        "Information Event → Claims → Themes → Intelligence Items → xAI generation → Morning Brief v3 → Deep Dive → Conversation → Runtime Inspector",
        "",
        "## LLM Providers",
        "",
        f"- Configured provider: {llm_config.provider}",
        f"- Active production provider: {active_provider}",
        f"- Fallback provider: {llm_config.fallback_provider}",
        f"- Model: {llm_config.model}",
        f"- API key configured: {llm_config.xai_api_key_configured}",
        "",
        "## Benchmark: Heuristic vs xAI",
        "",
        f"- Theme title quality improved: {llm_benchmark.get('theme_titles', {}).get('improved')}",
        f"- Summary quality improved: {llm_benchmark.get('executive_summaries', {}).get('improved')}",
        f"- Human noticeable improvement: {llm_benchmark.get('quality_evaluation', {}).get('human_noticeable_improvement')}",
        f"- Heuristic enhancement latency: {heuristic_elapsed:.2f}s",
        f"- xAI enhancement latency: {xai_elapsed:.2f}s",
        f"- xAI estimated cost (USD): {llm_benchmark.get('runtime', {}).get('xai', {}).get('estimated_cost_usd', 0)}",
        "",
        "## Token Accounting",
        "",
        f"- Total tokens: {llm.get('token_usage', {}).get('total_tokens', 0)}",
        f"- Fallback events: {llm.get('fallback_events', 0)}",
        f"- Retries: {llm.get('retries', 0)}",
        f"- Failure count: {llm.get('failure_count', 0)}",
        "",
        "## Morning Brief v3",
        "",
        f"- Items: {brief.total_items if brief else 0}",
        f"- Reading time: {brief.reading_time_seconds if brief else 0}s",
        f"- Quality score: {production.quality_metrics.get('overall_score', 0)}",
        "",
        "## Performance",
        "",
        f"- Total elapsed: {elapsed:.2f}s",
        f"- Analyst pipeline: {analyst_elapsed:.2f}s",
        f"- Production enhancement: {production_elapsed:.2f}s",
        f"- Second run (learning): {second_elapsed:.2f}s",
        "",
        "## Blockers",
        "",
    ]
    if blockers:
        lines.extend(f"- {item}" for item in blockers)
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def _brief_markdown(brief) -> str:
    lines = [
        "# Morning Intelligence",
        "",
        f"Generated: {brief.generated_at}",
        f"Reading time: ~{brief.reading_time_seconds} seconds",
        f"Quality score: {brief.quality_score:.2f}",
        "",
    ]
    for entry in brief.items:
        stars = "★" * entry.star_rating + "☆" * (5 - entry.star_rating)
        lines.extend([
            f"## {entry.title}",
            stars,
            "",
            f"**What changed?** {entry.what_changed}",
            f"**Why should I care?** {entry.why_you_care}",
            f"**Why am I seeing this?** {entry.why_surfaced}",
            f"**Evidence:** {entry.evidence_summary}",
            "",
        ])
    return "\n".join(lines)


def _deep_dive_comparison(heuristic_items, xai_items, conversation) -> str:
    lines = ["# Deep Dive Comparison", ""]
    if heuristic_items and xai_items:
        lines.extend([
            "## Executive Summary Samples",
            "",
            f"**Heuristic:** {heuristic_items[0].executive_summary[:400]}",
            "",
            f"**xAI:** {xai_items[0].executive_summary[:400]}",
            "",
        ])
    if conversation:
        start = conversation.get("start") or {}
        follow = conversation.get("follow_up") or {}
        lines.extend([
            "## Conversation",
            "",
            f"**Opening ({start.get('llm_provider', 'unknown')}):**",
            (start.get("messages") or [{}])[-1].get("content", "")[:500],
            "",
            f"**Follow-up:**",
            (follow.get("messages") or [{}])[-1].get("content", "")[:500],
            "",
        ])
    return "\n".join(lines)


def _assert_no_secrets(output_dir: Path, api_key: str) -> None:
    if not api_key:
        return
    for path in output_dir.rglob("*"):
        if not path.is_file():
            continue
        if api_key in path.read_text(encoding="utf-8", errors="ignore"):
            raise RuntimeError(f"Secret leaked into certification artifact: {path}")


def _new_output_dir(base: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = base / f"phase51_intelligence_{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())