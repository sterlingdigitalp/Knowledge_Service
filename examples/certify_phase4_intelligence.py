#!/usr/bin/env python3
"""Certify Phase 4 Personal Intelligence Analyst on real persisted corpus state."""

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from knowledge_service.intelligence.analyst import run_phase4_pipeline
from knowledge_service.intelligence.briefing import LATEST_MORNING_BRIEF_FILE, MorningBrief, generate_morning_brief_markdown
from knowledge_service.intelligence.deep_dive import LATEST_DEEP_DIVES_FILE
from knowledge_service.intelligence.inspector import inspect_intelligence_runtime
from knowledge_service.intelligence.state import FileStateStore
from phase3_runtime_inspector import _to_markdown as inspector_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Certify Phase 4 Personal Intelligence Analyst")
    parser.add_argument("--source-state-dir", help="Existing real Phase 3/3.2 state directory to analyze")
    parser.add_argument("--max-items-per-profile", type=int, default=3)
    parser.add_argument("--max-deep-dives", type=int, default=12)
    args = parser.parse_args()

    source_state = Path(args.source_state_dir) if args.source_state_dir else _latest_real_state_dir()
    if source_state is None:
        print("No real persisted corpus state found under runtime_evidence", file=sys.stderr)
        return 1

    output_dir = _new_output_dir(ROOT / "runtime_evidence")
    for relative in ["raw", "reports", "logs"]:
        (output_dir / relative).mkdir(parents=True, exist_ok=True)
    state_dir = output_dir / "state"
    shutil.copytree(source_state, state_dir)
    _clear_phase4_outputs(state_dir)

    started = time.perf_counter()
    result = run_phase4_pipeline(
        state_dir,
        max_items_per_profile=args.max_items_per_profile,
        max_deep_dives=args.max_deep_dives,
    )
    elapsed = time.perf_counter() - started
    inspector = inspect_intelligence_runtime(state_dir)
    state = FileStateStore(state_dir)
    latest_brief = state.read_json(LATEST_MORNING_BRIEF_FILE, {})
    latest_dives = state.read_json(LATEST_DEEP_DIVES_FILE, {"deep_dives": []})
    blockers = _blockers(source_state, inspector, latest_brief, latest_dives, result.to_dict(), elapsed)

    _write_json(output_dir / "raw" / "phase4_pipeline_result.json", result.to_dict())
    _write_json(output_dir / "raw" / "runtime_inspector.json", inspector)
    _write_json(output_dir / "raw" / "latest_morning_brief.json", latest_brief)
    _write_json(output_dir / "raw" / "latest_deep_dives.json", latest_dives)
    _write_json(output_dir / "raw" / "blockers.json", blockers)
    _write_text(output_dir / "RUNTIME_INSPECTOR_OUTPUT.md", inspector_markdown(inspector))
    _write_json(output_dir / "RUNTIME_INSPECTOR_OUTPUT.json", inspector)
    if latest_brief:
        _write_text(output_dir / "MORNING_BRIEF.md", generate_morning_brief_markdown(MorningBrief.from_dict(latest_brief)))
    _write_text(output_dir / "PHASE4_RUNTIME_CERTIFICATION.md", _certification_report(output_dir, source_state, inspector, result.to_dict(), blockers, elapsed))
    _write_json(output_dir / "EVIDENCE_MANIFEST.json", _manifest(output_dir, source_state, inspector, blockers))
    _write_text(output_dir / "RUNTIME_TREE.txt", _runtime_tree(output_dir))
    _write_text(output_dir / "README.md", _readme(output_dir, source_state))

    print(str(output_dir))
    return 0 if not blockers else 1


def _blockers(
    source_state: Path,
    inspector: Dict[str, Any],
    latest_brief: Dict[str, Any],
    latest_dives: Dict[str, Any],
    result: Dict[str, Any],
    elapsed: float,
) -> List[Dict[str, Any]]:
    blockers: List[Dict[str, Any]] = []
    summary = inspector["system_summary"]
    phase4 = inspector["personal_intelligence"]
    claims = phase4["claims"]
    relevance = phase4["relevance"]
    importance = phase4["importance"]
    brief = phase4["brief_generation"]
    dives = phase4["deep_dives"]

    if not source_state.exists():
        blockers.append({"code": "SOURCE_STATE_MISSING", "message": str(source_state)})
    if summary["profile_count"] < 4:
        blockers.append({"code": "INSUFFICIENT_PROFILES", "message": f"Expected >=4 profiles, observed {summary['profile_count']}"})
    if summary["knowledge_objects"] <= 0 or summary["chunks"] <= 0:
        blockers.append({"code": "NO_REAL_CORPUS", "message": "Source state has no persisted KnowledgeObjects or chunks"})
    if claims["total"] < 10:
        blockers.append({"code": "INSUFFICIENT_CLAIMS", "message": f"Expected >=10 extracted claims, observed {claims['total']}"})
    if claims["total"] and claims["evidence_backed"] != claims["total"]:
        blockers.append({"code": "CLAIMS_NOT_EVIDENCE_BACKED", "message": f"{claims['evidence_backed']} of {claims['total']} claims have evidence"})
    if not relevance["all_profiles_evaluated"]:
        blockers.append({"code": "PROFILE_MATRIX_INCOMPLETE", "message": f"Expected {relevance['expected_total']} relevance scores, observed {relevance['total']}"})
    if importance["total"] != relevance["total"]:
        blockers.append({"code": "IMPORTANCE_MATRIX_INCOMPLETE", "message": f"Importance {importance['total']} != relevance {relevance['total']}"})
    if brief["item_count"] < summary["profile_count"]:
        blockers.append({"code": "BRIEF_INCOMPLETE", "message": f"Brief items {brief['item_count']} < profiles {summary['profile_count']}"})
    if not brief["required_explanations_present"]:
        blockers.append({"code": "BRIEF_NOT_EXPLAINABLE", "message": "Brief items must include what is new, why user cares, why it matters, and evidence"})
    if not _brief_items_have_evidence(latest_brief):
        blockers.append({"code": "BRIEF_EVIDENCE_MISSING", "message": "One or more brief items lack timestamp/source evidence"})
    if dives["total"] <= 0 or dives["with_evidence_trail"] != dives["total"]:
        blockers.append({"code": "DEEP_DIVES_INCOMPLETE", "message": "Deep dives require context and evidence trails"})
    if not _deep_dives_explainable(latest_dives):
        blockers.append({"code": "DEEP_DIVES_NOT_EXPLAINABLE", "message": "Deep dives missing intelligence explanations"})
    if result.get("status") != "pass" or phase4["status"] != "pass":
        blockers.append({"code": "PHASE4_STATUS_FAILED", "message": {"pipeline": result.get("warnings"), "inspector": phase4.get("warnings")}})
    if elapsed > 600:
        blockers.append({"code": "PERFORMANCE_REGRESSION", "message": f"Phase 4 took {elapsed:.2f}s"})
    return blockers


def _brief_items_have_evidence(latest_brief: Dict[str, Any]) -> bool:
    for section in latest_brief.get("sections", []):
        for item in section.get("items") or []:
            evidence = item.get("where_evidence_is") or {}
            if not evidence.get("quote"):
                return False
            if not (evidence.get("timestamped_source_url") or evidence.get("source_id") or evidence.get("source_name")):
                return False
    return bool(latest_brief.get("item_count", 0))


def _deep_dives_explainable(latest_dives: Dict[str, Any]) -> bool:
    dives = latest_dives.get("deep_dives") or []
    if not dives:
        return False
    for dive in dives:
        intelligence = dive.get("intelligence") or {}
        if not all(intelligence.get(key) for key in ["what_is_new", "why_user_cares", "why_it_matters"]):
            return False
        if not dive.get("focal_claim") or not dive.get("evidence_trail"):
            return False
    return True


def _certification_report(output_dir: Path, source_state: Path, inspector: Dict[str, Any], result: Dict[str, Any], blockers: List[Dict[str, Any]], elapsed: float) -> str:
    phase4 = inspector["personal_intelligence"]
    lines = [
        "# Phase 4 Runtime Certification",
        "",
        f"Generated: {_now_iso()}",
        f"Artifact directory: `{output_dir}`",
        f"Source state: `{source_state}`",
        "",
        "## Certification Decision",
        "PASS" if not blockers else "FAIL",
        "",
        "## Runtime Chain",
        "persisted real transcript corpus -> extracted evidence-backed claims -> scored novelty/relevance/importance -> correlated cross-source claims -> generated Morning Brief -> generated Interactive Deep Dives -> inspected persisted artifacts",
        "",
        "## Claim Intelligence",
        f"- claims: {phase4['claims']['total']}",
        f"- evidence_backed_claims: {phase4['claims']['evidence_backed']}",
        f"- novelty_distribution: {phase4['novelty']['labels']}",
        f"- importance_distribution: {phase4['importance']['bands']}",
        "",
        "## Profile Coverage",
        f"- profiles: {inspector['system_summary']['profile_count']}",
        f"- relevance_scores: {phase4['relevance']['total']}",
        f"- expected_relevance_scores: {phase4['relevance']['expected_total']}",
        f"- all_profiles_evaluated: {phase4['relevance']['all_profiles_evaluated']}",
        "",
        "## Briefing",
        f"- brief_items: {phase4['brief_generation']['item_count']}",
        f"- estimated_read_seconds: {phase4['brief_generation']['estimated_read_seconds']}",
        f"- required_explanations_present: {phase4['brief_generation']['required_explanations_present']}",
        f"- deep_dives: {phase4['deep_dives']['total']}",
        "",
        "## Performance",
        f"- pipeline_elapsed_seconds: {round(elapsed, 3)}",
        f"- recorded_elapsed_seconds: {result.get('elapsed_seconds')}",
        "",
        "## Remaining Blockers",
        "```json",
        json.dumps(blockers, indent=2, sort_keys=True),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _manifest(output_dir: Path, source_state: Path, inspector: Dict[str, Any], blockers: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "artifact_dir": str(output_dir),
        "source_state": str(source_state),
        "generated_at": _now_iso(),
        "status": "pass" if not blockers else "fail",
        "required_files": [
            "PHASE4_RUNTIME_CERTIFICATION.md",
            "MORNING_BRIEF.md",
            "RUNTIME_INSPECTOR_OUTPUT.json",
            "RUNTIME_INSPECTOR_OUTPUT.md",
            "state/claims.jsonl",
            "state/claim_novelty.jsonl",
            "state/claim_relevance.jsonl",
            "state/claim_importance.jsonl",
            "state/cross_source_clusters.jsonl",
            "state/latest_morning_brief.json",
            "state/latest_deep_dives.json",
        ],
        "system_summary": inspector["system_summary"],
        "personal_intelligence": inspector["personal_intelligence"],
        "blockers": blockers,
    }


def _latest_real_state_dir() -> Optional[Path]:
    evidence = ROOT / "runtime_evidence"
    if not evidence.exists():
        return None
    candidates: List[Path] = []
    for prefix in ["phase32_intelligence_", "phase3_intelligence_"]:
        for path in evidence.iterdir():
            state = path / "state"
            if path.is_dir() and path.name.startswith(prefix) and (state / "knowledge_objects.jsonl").exists():
                candidates.append(state)
        if candidates:
            return sorted(candidates, key=lambda item: item.parent.name, reverse=True)[0]
    return None


def _clear_phase4_outputs(state_dir: Path) -> None:
    names = [
        "claims.jsonl",
        "claim_index.json",
        "claim_novelty.jsonl",
        "claim_relevance.jsonl",
        "cross_source_clusters.jsonl",
        "claim_importance.jsonl",
        "morning_briefs.jsonl",
        "latest_morning_brief.json",
        "deep_dives.jsonl",
        "latest_deep_dives.json",
        "phase4_runs.json",
        "phase4_summary.json",
    ]
    for name in names:
        path = state_dir / name
        if path.exists():
            path.unlink()


def _new_output_dir(parent: Path) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = parent / f"phase4_intelligence_{stamp}"
    counter = 1
    while path.exists():
        path = parent / f"phase4_intelligence_{stamp}_{counter}"
        counter += 1
    path.mkdir(parents=True)
    return path


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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


def _readme(output_dir: Path, source_state: Path) -> str:
    return "\n".join([
        "# Phase 4 Personal Intelligence Analyst Evidence",
        "",
        f"Artifact directory: `{output_dir}`",
        f"Source state: `{source_state}`",
        "",
        "Reproduce with:",
        "```bash",
        f"PYTHONPATH=src ./.venv/bin/python examples/certify_phase4_intelligence.py --source-state-dir {source_state}",
        "```",
    ]) + "\n"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    raise SystemExit(main())
