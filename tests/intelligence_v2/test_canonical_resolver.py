"""Tests for canonical topic resolver."""

from knowledge_service.intelligence_v2.canonical_resolver import (
    UNRESOLVED,
    detect_title_failure_modes,
    resolve_canonical_title,
)


def test_visit_mercury_unresolvable_sponsor():
    result = resolve_canonical_title(
        raw_title="Visit Mercury",
        keywords=["visit", "mercury"],
        entities=[],
        claim_excerpts=["If you want to learn more, go to mercury.com."],
        sources=["Dwarkesh Podcast"],
    )
    assert result.canonical_title == UNRESOLVED
    assert not result.publishable
    assert "fm_sponsor_cta" in result.failure_modes


def test_figure_where_fragment_unresolvable():
    result = resolve_canonical_title(
        raw_title="If you want to help me out and help me figure out where next",
        keywords=["figure", "where"],
        entities=[],
        claim_excerpts=[
            "If you want to help me out and help me figure out where next that should go in the world."
        ],
        sources=["Lex Fridman Podcast"],
    )
    assert not result.publishable


def test_welcome_detects_intro_filler():
    modes = detect_title_failure_modes(
        "Welcome",
        "Welcome back to the number one podcast in the world, the All In Podcast.",
    )
    assert "fm_intro_filler" in modes or "fm_speech_fragment" in modes


def test_byzantine_resolves_from_evidence():
    result = resolve_canonical_title(
        raw_title="East Roman Empire Western",
        keywords=["roman", "empire", "east"],
        entities=[],
        claim_excerpts=[
            "those ideals become concretized through the East Roman Empire and Constantine."
        ],
        sources=["Lex Fridman Podcast"],
    )
    assert result.publishable
    assert result.canonical_title == "Byzantine Empire Historical Analysis"