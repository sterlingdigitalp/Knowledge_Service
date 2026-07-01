"""Morning brief markdown rendering."""

from __future__ import annotations

from typing import Any

from ..briefing.morning_brief_v3 import IntelligenceBriefV3


def render_brief_markdown(brief: IntelligenceBriefV3, *, empty_signal: bool = False) -> str:
    lines = [
        "# Morning Intelligence",
        "",
        f"Generated: {brief.generated_at}",
        f"Reading time: ~{brief.reading_time_seconds} seconds",
        f"Quality score: {brief.quality_score:.2f}",
        "",
    ]
    if empty_signal:
        lines.extend([
            "> **No significant new intelligence today.**",
            "> The freshness gate found no high-signal new developments worth headline placement.",
            "",
        ])
    for entry in brief.items:
        stars = "★" * entry.star_rating + "☆" * (5 - entry.star_rating)
        lines.extend([
            f"## {entry.title}",
            stars,
            "",
            f"**What changed?** {entry.what_changed}",
            f"**Why should I care?** {entry.why_you_care}",
            f"**Why am I seeing this?** {entry.why_surfaced}",
            f"**Evidence:** {entry.evidence_summary}",
            "",
        ])
    return "\n".join(lines)


def build_empty_brief(*, pipeline_run_id: str = "") -> IntelligenceBriefV3:
    from ...analyst.synthesis.models import IntelligenceBriefEntry
    from ...intelligence.models import now_iso, stable_id

    generated_at = now_iso()
    entry = IntelligenceBriefEntry(
        entry_id=stable_id("empty-brief-entry", generated_at),
        intelligence_item_id="",
        profile_id="general",
        profile_name="General",
        title="No significant new intelligence today",
        what_changed=(
            "No high-signal new information events were acquired since the last briefing cycle. "
            "Historical corpus remains available for on-demand deep dives."
        ),
        why_you_care=(
            "Today's edition intentionally avoids recycling stale headlines. "
            "Check back after the next acquisition cycle or review archived briefs."
        ),
        why_surfaced="Freshness gate: no eligible items met the today-signal threshold.",
        evidence_summary="Evidence: freshness gate evaluation (no new transcript-backed claims)",
        star_rating=1,
        importance_band="low",
        corroborated_by=0,
        explainability={"freshness_gate": "no_fresh_signal"},
    )
    return IntelligenceBriefV3(
        brief_id=stable_id("brief-v3-empty", generated_at),
        generated_at=generated_at,
        reading_time_seconds=30,
        total_items=1,
        items=[entry],
        compression_ratio=0.0,
        claims_synthesized=0,
        quality_score=1.0,
        pipeline_run_id=pipeline_run_id,
        narrative_flow=["freshness_gate_empty"],
        brief_polish_applied=False,
    )