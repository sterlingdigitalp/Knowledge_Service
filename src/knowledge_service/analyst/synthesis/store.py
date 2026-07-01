"""Persistent store for synthesis artifacts."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...intelligence.state import FileStateStore
from .models import IntelligenceBrief, IntelligenceItem, Theme, ThemeEvolution


class SynthesisStore:
    THEMES_FILE = "analyst/synthesis/themes.json"
    THEME_HISTORY_FILE = "analyst/synthesis/theme_history.jsonl"
    ITEMS_FILE = "analyst/synthesis/intelligence_items.json"
    BRIEFS_FILE = "analyst/synthesis/intelligence_briefs.json"
    RUNS_FILE = "analyst/synthesis/pipeline_runs.json"

    def __init__(self, state: FileStateStore):
        self.state = state
        (self.state.root / "analyst" / "synthesis").mkdir(parents=True, exist_ok=True)

    def save_themes(self, themes: List[Theme]) -> None:
        self.state.write_json(self.THEMES_FILE, {"themes": [theme.to_dict() for theme in themes]})

    def load_themes(self) -> List[Theme]:
        data = self.state.read_json(self.THEMES_FILE, {"themes": []})
        return [Theme.from_dict(item) for item in data.get("themes", [])]

    def append_theme_history(self, evolutions: List[ThemeEvolution]) -> None:
        rows = self.state.read_jsonl(self.THEME_HISTORY_FILE)
        rows.extend([record.to_dict() for record in evolutions])
        self.state.write_jsonl(self.THEME_HISTORY_FILE, rows)

    def load_theme_history(self) -> List[ThemeEvolution]:
        return [ThemeEvolution.from_dict(row) for row in self.state.read_jsonl(self.THEME_HISTORY_FILE)]

    def save_items(self, items: List[IntelligenceItem]) -> None:
        self.state.write_json(self.ITEMS_FILE, {"items": [item.to_dict() for item in items]})

    def load_items(self) -> List[IntelligenceItem]:
        data = self.state.read_json(self.ITEMS_FILE, {"items": []})
        return [IntelligenceItem.from_dict(item) for item in data.get("items", [])]

    def save_brief(self, brief: IntelligenceBrief) -> None:
        briefs = self.load_briefs()
        briefs.append(brief)
        self.state.write_json(self.BRIEFS_FILE, {"briefs": [item.to_dict() for item in briefs]})

    def load_briefs(self) -> List[IntelligenceBrief]:
        data = self.state.read_json(self.BRIEFS_FILE, {"briefs": []})
        return [IntelligenceBrief.from_dict(item) for item in data.get("briefs", [])]

    def latest_brief(self) -> Optional[IntelligenceBrief]:
        briefs = self.load_briefs()
        return briefs[-1] if briefs else None

    def record_run(self, run: Dict[str, Any]) -> None:
        data = self.state.read_json(self.RUNS_FILE, {"runs": []})
        data["runs"].append(run)
        self.state.write_json(self.RUNS_FILE, data)

    def load_runs(self) -> List[Dict[str, Any]]:
        return self.state.read_json(self.RUNS_FILE, {"runs": []}).get("runs", [])

    def summary(self, claims_count: int = 0) -> Dict[str, Any]:
        themes = self.load_themes()
        items = self.load_items()
        briefs = self.load_briefs()
        latest = briefs[-1] if briefs else None
        item_claims = sum(item.claim_count for item in items)
        compression = round(claims_count / max(len(items), 1), 1) if claims_count else 0.0
        return {
            "themes": len(themes),
            "intelligence_items": len(items),
            "briefs": len(briefs),
            "latest_brief_id": latest.brief_id if latest else None,
            "latest_brief_items": latest.total_items if latest else 0,
            "reading_time_seconds": latest.reading_time_seconds if latest else 0,
            "compression_ratio": latest.compression_ratio if latest else compression,
            "claims_per_item": round(item_claims / max(len(items), 1), 1) if items else 0.0,
            "runs": len(self.load_runs()),
        }