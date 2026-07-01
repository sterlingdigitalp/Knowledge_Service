#!/usr/bin/env python3
"""Certify Phase 3 profile-driven intelligence collection on real podcast data."""

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

from knowledge_service.intelligence.config import save_profiles
from knowledge_service.intelligence.collector import IntelligenceCollector
from knowledge_service.intelligence.inspector import inspect_intelligence_runtime
from knowledge_service.intelligence.models import IntelligenceProfile, PodcastSource, WatchListEntry
from knowledge_service.intelligence.scheduler import RuntimeScheduler
from phase3_runtime_inspector import _to_markdown as inspector_markdown


def main() -> int:
    output_dir = _new_output_dir(ROOT / "runtime_evidence")
    for relative in ["config", "state", "raw", "reports", "logs"]:
        (output_dir / relative).mkdir(parents=True, exist_ok=True)

    profiles = _certification_profiles()
    save_profiles(output_dir / "config" / "profiles.json", profiles)
    save_profiles(output_dir / "config" / "profiles.yaml", profiles)

    state_dir = output_dir / "state"
    started = time.perf_counter()
    first_collector = IntelligenceCollector(str(state_dir), profiles=profiles, timeout_ms=30000)
    first_scheduler = RuntimeScheduler(first_collector, interval_seconds=0)
    first_run = first_scheduler.run_daemon(max_iterations=1)

    restart_started = time.perf_counter()
    restarted_collector = IntelligenceCollector(str(state_dir), profiles=profiles, timeout_ms=30000)
    restart_scheduler = RuntimeScheduler(restarted_collector, interval_seconds=0)
    restart_run = restart_scheduler.run_daemon(max_iterations=1)
    restart_seconds = time.perf_counter() - restart_started

    inspector = inspect_intelligence_runtime(state_dir)
    blockers = _blockers(inspector, first_run, restart_run)
    elapsed = time.perf_counter() - started

    _write_json(output_dir / "raw" / "first_scheduler_run.json", first_run)
    _write_json(output_dir / "raw" / "restart_scheduler_run.json", restart_run)
    _write_json(output_dir / "raw" / "runtime_inspector.json", inspector)
    _write_json(output_dir / "raw" / "blockers.json", blockers)
    _write_text(output_dir / "reports" / "PHASE3_RUNTIME_INSPECTOR.md", inspector_markdown(inspector))
    _write_text(output_dir / "PHASE3_RUNTIME_CERTIFICATION.md", _certification_report(output_dir, inspector, first_run, restart_run, blockers, elapsed, restart_seconds))
    _write_text(output_dir / "CORPUS_STATISTICS.md", _corpus_report(inspector))
    _write_text(output_dir / "DEDUPLICATION_RESTART_PROOF.md", _dedupe_report(inspector, first_run, restart_run))
    _write_text(output_dir / "PERFORMANCE_METRICS.md", _performance_report(first_run, restart_run, elapsed, restart_seconds))
    _write_text(output_dir / "RUNTIME_INSPECTOR_OUTPUT.md", inspector_markdown(inspector))
    _write_json(output_dir / "RUNTIME_INSPECTOR_OUTPUT.json", inspector)
    _write_json(output_dir / "EVIDENCE_MANIFEST.json", _manifest(output_dir, inspector, blockers))
    _write_text(output_dir / "RUNTIME_TREE.txt", _runtime_tree(output_dir))
    _write_text(output_dir / "README.md", _readme(output_dir))

    print(str(output_dir))
    return 0 if not blockers else 1


def _certification_profiles() -> List[IntelligenceProfile]:
    return [
        IntelligenceProfile(
            name="AI",
            description="AI systems, coding, datacenters, inference, agents, and enterprise AI.",
            icon="brain",
            color="#3b82f6",
            interests=["AI", "Coding", "Datacenters", "Inference", "Agents", "Enterprise AI"],
            watch_list=[
                WatchListEntry(display_name="Grant Sanderson", aliases=["3Blue1Brown"], priority=8),
                WatchListEntry(display_name="Satya Nadella", organization="Microsoft", priority=7),
                WatchListEntry(display_name="Sam Altman", aliases=["sama"], organization="OpenAI", source_handles={"x": "sama"}, priority=10),
            ],
            required_podcasts=[PodcastSource(name="Dwarkesh Podcast", url="https://podscripts.co/podcasts/dwarkesh-podcast", priority=9, max_episodes=1, polling_interval_seconds=1800)],
        ),
        IntelligenceProfile(
            name="Investing",
            description="Markets, capital allocation, technology investing, and macro debates.",
            icon="chart",
            color="#22c55e",
            interests=["investing", "markets", "AI", "China", "coding"],
            watch_list=[
                WatchListEntry(display_name="Bill Ackman", organization="Pershing Square", priority=9),
                WatchListEntry(display_name="Nate Silver", priority=6),
                WatchListEntry(display_name="Patrick O'Shaughnessy", aliases=["Patrick O’Shaughnessy"], priority=7),
            ],
            required_podcasts=[PodcastSource(name="All-In Podcast", url="https://podscripts.co/podcasts/all-in-with-chamath-jason-sacks-friedberg", priority=8, max_episodes=1, polling_interval_seconds=1800)],
        ),
        IntelligenceProfile(
            name="Founders",
            description="Company building, founder biographies, and operating lessons.",
            icon="spark",
            color="#f59e0b",
            interests=["founders", "company building", "biography", "business"],
            watch_list=[
                WatchListEntry(display_name="Soichiro Honda", organization="Honda", priority=8),
                WatchListEntry(display_name="Joseph Pulitzer", priority=6),
                WatchListEntry(display_name="Steve Jobs", organization="Apple", priority=7),
            ],
            required_podcasts=[PodcastSource(name="Founders", url="https://podscripts.co/podcasts/founders", priority=7, max_episodes=1, polling_interval_seconds=86400)],
        ),
        IntelligenceProfile(
            name="Longevity",
            description="Healthspan, performance, metabolic health, and translational medicine.",
            icon="pulse",
            color="#ef4444",
            interests=["longevity", "muscle", "GLP-1", "metabolic", "healthspan"],
            watch_list=[
                WatchListEntry(display_name="Peter Attia", source_handles={"x": "PeterAttiaMD"}, priority=10),
                WatchListEntry(display_name="Tom Dayspring", priority=7),
                WatchListEntry(display_name="Renato Tomioka", priority=6),
            ],
            required_podcasts=[PodcastSource(name="The Peter Attia Drive", url="https://podscripts.co/podcasts/the-peter-attia-drive", priority=9, max_episodes=1, polling_interval_seconds=86400)],
        ),
    ]


def _blockers(inspector: Dict[str, Any], first_run: Dict[str, Any], restart_run: Dict[str, Any]) -> List[Dict[str, Any]]:
    blockers = []
    summary = inspector["system_summary"]
    if summary["profile_count"] < 4 or summary["enabled_profiles"] < 4:
        blockers.append({"code": "PROFILES_INCOMPLETE", "message": "Expected four enabled certification profiles"})
    if summary["processed_episodes"] < 4:
        blockers.append({"code": "INSUFFICIENT_REAL_TRANSCRIPTS", "message": f"Expected at least four processed real episodes, observed {summary['processed_episodes']}"})
    if summary["knowledge_objects"] <= 0 or summary["chunks"] <= 0 or summary["embeddings"] <= 0:
        blockers.append({"code": "CORPUS_NOT_BUILT", "message": "KnowledgeObjects, chunks, or embeddings were not persisted"})
    if inspector["deduplication"]["transcript_hash_count"] < 4:
        blockers.append({"code": "TRANSCRIPT_HASHES_MISSING", "message": "Persistent transcript hashes were not recorded for all profiles"})
    first_jobs = first_run.get("jobs", [])
    restart_jobs = restart_run.get("jobs", [])
    if not first_jobs or first_jobs[0].get("processed_count", 0) < 4:
        blockers.append({"code": "FIRST_RUN_INCOMPLETE", "message": "Initial scheduled run did not process all expected profile episodes"})
    if not restart_jobs or restart_jobs[0].get("processed_count", -1) != 0 or restart_jobs[0].get("duplicate_count", 0) < 4:
        blockers.append({"code": "RESTART_DEDUPE_FAILED", "message": "Restart run did not prove duplicate prevention"})
    if summary["failed_episodes"]:
        blockers.append({"code": "FAILED_EPISODES", "message": f"Observed {summary['failed_episodes']} failed episodes", "failures": inspector["runtime"]["errors"]})
    return blockers


def _certification_report(output_dir: Path, inspector: Dict[str, Any], first_run: Dict[str, Any], restart_run: Dict[str, Any], blockers: List[Dict[str, Any]], elapsed: float, restart_seconds: float) -> str:
    lines = [
        "# Phase 3 Runtime Certification",
        "",
        f"Generated: {_now_iso()}",
        f"Artifact directory: `{output_dir}`",
        "",
        "## Certification Decision",
        "PASS" if not blockers else "FAIL",
        "",
        "## Runtime Chain",
        "new podcast episode from configured live podcast page -> discovered -> queued -> deduplicated -> transcript acquired -> KnowledgeObjects created -> corpus updated -> inspector updated -> restart run skipped duplicates",
        "",
        "## Profiles",
    ]
    for profile in inspector["profiles"]:
        lines.append(f"- {profile['name']}: enabled={profile['enabled']}, interests={profile['interest_count']}, watch_list={profile['watch_list_size']}, required_podcasts={profile['required_podcasts']}")
    lines.extend([
        "",
        "## Corpus Summary",
        f"- episodes: {inspector['corpus']['episodes']}",
        f"- processed_episodes: {inspector['corpus']['processed_episodes']}",
        f"- duplicate_episodes: {inspector['corpus']['duplicate_episodes']}",
        f"- duplicate_detections: {inspector['corpus'].get('duplicate_detections', 0)}",
        f"- knowledge_objects: {inspector['corpus']['knowledge_objects']}",
        f"- chunks: {inspector['corpus']['chunks']}",
        f"- embeddings: {inspector['corpus']['embeddings']}",
        f"- source_graphs: {inspector['corpus']['source_graphs']}",
        "",
        "## Deduplication",
        f"- acquisition_hash_count: {inspector['deduplication']['acquisition_hash_count']}",
        f"- transcript_hash_count: {inspector['deduplication']['transcript_hash_count']}",
        f"- source_hash_count: {inspector['deduplication']['source_hash_count']}",
        "",
        "## Scheduler Evidence",
        f"- first_run_iterations: {first_run.get('iterations')}",
        f"- first_run_processed: {first_run.get('jobs', [{}])[0].get('processed_count') if first_run.get('jobs') else None}",
        f"- restart_run_processed: {restart_run.get('jobs', [{}])[0].get('processed_count') if restart_run.get('jobs') else None}",
        f"- restart_run_duplicates: {restart_run.get('jobs', [{}])[0].get('duplicate_count') if restart_run.get('jobs') else None}",
        "",
        "## Performance",
        f"- total_certification_seconds: {round(elapsed, 3)}",
        f"- restart_proof_seconds: {round(restart_seconds, 3)}",
        "",
        "## Remaining Blockers",
        "```json",
        json.dumps(blockers, indent=2, sort_keys=True),
        "```",
    ])
    return "\n".join(lines)


def _corpus_report(inspector: Dict[str, Any]) -> str:
    return "# Corpus Statistics\n\n```json\n" + json.dumps(inspector["corpus"], indent=2, sort_keys=True) + "\n```\n"


def _dedupe_report(inspector: Dict[str, Any], first_run: Dict[str, Any], restart_run: Dict[str, Any]) -> str:
    return "# Deduplication Restart Proof\n\n" + "\n".join([
        f"- first_run_processed: {first_run.get('jobs', [{}])[0].get('processed_count') if first_run.get('jobs') else None}",
        f"- restart_run_processed: {restart_run.get('jobs', [{}])[0].get('processed_count') if restart_run.get('jobs') else None}",
        f"- restart_run_duplicates: {restart_run.get('jobs', [{}])[0].get('duplicate_count') if restart_run.get('jobs') else None}",
        f"- acquisition_hash_count: {inspector['deduplication']['acquisition_hash_count']}",
        f"- transcript_hash_count: {inspector['deduplication']['transcript_hash_count']}",
        f"- source_hash_count: {inspector['deduplication']['source_hash_count']}",
    ]) + "\n"


def _performance_report(first_run: Dict[str, Any], restart_run: Dict[str, Any], elapsed: float, restart_seconds: float) -> str:
    return "# Performance Metrics\n\n```json\n" + json.dumps({
        "total_certification_seconds": round(elapsed, 6),
        "restart_proof_seconds": round(restart_seconds, 6),
        "first_run": first_run,
        "restart_run": restart_run,
    }, indent=2, sort_keys=True) + "\n```\n"


def _manifest(output_dir: Path, inspector: Dict[str, Any], blockers: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "artifact_dir": str(output_dir),
        "generated_at": _now_iso(),
        "status": "pass" if not blockers else "fail",
        "required_files": [
            "PHASE3_RUNTIME_CERTIFICATION.md",
            "RUNTIME_INSPECTOR_OUTPUT.json",
            "RUNTIME_INSPECTOR_OUTPUT.md",
            "CORPUS_STATISTICS.md",
            "DEDUPLICATION_RESTART_PROOF.md",
            "PERFORMANCE_METRICS.md",
            "config/profiles.json",
            "config/profiles.yaml",
            "state/profiles.json",
            "state/episodes.json",
            "state/dedupe.json",
            "state/knowledge_objects.jsonl",
        ],
        "system_summary": inspector["system_summary"],
        "blockers": blockers,
    }


def _readme(output_dir: Path) -> str:
    return "\n".join([
        "# Phase 3 Intelligence Collection Evidence",
        "",
        f"Artifact directory: `{output_dir}`",
        "",
        "Reproduce with:",
        "```bash",
        "PYTHONPATH=src ./.venv/bin/python examples/certify_phase3_intelligence_collection.py",
        "```",
    ])


def _runtime_tree(output_dir: Path) -> str:
    lines = []
    for root, dirs, files in os.walk(output_dir):
        dirs.sort()
        files.sort()
        rel = Path(root).relative_to(output_dir)
        indent = "  " * (0 if str(rel) == "." else len(rel.parts))
        lines.append(f"{indent}{rel if str(rel) != '.' else output_dir.name}/")
        for file_name in files:
            lines.append(f"{indent}  {file_name}")
    return "\n".join(lines)


def _new_output_dir(parent: Path) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = parent / f"phase3_intelligence_{stamp}"
    counter = 1
    while path.exists():
        path = parent / f"phase3_intelligence_{stamp}_{counter}"
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
