"""Runtime 3 brief generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from ..intelligence.models import now_iso, stable_id
from .models import Runtime3Result, StoryObject


@dataclass
class Runtime3BriefEntry:
    story_id: str
    headline: str
    executive_summary: str
    what_happened: str
    why_it_matters: str
    evidence_summary: str
    future_watch: str
    confidence: float
    importance: float
    story_type: str
    supporting_sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "story_id": self.story_id,
            "headline": self.headline,
            "executive_summary": self.executive_summary,
            "what_happened": self.what_happened,
            "why_it_matters": self.why_it_matters,
            "evidence_summary": self.evidence_summary,
            "future_watch": self.future_watch,
            "confidence": self.confidence,
            "importance": self.importance,
            "story_type": self.story_type,
            "supporting_sources": list(self.supporting_sources),
        }


@dataclass
class Runtime3Brief:
    brief_id: str
    generated_at: str
    date: str
    total_stories: int
    entries: List[Runtime3BriefEntry]
    pipeline: str = "runtime3"
    version: str = "3.0"
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brief_id": self.brief_id,
            "generated_at": self.generated_at,
            "date": self.date,
            "total_stories": self.total_stories,
            "entries": [entry.to_dict() for entry in self.entries],
            "pipeline": self.pipeline,
            "version": self.version,
            "latency_ms": self.latency_ms,
        }


class Runtime3BriefGenerator:
    """Generate editor-ready brief from Runtime 3 stories."""

    def __init__(self, max_stories: int = 10):
        self.max_stories = max_stories

    def generate(self, result: Runtime3Result, *, date: str = "") -> Runtime3Brief:
        stories = sorted(result.stories, key=lambda story: story.importance, reverse=True)
        selected = stories[: self.max_stories]
        entries = [self._story_to_entry(story) for story in selected]
        return Runtime3Brief(
            brief_id=stable_id("r3-brief", date or now_iso()),
            generated_at=now_iso(),
            date=date,
            total_stories=len(entries),
            entries=entries,
            latency_ms=result.latency_ms,
        )

    def _story_to_entry(self, story: StoryObject) -> Runtime3BriefEntry:
        evidence = story.evidence[0][:200] if story.evidence else story.summary[:200]
        return Runtime3BriefEntry(
            story_id=story.story_id,
            headline=story.headline,
            executive_summary=story.executive_summary,
            what_happened=story.what_happened,
            why_it_matters=story.why_it_matters,
            evidence_summary=evidence,
            future_watch=story.future_watch,
            confidence=story.confidence,
            importance=story.importance,
            story_type=story.story_type.value,
            supporting_sources=list(story.supporting_sources),
        )


def render_brief_markdown(brief: Runtime3Brief) -> str:
    lines = [
        "# Morning Intelligence — Runtime 3 (Semantic Understanding)",
        "",
        f"**Date:** {brief.date}",
        f"**Generated:** {brief.generated_at}",
        f"**Stories:** {brief.total_stories}",
        f"**Latency:** {brief.latency_ms:.0f}ms",
        "",
    ]
    for index, entry in enumerate(brief.entries, start=1):
        lines.extend([
            f"## {index}. {entry.headline}",
            "",
            f"**Type:** {entry.story_type} | **Confidence:** {entry.confidence:.0%} | **Importance:** {entry.importance:.0%}",
            f"**Sources:** {', '.join(entry.supporting_sources) or '—'}",
            "",
            f"**Executive Summary:** {entry.executive_summary}",
            "",
            "**What Happened:**",
            entry.what_happened,
            "",
            f"**Why It Matters:** {entry.why_it_matters}",
            "",
            f"**Evidence:** {entry.evidence_summary}",
            "",
            f"**Future Watch:** {entry.future_watch}",
            "",
            "---",
            "",
        ])
    return "\n".join(lines)