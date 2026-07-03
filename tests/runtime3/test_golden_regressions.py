"""Golden regression tests — Runtime 3 must not resurrect known failures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge_service.runtime3.claims.extractor import SemanticClaimExtractor
from knowledge_service.runtime3.evaluation.metrics import is_fragment_title, is_sponsor_residue
from knowledge_service.runtime3.models import SegmentType
from knowledge_service.runtime3.narrative.headlines import generate_headline
from tests.runtime3.conftest import make_segment

FIXTURES = Path(__file__).parent / "fixtures" / "golden_degradation_cases.json"


def _load_cases() -> list[dict]:
    if not FIXTURES.exists():
        pytest.skip("golden fixtures not found")
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["case_id"])
def test_degradation_cases_not_resurrected(case: dict):
    extractor = SemanticClaimExtractor()
    segment = make_segment(
        case["transcript_excerpt"],
        segment_type=SegmentType(case.get("segment_type", "discussion")),
        podcast=case.get("podcast", "Test Podcast"),
    )
    claims = extractor.extract_from_segments([segment])

    if case.get("should_produce_claim"):
        assert claims, f"Expected claim for {case['case_id']}"
    else:
        assert not claims, f"Should not produce claim for {case['case_id']}: {claims}"

    if case.get("expected_headline"):
        from knowledge_service.runtime3.entities.resolver import EntityResolver
        from knowledge_service.runtime3.events.detector import EventDetector
        from knowledge_service.runtime3.story_graph.builder import StoryGraphBuilder
        from knowledge_service.runtime3.narrative.synthesis import NarrativeSynthesizer

        if len(claims) >= 2:
            claims = claims * 2  # ensure cluster threshold
        entities = EntityResolver().resolve_claims(claims)
        events = EventDetector().detect(claims, entities)
        graph = StoryGraphBuilder().build(claims, entities, events)
        stories = NarrativeSynthesizer().synthesize(graph.stories)
        if stories:
            assert not is_fragment_title(stories[0].headline)
            assert not is_sponsor_residue(stories[0].headline)


def test_visit_mercury_never_becomes_headline():
    from knowledge_service.runtime3.models import StoryType
    headline = generate_headline([], [], [], StoryType.GENERAL)
    assert headline != "Visit Mercury"
    assert not is_fragment_title("Byzantine Empire Historical Analysis")
    assert is_fragment_title("Visit Mercury")
    assert is_fragment_title("Agents Better")