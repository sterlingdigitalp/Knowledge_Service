"""Fast smoke tests for repository trustworthiness.

These tests verify critical configuration, CLI entrypoints, and runtime
inspector contracts without requiring live provider infrastructure.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from knowledge_service.intelligence.config import load_profiles
from knowledge_service.production.inspector import inspect_production_runtime
from knowledge_service.production.morning.daily_runner import main as morning_main
from knowledge_service.production.morning.env import load_env_local


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_production_config_files_parse():
    profiles_path = REPO_ROOT / "config" / "profiles.json"
    routes_path = REPO_ROOT / "data" / "source_routes.json"

    assert profiles_path.exists(), "config/profiles.json is required for production runs"
    assert routes_path.exists(), "data/source_routes.json is required for acquisition routing"

    profiles = load_profiles(profiles_path)
    routes = json.loads(routes_path.read_text(encoding="utf-8"))

    assert len(profiles) >= 1
    assert all(profile.profile_id for profile in profiles)
    route_entries = routes.get("routes", routes)
    assert isinstance(route_entries, (list, dict))
    assert len(route_entries) >= 1


def test_load_env_local_redacts_secrets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "XAI_API_KEY=super-secret\n"
        "KNOWLEDGE_LLM_PROVIDER=xai_responses\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("KNOWLEDGE_LLM_PROVIDER", raising=False)

    loaded = load_env_local([env_file])

    assert loaded["XAI_API_KEY"] == "***"
    assert loaded["KNOWLEDGE_LLM_PROVIDER"] == "xai_responses"
    assert os.environ["XAI_API_KEY"] == "super-secret"


def test_morning_cli_status_exits_zero():
    class _StubRunner:
        def status(self) -> dict:
            return {
                "artifacts": {"latest.html": True, "latest.json": True, "latest.md": True},
                "brief": {"brief_items": 0},
                "last_run": None,
                "llm": {"provider": "analyst_heuristic"},
            }

    with patch(
        "knowledge_service.production.morning.daily_runner.MorningIntelligenceRunner",
        return_value=_StubRunner(),
    ):
        exit_code = morning_main(["status"])

    assert exit_code == 0


def test_production_inspector_contract(tmp_path: Path):
    report = inspect_production_runtime(tmp_path)

    assert report["phase"] == "5.1.2"
    assert report["status"] in {"pass", "fail"}
    for key in ("analyst", "production", "llm", "personalization", "scheduler", "warnings"):
        assert key in report
    assert isinstance(report["warnings"], list)


def test_critical_packages_import():
    import knowledge_service.acquisition.acquisition_bundle  # noqa: F401
    import knowledge_service.planning.planner  # noqa: F401
    import knowledge_service.processing.pipeline  # noqa: F401
    import knowledge_service.intelligence.collector  # noqa: F401
    import knowledge_service.production.pipeline  # noqa: F401
    import knowledge_service.production.morning  # noqa: F401
    import knowledge_service.retrieval.retriever  # noqa: F401