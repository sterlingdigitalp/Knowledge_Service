"""Tests for Agent E — story graph."""

from __future__ import annotations

from knowledge_service.runtime3.claims.extractor import SemanticClaimExtractor
from knowledge_service.runtime3.entities.resolver import EntityResolver
from knowledge_service.runtime3.events.detector import EventDetector
from knowledge_service.runtime3.models import SegmentType
from knowledge_service.runtime3.story_graph.builder import StoryGraphBuilder
from tests.runtime3.conftest import make_segment


def test_story_graph_clusters_related_claims():
    extractor = SemanticClaimExtractor()
    segments = [
        make_segment(
            "Coding agents are getting better at consolidating workplace knowledge across enterprise teams.",
            segment_type=SegmentType.DISCUSSION,
            podcast="Dwarkesh Podcast",
        ),
        make_segment(
            "RLVR training is improving how coding agents reason through multi-step software tasks.",
            segment_type=SegmentType.DISCUSSION,
            podcast="Dwarkesh Podcast",
        ),
        make_segment(
            "If you want to learn more, go to mercury.com.",
            segment_type=SegmentType.SPONSOR,
            podcast="Dwarkesh Podcast",
        ),
    ]
    claims = extractor.extract_from_segments(segments)
    entities = EntityResolver().resolve_claims(claims)
    events = EventDetector().detect(claims, entities)
    graph = StoryGraphBuilder().build(claims, entities, events)
    assert graph.stories
    story = graph.stories[0]
    assert len(story.supporting_claims) >= 2
    assert "mercury" not in story.headline.lower()


def test_byzantine_story_title():
    extractor = SemanticClaimExtractor()
    segments = [
        make_segment(
            "Constantine shaped the East Roman Empire and the Byzantine legacy after Rome fell in 476 AD.",
            segment_type=SegmentType.DISCUSSION,
        ),
        make_segment(
            "The East Roman Empire preserved classical ideals even as the Western empire collapsed.",
            segment_type=SegmentType.DISCUSSION,
        ),
    ]
    claims = extractor.extract_from_segments(segments)
    entities = EntityResolver().resolve_claims(claims)
    events = EventDetector().detect(claims, entities)
    graph = StoryGraphBuilder().build(claims, entities, events)
    assert graph.stories
    titles = " ".join(story.title.lower() for story in graph.stories)
    assert "roman" in titles or "byzantine" in titles or "constantine" in titles