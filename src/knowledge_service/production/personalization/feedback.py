"""User Feedback Engine — capture behavior signals."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...intelligence.models import now_iso
from .store import PersonalizationStore


class UserFeedbackEngine:
    """Record user interactions that drive future ranking."""

    def __init__(self, store: PersonalizationStore):
        self.store = store

    def tell_me_more(self, intelligence_item_id: str, *, duration_seconds: float = 0.0, profile_id: str = "") -> Dict[str, Any]:
        return self._record("tell_me_more", intelligence_item_id, duration_seconds=duration_seconds, profile_id=profile_id)

    def dismiss(self, intelligence_item_id: str, *, profile_id: str = "") -> Dict[str, Any]:
        return self._record("dismiss", intelligence_item_id, profile_id=profile_id)

    def save(self, intelligence_item_id: str, *, profile_id: str = "") -> Dict[str, Any]:
        return self._record("save", intelligence_item_id, profile_id=profile_id)

    def ignore(self, intelligence_item_id: str, *, profile_id: str = "") -> Dict[str, Any]:
        return self._record("ignore", intelligence_item_id, profile_id=profile_id)

    def brief_view(self, *, seconds: float, items_viewed: int) -> Dict[str, Any]:
        event = {
            "event_type": "brief_view",
            "seconds": seconds,
            "items_viewed": items_viewed,
            "recorded_at": now_iso(),
        }
        self.store.record_feedback(event)
        return event

    def _record(self, event_type: str, intelligence_item_id: str, **extra: Any) -> Dict[str, Any]:
        event = {
            "event_type": event_type,
            "intelligence_item_id": intelligence_item_id,
            "recorded_at": now_iso(),
            **extra,
        }
        self.store.record_feedback(event)
        prefs = self.store.load_preferences()
        if event_type == "tell_me_more":
            items = prefs.setdefault("tell_me_more_items", [])
            if intelligence_item_id not in items:
                items.append(intelligence_item_id)
            if extra.get("duration_seconds"):
                prefs.setdefault("deep_dive_seconds", {})[intelligence_item_id] = prefs["deep_dive_seconds"].get(intelligence_item_id, 0) + extra["duration_seconds"]
        elif event_type == "dismiss":
            dismissed = prefs.setdefault("dismissed_items", [])
            if intelligence_item_id not in dismissed:
                dismissed.append(intelligence_item_id)
        elif event_type == "save":
            saved = prefs.setdefault("saved_items", [])
            if intelligence_item_id not in saved:
                saved.append(intelligence_item_id)
        elif event_type == "ignore":
            dismissed = prefs.setdefault("dismissed_items", [])
            if intelligence_item_id not in dismissed:
                dismissed.append(intelligence_item_id)
        self.store.save_preferences(prefs)
        return event

    def summary(self) -> Dict[str, Any]:
        events = self.store.load_feedback()
        prefs = self.store.load_preferences()
        counts: Dict[str, int] = {}
        for event in events:
            event_type = event.get("event_type", "unknown")
            counts[event_type] = counts.get(event_type, 0) + 1
        return {
            "event_count": len(events),
            "event_types": counts,
            "tell_me_more_items": len(prefs.get("tell_me_more_items", [])),
            "dismissed_items": len(prefs.get("dismissed_items", [])),
            "saved_items": len(prefs.get("saved_items", [])),
            "topic_weights": prefs.get("topic_weights", {}),
            "profile_weights": prefs.get("profile_weights", {}),
        }