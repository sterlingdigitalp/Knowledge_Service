#!/usr/bin/env python3
"""Replay archived data through Runtime 3 and compare with Runtime 1 and IL2."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_service.runtime3.brief import render_brief_markdown
from knowledge_service.runtime3.evaluation.comparison import Runtime3ComparisonHarness
from knowledge_service.runtime3.evaluation.metrics import compute_metrics
from knowledge_service.runtime3.integration import Runtime3Layer

OUTPUT_ROOT = ROOT / "data" / "runtime3"
SIDE_BY_SIDE = ROOT / "data" / "intelligence_v2" / "side_by_side"
STATE_DIR = ROOT / "state"
ARCHIVE = ROOT / "frontend" / "archive"


def main() -> int:
    parser = argparse.ArgumentParser(description="Runtime 1 vs IL2 vs Runtime 3 comparison")
    parser.add_argument(
        "--dates",
        nargs="*",
        default=["2026-07-01", "2026-07-02"],
        help="Archive dates (YYYY-MM-DD)",
    )
    args = parser.parse_args()

    os.environ["KNOWLEDGE_RUNTIME3_ENABLED"] = "1"
    layer = Runtime3Layer(state_dir=str(STATE_DIR))
    harness = Runtime3ComparisonHarness()

    all_metrics = []
    comparison_reports = []

    for date in args.dates:
        print(f"\n=== Processing {date} ===")
        result, brief = layer.run(date=date)
        if brief is None:
            print(f"Runtime 3 disabled or failed for {date}")
            continue

        out_dir = OUTPUT_ROOT / date
        out_dir.mkdir(parents=True, exist_ok=True)

        r1_titles = _load_runtime1_titles(date)
        il2_titles = _load_il2_titles(date)

        metrics = compute_metrics(
            result.stories,
            runtime1_titles=r1_titles,
            il2_titles=il2_titles,
            runtime3_result=result,
        )
        metrics["date"] = date
        all_metrics.append(metrics)

        _write_artifacts(out_dir, result, brief, metrics)

        report = harness.compare_day(
            date,
            side_by_side_dir=SIDE_BY_SIDE,
            runtime3_brief=brief.to_dict(),
            runtime3_metrics=metrics,
        )
        comparison_reports.append(report)
        print(json.dumps({k: v for k, v in metrics.items() if k != "date"}, indent=2))

    combined_metrics = {
        "dates": args.dates,
        "per_day": all_metrics,
        "aggregate": _aggregate_metrics(all_metrics),
    }
    (OUTPUT_ROOT / "runtime3_metrics.json").write_text(
        json.dumps(combined_metrics, indent=2), encoding="utf-8",
    )

    comparison_md = harness.render_comparison_markdown(comparison_reports)
    (OUTPUT_ROOT / "runtime3_comparison.md").write_text(comparison_md, encoding="utf-8")

    index = {
        "dates": args.dates,
        "output_root": str(OUTPUT_ROOT),
        "metrics": combined_metrics,
        "reports": comparison_reports,
    }
    (OUTPUT_ROOT / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")

    print(f"\nWrote artifacts to {OUTPUT_ROOT}")
    return 0


def _write_artifacts(out_dir: Path, result, brief, metrics: dict) -> None:
    (out_dir / "runtime3_brief.json").write_text(
        json.dumps({"brief": brief.to_dict(), "metrics": metrics}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "runtime3_brief.md").write_text(render_brief_markdown(brief), encoding="utf-8")
    (out_dir / "runtime3_story_graph.json").write_text(
        json.dumps(result.story_graph.to_dict() if result.story_graph else {}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "runtime3_events.json").write_text(
        json.dumps([event.to_dict() for event in result.events], indent=2),
        encoding="utf-8",
    )
    (out_dir / "runtime3_entities.json").write_text(
        json.dumps([entity.to_dict() for entity in result.entities], indent=2),
        encoding="utf-8",
    )
    (out_dir / "runtime3_segments.json").write_text(
        json.dumps([segment.to_dict() for segment in result.segments], indent=2),
        encoding="utf-8",
    )
    (out_dir / "runtime3_claims.json").write_text(
        json.dumps([claim.to_dict() for claim in result.claims], indent=2),
        encoding="utf-8",
    )
    (out_dir / "runtime3_pipeline.json").write_text(
        json.dumps(result.to_dict(), indent=2),
        encoding="utf-8",
    )


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


def _aggregate_metrics(per_day: list[dict]) -> dict:
    if not per_day:
        return {}
    keys = [
        "runtime3_story_count", "runtime3_fragment_titles", "runtime1_fragment_titles",
        "il2_fragment_titles", "editorial_usefulness_score", "runtime3_filtered_non_news_segments",
    ]
    aggregate = {}
    for key in keys:
        values = [row.get(key, 0) for row in per_day]
        aggregate[key] = round(sum(values) / len(values), 3) if values else 0
    aggregate["total_stories"] = sum(row.get("runtime3_story_count", 0) for row in per_day)
    return aggregate


if __name__ == "__main__":
    raise SystemExit(main())