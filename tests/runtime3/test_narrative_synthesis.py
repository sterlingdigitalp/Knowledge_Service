"""Tests for Agent F — narrative synthesis."""

from __future__ import annotations

from knowledge_service.runtime3.claims.extractor import SemanticClaimExtractor
from knowledge_service.runtime3.entities.resolver import EntityResolver
from knowledge_service.runtime3.events.detector import EventDetector
from knowledge_service.runtime3.models import SegmentType
from knowledge_service.runtime3.narrative.synthesis import NarrativeSynthesizer
from knowledge_service.runtime3.story_graph.builder import StoryGraphBuilder
from tests.runtime3.conftest import make_segment


def test_narrative_produces_editorial_fields():
    extractor = SemanticClaimExtractor()
    segments = [
        make_segment(
            "Physicists detected new evidence of dark matter using underground observatory instruments.",
            segment_type=SegmentType.NEWS,
        ),
        make_segment(
            "The dark matter debate intensified after rival labs reported conflicting detection signals.",
            segment_type=SegmentType.DISCUSSION,
        ),
    ]
    claims = extractor.extract_from_segments(segments)
    entities = EntityResolver().resolve_claims(claims)
    events = EventDetector().detect(claims, entities)
    graph = StoryGraphBuilder().build(claims, entities, events)
    stories = NarrativeSynthesizer().synthesize(graph.stories)
    assert stories
    story = stories[0]
    assert story.headline
    assert story.executive_summary
    assert story.what_happened
    assert story.why_it_matters
    assert story.future_watch
    assert "Dark Matter" in story.headline or "dark matter" in story.headline.lower()