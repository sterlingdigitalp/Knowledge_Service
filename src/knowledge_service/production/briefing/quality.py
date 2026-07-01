"""Brief quality self-evaluation."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from ..personalization.store import PersonalizationStore
from .morning_brief_v3 import IntelligenceBriefV3


class BriefQualityEvaluator:
    """Score every brief on signal quality dimensions."""

    def evaluate(
        self,
        brief: IntelligenceBriefV3,
        items: Sequence,
        claims_synthesized: int,
        personalization_store: PersonalizationStore | None = None,
    ) -> Dict[str, Any]:
        prefs = personalization_store.load_preferences() if personalization_store else {}
        topic_weights = prefs.get("topic_weights", {})

        novelty_scores = [entry.explainability.get("novelty_score", 0.0) for entry in brief.items]
        importance_scores = [entry.explainability.get("importance_score", 0.0) for entry in brief.items]
        corroboration = [entry.corroborated_by for entry in brief.items]
        personal_hits = sum(
            1 for entry in brief.items
            if topic_weights.get(entry.title.lower(), 0) > 0 or entry.intelligence_item_id in prefs.get("tell_me_more_items", [])
        )

        duplicate_titles = len(brief.items) - len({entry.title.lower() for entry in brief.items})
        avg_importance = sum(importance_scores) / len(importance_scores) if importance_scores else 0.0
        avg_novelty = sum(novelty_scores) / len(novelty_scores) if novelty_scores else 0.0
        avg_corroboration = sum(corroboration) / len(corroboration) if corroboration else 0.0
        compression = brief.compression_ratio
        reading_ok = 45 <= brief.reading_time_seconds <= 60
        item_ok = 5 <= brief.total_items <= 10

        signal_noise = min(1.0, (avg_importance * 0.4 + avg_novelty * 0.35 + avg_corroboration * 0.15 + (0.1 if duplicate_titles == 0 else 0.0)))

        return {
            "compression": compression,
            "novelty": round(avg_novelty, 3),
            "importance": round(avg_importance, 3),
            "corroboration": round(avg_corroboration, 3),
            "reading_time_seconds": brief.reading_time_seconds,
            "reading_time_ok": reading_ok,
            "item_count_ok": item_ok,
            "duplicate_titles": duplicate_titles,
            "personal_relevance_hits": personal_hits,
            "signal_to_noise": round(signal_noise, 3),
            "evidence_quality": round(min(1.0, avg_corroboration / 3.0 + 0.4), 3),
            "overall_score": round(signal_noise * 0.7 + (0.15 if reading_ok else 0.0) + (0.15 if item_ok else 0.0), 3),
            "claims_synthesized": claims_synthesized,
            "items_selected": brief.total_items,
        }