#!/usr/bin/env python3
"""Phase 5 Production Personal Intelligence Analyst runtime certification."""

import json
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

from knowledge_service.production.pipeline import ProductionIntelligencePipeline
from knowledge_service.intelligence.collector import IntelligenceCollector
from knowledge_service.intelligence.config import save_profiles
from knowledge_service.intelligence.inspector import inspect_intelligence_runtime
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

    acquisition = _seed_corpus(state_dir, profiles)
    pipeline = ProductionIntelligencePipeline(str(state_dir))

    first_started = time.perf_counter()
    first_result = pipeline.run(manual=True)
    first_elapsed = time.perf_counter() - first_started

    conversation = None
    brief = first_result.production.intelligence_brief_v3
    if brief and brief.items:
        item_id = brief.items[0].intelligence_item_id
        session = pipeline.start_conversation(item_id)
        if session:
            conversation = {
                "start": session,
                "follow_up": pipeline.continue_conversation(session["session_id"], "Show me the timeline"),
            }

    learning = _simulate_learning_loop(pipeline, first_result)
    second_started = time.perf_counter()
    second_result = pipeline.rerun_with_learning()
    second_elapsed = time.perf_counter() - second_started

    inspector = inspect_intelligence_runtime(state_dir)
    elapsed = time.perf_counter() - started
    blockers = _blockers(inspector, first_result, second_result, conversation, learning, acquisition, pipeline)

    _write_json(output_dir / "raw" / "acquisition.json", acquisition)
    _write_json(output_dir / "raw" / "first_pipeline_result.json", first_result.to_dict())
    _write_json(output_dir / "raw" / "second_pipeline_result.json", second_result.to_dict())
    _write_json(output_dir / "raw" / "learning_loop.json", learning)
    _write_json(output_dir / "raw" / "conversation.json", conversation)
    _write_json(output_dir / "raw" / "blockers.json", blockers)
    _write_json(output_dir / "RUNTIME_INSPECTOR_OUTPUT.json", inspector)
    _write_text(output_dir / "RUNTIME_INSPECTOR_OUTPUT.md", inspector_markdown(inspector))
    _write_text(output_dir / "PHASE5_RUNTIME_CERTIFICATION.md", _certification_report(
        output_dir, inspector, first_result, second_result, conversation, learning, blockers, elapsed, first_elapsed, second_elapsed,
    ))
    if brief:
        _write_json(output_dir / "MORNING_INTELLIGENCE_BRIEF.json", brief.to_dict())
        _write_text(output_dir / "MORNING_INTELLIGENCE_BRIEF.md", _brief_markdown(brief))
    _write_json(output_dir / "BENCHMARK_VS_PHASE41.json", first_result.benchmark)

    print(str(output_dir))
    return 0 if not blockers else 1


def _seed_corpus(state_dir: Path, profiles) -> Dict[str, Any]:
    shutil.copytree(DEFAULT_PRIOR_STATE, state_dir, dirs_exist_ok=True)
    save_profiles(state_dir.parent / "config" / "profiles.json", profiles)
    collector = IntelligenceCollector(str(state_dir), profiles=profiles, route_config_path=str(ROOT / "data" / "source_routes.json"))
    episodes = collector.corpus.episodes()
    return {
        "mode": "seeded_from_phase32",
        "processed_episodes": sum(1 for episode in episodes if episode.status.value == "processed"),
    }


def _simulate_learning_loop(pipeline: ProductionIntelligencePipeline, result) -> Dict[str, Any]:
    brief = result.production.intelligence_brief_v3
    if not brief or not brief.items:
        return {"events": []}
    events = []
    lead = brief.items[0]
    runner = brief.items[1] if len(brief.items) > 1 else lead
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


def _blockers(inspector, first, second, conversation, learning, acquisition, pipeline) -> List[str]:
    blockers: List[str] = []
    prod = inspector.get("production") or {}
    if prod.get("status") != "pass":
        blockers.append("Production runtime status is not pass")
    brief = first.production.intelligence_brief_v3
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
    if first.production.embedding_provider == "hash":
        blockers.append("Neural embeddings not active")
    if first.production.quality_metrics.get("overall_score", 0) < 0.4:
        blockers.append("Brief quality score below threshold")
    if acquisition.get("processed_episodes", 0) <= 0:
        blockers.append("No processed episodes")
    prefs = pipeline.personalization.load_preferences()
    boosted = learning.get("boosted_item")
    if boosted and boosted not in prefs.get("tell_me_more_items", []):
        blockers.append("Tell-me-more feedback not recorded")
    topic_weights = prefs.get("topic_weights", {})
    if boosted and not topic_weights:
        blockers.append("Personalized topic weights not updated after feedback")
    return blockers


def _certification_report(output_dir, inspector, first, second, conversation, learning, blockers, elapsed, first_elapsed, second_elapsed) -> str:
    prod = inspector.get("production") or {}
    brief = first.production.intelligence_brief_v3
    benchmark = first.benchmark
    status = "PASS" if not blockers else "FAIL"
    lines = [
        "# Phase 5 Runtime Certification",
        "",
        f"**Status:** {status}",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Evidence Directory:** `{output_dir}`",
        "",
        "## Learning Loop",
        "",
        "1. Pipeline run → Brief v3 generated",
        f"2. User feedback simulated ({len(learning.get('events', []))} events)",
        "3. Personalized ranking updated",
        "4. Second pipeline run with adapted ranking",
        f"5. Multi-turn conversation: {'yes' if conversation else 'no'}",
        "",
        "## Quality",
        "",
        f"- Brief items: {brief.total_items if brief else 0}",
        f"- Reading time: {brief.reading_time_seconds if brief else 0}s",
        f"- Quality score: {first.production.quality_metrics.get('overall_score', 0)}",
        f"- Embedding provider: {first.production.embedding_provider}",
        f"- LLM provider: {first.production.llm_provider}",
        "",
        "## Benchmark vs Phase 4.1",
        "",
        f"- Neural embedding delta: {benchmark.get('improvement_delta', 'n/a')}",
        f"- Title quality improved: {benchmark.get('brief', {}).get('title_quality_improved', False)}",
        f"- Phase 5 compression: {benchmark.get('brief', {}).get('phase5_compression', 0)}",
        "",
        "## Performance",
        "",
        f"- Total elapsed: {elapsed:.2f}s",
        f"- First run: {first_elapsed:.2f}s",
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


def _new_output_dir(base: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = base / f"phase5_intelligence_{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())