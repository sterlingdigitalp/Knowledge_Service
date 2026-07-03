"""Tests for Agent C — entity resolution."""

from __future__ import annotations

from knowledge_service.runtime3.claims.extractor import SemanticClaimExtractor
from knowledge_service.runtime3.entities.resolver import EntityResolver
from knowledge_service.runtime3.models import SegmentType
from tests.runtime3.conftest import make_segment


def test_false_positive_entities_rejected():
    resolver = EntityResolver()
    claims = [
        _claim("Rather than focusing on hype, coding agents are getting better at workplace tasks."),
        _claim("However, dark matter detection remains debated among physicists."),
        _claim("There are interesting things to study in science."),
    ]
    entities = resolver.resolve_claims(claims)
    names = {entity.canonical_name.lower() for entity in entities}
    assert "rather" not in names
    assert "however" not in names
    assert "there" not in names


def test_canonical_entity_resolution():
    resolver = EntityResolver()
    claims = [_claim("Constantine shaped the East Roman Empire and Byzantine legacy after 476 AD.")]
    entities = resolver.resolve_claims(claims)
    names = [entity.canonical_name for entity in entities]
    assert any("constantine" in name.lower() or "roman" in name.lower() or "byzantine" in name.lower() for name in names)


def test_sponsor_entity_not_promoted():
    extractor = SemanticClaimExtractor()
    segments = [make_segment("Visit Mercury.com slash Command to learn more.", segment_type=SegmentType.SPONSOR)]
    claims = extractor.extract_from_segments(segments)
    resolver = EntityResolver()
    entities = resolver.resolve_claims(claims)
    assert entities == []


def _claim(text: str):
    extractor = SemanticClaimExtractor()
    segment = make_segment(text, segment_type=SegmentType.DISCUSSION)
    claims = extractor.extract_from_segments([segment])
    assert claims
    return claims[0]