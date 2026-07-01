#!/usr/bin/env python3
"""Certify Phase 3.1 person-centric collection with route registry."""

import json
import os
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
from knowledge_service.intelligence.models import IntelligenceProfile, PodcastSource, WatchListEntry
from knowledge_service.intelligence.route_registry import AcquisitionRouteRegistry, generate_route_certification_markdown
from knowledge_service.intelligence.scheduler import RuntimeScheduler
from certify_phase3_intelligence_collection import _certification_profiles
from phase3_runtime_inspector import _to_markdown as inspector_markdown


def main() -> int:
    output_dir = _new_output_dir(ROOT / "runtime_evidence")
    for relative in ["config", "state", "raw", "reports", "logs"]:
        (output_dir / relative).mkdir(parents=True, exist_ok=True)

    profiles = _certification_profiles()
    save_profiles(output_dir / "config" / "profiles.json", profiles)
    route_config = ROOT / "data" / "source_routes.yaml"
    state_dir = output_dir / "state"
    started = time.perf_counter()

    collector = IntelligenceCollector(
        str(state_dir),
        profiles=profiles,
        route_config_path=str(route_config),
        timeout_ms=45000,
    )
    registry = collector.route_registry
    first_run = RuntimeScheduler(collector, interval_seconds=0).run_daemon(max_iterations=1)

    restart_collector = IntelligenceCollector(
        str(state_dir),
        profiles=profiles,
        route_config_path=str(route_config),
        timeout_ms=45000,
    )
    restart_started = time.perf_counter()
    restart_run = RuntimeScheduler(restart_collector, interval_seconds=0).run_daemon(max_iterations=1)
    restart_seconds = time.perf_counter() - restart_started

    inspector = inspect_intelligence_runtime(state_dir)
    blockers = _blockers(inspector, first_run, restart_run)
    elapsed = time.perf_counter() - started

    route_report = generate_route_certification_markdown(registry)
    _write_text(output_dir / "ROUTE_CERTIFICATION.md", route_report)
    _write_text(output_dir / "reports" / "ROUTE_CERTIFICATION.md", route_report)
    _write_json(output_dir / "raw" / "runtime_inspector.json", inspector)
    _write_json(output_dir / "raw" / "route_registry.json", registry.summary())
    _write_json(output_dir / "raw" / "blockers.json", blockers)
    _write_text(output_dir / "PHASE31_RUNTIME_CERTIFICATION.md", _certification_report(output_dir, inspector, first_run, restart_run, blockers, elapsed, restart_seconds))
    _write_text(output_dir / "reports" / "PHASE31_RUNTIME_INSPECTOR.md", inspector_markdown(inspector))
    _write_text(output_dir / "RUNTIME_INSPECTOR_OUTPUT.md", inspector_markdown(inspector))
    _write_json(output_dir / "RUNTIME_INSPECTOR_OUTPUT.json", inspector)

    print(str(output_dir))
    return 0 if not blockers else 1


def _blockers(inspector: Dict[str, Any], first_run: Dict[str, Any], restart_run: Dict[str, Any]) -> List[Dict[str, Any]]:
    blockers = []
    summary = inspector["system_summary"]
    if summary.get("certified_sources", 0) < 4:
        blockers.append({"code": "REGISTRY_NOT_CERTIFIED", "message": "Expected at least four certified registry sources"})
    if summary["processed_episodes"] < 4:
        blockers.append({"code": "INSUFFICIENT_PROCESSED_EVENTS", "message": f"Expected >=4 processed events, observed {summary['processed_episodes']}"})
    if inspector["information_events"]["with_acquisition_route"] < 4:
        blockers.append({"code": "MISSING_ROUTE_PROVENANCE", "message": "Processed events missing acquisition route provenance"})
    first_jobs = first_run.get("jobs", [])
    restart_jobs = restart_run.get("jobs", [])
    if not first_jobs or first_jobs[0].get("processed_count", 0) < 4:
        blockers.append({"code": "FIRST_RUN_INCOMPLETE", "message": "Initial run did not process expected events"})
    if not restart_jobs or restart_jobs[0].get("processed_count", -1) != 0:
        blockers.append({"code": "RESTART_DEDUPE_FAILED", "message": "Restart run did not skip duplicates"})
    if summary["failed_episodes"]:
        blockers.append({"code": "FAILED_EVENTS", "message": f"Observed {summary['failed_episodes']} failed events"})
    return blockers


def _certification_report(output_dir: Path, inspector: Dict[str, Any], first_run: Dict[str, Any], restart_run: Dict[str, Any], blockers: List[Dict[str, Any]], elapsed: float, restart_seconds: float) -> str:
    lines = [
        "# Phase 3.1 Runtime Certification",
        "",
        f"Generated: {_now_iso()}",
        f"Artifact directory: `{output_dir}`",
        "",
        "## Certification Decision",
        "PASS" if not blockers else "FAIL",
        "",
        "## Runtime Chain",
        "watched person -> new appearance -> information event -> registry lookup -> preferred acquisition route -> transcript -> KnowledgeObject -> corpus update -> runtime inspector",
        "",
        "## Registry Statistics",
        f"- source_count: {inspector['route_registry']['source_count']}",
        f"- certified_sources: {inspector['route_registry']['certified_sources']}",
        "",
        "## Information Events",
        f"- total: {inspector['information_events']['total']}",
        f"- with_acquisition_route: {inspector['information_events']['with_acquisition_route']}",
        "",
        "## Performance",
        f"- total_seconds: {round(elapsed, 3)}",
        f"- restart_seconds: {round(restart_seconds, 3)}",
        "",
        "## Blockers",
        "```json",
        json.dumps(blockers, indent=2, sort_keys=True),
        "```",
    ]
    return "\n".join(lines)


def _new_output_dir(parent: Path) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = parent / f"phase31_intelligence_{stamp}"
    counter = 1
    while path.exists():
        path = parent / f"phase31_intelligence_{stamp}_{counter}"
        counter += 1
    path.mkdir(parents=True)
    return path


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    raise SystemExit(main())