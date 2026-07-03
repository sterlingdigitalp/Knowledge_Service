"""Editorial quality gate — reject low-quality intelligence cards."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from .canonical_resolver import UNRESOLVED, detect_title_failure_modes
from .config import IL2Config
from .failure_modes import BOILERPLATE_PHRASES, FailureMode
from .models import AnalystBriefCard
from .title_validation import validate_final_title


@dataclass
class GateVerdict:
    accepted: bool
    quality_score: float
    rejection_reason: Optional[str]
    failure_modes: List[str]


class EditorialQualityGate:
    """Reject fragment titles, sponsor CTAs, boilerplate, and low-information cards."""

    def __init__(self, config: Optional[IL2Config] = None):
        self.config = config or IL2Config()

    def evaluate(self, card: AnalystBriefCard) -> GateVerdict:
        failure_modes = list(card.failure_modes)
        evidence_text = " ".join(str(row.get("excerpt", "")) for row in card.evidence)
        failure_modes.extend(detect_title_failure_modes(card.original_title, evidence_text))

        if self.config.reject_sponsor_ctas and FailureMode.SPONSOR_CTA.value in failure_modes:
            return GateVerdict(
                accepted=False,
                quality_score=0.0,
                rejection_reason="Sponsor CTA detected in evidence",
                failure_modes=sorted(set(failure_modes)),
            )

        if card.title == UNRESOLVED or not card.title.strip():
            return GateVerdict(
                accepted=False,
                quality_score=0.0,
                rejection_reason="Could not resolve a publishable title from evidence",
                failure_modes=sorted(set(failure_modes + [FailureMode.LOW_INFORMATION.value])),
            )

        resolved_from = "insufficient_evidence" if card.title == UNRESOLVED else "evidence_pattern"
        title_validation = validate_final_title(
            card.title,
            evidence_text=evidence_text,
            resolution_confidence=card.confidence,
            resolved_from=resolved_from,
        )
        failure_modes.extend(title_validation.failure_modes)
        failure_modes.extend(detect_title_failure_modes(card.title, evidence_text))
        title_score = 0.0 if not title_validation.valid else min(1.0, 0.55 + title_validation.alignment_score * 0.45)
        summary_score = self._summary_score(card)
        evidence_score = self._evidence_score(card, evidence_text)
        overall = round(0.45 * title_score + 0.35 * summary_score + 0.20 * evidence_score, 3)

        rejection: Optional[str] = None
        if not title_validation.valid:
            rejection = title_validation.reason or "Title failed final quality validation"
        elif self.config.reject_fragment_titles and title_score < self.config.min_title_quality:
            rejection = f"Fragment or low-quality title (score {title_score:.2f})"
        elif self.config.reject_boilerplate_summaries and summary_score < self.config.min_summary_quality:
            rejection = f"Boilerplate or generic summary (score {summary_score:.2f})"
        elif evidence_score < 0.35:
            rejection = "Insufficient evidence density"
            failure_modes.append(FailureMode.LOW_INFORMATION.value)
        elif overall < 0.50:
            rejection = f"Overall editorial quality below threshold ({overall:.2f})"
            failure_modes.append(FailureMode.LOW_INFORMATION.value)

        accepted = rejection is None
        return GateVerdict(
            accepted=accepted,
            quality_score=overall,
            rejection_reason=rejection,
            failure_modes=sorted(set(failure_modes)),
        )

    def _summary_score(self, card: AnalystBriefCard) -> float:
        fields = " ".join([
            card.executive_summary,
            card.what_happened,
            card.why_it_matters,
        ])
        if len(fields.strip()) < 50:
            return 0.15

        lower = fields.lower()
        if "importance band" in lower or "novelty classification" in lower:
            return 0.20
        if "monitored speakers" in lower or "monitored corpus" in lower:
            return 0.25
        if "are converging on" in lower:
            return 0.28

        if "discussed:" in lower:
            base = 0.62
        elif "relevant to" in lower:
            base = 0.56
        else:
            base = 0.45

        boilerplate_hits = sum(1 for phrase in BOILERPLATE_PHRASES if phrase in lower)
        if boilerplate_hits >= 2:
            return min(base, 0.30)
        if boilerplate_hits >= 1:
            base -= 0.08

        unique_tokens = len(set(re.findall(r"[a-z]{4,}", lower)))
        if unique_tokens < 8:
            return max(0.35, base - 0.08)
        return min(1.0, base + unique_tokens * 0.012)

    def _evidence_score(self, card: AnalystBriefCard, evidence_text: str) -> float:
        if not card.evidence:
            return 0.0
        excerpts = [str(row.get("excerpt", "")).strip() for row in card.evidence]
        non_empty = [text for text in excerpts if len(text) >= 20]
        if not non_empty:
            return 0.10

        sponsor_hits = sum(
            1 for text in non_empty
            if any(marker in text.lower() for marker in ("mercury.com", "sponsored", "promo code"))
        )
        if sponsor_hits:
            return 0.05

        filler_hits = sum(
            1 for text in non_empty
            if any(filler in text.lower() for filler in ("welcome back", "number one podcast", "if you want"))
        )
        if filler_hits == len(non_empty):
            return 0.12

        alignment = validate_final_title(card.title, evidence_text=evidence_text).alignment_score
        return min(1.0, 0.30 + len(non_empty) * 0.10 + alignment * 0.35)