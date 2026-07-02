import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _preflight_script() -> Path | None:
    candidates: list[Path] = []
    if override := os.environ.get("KNOWLEDGE_SERVICE_PCC_PREFLIGHT"):
        candidates.append(Path(override))
    candidates.extend(
        [
            Path.home() / "bin" / "pcc-morning-preflight.sh",
            Path("/Users/sterlingdigital/bin/pcc-morning-preflight.sh"),
        ]
    )
    return next((path for path in candidates if path.exists()), None)


def test_pcc_preflight_invokes_morning_intelligence():
    preflight = _preflight_script()
    script = PROJECT_ROOT / "bin" / "morning-intelligence.sh"
    if preflight is None:
        pytest.skip(
            "PCC preflight script not found; set KNOWLEDGE_SERVICE_PCC_PREFLIGHT to override"
        )
    assert script.exists()
    text = preflight.read_text(encoding="utf-8")
    assert "morning-intelligence" in text
    assert "Knowledge_Service" in text
    assert "scheduled" in text


def test_morning_intelligence_shell_uses_module_runner():
    script = PROJECT_ROOT / "bin" / "morning-intelligence.sh"
    text = script.read_text(encoding="utf-8")
    assert "knowledge_service.production.morning" in text
    assert "PYTHONPATH" in text