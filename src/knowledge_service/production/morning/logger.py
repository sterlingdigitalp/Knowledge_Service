"""Structured runtime logging for morning intelligence runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ...intelligence.models import now_iso
from ..llm.config import redact_secrets


DEFAULT_LOG_PATH = Path.home() / "Library/Logs/pcc/morning-intelligence.log"


@dataclass
class MorningIntelligenceLogger:
    log_path: Path = field(default_factory=lambda: DEFAULT_LOG_PATH)
    preflight_log_path: Path = field(
        default_factory=lambda: Path.home() / "Library/Logs/pcc/morning-preflight.log"
    )
    _lines: list[str] = field(default_factory=list, init=False)

    def start(self, *, mode: str) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lines = [f"==== {now_iso()} morning-intelligence ({mode}) ===="]

    def info(self, message: str) -> None:
        self._lines.append(message)

    def section(self, title: str, payload: Dict[str, Any]) -> None:
        self._lines.append(f"[{title}]")
        self._lines.append(json.dumps(redact_secrets(payload), indent=2, sort_keys=True))

    def finalize(self, summary: Dict[str, Any], *, append_preflight: bool = True) -> None:
        summary = redact_secrets(summary)
        self._lines.append("[summary]")
        self._lines.append(json.dumps(summary, indent=2, sort_keys=True))
        self._lines.append(f"==== end {summary.get('status', 'unknown')} ====")
        text = "\n".join(self._lines) + "\n"
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(text)
        if append_preflight:
            concise = _concise_preflight_line(summary)
            with self.preflight_log_path.open("a", encoding="utf-8") as handle:
                handle.write(concise + "\n")

    def read_last_summary(self) -> Optional[Dict[str, Any]]:
        if not self.log_path.exists():
            return None
        text = self.log_path.read_text(encoding="utf-8")
        marker = "[summary]"
        if marker not in text:
            return None
        payload = text.rsplit(marker, 1)[1].strip()
        if "==== end" in payload:
            payload = payload.split("==== end", 1)[0].strip()
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None


def _concise_preflight_line(summary: Dict[str, Any]) -> str:
    started = summary.get("started_at", "")
    status = summary.get("status", "unknown")
    brief_items = summary.get("morning_brief_item_count", 0)
    fresh = summary.get("freshness_gate", {}).get("items_eligible", 0)
    return (
        f"{started} knowledge_service morning-intelligence: status={status} "
        f"brief_items={brief_items} fresh_items={fresh}"
    )