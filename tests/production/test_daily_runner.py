import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from knowledge_service.production.morning.daily_runner import MorningIntelligenceRunner
from knowledge_service.production.morning.freshness_gate import FreshnessReport


PHASE512_STATE = (
    Path(__file__).resolve().parents[2]
    / "runtime_evidence"
    / "phase512_optimization_20260701T074324Z"
    / "state"
)


@pytest.fixture
def morning_env(tmp_path: Path):
    service_root = tmp_path / "service"
    state_dir = tmp_path / "state"
    frontend = service_root / "frontend"
    config = service_root / "config"
    data = service_root / "data"
    for directory in [frontend, config, data]:
        directory.mkdir(parents=True)
    shutil.copytree(PHASE512_STATE, state_dir, dirs_exist_ok=True)

    for name in ["index.html", "styles.css", "app.js"]:
        src = Path(__file__).resolve().parents[2] / "frontend" / name
        (frontend / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    profiles_src = Path(__file__).resolve().parents[2] / "config" / "profiles.json"
    if profiles_src.exists():
        (config / "profiles.json").write_text(profiles_src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        shutil.copy2(state_dir / "profiles.json", config / "profiles.json")
    routes_src = Path(__file__).resolve().parents[2] / "data" / "source_routes.json"
    (data / "source_routes.json").write_text(routes_src.read_text(encoding="utf-8"), encoding="utf-8")

    log_path = tmp_path / "morning-intelligence.log"
    preflight_log = tmp_path / "morning-preflight.log"
    from knowledge_service.production.morning.logger import MorningIntelligenceLogger

    logger = MorningIntelligenceLogger(log_path=log_path, preflight_log_path=preflight_log)
    runner = MorningIntelligenceRunner(
        service_root=service_root,
        state_dir=state_dir,
        profiles_path=config / "profiles.json",
        routes_path=data / "source_routes.json",
        frontend_dir=frontend,
        logger=logger,
    )
    return {
        "runner": runner,
        "service_root": service_root,
        "frontend": frontend,
        "log_path": log_path,
        "preflight_log": preflight_log,
    }


def test_daily_runner_publishes_artifacts(morning_env):
    runner = morning_env["runner"]
    with patch.object(runner, "_check_network", return_value=False), patch.object(
        runner,
        "_run_acquisition",
        return_value=({"status": "skipped", "queued_count": 0, "processed_count": 0, "duplicate_count": 0, "profiles_checked": 4}, []),
    ):
        result = runner.run(mode="manual")

    frontend = morning_env["frontend"]
    assert result.status in {"success", "degraded"}
    assert (frontend / "latest.html").exists()
    assert (frontend / "latest.md").exists()
    assert (frontend / "data" / "latest.json").exists()
    payload = json.loads((frontend / "data" / "latest.json").read_text(encoding="utf-8"))
    assert "brief" in payload
    assert morning_env["log_path"].exists()


def test_daily_runner_empty_signal_brief(morning_env):
    runner = morning_env["runner"]
    with patch.object(runner, "_check_network", return_value=False), patch.object(
        runner,
        "_run_acquisition",
        return_value=({"status": "skipped", "queued_count": 0, "processed_count": 0, "duplicate_count": 0, "profiles_checked": 4}, []),
    ), patch.object(
        runner.freshness_gate,
        "filter_items",
        return_value=(
            [],
            FreshnessReport(
                evaluated_at="2026-07-01T06:30:00Z",
                new_episode_ids=[],
                new_claim_ids=[],
                no_fresh_signal=True,
            ),
        ),
    ):
        result = runner.run(mode="manual")
    assert result.empty_signal is True
    payload = json.loads((morning_env["frontend"] / "data" / "latest.json").read_text(encoding="utf-8"))
    assert payload.get("empty_signal") is True


def test_daily_runner_status_command(morning_env):
    runner = morning_env["runner"]
    with patch.object(runner, "_check_network", return_value=False), patch.object(
        runner,
        "_run_acquisition",
        return_value=({"status": "skipped", "queued_count": 0, "processed_count": 0, "duplicate_count": 0, "profiles_checked": 4}, []),
    ):
        runner.run(mode="manual")
    status = runner.status()
    assert status["artifacts"]["latest.html"] is True
    assert status["artifacts"]["latest.json"] is True