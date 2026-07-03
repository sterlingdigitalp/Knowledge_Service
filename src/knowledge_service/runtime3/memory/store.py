"""Persistent cross-day story memory store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from ...intelligence.models import now_iso
from ..thinking.models import PersistentStoryRecord, StoryMemory


class StoryMemoryStore:
    """File-backed persistent story memory."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> StoryMemory:
        if not self.path.exists():
            return StoryMemory()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        records = [PersistentStoryRecord.from_dict(row) for row in data.get("records", [])]
        return StoryMemory(
            version=str(data.get("version", "1.0")),
            updated_at=str(data.get("updated_at", now_iso())),
            records=records,
        )

    def save(self, memory: StoryMemory) -> None:
        memory.updated_at = now_iso()
        self.path.write_text(json.dumps(memory.to_dict(), indent=2), encoding="utf-8")

    def get_active_records(self, memory: StoryMemory) -> List[PersistentStoryRecord]:
        return [
            record for record in memory.records
            if record.evolution_state.value != "retired"
        ]