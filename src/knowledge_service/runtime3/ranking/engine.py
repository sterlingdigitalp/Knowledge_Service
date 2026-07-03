"""Agent — story ranking for editorial opportunity."""

from __future__ import annotations

from typing import Dict, List, Sequence

from ..models import StoryObject
from ..thinking.models import RankedStory


class StoryRankingEngine:
    """Rank stories by editorial value."""

    def rank(
        self,
        stories: Sequence[StoryObject],
        *,
        date: str = "",
        persistent_map: Dict[str, str] | None = None,
        evolution_states: Dict[str, str] | None = None,
    ) -> List[RankedStory]:
        persistent_map = persistent_map or {}
        evolution_states = evolution_states or {}
        ranked: List[RankedStory] = []

        for story in stories:
            source_diversity = min(1.0, len(set(story.supporting_sources)) / 4.0)
            corroboration = min(1.0, len(story.supporting_claims) / 6.0)
            evidence_quality = min(1.0, story.confidence * 0.6 + corroboration * 0.4)
            recency = 1.0 if date else 0.8
            novelty = story.novelty
            importance = story.importance

            persistent_id = persistent_map.get(story.story_id, "")
            evolution = evolution_states.get(persistent_id, "")
            evolution_bonus = {
                "first_seen": 0.12,
                "strengthened": 0.10,
                "contradicted": 0.08,
                "stable": 0.04,
            }.get(evolution, 0.0)

            editorial_opportunity = min(1.0, (
                0.30 * importance
                + 0.20 * novelty
                + 0.20 * evidence_quality
                + 0.15 * source_diversity
                + 0.10 * corroboration
                + evolution_bonus
            ))

            rank_score = round(
                0.25 * importance
                + 0.20 * novelty
                + 0.20 * editorial_opportunity
                + 0.15 * evidence_quality
                + 0.10 * source_diversity
                + 0.10 * recency,
                3,
            )

            ranked.append(RankedStory(
                story=story,
                rank_score=rank_score,
                importance_score=importance,
                novelty_score=novelty,
                editorial_opportunity=round(editorial_opportunity, 3),
                recency_score=recency,
                evidence_quality=round(evidence_quality, 3),
                source_diversity=round(source_diversity, 3),
                corroboration_score=round(corroboration, 3),
                persistent_story_id=persistent_id,
                evolution_state=evolution,
            ))

        ranked.sort(key=lambda row: row.rank_score, reverse=True)
        return ranked