"""Quality scoring for old vs new intelligence output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ..canonical_resolver import detect_title_failure_modes
from ..failure_modes import BOILERPLATE_PHRASES
from ..models import AnalystBriefCard


@dataclass
class DimensionScores:
    title_quality: float
    summary_quality: float
    entity_accuracy: float
    topic_coherence: float
    signal_usefulness: float
    actionability: float
    duplication: float
    editorial_quality: float

    def overall(self) -> float:
        values = [
            self.title_quality,
            self.summary_quality,
            self.entity_accuracy,
            self.topic_coherence,
            self.signal_usefulness,
            self.actionability,
            self.duplication,
            self.editorial_quality,
        ]
        return round(sum(values) / len(values), 3)

    def to_dict(self) -> Dict[str, float]:
        return {
            "title_quality": self.title_quality,
            "summary_quality": self.summary_quality,
            "entity_accuracy": self.entity_accuracy,
            "topic_coherence": self.topic_coherence,
            "signal_usefulness": self.signal_usefulness,
            "actionability": self.actionability,
            "duplication": self.duplication,
            "editorial_quality": self.editorial_quality,
            "overall": self.overall(),
        }


class QualityScorer:
    """Score intelligence cards across editorial dimensions."""

    def score_card(self, card: AnalystBriefCard) -> DimensionScores:
        evidence_text = " ".join(str(row.get("excerpt", "")) for row in card.evidence)
        failure_modes = detect_title_failure_modes(card.original_title or card.title, evidence_text)
        title_penalty = min(0.6, len(failure_modes) * 0.15)
        title_quality = max(0.0, 1.0 - title_penalty) if card.title else 0.0
        if card.original_title and card.title != card.original_title and title_quality < 0.7:
            title_quality = min(1.0, title_quality + 0.35)

        summary_quality = self._summary_quality(card.executive_summary)
        entity_accuracy = min(1.0, len(card.supporting_sources) * 0.15 + 0.4)
        topic_coherence = 0.85 if card.canonical_topic and "_" in card.canonical_topic else 0.55
        signal_usefulness = min(1.0, card.confidence + (0.1 if card.evidence else 0))
        actionability = 0.75 if card.suggested_action and "monitor" not in card.suggested_action.lower() else 0.45
        duplication = 0.9 if not failure_modes or "fm_duplicate" not in failure_modes else 0.4
        editorial_quality = card.quality_score if card.quality_score else summary_quality

        return DimensionScores(
            title_quality=round(title_quality, 3),
            summary_quality=round(summary_quality, 3),
            entity_accuracy=round(entity_accuracy, 3),
            topic_coherence=round(topic_coherence, 3),
            signal_usefulness=round(signal_usefulness, 3),
            actionability=round(actionability, 3),
            duplication=round(duplication, 3),
            editorial_quality=round(editorial_quality, 3),
        )

    def _summary_quality(self, summary: str) -> float:
        if not summary:
            return 0.0
        lower = summary.lower()
        hits = sum(1 for phrase in BOILERPLATE_PHRASES if phrase in lower)
        base = 0.85 - hits * 0.15
        return max(0.1, min(1.0, base))