#!/usr/bin/env python3
"""Replay archived morning intelligence through Runtime 1 and IL2 side-by-side."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from knowledge_service.analyst.synthesis.models import IntelligenceItem
from knowledge_service.intelligence_v2.editorial_synthesis import synthesize_from_item
from knowledge_service.intelligence_v2.integration import apply_intelligence_layer_v2
from knowledge_service.intelligence_v2.pipeline import IntelligenceV2Pipeline
from knowledge_service.production.briefing.morning_brief_v3 import MorningBriefV3Generator
from knowledge_service.production.morning.markdown import render_brief_markdown


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "frontend" / "archive"
OUTPUT_ROOT = ROOT / "data" / "intelligence_v2" / "side_by_side"


def main() -> int:
    parser = argparse.ArgumentParser(description="Runtime 1 vs IL2 side-by-side brief comparison")
    parser.add_argument(
        "--dates",
        nargs="*",
        default=["2026-07-01", "2026-07-02"],
        help="Archive dates to compare (YYYY-MM-DD)",
    )
    args = parser.parse_args()

    summaries = []
    for date in args.dates:
        summary = process_day(date)
        summaries.append(summary)
        print(json.dumps(summary, indent=2))

    index_path = OUTPUT_ROOT / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps({"comparisons": summaries}, indent=2), encoding="utf-8")
    print(f"\nWrote index: {index_path}")
    return 0


def process_day(date: str) -> Dict[str, Any]:
    archive_dir = ARCHIVE / date
    morning_path = archive_dir / "morning.json"
    if not morning_path.exists():
        raise FileNotFoundError(f"Missing archived morning intelligence: {morning_path}")

    payload = json.loads(morning_path.read_text(encoding="utf-8"))
    out_dir = OUTPUT_ROOT / date
    out_dir.mkdir(parents=True, exist_ok=True)

    # Preserve exact published Runtime 1 artifacts
    for name in ("morning.json", "morning.md", "morning.html", "run_summary.json"):
        src = archive_dir / name
        if src.exists():
            shutil.copy2(src, out_dir / f"runtime1_published_{name}")

    brief = payload.get("brief", {})
    all_items = [IntelligenceItem.from_dict(row) for row in payload.get("items", [])]
    brief_ids = [row.get("intelligence_item_id") for row in brief.get("items", [])]
    item_index = {item.item_id: item for item in all_items}
    fresh_items = [item_index[item_id] for item_id in brief_ids if item_id in item_index]
    if not fresh_items:
        fresh_items = sorted(all_items, key=lambda row: row.importance_score, reverse=True)[:10]

    claims_synthesized = int(brief.get("claims_synthesized", len(all_items)))
    pipeline_run_id = str(brief.get("pipeline_run_id", ""))

    # Runtime 1 regenerated (same path as production, IL2 disabled)
    os.environ.pop("KNOWLEDGE_IL2_ENABLED", None)
    runtime1_items = deepcopy(fresh_items)
    runtime1_brief = _generate_brief(runtime1_items, claims_synthesized, pipeline_run_id)
    runtime1_md = render_brief_markdown(runtime1_brief)
    _write_brief_artifacts(out_dir, "runtime1_regenerated", runtime1_brief, runtime1_md, runtime1_items)

    # Intelligence Layer 2.0
    os.environ["KNOWLEDGE_IL2_ENABLED"] = "1"
    il2_items_input = deepcopy(fresh_items)
    il2_items, il2_result = apply_intelligence_layer_v2(il2_items_input)
    il2_brief = _generate_brief(il2_items, claims_synthesized, pipeline_run_id)
    il2_md = render_il2_markdown(il2_brief, il2_result.to_dict(), il2_items)
    _write_brief_artifacts(out_dir, "il2", il2_brief, il2_md, il2_items, extra={"intelligence_v2": il2_result.to_dict()})

    # Side-by-side narrative
    comparison = build_comparison(brief, runtime1_brief, il2_brief, il2_result.to_dict())
    (out_dir / "comparison.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    (out_dir / "SIDE_BY_SIDE.md").write_text(render_side_by_side(date, comparison, brief, il2_brief), encoding="utf-8")

    os.environ.pop("KNOWLEDGE_IL2_ENABLED", None)
    return {
        "date": date,
        "generated_at": payload.get("generated_at"),
        "source_archive": str(morning_path),
        "output_dir": str(out_dir),
        "runtime1_item_count": runtime1_brief.total_items,
        "il2_item_count": il2_brief.total_items,
        "il2_accepted": il2_result.accepted_count,
        "il2_rejected": il2_result.rejected_count,
        "artifacts": sorted(path.name for path in out_dir.iterdir() if path.is_file()),
    }


def _generate_brief(items: List[IntelligenceItem], claims_synthesized: int, pipeline_run_id: str):
    generator = MorningBriefV3Generator()
    selected = generator.select_items(items)
    return generator.generate(
        selected,
        pipeline_run_id=pipeline_run_id,
        claims_synthesized=claims_synthesized,
    )


def _write_brief_artifacts(
    out_dir: Path,
    prefix: str,
    brief,
    markdown: str,
    items: List[IntelligenceItem],
    *,
    extra: Dict[str, Any] | None = None,
) -> None:
    payload: Dict[str, Any] = {
        "brief": brief.to_dict(),
        "items": [item.to_dict() for item in items],
        "generated_at": brief.generated_at,
        "empty_signal": False,
    }
    if extra:
        payload.update(extra)
    (out_dir / f"{prefix}_brief.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (out_dir / f"{prefix}_brief.md").write_text(markdown, encoding="utf-8")


def render_il2_markdown(brief, il2_meta: Dict[str, Any], items: List[IntelligenceItem]) -> str:
    lines = [
        "# Morning Intelligence — Intelligence Layer 2.0",
        "",
        f"Generated: {brief.generated_at}",
        f"Reading time: ~{brief.reading_time_seconds} seconds",
        f"IL2 accepted: {il2_meta.get('accepted_count', 0)} | rejected: {il2_meta.get('rejected_count', 0)}",
        "",
    ]
    card_index = {card["item_id"]: card for card in il2_meta.get("cards", [])}
    for entry in brief.items:
        card = card_index.get(entry.intelligence_item_id, {})
        stars = "★" * entry.star_rating + "☆" * (5 - entry.star_rating)
        lines.extend([
            f"## {entry.title}",
            stars,
            "",
            f"**Original title:** {card.get('original_title', entry.title)}",
            f"**Canonical topic:** {card.get('canonical_topic', '')}",
            f"**Accepted:** {card.get('accepted', True)}",
        ])
        if card.get("rejection_reason"):
            lines.append(f"**Rejection reason:** {card['rejection_reason']}")
        if card.get("failure_modes"):
            lines.append(f"**Failure modes:** {', '.join(card['failure_modes'])}")
        lines.extend([
            "",
            f"**Executive summary:** {entry.what_changed}",
            f"**Why it matters:** {entry.why_you_care}",
            f"**What to watch:** {card.get('what_to_watch', '—')}",
            f"**Suggested action:** {card.get('suggested_action', '—')}",
            f"**Evidence:** {entry.evidence_summary}",
            "",
        ])
    return "\n".join(lines)


def build_comparison(
    published_brief: Dict[str, Any],
    runtime1_brief,
    il2_brief,
    il2_meta: Dict[str, Any],
) -> Dict[str, Any]:
    card_index = {card["item_id"]: card for card in il2_meta.get("cards", [])}
    published_items = {row["intelligence_item_id"]: row for row in published_brief.get("items", [])}
    entries = []
    for r1_entry in runtime1_brief.items:
        il2_entry = next(
            (entry for entry in il2_brief.items if entry.intelligence_item_id == r1_entry.intelligence_item_id),
            None,
        )
        card = card_index.get(r1_entry.intelligence_item_id, {})
        pub = published_items.get(r1_entry.intelligence_item_id, {})
        entries.append({
            "item_id": r1_entry.intelligence_item_id,
            "published_title": pub.get("title", r1_entry.title),
            "runtime1_title": r1_entry.title,
            "il2_title": il2_entry.title if il2_entry else "(filtered out)",
            "il2_accepted": card.get("accepted"),
            "il2_rejection_reason": card.get("rejection_reason"),
            "failure_modes": card.get("failure_modes", []),
        })
    return {
        "published_brief_id": published_brief.get("brief_id"),
        "runtime1_brief_id": runtime1_brief.brief_id,
        "il2_brief_id": il2_brief.brief_id,
        "il2_metadata": {
            "accepted_count": il2_meta.get("accepted_count"),
            "rejected_count": il2_meta.get("rejected_count"),
            "titles_resolved": il2_meta.get("titles_resolved"),
            "latency_ms": il2_meta.get("latency_ms"),
        },
        "entries": entries,
    }


def render_side_by_side(
    date: str,
    comparison: Dict[str, Any],
    published_brief: Dict[str, Any],
    il2_brief,
) -> str:
    lines = [
        f"# Side-by-Side Morning Intelligence — {date}",
        "",
        f"**Published Runtime 1 brief:** `{published_brief.get('brief_id')}` @ {published_brief.get('generated_at')}",
        f"**IL2 brief:** `{il2_brief.brief_id}` @ {il2_brief.generated_at}",
        "",
        "| # | Published (Runtime 1) | IL2 Title | IL2 Status |",
        "|---|----------------------|-----------|------------|",
    ]
    for index, entry in enumerate(comparison.get("entries", []), start=1):
        status = "accepted" if entry.get("il2_accepted") else f"rejected: {entry.get('il2_rejection_reason', '—')}"
        lines.append(
            f"| {index} | {entry.get('published_title', '')} | {entry.get('il2_title', '')} | {status} |"
        )
    lines.extend([
        "",
        "## Artifact Paths",
        "",
        f"- Published Runtime 1: `runtime1_published_morning.json`, `runtime1_published_morning.md`",
        f"- Regenerated Runtime 1: `runtime1_regenerated_brief.json`, `runtime1_regenerated_brief.md`",
        f"- IL2: `il2_brief.json`, `il2_brief.md`",
        f"- Comparison: `comparison.json`",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())