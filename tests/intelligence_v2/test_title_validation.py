"""Tests for final title validation."""

from knowledge_service.intelligence_v2.title_validation import (
    classify_title_defects,
    validate_final_title,
)

FRAGMENT_TITLES = [
    "If you want to help me out and help me figure out where next",
    "Agents Better",
    "Welcome",
    "AI I'D",
    "However",
    "There There'S",
    "Visit Mercury",
]


def test_fragment_titles_classified():
    for title in FRAGMENT_TITLES:
        modes = classify_title_defects(title)
        assert modes, f"Expected defects for '{title}'"


def test_valid_canonical_title_passes():
    result = validate_final_title(
        "Byzantine Empire Historical Analysis",
        evidence_text="discussion of the East Roman Empire and Constantine",
        resolution_confidence=0.85,
        resolved_from="evidence_pattern",
    )
    assert result.valid