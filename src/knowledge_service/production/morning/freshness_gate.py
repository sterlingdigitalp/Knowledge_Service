"""Freshness gate — prevent stale headlines in the Morning Brief."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from ...analyst.models import Claim, NoveltyClass
from ...analyst.synthesis.models import IntelligenceItem, ThemeEvolutionState
from ...intelligence.models import now_iso


FRESH_THEME_STATES = {
    ThemeEvolutionState.NEW.value,
    ThemeEvolutionState.STRENGTHENING.value,
    ThemeEvolutionState.MATERIAL_CHANGE.value,
    ThemeEvolutionState.CONTRADICTING.value,
}


@dataclass
class FreshnessDecision:
    item_id: str
    title: str
    eligible: bool
    reason: str
    signals: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "title": self.title,
            "eligible": self.eligible,
            "reason": self.reason,
            "signals": dict(self.signals),
        }


@dataclass
class FreshnessReport:
    evaluated_at: str
    new_episode_ids: List[str]
    new_claim_ids: List[str]
    items_evaluated: int = 0
    items_eligible: int = 0
    items_rejected: int = 0
    no_fresh_signal: bool = False
    decisions: List[FreshnessDecision] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluated_at": self.evaluated_at,
            "new_episode_ids": list(self.new_episode_ids),
            "new_claim_ids": list(self.new_claim_ids),
            "items_evaluated": self.items_evaluated,
            "items_eligible": self.items_eligible,
            "items_rejected": self.items_rejected,
            "no_fresh_signal": self.no_fresh_signal,
            "decisions": [decision.to_dict() for decision in self.decisions],
        }


class FreshnessGate:
    """Filter intelligence items so headlines reflect genuinely new signal."""

    def __init__(
        self,
        *,
        headline_max_age_days: Optional[int] = None,
        new_claim_window_hours: Optional[int] = None,
    ):
        self.headline_max_age_days = headline_max_age_days or int(
            os.environ.get("KNOWLEDGE_FRESHNESS_MAX_AGE_DAYS", "7")
        )
        self.new_claim_window_hours = new_claim_window_hours or int(
            os.environ.get("KNOWLEDGE_FRESHNESS_NEW_CLAIM_HOURS", "36")
        )

    def filter_items(
        self,
        items: Sequence[IntelligenceItem],
        *,
        new_episode_ids: Iterable[str],
        new_claim_ids: Iterable[str],
        claims_by_id: Dict[str, Claim],
        reference_time: Optional[datetime] = None,
    ) -> tuple[List[IntelligenceItem], FreshnessReport]:
        episode_set = set(new_episode_ids)
        claim_set = set(new_claim_ids)
        current = reference_time or datetime.now(timezone.utc)
        decisions: List[FreshnessDecision] = []
        eligible: List[IntelligenceItem] = []

        for item in items:
            decision = self._evaluate_item(
                item,
                new_episode_ids=episode_set,
                new_claim_ids=claim_set,
                claims_by_id=claims_by_id,
                reference_time=current,
            )
            decisions.append(decision)
            if decision.eligible:
                eligible.append(item)

        report = FreshnessReport(
            evaluated_at=now_iso(),
            new_episode_ids=sorted(episode_set),
            new_claim_ids=sorted(claim_set),
            items_evaluated=len(items),
            items_eligible=len(eligible),
            items_rejected=len(items) - len(eligible),
            no_fresh_signal=len(eligible) == 0,
            decisions=decisions,
        )
        return eligible, report

    def _evaluate_item(
        self,
        item: IntelligenceItem,
        *,
        new_episode_ids: Set[str],
        new_claim_ids: Set[str],
        claims_by_id: Dict[str, Claim],
        reference_time: datetime,
    ) -> FreshnessDecision:
        supporting = [claims_by_id[cid] for cid in item.supporting_claim_ids if cid in claims_by_id]
        signals: Dict[str, Any] = {
            "novelty_classification": item.novelty_classification,
            "novelty_score": item.novelty_score,
            "theme_evolution": item.theme_evolution.state.value if item.theme_evolution else None,
        }

        if any(claim.episode_id in new_episode_ids for claim in supporting):
            return FreshnessDecision(
                item_id=item.item_id,
                title=item.title,
                eligible=True,
                reason="new_acquisition",
                signals={**signals, "matched_new_episode": True},
            )

        if any(claim.claim_id in new_claim_ids for claim in supporting):
            return FreshnessDecision(
                item_id=item.item_id,
                title=item.title,
                eligible=True,
                reason="new_claim",
                signals={**signals, "matched_new_claim": True},
            )

        if item.theme_evolution and item.theme_evolution.state.value in FRESH_THEME_STATES:
            if item.novelty_classification.lower() != NoveltyClass.REPEAT.value:
                return FreshnessDecision(
                    item_id=item.item_id,
                    title=item.title,
                    eligible=True,
                    reason="theme_evolution",
                    signals={**signals, "theme_state": item.theme_evolution.state.value},
                )

        if item.novelty_classification.lower() == NoveltyClass.REPEAT.value and item.novelty_score < 0.35:
            return FreshnessDecision(
                item_id=item.item_id,
                title=item.title,
                eligible=False,
                reason="repeat_no_new_signal",
                signals=signals,
            )

        newest_claim_age = _newest_claim_age_days(supporting, reference_time)
        signals["newest_claim_age_days"] = newest_claim_age
        if newest_claim_age is not None and newest_claim_age > self.headline_max_age_days:
            return FreshnessDecision(
                item_id=item.item_id,
                title=item.title,
                eligible=False,
                reason="stale_source_material",
                signals=signals,
            )

        if item.novelty_score >= 0.72 and item.novelty_classification.lower() in {
            NoveltyClass.NEW.value,
            NoveltyClass.REFINEMENT.value,
            NoveltyClass.CONTRADICTION.value,
            NoveltyClass.UPDATE.value,
        }:
            if newest_claim_age is None or newest_claim_age <= self.headline_max_age_days:
                return FreshnessDecision(
                    item_id=item.item_id,
                    title=item.title,
                    eligible=True,
                    reason="high_novelty_recent",
                    signals=signals,
                )

        return FreshnessDecision(
            item_id=item.item_id,
            title=item.title,
            eligible=False,
            reason="no_today_signal",
            signals=signals,
        )


def _newest_claim_age_days(claims: Sequence[Claim], reference_time: datetime) -> Optional[float]:
    timestamps: List[datetime] = []
    for claim in claims:
        parsed = _parse_timestamp(claim.published_at) or _parse_timestamp(claim.created_at)
        if parsed is not None:
            timestamps.append(parsed)
    if not timestamps:
        return None
    newest = max(timestamps)
    if newest.tzinfo is None:
        newest = newest.replace(tzinfo=timezone.utc)
    delta = reference_time - newest.astimezone(timezone.utc)
    return max(0.0, delta.total_seconds() / 86400.0)


def _parse_timestamp(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None