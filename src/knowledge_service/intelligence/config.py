"""Import and export Intelligence Profile configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .models import IntelligenceProfile, profile_collection_to_dict


def load_profiles(path: str | Path) -> List[IntelligenceProfile]:
    file_path = Path(path)
    data = _load_config_data(file_path)
    raw_profiles = data.get("profiles") if isinstance(data, dict) else data
    if not isinstance(raw_profiles, list):
        raise ValueError("Profile configuration must contain a profiles list")
    return [IntelligenceProfile.from_dict(item) for item in raw_profiles]


def save_profiles(path: str | Path, profiles: Iterable[IntelligenceProfile]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    data = profile_collection_to_dict(profiles)
    if file_path.suffix.lower() in {".yaml", ".yml"}:
        _write_yaml_compatible(file_path, data)
    else:
        file_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _load_config_data(file_path: Path) -> Dict[str, Any] | List[Any]:
    text = file_path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        if file_path.suffix.lower() not in {".yaml", ".yml"}:
            raise ValueError(f"Invalid JSON in profile configuration: {file_path}") from exc
    if file_path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except Exception as exc:
            raise ValueError("YAML profile import requires PyYAML unless the YAML file is JSON-compatible") from exc
        data = yaml.safe_load(text)
        if data is None:
            return {"profiles": []}
        return data
    raise ValueError(f"Unable to parse profile configuration: {file_path}")


def _write_yaml_compatible(file_path: Path, data: Dict[str, Any]) -> None:
    try:
        import yaml  # type: ignore
    except Exception:
        # JSON is valid YAML 1.2, so this still provides YAML-compatible export.
        file_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return
    file_path.write_text(yaml.safe_dump(data, sort_keys=True), encoding="utf-8")
