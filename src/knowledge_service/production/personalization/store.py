"""User behavior and preference persistence."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...intelligence.state import FileStateStore


class PersonalizationStore:
    FEEDBACK_FILE = "production/feedback.jsonl"
    PREFERENCES_FILE = "production/preferences.json"
    SESSIONS_FILE = "production/conversation_sessions.json"

    def __init__(self, state: FileStateStore):
        self.state = state
        (self.state.root / "production").mkdir(parents=True, exist_ok=True)

    def record_feedback(self, event: Dict[str, Any]) -> None:
        rows = self.state.read_jsonl(self.FEEDBACK_FILE)
        rows.append(event)
        self.state.write_jsonl(self.FEEDBACK_FILE, rows)

    def load_feedback(self) -> List[Dict[str, Any]]:
        return self.state.read_jsonl(self.FEEDBACK_FILE)

    def load_preferences(self) -> Dict[str, Any]:
        return self.state.read_json(self.PREFERENCES_FILE, {
            "topic_weights": {},
            "profile_weights": {},
            "dismissed_items": [],
            "saved_items": [],
            "tell_me_more_items": [],
            "deep_dive_seconds": {},
        })

    def save_preferences(self, preferences: Dict[str, Any]) -> None:
        self.state.write_json(self.PREFERENCES_FILE, preferences)

    def save_sessions(self, sessions: Dict[str, Any]) -> None:
        self.state.write_json(self.SESSIONS_FILE, sessions)

    def load_sessions(self) -> Dict[str, Any]:
        return self.state.read_json(self.SESSIONS_FILE, {"sessions": {}})