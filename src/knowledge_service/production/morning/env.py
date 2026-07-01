"""Load gitignored local environment for launchd runs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


def load_env_local(paths: Iterable[Path | str] | None = None) -> dict[str, str]:
    """Parse KEY=VALUE lines from .env.local without printing secrets."""
    loaded: dict[str, str] = {}
    candidates = list(paths or default_env_paths())
    for path in candidates:
        file_path = Path(path)
        if not file_path.exists():
            continue
        for line in file_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
                loaded[key] = "***" if _is_secret(key) else value
    return loaded


def default_env_paths() -> list[Path]:
    root = Path(__file__).resolve().parents[4]
    return [
        root / ".env.local",
        root / ".env",
        Path.home() / ".config" / "knowledge_service" / ".env.local",
    ]


def _is_secret(key: str) -> bool:
    lowered = key.lower()
    return "api_key" in lowered or "token" in lowered or "secret" in lowered