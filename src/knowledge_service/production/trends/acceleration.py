"""Trend acceleration — theme velocity, consensus, decay."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Sequence

from ...analyst.synthesis.models import Theme, ThemeEvolution
from ...intelligence.models import now_iso


class TrendAccelerationEngine:
    """Track whether themes are accelerating, decaying, or forming consensus."""

    def analyze(
        self,
        themes: Sequence[Theme],
        evolutions: Sequence[ThemeEvolution],
        history: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        prior_by_label: Dict[str, Dict[str, Any]] = {}
        for snapshot in history:
            for item in snapshot.get("themes", []):
                prior_by_label[item.get("label", "").lower()] = item

        evolution_by_id = {record.theme_id: record for record in evolutions}
        results: List[Dict[str, Any]] = []

        for theme in themes:
            prior = prior_by_label.get(theme.label.lower())
            prior_claims = int((prior or {}).get("claim_count", 0))
            prior_sources = int((prior or {}).get("source_count", 0))
            claim_velocity = len(theme.claim_ids) - prior_claims
            source_velocity = theme.source_count - prior_sources
            evolution = evolution_by_id.get(theme.theme_id)

            if claim_velocity >= 3 or source_velocity >= 1:
                acceleration = "accelerating"
            elif claim_velocity <= -2:
                acceleration = "decaying"
            else:
                acceleration = "stable"

            consensus = "forming" if theme.source_count >= 3 else ("emerging" if theme.source_count >= 2 else "early")

            results.append({
                "theme_id": theme.theme_id,
                "label": theme.label,
                "acceleration": acceleration,
                "claim_velocity": claim_velocity,
                "source_velocity": source_velocity,
                "consensus": consensus,
                "source_count": theme.source_count,
                "claim_count": len(theme.claim_ids),
                "evolution_state": evolution.state.value if evolution else "unknown",
                "explanation": _explain(acceleration, consensus, theme, evolution),
                "recorded_at": now_iso(),
            })
        return sorted(results, key=lambda row: (row["claim_velocity"], row["source_count"]), reverse=True)

    def snapshot(self, themes: Sequence[Theme], trends: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "recorded_at": now_iso(),
            "themes": [
                {
                    "theme_id": theme.theme_id,
                    "label": theme.label,
                    "claim_count": len(theme.claim_ids),
                    "source_count": theme.source_count,
                }
                for theme in themes
            ],
            "trends": list(trends),
        }


def _explain(acceleration: str, consensus: str, theme: Theme, evolution: ThemeEvolution | None) -> str:
    parts = [f"{theme.label} is {acceleration}"]
    if consensus == "forming":
        parts.append(f"consensus forming across {theme.source_count} sources")
    elif consensus == "emerging":
        parts.append("early multi-source signal")
    if evolution:
        parts.append(evolution.explanation)
    return "; ".join(parts) + "."