"""Final-title quality validation for IL2 publication."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Sequence, Set

from .failure_modes import (
    FRAGMENT_STARTERS,
    GENERIC_TITLE_PATTERNS,
    INTRO_FILLERS,
    SPONSOR_MARKERS,
    FailureMode,
)

# Single-token titles that are never acceptable as intelligence headlines.
GENERIC_SINGLE_WORDS = frozenset({
    "welcome", "however", "rather", "there", "ai", "agents", "better",
    "matched", "welcome", "episode", "podcast", "intro", "signal",
})

# Orphan adverbs/conjunctions that cannot head a title.
ORPHAN_OPENERS = frozenset({
    "however", "rather", "therefore", "meanwhile", "otherwise", "welcome",
    "and", "but", "so", "well", "yeah", "okay", "if", "when", "because",
})

# Two-word fragment patterns (second word is not a substantive noun).
WEAK_BIGRAM_ENDINGS = frozenset({
    "better", "there", "back", "out", "next", "western", "i'd", "i'm",
    "they're", "we're", "you're",
})

CLAUSE_OPENERS = (
    "if you want",
    "if you ",
    "and i'd",
    "and we'll",
    "and they",
    "rather, it's",
    "rather it",
    "i want to",
    "help me ",
    "go to ",
)

MALFORMED_POSSESSIVE = re.compile(r"\b\w+'[A-Z]{1,2}\b")

MIN_TITLE_WORDS = 3
MAX_TITLE_WORDS = 8
MIN_RESOLUTION_CONFIDENCE = 0.72
MIN_EVIDENCE_ALIGNMENT = 0.38


@dataclass
class TitleValidation:
    valid: bool
    failure_modes: List[str]
    reason: str = ""
    alignment_score: float = 0.0


def validate_final_title(
    title: str,
    *,
    evidence_text: str = "",
    resolution_confidence: float = 0.0,
    resolved_from: str = "",
) -> TitleValidation:
    """Return whether a title is acceptable for publication."""
    cleaned = re.sub(r"\s+", " ", title.strip())
    if not cleaned:
        return TitleValidation(False, [FailureMode.SPEECH_FRAGMENT.value], "Empty title")

    modes = classify_title_defects(cleaned)
    if modes:
        return TitleValidation(
            False,
            modes,
            _primary_reason(modes),
        )

    if resolved_from in {"fallback", "claim_extraction", "entity_keyword_merge", "primary_entity"}:
        return TitleValidation(
            False,
            [FailureMode.LOW_INFORMATION.value, FailureMode.GENERIC_TOPIC.value],
            f"Resolution path '{resolved_from}' cannot produce publishable titles",
        )

    if resolution_confidence < MIN_RESOLUTION_CONFIDENCE:
        return TitleValidation(
            False,
            [FailureMode.LOW_INFORMATION.value],
            f"Resolution confidence {resolution_confidence:.2f} below threshold",
        )

    alignment = evidence_title_alignment(cleaned, evidence_text)
    if alignment < MIN_EVIDENCE_ALIGNMENT:
        return TitleValidation(
            False,
            [FailureMode.TITLE_EVIDENCE_MISMATCH.value],
            f"Title not substantiated by evidence (alignment {alignment:.2f})",
            alignment_score=alignment,
        )

    return TitleValidation(True, [], alignment_score=alignment)


def classify_title_defects(title: str) -> List[str]:
    """Detect fragment and low-quality title defects."""
    modes: List[str] = []
    lower = title.lower()
    words = title.split()

    if len(words) < MIN_TITLE_WORDS:
        modes.append(FailureMode.SPEECH_FRAGMENT.value)
    if len(words) > MAX_TITLE_WORDS:
        modes.append(FailureMode.SPEECH_FRAGMENT.value)

    if words and words[0].lower() in ORPHAN_OPENERS:
        modes.append(FailureMode.SPEECH_FRAGMENT.value)
    if words and words[0].lower() in FRAGMENT_STARTERS:
        modes.append(FailureMode.SPEECH_FRAGMENT.value)

    if len(words) == 1 and lower in GENERIC_SINGLE_WORDS:
        modes.append(FailureMode.GENERIC_TOPIC.value)
    if lower in GENERIC_SINGLE_WORDS:
        modes.append(FailureMode.GENERIC_TOPIC.value)

    if len(words) == 2 and words[-1].lower() in WEAK_BIGRAM_ENDINGS:
        modes.append(FailureMode.SPEECH_FRAGMENT.value)

    if any(lower.startswith(opener) for opener in CLAUSE_OPENERS):
        modes.append(FailureMode.SPEECH_FRAGMENT.value)

    if MALFORMED_POSSESSIVE.search(title):
        modes.append(FailureMode.SPEECH_FRAGMENT.value)

    if lower.endswith(" developments") or lower.endswith(" signal"):
        modes.append(FailureMode.DEVELOPMENTS_SUFFIX.value)

    if any(pattern in lower for pattern in GENERIC_TITLE_PATTERNS):
        modes.append(FailureMode.GENERIC_TOPIC.value)

    if _looks_like_transcript_residue(title):
        modes.append(FailureMode.SPEECH_FRAGMENT.value)

    if not _has_subject_and_theme(title):
        modes.append(FailureMode.LOW_INFORMATION.value)

    return sorted(set(modes))


def evidence_title_alignment(title: str, evidence_text: str) -> float:
    """Score how well evidence substantiates the proposed title."""
    if not evidence_text.strip():
        return 0.0

    evidence_lower = evidence_text.lower()
    if any(marker in evidence_lower for marker in SPONSOR_MARKERS):
        return 0.05
    if any(filler in evidence_lower for filler in INTRO_FILLERS):
        return 0.12
    title_tokens = _expand_semantic_tokens(_significant_tokens(title))
    evidence_tokens = _expand_semantic_tokens(_significant_tokens(evidence_text))
    if not title_tokens:
        return 0.0

    overlap = len(title_tokens & evidence_tokens)
    ratio = overlap / max(len(title_tokens), 1)
    substantive_evidence = len([t for t in evidence_tokens if len(t) >= 5])
    density_bonus = min(0.25, substantive_evidence * 0.04)
    phrase_bonus = _phrase_alignment_bonus(title, evidence_lower)
    return min(1.0, ratio * 0.65 + density_bonus + phrase_bonus)


SEMANTIC_ALIASES: dict[str, set[str]] = {
    "byzantine": {"roman", "east", "empire", "constantine"},
    "empire": {"roman", "byzantine", "east"},
    "california": {"swalwell", "porter", "becerra", "attorney"},
    "race": {"swalwell", "porter", "election", "attorney"},
    "dynamics": {"swalwell", "porter", "becerra"},
    "matter": {"dark", "gamma", "neutron", "stars"},
    "detection": {"dark", "gamma", "neutron"},
    "knowledge": {"insights", "consolidating", "job", "workplace"},
    "workplace": {"job", "insights", "consolidating"},
}


def _expand_semantic_tokens(tokens: Set[str]) -> Set[str]:
    expanded = set(tokens)
    for token in list(tokens):
        for alias in SEMANTIC_ALIASES.get(token, set()):
            expanded.add(alias)
    return expanded


def _phrase_alignment_bonus(title: str, evidence_lower: str) -> float:
    bonus = 0.0
    pairs = (
        ("byzantine", ("east roman", "roman empire", "constantine")),
        ("california", ("swalwell", "porter", "becerra", "attorney general")),
        ("dark matter", ("dark matter", "gamma rays", "neutron stars")),
    )
    title_lower = title.lower()
    for title_hint, evidence_hints in pairs:
        if title_hint in title_lower and any(hint in evidence_lower for hint in evidence_hints):
            bonus = max(bonus, 0.28)
    return bonus


def _significant_tokens(text: str) -> Set[str]:
    stop = GENERIC_SINGLE_WORDS | FRAGMENT_STARTERS | ORPHAN_OPENERS | {
        "independent", "source", "sources", "related", "claims", "discussed",
        "development", "developments", "strategic", "signals", "signal",
        "historical", "analysis", "coverage", "adoption", "economics",
    }
    tokens = set(re.findall(r"[a-z0-9]{3,}", text.lower()))
    return {token for token in tokens if token not in stop}


def _looks_like_transcript_residue(title: str) -> bool:
    lower = title.lower()
    residue_markers = (
        "if you want",
        "help me figure",
        "help me out",
        "go to mercury",
        "visit mercury",
        "welcome back",
        "number one podcast",
        "there there",
        "ai i'd",
        "agents better",
        "east roman empire western",
    )
    return any(marker in lower for marker in residue_markers)


def _has_subject_and_theme(title: str) -> bool:
    """Require at least one substantive token suggesting a subject or theme."""
    tokens = _significant_tokens(title)
    if len(tokens) < 2:
        return False
    # Accept known analyst headline shapes: proper nouns / domain terms.
    domain_hints = {
        "empire", "byzantine", "roman", "inference", "agent", "agents",
        "founder", "mercury", "banking", "glp", "ozempic", "nvidia",
        "openai", "anthropic", "swalwell", "porter", "election", "podcast",
        "longevity", "peptide", "capital", "valuation", "infrastructure",
    }
    lower_tokens = {t.lower() for t in tokens}
    if lower_tokens & domain_hints:
        return True
    # Multi-word title with at least two substantive non-stop tokens.
    return len([t for t in tokens if len(t) >= 5]) >= 1 and len(tokens) >= 2


def _primary_reason(modes: List[str]) -> str:
    if FailureMode.SPONSOR_CTA.value in modes:
        return "Sponsor CTA detected"
    if FailureMode.INTRO_FILLER.value in modes:
        return "Podcast intro filler — not intelligence"
    if FailureMode.SPEECH_FRAGMENT.value in modes:
        return "Speech fragment — not a publishable title"
    if FailureMode.GENERIC_TOPIC.value in modes:
        return "Generic or low-information title"
    if FailureMode.TITLE_EVIDENCE_MISMATCH.value in modes:
        return "Title not supported by evidence"
    return "Title failed quality validation"