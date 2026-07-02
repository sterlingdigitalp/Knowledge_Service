import json
from pathlib import Path
from unittest.mock import patch

import pytest

from knowledge_service.intelligence.config import _load_config_data
from knowledge_service.intelligence.state import FileStateStore
from knowledge_service.production.morning.daily_runner import MorningIntelligenceRunner
from knowledge_service.production.morning.logger import MorningIntelligenceLogger
from knowledge_service.production.morning.publisher import FrontendPublisher


def test_invalid_profile_json_raises_clear_error(tmp_path: Path):
    bad = tmp_path / "profiles.json"
    bad.write_text("{not-json", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON in profile configuration"):
        _load_config_data(bad)


def test_status_survives_corrupt_latest_json(tmp_path: Path):
    frontend = tmp_path / "frontend"
    data_dir = frontend / "data"
    data_dir.mkdir(parents=True)
    (frontend / "latest.json").write_text("not-json", encoding="utf-8")
    (data_dir / "latest.json").write_text("{broken", encoding="utf-8")

    runner = MorningIntelligenceRunner(
        service_root=tmp_path,
        state_dir=tmp_path / "state",
        frontend_dir=frontend,
    )
    status = runner.status()

    assert status["artifacts"]["latest.json"] is True
    assert status["brief_meta_error"]
    assert "not valid JSON" in status["brief_meta_error"]


def test_publisher_load_prior_documents_ignores_corrupt_json(tmp_path: Path):
    frontend = tmp_path / "frontend"
    data_dir = frontend / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "latest.json").write_text("{broken", encoding="utf-8")

    publisher = FrontendPublisher(frontend_dir=frontend)
    assert publisher.load_prior_documents() == []


def test_publisher_missing_template_reports_clear_error(tmp_path: Path):
    frontend = tmp_path / "frontend"
    frontend.mkdir(parents=True)
    publisher = FrontendPublisher(frontend_dir=frontend)

    with pytest.raises(FileNotFoundError, match="index.html"):
        publisher._render_latest_html({"brief": {}, "items": [], "documents": []})


def test_state_store_invalid_json_includes_path(tmp_path: Path):
    store = FileStateStore(tmp_path)
    store.path("broken.json").write_text("{bad", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON in state file"):
        store.read_json("broken.json", {})


def test_logger_finalize_survives_unwritable_log_path(tmp_path: Path, capsys):
    log_path = tmp_path / "morning-intelligence.log"
    log_path.write_text("", encoding="utf-8")
    log_path.chmod(0o000)
    logger = MorningIntelligenceLogger(log_path=log_path, preflight_log_path=tmp_path / "preflight.log")
    logger.start(mode="manual")

    try:
        logger.finalize({"status": "success", "started_at": "2026-07-01T06:30:00Z"})
    finally:
        log_path.chmod(0o644)

    captured = capsys.readouterr()
    assert "failed to write log" in captured.err