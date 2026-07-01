"""Morning Brief Scheduler — daily intelligence delivery."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ...intelligence.models import now_iso
from ...intelligence.state import FileStateStore


SCHEDULE_DAILY = "daily"
SCHEDULE_WEEKDAYS = "weekdays"
SCHEDULE_MANUAL = "manual"


class MorningBriefScheduler:
    """Schedule automatic brief generation."""

    CONFIG_FILE = "production/brief_scheduler.json"
    HISTORY_FILE = "production/brief_schedule_history.jsonl"

    def __init__(self, state: FileStateStore):
        self.state = state
        (self.state.root / "production").mkdir(parents=True, exist_ok=True)

    def configure(self, schedule: str = SCHEDULE_DAILY, hour_utc: int = 12, enabled: bool = True) -> Dict[str, Any]:
        config = {
            "schedule": schedule,
            "hour_utc": hour_utc,
            "enabled": enabled,
            "updated_at": now_iso(),
        }
        self.state.write_json(self.CONFIG_FILE, config)
        return config

    def load_config(self) -> Dict[str, Any]:
        return self.state.read_json(self.CONFIG_FILE, {
            "schedule": SCHEDULE_DAILY,
            "hour_utc": 12,
            "enabled": True,
            "updated_at": now_iso(),
        })

    def should_run(self, now: Optional[datetime] = None) -> bool:
        config = self.load_config()
        if not config.get("enabled", True):
            return False
        current = now or datetime.now(timezone.utc)
        schedule = config.get("schedule", SCHEDULE_DAILY)
        if schedule == SCHEDULE_MANUAL:
            return False
        if schedule == SCHEDULE_WEEKDAYS and current.weekday() >= 5:
            return False
        if current.hour < int(config.get("hour_utc", 12)):
            return False
        last = self._last_run_date()
        return last != current.strftime("%Y-%m-%d")

    def record_run(self, run_id: str, *, manual: bool = False) -> Dict[str, Any]:
        entry = {
            "run_id": run_id,
            "recorded_at": now_iso(),
            "manual": manual,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        rows = self.state.read_jsonl(self.HISTORY_FILE)
        rows.append(entry)
        self.state.write_jsonl(self.HISTORY_FILE, rows)
        return entry

    def _last_run_date(self) -> str | None:
        rows = self.state.read_jsonl(self.HISTORY_FILE)
        if not rows:
            return None
        return rows[-1].get("date")

    def inspect(self) -> Dict[str, Any]:
        config = self.load_config()
        history = self.state.read_jsonl(self.HISTORY_FILE)
        return {
            "config": config,
            "history_count": len(history),
            "last_run": history[-1] if history else None,
            "should_run_now": self.should_run(),
        }