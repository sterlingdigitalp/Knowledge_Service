#!/usr/bin/env python3
"""Replay archived production days through the Thinking Engine."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_service.runtime3.brief import Runtime3BriefGenerator, render_brief_markdown
from knowledge_service.runtime3.evaluation.comparison import Runtime3ComparisonHarness
from knowledge_service.runtime3.evaluation.metrics import compute_metrics, is_fragment_title
from knowledge_service.runtime3.thinking.engine import ThinkingEngine

OUTPUT_ROOT = ROOT / "data" / "runtime3"
ARCHIVE = ROOT / "frontend" / "archive"
SIDE_BY_SIDE = ROOT / "data" / "intelligence_v2" / "side_by_side"
STATE_DIR = ROOT / "state"


def main() -> int:
    parser = argparse.ArgumentParser(description="Thinking Engine benchmark replay")
    parser.add_argument(
        "--dates",
        nargs="*",
        default=None,
        help="Archive dates (default: all available)",
    )
    args = parser.parse_args()

    dates = args.dates or discover_archive_dates()
    if not dates:
        print("No archive dates found.")
        return 1

    os.environ["KNOWLEDGE_RUNTIME3_ENABLED"] = "1"
    engine = ThinkingEngine(
        state_dir=str(STATE_DIR),
        memory_path=str(OUTPUT_ROOT / "runtime3_story_memory.json"),
    )
    harness = Runtime3ComparisonHarness()
    brief_gen = Runtime3BriefGenerator()

    all_metrics = []
    comparison_reports = []
    total_started = time.perf_counter()

    for date in sorted(dates):
        print(f"\n=== Thinking Engine: {date} ===")
        result = engine.run_for_date(date, state_dir=str(STATE_DIR))
        out_dir = OUTPUT_ROOT / date
        out_dir.mkdir(parents=True, exist_ok=True)

        r1_titles = _load_runtime1_titles(date)
        il2_titles = _load_il2_titles(date)
        r3_titles = [row.story.headline for row in result.ranked_stories]

        metrics = compute_metrics(
            result.stories,
            runtime1_titles=r1_titles,
            il2_titles=il2_titles,
            runtime3_result=None,
        )
        metrics.update({
            "date": date,
            "boundary_count": len(result.boundaries),
            "ranked_story_count": len(result.ranked_stories),
            "memory_record_count": len(result.story_memory.records) if result.story_memory else 0,
            "memory_actions": len(result.memory_actions),
            "entity_graph_edges": len(result.entity_graph.edges) if result.entity_graph else 0,
            "event_graph_edges": len(result.event_graph.edges) if result.event_graph else 0,
            "relationship_edges": len(result.relationship_graph.edges) if result.relationship_graph else 0,
            "latency_ms": result.latency_ms,
            "duplicate_headlines": _duplicate_count(r3_titles),
        })
        all_metrics.append(metrics)

        _write_artifacts(out_dir, result, metrics, brief_gen)
        report = harness.compare_day(
            date,
            side_by_side_dir=SIDE_BY_SIDE,
            runtime3_brief={"entries": [{"headline": t} for t in r3_titles]},
            runtime3_metrics=metrics,
        )
        comparison_reports.append(report)
        print(json.dumps({k: v for k, v in metrics.items() if k != "memory_actions"}, indent=2))

    combined = {
        "dates": dates,
        "per_day": all_metrics,
        "aggregate": _aggregate(all_metrics),
        "total_latency_ms": round((time.perf_counter() - total_started) * 1000, 2),
    }
    _write_final_artifacts(combined, comparison_reports, engine)
    print(f"\nWrote Thinking Engine artifacts to {OUTPUT_ROOT}")
    return 0


def discover_archive_dates() -> list[str]:
    if not ARCHIVE.exists():
        return []
    return sorted(
        path.name for path in ARCHIVE.iterdir()
        if path.is_dir() and (path / "morning.json").exists()
    )


def _write_artifacts(out_dir: Path, result, metrics: dict, brief_gen) -> None:
    from knowledge_service.runtime3.models import Runtime3Result as R3

    brief = brief_gen.generate(
        R3(stories=[row.story for row in result.ranked_stories], latency_ms=result.latency_ms),
        date=result.date,
    )

    (out_dir / "runtime3_brief.json").write_text(
        json.dumps({"brief": brief.to_dict(), "metrics": metrics, "rankings": [
            row.to_dict() for row in result.ranked_stories
        ]}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "runtime3_brief.md").write_text(render_brief_markdown(brief), encoding="utf-8")
    (out_dir / "runtime3_story_graph.json").write_text(
        json.dumps(result.story_graph or {}, indent=2), encoding="utf-8",
    )
    (out_dir / "runtime3_entity_graph.json").write_text(
        json.dumps(result.entity_graph.to_dict() if result.entity_graph else {}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "runtime3_event_graph.json").write_text(
        json.dumps(result.event_graph.to_dict() if result.event_graph else {}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "runtime3_story_memory.json").write_text(
        json.dumps(result.story_memory.to_dict() if result.story_memory else {}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "runtime3_story_rankings.json").write_text(
        json.dumps([row.to_dict() for row in result.ranked_stories], indent=2),
        encoding="utf-8",
    )
    (out_dir / "runtime3_relationship_graph.json").write_text(
        json.dumps(result.relationship_graph.to_dict() if result.relationship_graph else {}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "runtime3_thinking.json").write_text(
        json.dumps(result.to_dict(), indent=2), encoding="utf-8",
    )


def _write_final_artifacts(combined: dict, reports: list, engine: ThinkingEngine) -> None:
    harness = Runtime3ComparisonHarness()
    comparison_md = harness.render_comparison_markdown(reports)

    (OUTPUT_ROOT / "runtime3_metrics.json").write_text(
        json.dumps(combined, indent=2), encoding="utf-8",
    )
    (OUTPUT_ROOT / "runtime3_comparison.md").write_text(comparison_md, encoding="utf-8")

    r1_md = _versus_report(reports, "runtime1")
    il2_md = _versus_report(reports, "il2")
    (OUTPUT_ROOT / "runtime3_vs_runtime1.md").write_text(r1_md, encoding="utf-8")
    (OUTPUT_ROOT / "runtime3_vs_il2.md").write_text(il2_md, encoding="utf-8")

    memory = engine.memory_store.load()
    (OUTPUT_ROOT / "runtime3_story_memory.json").write_text(
        json.dumps(memory.to_dict(), indent=2), encoding="utf-8",
    )

    if reports:
        latest_date = reports[-1]["date"]
        latest_dir = OUTPUT_ROOT / latest_date
        for name in (
            "runtime3_brief.md", "runtime3_brief.json",
            "runtime3_story_graph.json", "runtime3_entity_graph.json",
            "runtime3_event_graph.json",
        ):
            src = latest_dir / name
            if src.exists():
                (OUTPUT_ROOT / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _versus_report(reports: list, baseline: str) -> str:
    lines = [f"# Runtime 3 vs {baseline.upper()}", ""]
    for report in reports:
        metrics = report.get("runtime3_metrics", {})
        if baseline == "runtime1":
            base_count = report.get("runtime1_count", 0)
            base_fragments = metrics.get("runtime1_fragment_titles", 0)
        else:
            base_count = report.get("il2_count", 0)
            base_fragments = metrics.get("il2_fragment_titles", 0)
        lines.extend([
            f"## {report['date']}",
            "",
            f"| Metric | {baseline.upper()} | Runtime 3 |",
            f"|--------|{'-' * len(baseline)}|----------|",
            f"| Stories | {base_count} | {report.get('runtime3_count', 0)} |",
            f"| Fragment titles | {base_fragments} | {metrics.get('runtime3_fragment_titles', 0)} |",
            f"| Editorial usefulness | — | {metrics.get('editorial_usefulness_score', 0):.2f} |",
            f"| Memory actions | — | {metrics.get('memory_actions', 0)} |",
            "",
        ])
    return "\n".join(lines)


def _load_runtime1_titles(date: str) -> list[str]:
    path = SIDE_BY_SIDE / date / "runtime1_regenerated_brief.json"
    if not path.exists():
        path = ARCHIVE / date / "morning.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    brief = payload.get("brief", payload)
    return [item.get("title", "") for item in brief.get("items", [])]


def _load_il2_titles(date: str) -> list[str]:
    path = SIDE_BY_SIDE / date / "il2_brief.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [item.get("title", "") for item in payload.get("brief", {}).get("items", [])]


def _duplicate_count(titles: list[str]) -> int:
    normalized = [title.strip().lower() for title in titles if title]
    return len(normalized) - len(set(normalized))


def _aggregate(per_day: list[dict]) -> dict:
    if not per_day:
        return {}
    keys = [
        "runtime3_story_count", "runtime3_fragment_titles", "runtime1_fragment_titles",
        "il2_fragment_titles", "editorial_usefulness_score", "memory_actions",
        "duplicate_headlines", "latency_ms",
    ]
    agg = {}
    for key in keys:
        values = [row.get(key, 0) for row in per_day]
        agg[key] = round(sum(values) / len(values), 3) if values else 0
    agg["total_stories"] = sum(row.get("runtime3_story_count", 0) for row in per_day)
    return agg


if __name__ == "__main__":
    raise SystemExit(main())