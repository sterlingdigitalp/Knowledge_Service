"""Golden regression tests — known fragment titles must never be accepted."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge_service.intelligence_v2.editorial_synthesis import synthesize_from_item
from knowledge_service.intelligence_v2.quality_gate import EditorialQualityGate
from knowledge_service.intelligence_v2.title_validation import validate_final_title
from tests.intelligence_v2.conftest import make_item

FIXTURES = Path(__file__).parent / "fixtures" / "golden_fragment_titles.json"


def _load_cases() -> list[dict]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["sample_id"])
def test_fragment_titles_rejected_or_canonicalized(case: dict):
    item = make_item(
        title=case["title"],
        excerpt=case["evidence_excerpt"],
        item_id=case["sample_id"],
        corroboration=case.get("corroborated_by", 3),
        importance=case.get("importance_score", 0.8),
    )
    if case.get("theme_label"):
        item.theme_label = case["theme_label"]

    card = synthesize_from_item(item)
    verdict = EditorialQualityGate().evaluate(card)

    if case.get("should_reject", True):
        assert not verdict.accepted, (
            f"Expected rejection for '{case['title']}' but got title '{card.title}': "
            f"{verdict.rejection_reason}"
        )
        return

    assert verdict.accepted, f"Expected acceptance: {verdict.rejection_reason}"
    assert card.title == case["expected_canonical_title"]
    validation = validate_final_title(
        card.title,
        evidence_text=case["evidence_excerpt"],
        resolution_confidence=card.confidence,
        resolved_from="evidence_pattern",
    )
    assert validation.valid, validation.reason


def test_byzantine_empire_canonicalizes_and_passes():
    item = make_item(
        title="East Roman Empire Western",
        excerpt=(
            "And we'll talk about because those ideals become even more concretized "
            "through the East Roman Empire, because one of the things you talk about "
            "is Constantine and the Byzantine legacy."
        ),
        item_id="byzantine-1",
    )
    card = synthesize_from_item(item)
    verdict = EditorialQualityGate().evaluate(card)
    assert verdict.accepted
    assert card.title == "Byzantine Empire Historical Analysis"


def test_sponsor_cta_still_rejected():
    item = make_item(
        title="Visit Mercury",
        excerpt="If you want to learn more, go to mercury.com.",
        item_id="mercury-1",
    )
    card = synthesize_from_item(item)
    verdict = EditorialQualityGate().evaluate(card)
    assert not verdict.accepted
    assert "sponsor" in (verdict.rejection_reason or "").lower()