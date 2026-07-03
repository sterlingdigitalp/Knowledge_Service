"""Runtime 3 evaluation metrics."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence

from ..models import Runtime3Result, StoryObject

FRAGMENT_PATTERNS = [
    re.compile(r"^(?:visit|welcome|figure|there|however|agents?\s+better)\b", re.I),
    re.compile(r"^if you want to\b", re.I),
    re.compile(r"^ai i'?d\b", re.I),
    re.compile(r"\.{3}$"),
    re.compile(r"^\w{1,12}$"),
]

SPONSOR_PATTERNS = [
    re.compile(r"mercury\.com", re.I),
    re.compile(r"visit\s+\w+\.com", re.I),
    re.compile(r"thanks?\s+to\s+our\s+partner", re.I),
]


def is_fragment_title(title: str) -> bool:
    cleaned = (title or "").strip()
    if not cleaned:
        return True
    return any(pattern.search(cleaned) for pattern in FRAGMENT_PATTERNS)


def is_sponsor_residue(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in SPONSOR_PATTERNS)


def compute_metrics(
    runtime3_stories: Sequence[StoryObject],
    *,
    runtime1_titles: Sequence[str] | None = None,
    il2_titles: Sequence[str] | None = None,
    runtime3_result: Runtime3Result | None = None,
) -> Dict[str, Any]:
    r3_titles = [story.headline for story in runtime3_stories]
    r1_titles = list(runtime1_titles or [])
    il2_titles_list = list(il2_titles or [])

    metrics: Dict[str, Any] = {
        "runtime3_story_count": len(runtime3_stories),
        "runtime1_item_count": len(r1_titles),
        "il2_item_count": len(il2_titles_list),
        "runtime3_fragment_titles": sum(1 for title in r3_titles if is_fragment_title(title)),
        "runtime1_fragment_titles": sum(1 for title in r1_titles if is_fragment_title(title)),
        "il2_fragment_titles": sum(1 for title in il2_titles_list if is_fragment_title(title)),
        "runtime3_sponsor_residue": sum(
            1 for story in runtime3_stories
            if any(is_sponsor_residue(claim.claim_text) for claim in story.supporting_claims)
        ),
        "runtime3_avg_confidence": round(
            sum(story.confidence for story in runtime3_stories) / len(runtime3_stories), 3,
        ) if runtime3_stories else 0.0,
        "runtime3_avg_claims_per_story": round(
            sum(len(story.supporting_claims) for story in runtime3_stories) / len(runtime3_stories), 2,
        ) if runtime3_stories else 0.0,
        "runtime3_entity_count": len(runtime3_result.entities) if runtime3_result else 0,
        "runtime3_event_count": len(runtime3_result.events) if runtime3_result else 0,
        "runtime3_claim_count": len(runtime3_result.claims) if runtime3_result else 0,
        "runtime3_filtered_non_news_segments": sum(
            1 for segment in (runtime3_result.segments if runtime3_result else [])
            if segment.segment_type.value in {"sponsor", "advertisement", "intro", "outro", "meta_request", "housekeeping"}
        ),
    }

    metrics["story_recovery_vs_il2"] = max(0, len(runtime3_stories) - len(il2_titles_list))
    metrics["fragment_reduction_vs_runtime1"] = (
        metrics["runtime1_fragment_titles"] - metrics["runtime3_fragment_titles"]
    )
    metrics["editorial_usefulness_score"] = _editorial_score(runtime3_stories, r1_titles, il2_titles_list)
    return metrics


def _editorial_score(
    stories: Sequence[StoryObject],
    r1_titles: Sequence[str],
    il2_titles: Sequence[str],
) -> float:
    if not stories:
        return 0.0
    score = 0.0
    for story in stories:
        if not is_fragment_title(story.headline):
            score += 0.25
        if story.executive_summary and len(story.executive_summary) > 80:
            score += 0.15
        if story.events:
            score += 0.10
        if len(story.people) + len(story.organizations) >= 1:
            score += 0.10
        if len(story.supporting_sources) >= 1:
            score += 0.10
    max_possible = len(stories) * 0.70
    base = score / max_possible if max_possible else 0.0
    fragment_penalty = metrics_fragment_penalty(r1_titles, il2_titles, stories)
    return round(min(1.0, base + fragment_penalty), 3)


def metrics_fragment_penalty(
    r1_titles: Sequence[str],
    il2_titles: Sequence[str],
    stories: Sequence[StoryObject],
) -> float:
    r1_fragments = sum(1 for title in r1_titles if is_fragment_title(title))
    r3_fragments = sum(1 for story in stories if is_fragment_title(story.headline))
    if r1_fragments == 0:
        return 0.0
    improvement = (r1_fragments - r3_fragments) / r1_fragments
    return round(max(0.0, improvement * 0.15), 3)