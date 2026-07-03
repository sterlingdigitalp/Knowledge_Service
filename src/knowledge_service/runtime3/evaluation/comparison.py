"""Three-way comparison: Runtime 1 vs IL2 vs Runtime 3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .metrics import compute_metrics, is_fragment_title


class Runtime3ComparisonHarness:
    """Compare Runtime 1, IL2, and Runtime 3 outputs for archived dates."""

    def compare_day(
        self,
        date: str,
        *,
        side_by_side_dir: Path,
        runtime3_brief: Dict[str, Any],
        runtime3_metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        day_dir = side_by_side_dir / date
        r1_payload = self._load_json(day_dir / "runtime1_regenerated_brief.json")
        il2_payload = self._load_json(day_dir / "il2_brief.json")
        comparison_payload = self._load_json(day_dir / "comparison.json")

        r1_titles = [entry.get("title", "") for entry in r1_payload.get("brief", {}).get("items", [])]
        il2_titles = [entry.get("title", "") for entry in il2_payload.get("brief", {}).get("items", [])]
        r3_titles = [entry.get("headline", "") for entry in runtime3_brief.get("entries", [])]

        entries: List[Dict[str, Any]] = []
        for row in comparison_payload.get("entries", []):
            entries.append({
                "item_id": row.get("item_id"),
                "runtime1_title": row.get("runtime1_title"),
                "il2_title": row.get("il2_title"),
                "il2_accepted": row.get("il2_accepted"),
                "il2_rejection_reason": row.get("il2_rejection_reason"),
                "runtime1_fragment": is_fragment_title(row.get("runtime1_title", "")),
                "il2_fragment": is_fragment_title(row.get("il2_title", "") or ""),
            })

        return {
            "date": date,
            "runtime1_titles": r1_titles,
            "il2_titles": il2_titles,
            "runtime3_titles": r3_titles,
            "runtime1_count": len(r1_titles),
            "il2_count": len(il2_titles),
            "runtime3_count": len(r3_titles),
            "runtime3_metrics": runtime3_metrics,
            "per_item_comparison": entries,
            "improvements": {
                "more_stories_than_il2": len(r3_titles) > len(il2_titles),
                "fewer_fragments_than_runtime1": (
                    sum(1 for title in r3_titles if is_fragment_title(title))
                    < sum(1 for title in r1_titles if is_fragment_title(title))
                ),
                "editorial_usefulness": runtime3_metrics.get("editorial_usefulness_score", 0),
            },
        }

    def render_comparison_markdown(self, reports: List[Dict[str, Any]]) -> str:
        lines = [
            "# Runtime 1 vs IL2 vs Runtime 3 — Comparison Report",
            "",
        ]
        for report in reports:
            metrics = report.get("runtime3_metrics", {})
            lines.extend([
                f"## {report['date']}",
                "",
                "| Pipeline | Stories | Fragment Titles |",
                "|----------|---------|-----------------|",
                f"| Runtime 1 | {report['runtime1_count']} | {metrics.get('runtime1_fragment_titles', '—')} |",
                f"| IL2 | {report['il2_count']} | {metrics.get('il2_fragment_titles', '—')} |",
                f"| Runtime 3 | {report['runtime3_count']} | {metrics.get('runtime3_fragment_titles', '—')} |",
                "",
                f"**Editorial usefulness:** {metrics.get('editorial_usefulness_score', 0):.2f}",
                f"**Non-news segments filtered:** {metrics.get('runtime3_filtered_non_news_segments', 0)}",
                f"**Claims extracted:** {metrics.get('runtime3_claim_count', 0)}",
                f"**Entities resolved:** {metrics.get('runtime3_entity_count', 0)}",
                f"**Events detected:** {metrics.get('runtime3_event_count', 0)}",
                "",
                "### Runtime 3 Headlines",
                "",
            ])
            for index, title in enumerate(report.get("runtime3_titles", []), start=1):
                lines.append(f"{index}. {title}")
            lines.extend(["", "### Per-Item (Runtime 1 → IL2)", ""])
            for entry in report.get("per_item_comparison", []):
                il2_status = "accepted" if entry.get("il2_accepted") else f"rejected: {entry.get('il2_rejection_reason')}"
                lines.append(f"- **{entry.get('runtime1_title')}** → IL2: {entry.get('il2_title')} ({il2_status})")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))