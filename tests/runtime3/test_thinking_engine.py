"""Tests for the FEGOS Thinking Engine."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from knowledge_service.runtime3.memory.matcher import StoryMemoryMatcher
from knowledge_service.runtime3.memory.store import StoryMemoryStore
from knowledge_service.runtime3.models import StoryObject, StoryType
from knowledge_service.runtime3.ranking.engine import StoryRankingEngine
from knowledge_service.runtime3.relationships.graph import RelationshipGraphBuilder
from knowledge_service.runtime3.segmentation.boundaries import StoryBoundaryDetector, enrich_segments
from knowledge_service.runtime3.thinking.models import StoryMemory
from knowledge_service.runtime3.thinking.engine import ThinkingEngine

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "state"
ARCHIVE = ROOT / "frontend" / "archive"


def _make_story(headline: str, entities: list[str] | None = None) -> StoryObject:
    from knowledge_service.runtime3.models import ResolvedEntity, EntityType
    entity_objs = [
        ResolvedEntity(
            entity_id=f"e-{name}",
            canonical_name=name,
            entity_type=EntityType.PERSON,
            confidence=0.8,
        )
        for name in (entities or [])
    ]
    return StoryObject(
        story_id=f"story-{headline[:12]}",
        title=headline,
        summary=f"Summary for {headline}",
        story_type=StoryType.POLICY,
        headline=headline,
        executive_summary=f"Executive summary for {headline}",
        what_happened="What happened text.",
        why_it_matters="Why it matters text.",
        entities=entity_objs,
        confidence=0.85,
        importance=0.80,
        novelty=0.75,
        supporting_sources=["All-In Podcast"],
        supporting_claim_ids=["c1", "c2"],
        supporting_claims=[],
    )


def test_story_memory_extends_across_days(tmp_path: Path):
    matcher = StoryMemoryMatcher()
    memory = StoryMemory()

    story_day1 = _make_story("California AG Race Dynamics", ["Eric Swalwell", "Katie Porter"])
    memory, actions1, map1 = matcher.reconcile("2026-07-01", [story_day1], memory)
    assert any(action["action"] == "create" for action in actions1)

    story_day2 = _make_story("California AG Race Developments", ["Eric Swalwell", "Xavier Becerra"])
    memory, actions2, map2 = matcher.reconcile("2026-07-02", [story_day2], memory)
    assert any(action["action"] == "extend" for action in actions2)
    assert len(memory.records) == 1
    assert memory.records[0].last_seen_date == "2026-07-02"


def test_story_ranking_orders_by_score():
    stories = [
        _make_story("Low priority story"),
        _make_story("Byzantine Empire Historical Analysis", ["Constantine"]),
    ]
    stories[0].importance = 0.4
    stories[1].importance = 0.9
    ranked = StoryRankingEngine().rank(stories, date="2026-07-02")
    assert ranked[0].story.headline == "Byzantine Empire Historical Analysis"
    assert ranked[0].rank_score >= ranked[1].rank_score


def test_boundary_detection_finds_arcs():
    from knowledge_service.runtime3.models import SegmentType, TranscriptSegment
    segments = [
        TranscriptSegment("s1", "OpenAI announced a new coding agent for enterprise.", "host", 0, 60, SegmentType.NEWS, 0.9, "ep1", "Pod"),
        TranscriptSegment("s2", "Moving on, let's talk about the California attorney general race.", "host", 60, 120, SegmentType.DISCUSSION, 0.8, "ep1", "Pod"),
        TranscriptSegment("s3", "Eric Swalwell and Katie Porter are leading candidates.", "host", 120, 180, SegmentType.NEWS, 0.9, "ep1", "Pod"),
    ]
    boundaries = StoryBoundaryDetector().detect(segments)
    assert len(boundaries) >= 2


def test_enriched_segments_mark_sponsor_non_substantive():
    from knowledge_service.runtime3.models import SegmentType, TranscriptSegment
    segments = [
        TranscriptSegment("s1", "Visit mercury.com for startup banking.", "host", 0, 30, SegmentType.SPONSOR, 0.9, "ep1", "Pod"),
    ]
    enriched = enrich_segments(segments)
    assert enriched[0].is_substantive is False
    assert enriched[0].rich_type == "sponsor"


@pytest.mark.skipif(not (ARCHIVE / "2026-07-02" / "morning.json").exists(), reason="archive missing")
def test_thinking_engine_runs_on_archive(tmp_path: Path):
    os.environ["KNOWLEDGE_RUNTIME3_ENABLED"] = "1"
    memory_path = tmp_path / "memory.json"
    try:
        engine = ThinkingEngine(
            state_dir=str(STATE_DIR),
            memory_path=str(memory_path),
        )
        result = engine.run_for_date("2026-07-02", state_dir=str(STATE_DIR))
        assert result.stories
        assert result.ranked_stories
        assert result.entity_graph
        assert result.event_graph
        assert result.relationship_graph
        assert result.story_memory is not None
        assert result.latency_ms < 60000
    finally:
        os.environ.pop("KNOWLEDGE_RUNTIME3_ENABLED", None)