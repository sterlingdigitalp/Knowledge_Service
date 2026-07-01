import json
from pathlib import Path

from knowledge_service.production.morning.logger import MorningIntelligenceLogger


def test_logger_writes_structured_summary(tmp_path: Path):
    log_path = tmp_path / "morning-intelligence.log"
    preflight_log = tmp_path / "morning-preflight.log"
    logger = MorningIntelligenceLogger(log_path=log_path, preflight_log_path=preflight_log)
    logger.start(mode="manual")
    logger.info("test line")
    summary = {
        "status": "success",
        "started_at": "2026-07-01T06:30:00Z",
        "morning_brief_item_count": 3,
        "freshness_gate": {"items_eligible": 2},
    }
    logger.finalize(summary, append_preflight=True)

    text = log_path.read_text(encoding="utf-8")
    assert "morning-intelligence" in text
    assert "test line" in text
    assert '"status": "success"' in text
    assert "XAI_API_KEY" not in text

    last = logger.read_last_summary()
    assert last is not None
    assert last["status"] == "success"
    assert preflight_log.read_text(encoding="utf-8").strip().endswith("fresh_items=2")