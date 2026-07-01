"""Small JSON-file state store for restart-persistent collection runtime."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List


class FileStateStore:
    """Persist runtime state as inspectable JSON/JSONL files.

    The store is intentionally simple: Phase 3 needs restart persistence and
    evidence-friendly files, not a new database dependency.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, name: str) -> Path:
        return self.root / name

    def read_json(self, name: str, default: Any) -> Any:
        path = self.path(name)
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json(self, name: str, data: Any) -> None:
        path = self.path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, path)

    def read_jsonl(self, name: str) -> List[Dict[str, Any]]:
        path = self.path(name)
        if not path.exists():
            return []
        rows: List[Dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def write_jsonl(self, name: str, rows: List[Dict[str, Any]]) -> None:
        path = self.path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + ("\n" if rows else ""), encoding="utf-8")
        os.replace(tmp, path)

    def append_jsonl(self, name: str, rows: List[Dict[str, Any]]) -> None:
        existing = self.read_jsonl(name)
        existing.extend(rows)
        self.write_jsonl(name, existing)
