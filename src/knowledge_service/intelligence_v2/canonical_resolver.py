"""Canonical topic resolver — evidence-driven titles, never phrase fragments."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .entity_resolver import resolve_entities
from .failure_modes import (
    INTRO_FILLERS,
    SPONSOR_MARKERS,
    FailureMode,
)
from .title_validation import (
    classify_title_defects,
    evidence_title_alignment,
    validate_final_title,
)


def _evidence_matches_pattern(triggers: Tuple[str, ...], evidence_lower: str) -> bool:
    """Pattern triggers must appear in claim evidence, not metadata alone."""
    if not evidence_lower.strip():
        return False
    for trigger in triggers:
        if " " in trigger:
            if trigger in evidence_lower:
                return True
        elif re.search(rf"\b{re.escape(trigger)}s?\b", evidence_lower):
            return True
    return False


def _pattern_allowed_for_evidence(
    canonical_title: str,
    evidence_text: str,
    raw_title: str,
    raw_defects: List[str],
) -> bool:
    """Block pattern overmatch when evidence cannot substantiate the headline."""
    evidence_lower = evidence_text.lower()
    raw_lower = raw_title.lower()

    if _evidence_trails_off_incomplete(evidence_lower):
        return False

    if FailureMode.SPEECH_FRAGMENT.value in raw_defects:
        if canonical_title == "Workplace Knowledge Consolidation" and "agent" not in evidence_lower:
            return False
        if canonical_title == "Enterprise AI Agent Adoption" and "agent" not in evidence_lower:
            return False
        if "welcome" in raw_lower and FailureMode.INTRO_FILLER.value not in raw_defects:
            if "welcome back" in evidence_lower or "number one podcast" in evidence_lower:
                return False

    return True


def _evidence_trails_off_incomplete(evidence_lower: str) -> bool:
    incomplete_endings = (
        "you talk about",
        "one of the things you",
        "because one of the",
        "i think, through",
    )
    return any(evidence_lower.rstrip().endswith(end) for end in incomplete_endings)


# (evidence triggers, canonical title, min alignment required)
TOPIC_PATTERNS: List[Tuple[Tuple[str, ...], str, float]] = [
    (("east roman empire", "byzantine", "constantine", "roman empire"), "Byzantine Empire Historical Analysis", 0.22),
    (("eric swalwell", "katie porter", "becerra", "attorney general"), "California AG Race Dynamics", 0.20),
    (("dark matter", "gamma rays", "neutron stars"), "Dark Matter Detection Debate", 0.30),
    (("getting better at your job", "consolidating", "insights", "knowledge"), "Workplace Knowledge Consolidation", 0.28),
    (("founder", "startup", "operator", "career", "figure out where"), "AI Founder Career Positioning", 0.35),
    (("agent", "autonomous", "tool use", "workflow", "enterprise"), "Enterprise AI Agent Adoption", 0.35),
    (("inference", "gpu", "compute", "datacenter", "cuda"), "AI Inference Economics", 0.30),
    (("glp", "ozempic", "wegovy", "metabolic"), "GLP-1 Competitive Landscape", 0.30),
    (("openai", "anthropic", "frontier model"), "Frontier Lab Strategy", 0.30),
    (("longevity", "peptide", "clinical"), "Longevity Medicine Signals", 0.30),
    (("market", "valuation", "capital"), "Capital Allocation Debate", 0.30),
]

UNRESOLVED = "UNRESOLVED"


@dataclass
class ResolutionResult:
    canonical_title: str
    canonical_topic: str
    resolved_from: str
    failure_modes: List[str]
    confidence: float
    resolvable: bool = True

    @property
    def publishable(self) -> bool:
        return self.resolvable and self.canonical_title != UNRESOLVED


def resolve_canonical_title(
    *,
    raw_title: str,
    keywords: Sequence[str],
    entities: Sequence[str],
    claim_excerpts: Sequence[str],
    sources: Sequence[str],
) -> ResolutionResult:
    """Transform fragment labels into canonical analyst topics or mark unresolvable."""
    failure_modes: List[str] = list(classify_title_defects(raw_title))
    evidence_text = " ".join(claim_excerpts[:5])
    haystack = _build_haystack(raw_title, keywords, entities, claim_excerpts, sources)
    evidence_lower = evidence_text.lower()
    lower = haystack.lower()

    for marker in SPONSOR_MARKERS:
        if marker in lower:
            failure_modes.append(FailureMode.SPONSOR_CTA.value)
            return _unresolved(failure_modes, "sponsor_cta", confidence=0.0)

    for filler in INTRO_FILLERS:
        if filler in evidence_text.lower():
            failure_modes.append(FailureMode.INTRO_FILLER.value)
            return _unresolved(failure_modes, "intro_filler", confidence=0.0)

    if classify_title_defects(raw_title):
        failure_modes.extend(classify_title_defects(raw_title))

    raw_defects = classify_title_defects(raw_title)
    # Evidence-only resolution — never invent from weak fragments.
    best: Optional[ResolutionResult] = None
    for triggers, title, min_align in TOPIC_PATTERNS:
        if not _evidence_matches_pattern(triggers, evidence_lower):
            continue
        if not _pattern_allowed_for_evidence(title, evidence_text, raw_title, raw_defects):
            failure_modes.append(FailureMode.PATTERN_OVERMATCH.value)
            continue
        alignment = evidence_title_alignment(title, evidence_text)
        if alignment < min_align:
            failure_modes.append(FailureMode.PATTERN_OVERMATCH.value)
            continue
        candidate = ResolutionResult(
            canonical_title=title,
            canonical_topic=_topic_slug(title),
            resolved_from="evidence_pattern",
            failure_modes=list(failure_modes),
            confidence=round(0.70 + alignment * 0.25, 3),
            resolvable=True,
        )
        validation = validate_final_title(
            title,
            evidence_text=evidence_text,
            resolution_confidence=candidate.confidence,
            resolved_from="evidence_pattern",
        )
        if validation.valid and (best is None or candidate.confidence > best.confidence):
            best = candidate

    if best is not None:
        return best

    # Raw title only if already valid (rare).
    if not failure_modes:
        validation = validate_final_title(
            raw_title,
            evidence_text=evidence_text,
            resolution_confidence=0.80,
            resolved_from="raw_valid",
        )
        if validation.valid:
            return ResolutionResult(
                canonical_title=raw_title,
                canonical_topic=_topic_slug(raw_title),
                resolved_from="raw_valid",
                failure_modes=[],
                confidence=0.80,
                resolvable=True,
            )

    failure_modes.append(FailureMode.LOW_INFORMATION.value)
    return _unresolved(sorted(set(failure_modes)), "insufficient_evidence", confidence=0.0)


def detect_title_failure_modes(title: str, evidence_text: str) -> List[str]:
    """Classify failure modes for an existing title."""
    modes = list(classify_title_defects(title))
    evidence_lower = evidence_text.lower()

    if any(marker in evidence_lower for marker in SPONSOR_MARKERS):
        modes.append(FailureMode.SPONSOR_CTA.value)
    if any(filler in evidence_lower for filler in INTRO_FILLERS):
        modes.append(FailureMode.INTRO_FILLER.value)
    alignment = evidence_title_alignment(title, evidence_text)
    if alignment < 0.38:
        modes.append(FailureMode.TITLE_EVIDENCE_MISMATCH.value)
    return sorted(set(modes))


def _unresolved(failure_modes: List[str], source: str, *, confidence: float) -> ResolutionResult:
    return ResolutionResult(
        canonical_title=UNRESOLVED,
        canonical_topic="unresolved",
        resolved_from=source,
        failure_modes=failure_modes,
        confidence=confidence,
        resolvable=False,
    )


def _build_haystack(
    raw_title: str,
    keywords: Sequence[str],
    entities: Sequence[str],
    claim_excerpts: Sequence[str],
    sources: Sequence[str],
) -> str:
    return " ".join([
        raw_title,
        " ".join(keywords),
        " ".join(entities),
        " ".join(claim_excerpts[:5]),
        " ".join(sources),
    ])


def _topic_slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return slug[:64]