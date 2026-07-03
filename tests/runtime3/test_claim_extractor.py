"""Tests for Agent B — semantic claim extraction."""

from __future__ import annotations

from knowledge_service.runtime3.claims.extractor import SemanticClaimExtractor
from knowledge_service.runtime3.models import SegmentType
from tests.runtime3.conftest import make_segment


def test_sponsor_claims_filtered():
    extractor = SemanticClaimExtractor()
    segments = [
        make_segment(
            "If you want to learn more, go to mercury.com.",
            segment_type=SegmentType.SPONSOR,
        ),
        make_segment(
            "Grant Sanderson argues that AI progress in mathematics reveals broader AGI timelines.",
            segment_type=SegmentType.DISCUSSION,
        ),
    ]
    claims = extractor.extract_from_segments(segments)
    assert len(claims) == 1
    assert "mathematics" in claims[0].claim_text


def test_meta_request_filtered():
    extractor = SemanticClaimExtractor()
    segments = [
        make_segment(
            "If you want to help me out and help me figure out where next that should go in the world, and also help me figure out where I'm in the world right now",
            segment_type=SegmentType.META_REQUEST,
        ),
    ]
    claims = extractor.extract_from_segments(segments)
    assert claims == []


def test_substantive_claim_has_metadata():
    extractor = SemanticClaimExtractor()
    segments = [
        make_segment(
            "Eric Swalwell, Katie Porter, and Xavier Becerra are competing in the California attorney general race.",
            segment_type=SegmentType.NEWS,
        ),
    ]
    claims = extractor.extract_from_segments(segments)
    assert len(claims) == 1
    assert claims[0].podcast_name == "Test Podcast"
    assert claims[0].confidence >= 0.5
    assert claims[0].embedding