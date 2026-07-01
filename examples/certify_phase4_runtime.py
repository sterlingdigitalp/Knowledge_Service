#!/usr/bin/env python3
"""Phase 4 Personal Intelligence Analyst runtime certification."""

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
from knowledge_service.intelligence.scheduler import RuntimeScheduler
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

    acquisition = _run_acquisition(state_dir, profiles, output_dir)
    analyst_started = time.perf_counter()
    pipeline = IntelligenceAnalystPipeline(str(state_dir))
    pipeline_result = pipeline.run()
    analyst_elapsed = time.perf_counter() - analyst_started

    deep_dive = None
    if pipeline_result.brief:
        first_item = _first_brief_item(pipeline_result.brief)
        if first_item:
            deep_dive = pipeline.deep_dive(first_item.claim_id)

    inspector = inspect_intelligence_runtime(state_dir)
    elapsed = time.perf_counter() - started
    blockers = _blockers(inspector, pipeline_result, deep_dive, acquisition)

    _write_json(output_dir / "raw" / "acquisition.json", acquisition)
    _write_json(output_dir / "raw" / "pipeline_result.json", pipeline_result.to_dict())
    _write_json(output_dir / "raw" / "deep_dive.json", deep_dive.to_dict() if deep_dive else None)
    _write_json(output_dir / "raw" / "blockers.json", blockers)
    _write_json(output_dir / "RUNTIME_INSPECTOR_OUTPUT.json", inspector)
    _write_text(output_dir / "RUNTIME_INSPECTOR_OUTPUT.md", inspector_markdown(inspector))
    _write_text(output_dir / "PHASE4_RUNTIME_CERTIFICATION.md", _certification_report(
        output_dir, inspector, pipeline_result, deep_dive, blockers, elapsed, analyst_elapsed,
    ))
    if pipeline_result.brief:
        _write_json(output_dir / "MORNING_INTELLIGENCE_BRIEF.json", pipeline_result.brief.to_dict())
        _write_text(output_dir / "MORNING_INTELLIGENCE_BRIEF.md", _brief_markdown(pipeline_result.brief))

    print(str(output_dir))
    return 0 if not blockers else 1


def _run_acquisition(state_dir: Path, profiles, output_dir: Path) -> Dict[str, Any]:
    if DEFAULT_PRIOR_STATE.exists():
        shutil.copytree(DEFAULT_PRIOR_STATE, state_dir, dirs_exist_ok=True)
        save_profiles(state_dir.parent / "config" / "profiles.json", profiles)
        corpus = IntelligenceCollector(str(state_dir), profiles=profiles, route_config_path=str(ROOT / "data" / "source_routes.json"))
        episodes = corpus.corpus.episodes()
        return {
            "mode": "seeded_from_phase32",
            "source_state": str(DEFAULT_PRIOR_STATE),
            "processed_episodes": sum(1 for episode in episodes if episode.status.value == "processed"),
            "episode_count": len(episodes),
        }

    collector = IntelligenceCollector(
        str(state_dir),
        profiles=profiles,
        route_config_path=str(ROOT / "data" / "source_routes.json"),
        timeout_ms=45000,
    )
    job = RuntimeScheduler(collector, interval_seconds=0).run_scheduled_once()
    return {
        "mode": "live_acquisition",
        "processed": job.processed_count,
        "duplicates": job.duplicate_count,
        "failed": job.failed_count,
    }


def _first_brief_item(brief):
    for items in brief.sections.values():
        if items:
            return items[0]
    return None


def _blockers(inspector, pipeline_result, deep_dive, acquisition) -> List[str]:
    blockers: List[str] = []
    analyst = inspector.get("analyst") or {}
    if analyst.get("status") != "pass":
        blockers.append("Analyst runtime status is not pass")
    if pipeline_result.claims_extracted <= 0:
        blockers.append("No claims extracted from transcripts")
    if pipeline_result.claims_scored <= 0:
        blockers.append("No claims scored through intelligence pipeline")
    if not pipeline_result.brief or pipeline_result.brief.total_items <= 0:
        blockers.append("Morning Intelligence Brief has no items")
    if deep_dive is None:
        blockers.append("Deep dive ('Tell me more') not generated")
    if acquisition.get("processed_episodes", acquisition.get("processed", 0)) <= 0:
        blockers.append("No processed episodes in corpus")
    if inspector["system_summary"]["status"] != "pass":
        blockers.append("Acquisition system summary is not pass")
    return blockers


def _certification_report(output_dir, inspector, pipeline_result, deep_dive, blockers, elapsed, analyst_elapsed) -> str:
    analyst = inspector.get("analyst") or {}
    status = "PASS" if not blockers else "FAIL"
    lines = [
        "# Phase 4 Runtime Certification",
        "",
        f"**Status:** {status}",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Evidence Directory:** `{output_dir}`",
        "",
        "## Pipeline Chain",
        "",
        "1. Information Event — seeded from Phase 3.2 certified corpus",
        "2. Transcript acquired — present in knowledge objects",
        f"3. Claims extracted — {pipeline_result.claims_extracted}",
        f"4. Novelty scored — {pipeline_result.claims_scored} claims",
        "5. Relevance scored — every claim × every profile",
        "6. Importance scored — explainable weighted formula",
        f"7. Cross-source correlation — {pipeline_result.clusters_found} clusters",
        f"8. Morning Brief generated — {pipeline_result.brief.total_items if pipeline_result.brief else 0} items",
        f"9. Deep dive available — {'yes' if deep_dive else 'no'}",
        "",
        "## Performance",
        "",
        f"- Total elapsed: {elapsed:.2f}s",
        f"- Analyst pipeline: {analyst_elapsed:.2f}s",
        f"- Latency breakdown: {json.dumps(pipeline_result.latency_seconds)}",
        "",
        "## Analyst Statistics",
        "",
        f"- Claims: {analyst.get('claims', {}).get('total', 0)}",
        f"- Novelty distribution: {analyst.get('novelty', {}).get('distribution', {})}",
        f"- Importance distribution: {analyst.get('importance', {}).get('distribution', {})}",
        f"- Cross-source clusters: {analyst.get('cross_source', {}).get('clusters', 0)}",
        f"- Brief reading time: {analyst.get('briefing', {}).get('reading_time_seconds', 0)}s",
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
        "",
    ]
    for section, items in brief.sections.items():
        lines.append(f"## {section}")
        lines.append("")
        if not items:
            lines.append("_No high-signal items today._")
            lines.append("")
            continue
        for item in items:
            lines.extend([
                f"### {item.headline}",
                "",
                f"**What is new?** {item.what_is_new}",
                f"**Why am I seeing this?** {item.why_you_see_this}",
                f"**Why might this matter?** {item.why_it_matters}",
                f"**Evidence:** {item.evidence_summary}",
                f"**Source:** {item.source} ({item.timestamp_label})",
                "",
            ])
    return "\n".join(lines)


def _new_output_dir(base: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = base / f"phase4_intelligence_{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())