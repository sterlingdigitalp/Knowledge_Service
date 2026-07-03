"""Side-by-side comparison harness for old vs new intelligence output."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..editorial_synthesis import synthesize_from_item
from ..models import AnalystBriefCard
from ..pipeline import IntelligenceV2Pipeline
from ..quality_gate import EditorialQualityGate
from .scorer import QualityScorer


@dataclass
class ComparisonEntry:
    sample_id: str
    old_title: str
    new_title: str
    old_summary: str
    new_summary: str
    old_score: float
    new_score: float
    delta: float
    accepted: bool
    failure_modes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "old_title": self.old_title,
            "new_title": self.new_title,
            "old_summary": self.old_summary,
            "new_summary": self.new_summary,
            "old_score": self.old_score,
            "new_score": self.new_score,
            "delta": self.delta,
            "accepted": self.accepted,
            "failure_modes": list(self.failure_modes),
        }


@dataclass
class ComparisonReport:
    entries: List[ComparisonEntry] = field(default_factory=list)
    average_old_score: float = 0.0
    average_new_score: float = 0.0
    average_delta: float = 0.0
    improved_count: int = 0
    rejected_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entries": [entry.to_dict() for entry in self.entries],
            "average_old_score": self.average_old_score,
            "average_new_score": self.average_new_score,
            "average_delta": self.average_delta,
            "improved_count": self.improved_count,
            "rejected_count": self.rejected_count,
        }


class ComparisonHarness:
    """Compare Runtime 1 cards against IL2 output."""

    def __init__(self):
        self.scorer = QualityScorer()
        self.gate = EditorialQualityGate()
        self.pipeline = IntelligenceV2Pipeline()

    def compare_samples(self, samples: List[Dict[str, Any]]) -> ComparisonReport:
        entries: List[ComparisonEntry] = []
        for sample in samples:
            entry = self._compare_sample(sample)
            entries.append(entry)

        old_scores = [entry.old_score for entry in entries]
        new_scores = [entry.new_score for entry in entries]
        deltas = [entry.delta for entry in entries]

        return ComparisonReport(
            entries=entries,
            average_old_score=round(sum(old_scores) / len(old_scores), 3) if old_scores else 0.0,
            average_new_score=round(sum(new_scores) / len(new_scores), 3) if new_scores else 0.0,
            average_delta=round(sum(deltas) / len(deltas), 3) if deltas else 0.0,
            improved_count=sum(1 for delta in deltas if delta > 0),
            rejected_count=sum(1 for entry in entries if not entry.accepted),
        )

    def write_report(self, report: ComparisonReport, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    def _compare_sample(self, sample: Dict[str, Any]) -> ComparisonEntry:
        from ...analyst.synthesis.models import IntelligenceItem

        item = IntelligenceItem(
            item_id=str(sample.get("sample_id", "sample")),
            title=str(sample.get("title", "")),
            executive_summary=str(sample.get("summary", "")),
            why_surfaced=str(sample.get("why_surfaced", "")),
            why_it_matters=str(sample.get("why_you_care", "")),
            novelty_score=float(sample.get("novelty_score", 0.8)),
            novelty_classification=str(sample.get("novelty", "new")),
            importance_score=float(sample.get("importance_score", 0.8)),
            importance_band=str(sample.get("importance_band", "high")),
            confidence=float(sample.get("confidence", 0.9)),
            corroboration_count=int(sample.get("corroborated_by", 0)),
            contradiction_count=0,
            theme_id="eval-theme",
            theme_label=str(sample.get("matched", sample.get("title", ""))),
            profile_ids=[str(sample.get("profile_id", "ai"))],
            profile_names=[str(sample.get("profile_name", "AI"))],
            supporting_claim_ids=[],
            supporting_evidence=[{"excerpt": sample.get("evidence_excerpt", sample.get("what_changed", ""))}],
            timestamped_citations=[],
            speakers=[],
            sources=[str(sample.get("evidence_summary", "source"))],
            contradictions=[],
            historical_developments=[],
            claim_count=int(sample.get("claim_count", 2)),
        )

        old_card = AnalystBriefCard(
            title=item.title,
            executive_summary=item.executive_summary,
            what_happened=str(sample.get("what_changed", "")),
            why_it_matters=item.why_it_matters,
            evidence=item.supporting_evidence,
            confidence=item.confidence,
            confidence_explanation="",
            contradictions=[],
            what_to_watch="",
            suggested_action="",
            supporting_sources=item.sources,
            canonical_topic=item.theme_label,
            original_title=item.title,
            item_id=item.item_id,
        )
        old_score = self.scorer.score_card(old_card).overall()

        new_card = synthesize_from_item(item)
        verdict = self.gate.evaluate(new_card)
        new_card.quality_score = verdict.quality_score
        new_card.accepted = verdict.accepted
        new_card.failure_modes = verdict.failure_modes
        new_score = self.scorer.score_card(new_card).overall()

        return ComparisonEntry(
            sample_id=str(sample.get("sample_id", item.item_id)),
            old_title=old_card.title,
            new_title=new_card.title,
            old_summary=old_card.executive_summary[:300],
            new_summary=new_card.executive_summary[:300],
            old_score=old_score,
            new_score=new_score,
            delta=round(new_score - old_score, 3),
            accepted=new_card.accepted,
            failure_modes=new_card.failure_modes,
        )