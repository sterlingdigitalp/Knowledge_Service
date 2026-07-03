"""Intelligence Layer 2.0 pipeline orchestrator."""

from __future__ import annotations

import time
from typing import List, Sequence

from ..analyst.synthesis.models import IntelligenceItem
from .config import IL2Config
from .editorial_synthesis import apply_card_to_item, synthesize_from_item
from .models import AnalystBriefCard, IL2Result
from .quality_gate import EditorialQualityGate
from .semantic_cluster import cluster_intelligence_items


class IntelligenceV2Pipeline:
    """Semantic clustering → canonical resolution → editorial synthesis → quality gate."""

    def __init__(self, config: IL2Config | None = None):
        self.config = config or IL2Config()
        self.gate = EditorialQualityGate(self.config)

    def run(self, items: Sequence[IntelligenceItem]) -> IL2Result:
        started = time.perf_counter()
        # Mutate caller-provided copies in place (integration layer owns deepcopy).
        working = list(items)

        cluster_result = cluster_intelligence_items(working, self.config)
        cards: List[AnalystBriefCard] = []
        titles_resolved = 0

        for item in cluster_result.items:
            card = synthesize_from_item(item)
            if card.original_title != card.title:
                titles_resolved += 1
            verdict = self.gate.evaluate(card)
            card.quality_score = verdict.quality_score
            card.accepted = verdict.accepted
            card.rejection_reason = verdict.rejection_reason
            card.failure_modes = verdict.failure_modes
            cards.append(card)
            if verdict.accepted:
                apply_card_to_item(item, card)

        accepted = [card for card in cards if card.accepted]
        rejected = [card for card in cards if not card.accepted]

        return IL2Result(
            cards=cards,
            accepted_count=len(accepted),
            rejected_count=len(rejected),
            clusters_formed=len(cluster_result.clusters),
            titles_resolved=titles_resolved,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            enabled=True,
        )

    def filter_items(self, items: Sequence[IntelligenceItem], result: IL2Result) -> List[IntelligenceItem]:
        """Return only items whose IL2 cards passed the quality gate."""
        accepted_ids = {card.item_id for card in result.cards if card.accepted}
        if not accepted_ids:
            return list(items)
        filtered = [item for item in items if item.item_id in accepted_ids]
        return filtered if filtered else list(items)