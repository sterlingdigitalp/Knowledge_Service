"""Integration tests for Runtime 3 pipeline."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from knowledge_service.runtime3.config import is_runtime3_enabled
from knowledge_service.runtime3.integration import apply_runtime3_layer
from knowledge_service.runtime3.pipeline import Runtime3Pipeline

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "state"
ARCHIVE = ROOT / "frontend" / "archive"


@pytest.mark.skipif(not STATE_DIR.exists(), reason="production state directory not available")
def test_pipeline_runs_on_state():
    """Use archive-scoped episodes to avoid loading the full 700MB+ corpus."""
    import json

    episode_ids: list[str] = []
    archive_path = ARCHIVE / "2026-07-02" / "morning.json"
    if archive_path.exists():
        payload = json.loads(archive_path.read_text(encoding="utf-8"))
        podcast_names = set()
        for item in payload.get("items", []):
            podcast_names.update(item.get("sources") or [])
        episodes = json.loads((STATE_DIR / "episodes.json").read_text(encoding="utf-8"))
        episode_ids = [
            episode.get("episode_id")
            for episode in episodes
            if episode.get("podcast_name") in podcast_names
        ]

    pipeline = Runtime3Pipeline(state_dir=str(STATE_DIR))
    result = pipeline.run(state_dir=str(STATE_DIR), episode_ids=episode_ids or None)
    assert result.episodes_processed > 0
    assert result.segments
    assert result.claims


@pytest.mark.skipif(not (ARCHIVE / "2026-07-02" / "morning.json").exists(), reason="archive missing")
def test_pipeline_runs_for_archive_date():
    os.environ["KNOWLEDGE_RUNTIME3_ENABLED"] = "1"
    try:
        result, brief, items = apply_runtime3_layer(state_dir=str(STATE_DIR), date="2026-07-02")
        assert is_runtime3_enabled()
        assert result.enabled
        assert brief is not None
        assert brief.total_stories >= 0
        assert result.segments
    finally:
        os.environ.pop("KNOWLEDGE_RUNTIME3_ENABLED", None)


@pytest.mark.skipif(not (ARCHIVE / "2026-07-02" / "morning.json").exists(), reason="archive missing")
def test_runtime3_filters_sponsor_segments():
    os.environ["KNOWLEDGE_RUNTIME3_ENABLED"] = "1"
    try:
        result, _, _ = apply_runtime3_layer(state_dir=str(STATE_DIR), date="2026-07-02")
        sponsor_segments = [
            segment for segment in result.segments
            if segment.segment_type.value in {"sponsor", "advertisement"}
        ]
        assert sponsor_segments
        sponsor_claims = [
            claim for claim in result.claims
            if "mercury.com" in claim.claim_text.lower()
        ]
        assert sponsor_claims == []
    finally:
        os.environ.pop("KNOWLEDGE_RUNTIME3_ENABLED", None)