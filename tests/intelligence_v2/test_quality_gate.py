"""Tests for editorial quality gate."""

from knowledge_service.intelligence_v2.editorial_synthesis import synthesize_from_item
from knowledge_service.intelligence_v2.quality_gate import EditorialQualityGate
from tests.intelligence_v2.conftest import make_item


def test_rejects_sponsor_cta_card():
    item = make_item(
        title="Visit Mercury",
        excerpt="If you want to learn more, go to mercury.com.",
        item_id="mercury-1",
    )
    card = synthesize_from_item(item)
    verdict = EditorialQualityGate().evaluate(card)
    assert not verdict.accepted
    assert verdict.rejection_reason


def test_accepts_substantive_canonical_card():
    item = make_item(
        title="East Roman Empire Western",
        excerpt=(
            "Ideals become concretized through the East Roman Empire; Constantine "
            "and Byzantine continuity remain central to the discussion."
        ),
        item_id="byzantine-1",
    )
    card = synthesize_from_item(item)
    verdict = EditorialQualityGate().evaluate(card)
    assert verdict.accepted
    assert card.title == "Byzantine Empire Historical Analysis"