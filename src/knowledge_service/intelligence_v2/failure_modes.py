"""Failure mode taxonomy for intelligence synthesis."""

from __future__ import annotations

from enum import Enum


class FailureMode(str, Enum):
    SPONSOR_CTA = "fm_sponsor_cta"
    SPEECH_FRAGMENT = "fm_speech_fragment"
    INTRO_FILLER = "fm_intro_filler"
    PATTERN_OVERMATCH = "fm_pattern_overmatch"
    DEVELOPMENTS_SUFFIX = "fm_developments_suffix"
    DEBUG_ARTIFACT = "fm_debug_artifact"
    BOILERPLATE_SUMMARY = "fm_boilerplate_summary"
    TITLE_EVIDENCE_MISMATCH = "fm_title_evidence_mismatch"
    GENERIC_TOPIC = "fm_generic_topic"
    LOW_INFORMATION = "fm_low_information"
    DUPLICATE_TOPIC = "fm_duplicate_topic"


FRAGMENT_STARTERS = frozenset({
    "i", "and", "but", "so", "well", "yeah", "okay", "the", "a", "we", "you",
    "ones", "this", "that", "visit", "figure", "welcome", "help", "if", "go",
})

SPONSOR_MARKERS = (
    "mercury.com",
    "go to ",
    "visit ",
    "sponsored by",
    "use code ",
    "promo code",
    "discount at",
)

INTRO_FILLERS = (
    "welcome back",
    "welcome to",
    "number one podcast",
    "episode ",
    "today on",
    "hey everyone",
)

BOILERPLATE_PHRASES = (
    "independent source",
    "are converging on",
    "what to watch next",
    "why it matters:",
    "why now:",
    "suggesting this is not stale repetition",
    "raises confidence this is a real shift, not noise",
    "monitored speakers",
    "monitored corpus",
    "importance band",
    "novelty classification",
    "independent corroboration",
    "flags strategic relevance",
)

GENERIC_TITLE_PATTERNS = (
    "emerging intelligence signal",
    "developments",
    "live discussion signal",
    "surfaces a",
)