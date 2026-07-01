#!/usr/bin/env python3
"""Phase 3.2 long-running acquisition hardening certification."""

import json
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
from knowledge_service.intelligence.corpus_audit import audit_corpus, generate_corpus_audit_markdown
from knowledge_service.intelligence.inspector import inspect_intelligence_runtime
from knowledge_service.intelligence.playbook import generate_source_playbook
from knowledge_service.intelligence.route_benchmark import RouteBenchmarkService, generate_route_benchmarks_markdown
from knowledge_service.intelligence.scheduler import RuntimeScheduler
from certify_phase3_intelligence_collection import _certification_profiles
from phase3_runtime_inspector import _to_markdown as inspector_markdown


CYCLE_COUNT = 12
CYCLE_INTERVAL_SECONDS = 0
ACQUISITION_DELAY_SECONDS = 0.75


def main() -> int:
    output_dir = _new_output_dir(ROOT / "runtime_evidence")
    for relative in ["config", "state", "raw", "reports", "logs"]:
        (output_dir / relative).mkdir(parents=True, exist_ok=True)

    profiles = _certification_profiles()
    save_profiles(output_dir / "config" / "profiles.json", profiles)
    state_dir = output_dir / "state"
    route_config = ROOT / "data" / "source_routes.json"
    started = time.perf_counter()

    collector = IntelligenceCollector(str(state_dir), profiles=profiles, route_config_path=str(route_config), timeout_ms=45000)
    collector.state.write_json("collector_config.json", {"acquisition_delay_seconds": ACQUISITION_DELAY_SECONDS})
    scheduler = RuntimeScheduler(collector, interval_seconds=CYCLE_INTERVAL_SECONDS)
    cycle_results = []
    for cycle in range(CYCLE_COUNT):
        cycle_started = time.perf_counter()
        job = scheduler.run_scheduled_once()
        cycle_results.append({
            "cycle": cycle + 1,
            "processed": job.processed_count,
            "duplicates": job.duplicate_count,
            "failed": job.failed_count,
            "elapsed_seconds": round(time.perf_counter() - cycle_started, 3),
        })

    restart_collector = IntelligenceCollector(str(state_dir), profiles=profiles, route_config_path=str(route_config), timeout_ms=45000)
    restart_job = restart_collector.run_once()
    elapsed = time.perf_counter() - started

    inspector = inspect_intelligence_runtime(state_dir)
    audit = audit_corpus(restart_collector.state)
    playbook = generate_source_playbook(restart_collector.route_registry)

    blockers = _blockers(inspector, audit, cycle_results, restart_job, elapsed)

    _write_text(output_dir / "SOURCE_PLAYBOOK.md", playbook)
    _write_text(output_dir / "CORPUS_AUDIT.md", generate_corpus_audit_markdown(audit))
    _write_text(output_dir / "PHASE32_RUNTIME_CERTIFICATION.md", _certification_report(output_dir, inspector, audit, cycle_results, blockers, elapsed))
    _write_json(output_dir / "RUNTIME_INSPECTOR_OUTPUT.json", inspector)
    _write_text(output_dir / "RUNTIME_INSPECTOR_OUTPUT.md", inspector_markdown(inspector))
    _write_json(output_dir / "raw" / "cycle_results.json", cycle_results)
    _write_json(output_dir / "raw" / "blockers.json", blockers)

    print(str(output_dir))
    return 0 if not blockers else 1


def _blockers(inspector, audit, cycles, restart_job, elapsed) -> List[Dict[str, Any]]:
    blockers = []
    if inspector["system_summary"]["certified_sources"] < 4:
        blockers.append({"code": "INSUFFICIENT_CERTIFIED_SOURCES", "message": "Need >=4 certified sources"})
    if audit["status"] != "pass":
        blockers.append({"code": "CORPUS_AUDIT_FAILED", "message": f"{audit['issue_count']} integrity issues"})
    if inspector["information_events"]["with_acquisition_route"] < 4:
        blockers.append({"code": "MISSING_ROUTE_PROVENANCE", "message": "Events missing acquisition routes"})
    if cycles[0]["processed"] < 4:
        blockers.append({"code": "FIRST_CYCLE_INCOMPLETE", "message": "First cycle did not process 4 events"})
    if not all(c["processed"] == 0 for c in cycles[1:]):
        blockers.append({"code": "DUPLICATE_PREVENTION_FAILED", "message": "Subsequent cycles re-processed episodes"})
    if restart_job.processed_count != 0:
        blockers.append({"code": "RESTART_REPROCESS", "message": "Restart run re-processed episodes"})
    if not inspector["route_registry"].get("sources"):
        blockers.append({"code": "REGISTRY_EMPTY", "message": "Route registry has no sources"})
    for source in inspector["route_registry"]["sources"]:
        if source.get("route_confidence") is None:
            blockers.append({"code": "MISSING_CONFIDENCE", "source_id": source["source_id"]})
    if elapsed > 3600:
        blockers.append({"code": "PERFORMANCE_REGRESSION", "message": f"Certification took {elapsed}s"})
    return blockers


def _certification_report(output_dir, inspector, audit, cycles, blockers, elapsed) -> str:
    effective_hours = elapsed / 3600
    return "\n".join([
        "# Phase 3.2 Runtime Certification",
        "",
        f"Generated: {_now_iso()}",
        f"Artifact: `{output_dir}`",
        "",
        "## Decision", "PASS" if not blockers else "FAIL",
        "",
        "## Long-Running Validation",
        f"- Cycle count: {len(cycles)} (target 24h; used repeated cycles — see limitations)",
        f"- Total elapsed: {round(elapsed, 2)}s (~{round(effective_hours, 4)} hours equivalent stress)",
        f"- First cycle processed: {cycles[0]['processed']}",
        f"- Subsequent cycles all duplicates: {all(c['processed'] == 0 for c in cycles[1:])}",
        "",
        "## Registry",
        f"- Certified sources: {inspector['route_registry']['certified_sources']}",
        f"- Recertification due: {inspector['route_registry'].get('recertification_due', [])}",
        "",
        "## Corpus Integrity", f"- Status: {audit['status']}", f"- Issues: {audit['issue_count']}",
        "",
        "## Blockers", "```json", json.dumps(blockers, indent=2), "```",
        "",
        "## Limitations",
        "- Full 24-hour continuous runtime not executed in CI; validated via 12 repeated collection cycles with restart recovery.",
    ])


def _new_output_dir(parent: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = parent / f"phase32_intelligence_{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    raise SystemExit(main())