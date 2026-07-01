#!/usr/bin/env python3
"""Phase 4.1 Intelligence Synthesis runtime certification."""

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

from knowledge_service.analyst.pipeline import IntelligenceAnalystPipeline
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
    pipeline_started = time.perf_counter()
    pipeline = IntelligenceAnalystPipeline(str(state_dir))
    result = pipeline.run()
    pipeline_elapsed = time.perf_counter() - pipeline_started

    deep_dive = None
    intel_brief = result.intelligence_brief
    if intel_brief and intel_brief.items:
        deep_dive = pipeline.intelligence_deep_dive(intel_brief.items[0].intelligence_item_id)

    inspector = inspect_intelligence_runtime(state_dir)
    elapsed = time.perf_counter() - started
    blockers = _blockers(inspector, result, deep_dive, acquisition)

    _write_json(output_dir / "raw" / "acquisition.json", acquisition)
    _write_json(output_dir / "raw" / "pipeline_result.json", result.to_dict())
    _write_json(output_dir / "raw" / "deep_dive.json", deep_dive.to_dict() if deep_dive else None)
    _write_json(output_dir / "raw" / "blockers.json", blockers)
    _write_json(output_dir / "RUNTIME_INSPECTOR_OUTPUT.json", inspector)
    _write_text(output_dir / "RUNTIME_INSPECTOR_OUTPUT.md", inspector_markdown(inspector))
    _write_text(output_dir / "PHASE41_RUNTIME_CERTIFICATION.md", _certification_report(
        output_dir, inspector, result, deep_dive, blockers, elapsed, pipeline_elapsed,
    ))
    if intel_brief:
        _write_json(output_dir / "MORNING_INTELLIGENCE_BRIEF.json", intel_brief.to_dict())
        _write_text(output_dir / "MORNING_INTELLIGENCE_BRIEF.md", _brief_markdown(intel_brief))

    print(str(output_dir))
    return 0 if not blockers else 1


def _seed_corpus(state_dir: Path, profiles) -> Dict[str, Any]:
    shutil.copytree(DEFAULT_PRIOR_STATE, state_dir, dirs_exist_ok=True)
    save_profiles(state_dir.parent / "config" / "profiles.json", profiles)
    collector = IntelligenceCollector(str(state_dir), profiles=profiles, route_config_path=str(ROOT / "data" / "source_routes.json"))
    episodes = collector.corpus.episodes()
    return {
        "mode": "seeded_from_phase32",
        "source_state": str(DEFAULT_PRIOR_STATE),
        "processed_episodes": sum(1 for episode in episodes if episode.status.value == "processed"),
        "episode_count": len(episodes),
    }


def _blockers(inspector, result, deep_dive, acquisition) -> List[str]:
    blockers: List[str] = []
    analyst = inspector.get("analyst") or {}
    synthesis = analyst.get("synthesis") or {}
    briefing = analyst.get("briefing") or {}

    if analyst.get("status") != "pass":
        blockers.append("Analyst runtime status is not pass")
    if result.claims_extracted <= 0:
        blockers.append("No claims extracted")
    if synthesis.get("themes", 0) <= 0:
        blockers.append("No themes discovered")
    if synthesis.get("intelligence_items", 0) <= 0:
        blockers.append("No intelligence items synthesized")
    if not result.intelligence_brief or result.intelligence_brief.total_items <= 0:
        blockers.append("Intelligence brief has no items")
    items = result.intelligence_brief.total_items if result.intelligence_brief else 0
    if items < 5:
        blockers.append(f"Brief has {items} items (minimum 5 required)")
    if items > 15:
        blockers.append(f"Brief has {items} items (maximum 15 allowed)")
    if briefing.get("reading_time_seconds", 0) > 60:
        blockers.append(f"Reading time {briefing.get('reading_time_seconds')}s exceeds 60s target")
    if deep_dive is None:
        blockers.append("Intelligence deep dive not generated")
    if acquisition.get("processed_episodes", 0) <= 0:
        blockers.append("No processed episodes in corpus")
    if synthesis.get("compression_ratio", 0) < 10:
        blockers.append(f"Compression ratio {synthesis.get('compression_ratio')} below 10x target")
    return blockers


def _certification_report(output_dir, inspector, result, deep_dive, blockers, elapsed, pipeline_elapsed) -> str:
    analyst = inspector.get("analyst") or {}
    synthesis = analyst.get("synthesis") or {}
    briefing = analyst.get("briefing") or {}
    status = "PASS" if not blockers else "FAIL"
    lines = [
        "# Phase 4.1 Runtime Certification",
        "",
        f"**Status:** {status}",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Evidence Directory:** `{output_dir}`",
        "",
        "## Pipeline Chain",
        "",
        "1. Information Event — Phase 3.2 certified corpus",
        f"2. Claims extracted — {result.claims_extracted}",
        f"3. Themes discovered — {synthesis.get('themes', 0)}",
        f"4. Intelligence Items — {synthesis.get('intelligence_items', 0)}",
        f"5. Morning Brief v2 — {briefing.get('latest_total_items', 0)} items",
        f"6. Deep dive — {'yes' if deep_dive else 'no'}",
        "",
        "## Compression Metrics",
        "",
        f"- Claims: {analyst.get('claims', {}).get('total', 0)}",
        f"- Intelligence Items: {synthesis.get('intelligence_items', 0)}",
        f"- Compression ratio: {synthesis.get('compression_ratio', 0)}:1",
        f"- Claims per item: {synthesis.get('claims_per_item', 0)}",
        f"- Reading time: {briefing.get('reading_time_seconds', 0)}s",
        "",
        "## Performance",
        "",
        f"- Total elapsed: {elapsed:.2f}s",
        f"- Pipeline elapsed: {pipeline_elapsed:.2f}s",
        f"- Synthesis latency: {analyst.get('pipeline', {}).get('synthesis_latency_seconds', {})}",
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
        f"Items: {brief.total_items} | Compression: {brief.compression_ratio}:1",
        "",
    ]
    for entry in brief.items:
        stars = "★" * entry.star_rating + "☆" * (5 - entry.star_rating)
        lines.extend([
            f"## {entry.title}",
            f"{stars}",
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
    path = base / f"phase41_intelligence_{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())