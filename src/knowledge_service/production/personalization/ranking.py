"""Personalized ranking — learn from user behavior."""

from __future__ import annotations

from typing import Dict, List, Sequence

from ...analyst.synthesis.models import IntelligenceItem
from .store import PersonalizationStore


class PersonalizedRankingEngine:
    """Adjust intelligence item scores from observed behavior."""

    TELL_ME_MORE_BOOST = 0.12
    SAVE_BOOST = 0.08
    DISMISS_PENALTY = 0.25
    PROFILE_BOOST = 0.06

    def __init__(self, store: PersonalizationStore):
        self.store = store

    def rank(self, items: Sequence[IntelligenceItem]) -> List[IntelligenceItem]:
        prefs = self.store.load_preferences()
        feedback = self.store.load_feedback()
        topic_weights = self._topic_weights(prefs, feedback)
        profile_weights = prefs.get("profile_weights", {})
        dismissed = set(prefs.get("dismissed_items", []))
        boosted_ids = set(prefs.get("tell_me_more_items", []))
        saved_ids = set(prefs.get("saved_items", []))

        ranked: List[IntelligenceItem] = []
        for item in items:
            if item.item_id in dismissed:
                continue
            score = item.importance_score
            if item.item_id in boosted_ids:
                score += self.TELL_ME_MORE_BOOST
            if item.item_id in saved_ids:
                score += self.SAVE_BOOST
            score += topic_weights.get(item.theme_label.lower(), 0.0)
            for profile_name in item.profile_names:
                score += profile_weights.get(profile_name, 0.0) * self.PROFILE_BOOST
            item.importance_score = min(0.99, round(score, 3))
            ranked.append(item)

        ranked.sort(key=lambda row: (row.importance_score, row.corroboration_count, row.star_rating), reverse=True)
        return ranked

    def learn_from_feedback(self, items: Sequence[IntelligenceItem]) -> Dict[str, float]:
        """Update topic/profile weights from feedback history."""
        prefs = self.store.load_preferences()
        topic_weights: Dict[str, float] = dict(prefs.get("topic_weights", {}))
        profile_weights: Dict[str, float] = dict(prefs.get("profile_weights", {}))
        item_index = {item.item_id: item for item in items}

        for event in self.store.load_feedback():
            item = item_index.get(event.get("intelligence_item_id", ""))
            if item is None:
                continue
            label = item.theme_label.lower()
            if event.get("event_type") in {"tell_me_more", "save"}:
                topic_weights[label] = min(0.35, topic_weights.get(label, 0.0) + 0.05)
                for profile in item.profile_names:
                    profile_weights[profile] = min(0.5, profile_weights.get(profile, 0.0) + 0.04)
            elif event.get("event_type") in {"dismiss", "ignore"}:
                topic_weights[label] = max(-0.35, topic_weights.get(label, 0.0) - 0.06)

        prefs["topic_weights"] = topic_weights
        prefs["profile_weights"] = profile_weights
        self.store.save_preferences(prefs)
        return topic_weights

    def _topic_weights(self, prefs: Dict, feedback: List[Dict]) -> Dict[str, float]:
        return {key.lower(): value for key, value in prefs.get("topic_weights", {}).items()}