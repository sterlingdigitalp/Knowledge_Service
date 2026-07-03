"""Tests for Agent D — event detection."""

from __future__ import annotations

from knowledge_service.runtime3.claims.extractor import SemanticClaimExtractor
from knowledge_service.runtime3.entities.resolver import EntityResolver
from knowledge_service.runtime3.events.detector import EventDetector
from knowledge_service.runtime3.models import SegmentType
from tests.runtime3.conftest import make_segment


def test_detect_election_event():
    extractor = SemanticClaimExtractor()
    segment = make_segment(
        "Eric Swalwell, Katie Porter, and Xavier Becerra are shaping the California attorney general race ahead of the election.",
        segment_type=SegmentType.NEWS,
    )
    claims = extractor.extract_from_segments([segment])
    entities = EntityResolver().resolve_claims(claims)
    events = EventDetector().detect(claims, entities)
    assert events
    assert events[0].event_type.value == "election"


def test_detect_scientific_discovery():
    extractor = SemanticClaimExtractor()
    segment = make_segment(
        "Physicists detected new evidence of dark matter using underground observatory instruments.",
        segment_type=SegmentType.NEWS,
    )
    claims = extractor.extract_from_segments([segment])
    entities = EntityResolver().resolve_claims(claims)
    events = EventDetector().detect(claims, entities)
    assert any(event.event_type.value in {"scientific_discovery", "research_paper"} for event in events)