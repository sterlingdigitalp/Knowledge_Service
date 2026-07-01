"""Shared fixtures for Phase 5 production tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from knowledge_service.intelligence.corpus import CorpusManager
from knowledge_service.intelligence.models import EpisodeStatus, IntelligenceProfile
from knowledge_service.intelligence.state import FileStateStore


PHASE32_STATE_DIR = (
    Path(__file__).resolve().parents[2]
    / "runtime_evidence"
    / "phase32_intelligence_20260701T011651Z"
    / "state"
)


def _copy_document_knowledge_objects(source: Path, destination: Path, episode_ids: set[str] | None = None) -> None:
    with source.open() as handle, destination.open("w", encoding="utf-8") as out:
        for line in handle:
            row = json.loads(line)
            if row.get("type") != "document":
                continue
            metadata = (row.get("structured_data") or {}).get("metadata") or {}
            episode_id = metadata.get("episode_id")
            if episode_ids is not None and episode_id not in episode_ids:
                continue
            out.write(json.dumps(row) + "\n")


def _filter_episodes(source: Path, destination: Path, episode_ids: set[str] | None = None) -> None:
    episodes = json.loads(source.read_text(encoding="utf-8"))
    if episode_ids is not None:
        episodes = [episode for episode in episodes if episode.get("episode_id") in episode_ids]
    destination.write_text(json.dumps(episodes), encoding="utf-8")


@pytest.fixture
def phase32_state_dir(tmp_path: Path) -> Path:
    shutil.copy2(PHASE32_STATE_DIR / "profiles.json", tmp_path / "profiles.json")
    _filter_episodes(PHASE32_STATE_DIR / "episodes.json", tmp_path / "episodes.json")
    _copy_document_knowledge_objects(
        PHASE32_STATE_DIR / "knowledge_objects.jsonl",
        tmp_path / "knowledge_objects.jsonl",
    )
    return tmp_path


@pytest.fixture
def phase32_single_episode_state(tmp_path: Path) -> Path:
    episodes = json.loads((PHASE32_STATE_DIR / "episodes.json").read_text(encoding="utf-8"))
    processed = [episode for episode in episodes if episode.get("status") == EpisodeStatus.PROCESSED.value]
    episode_id = processed[0]["episode_id"]

    shutil.copy2(PHASE32_STATE_DIR / "profiles.json", tmp_path / "profiles.json")
    _filter_episodes(PHASE32_STATE_DIR / "episodes.json", tmp_path / "episodes.json", {episode_id})
    _copy_document_knowledge_objects(
        PHASE32_STATE_DIR / "knowledge_objects.jsonl",
        tmp_path / "knowledge_objects.jsonl",
        {episode_id},
    )
    return tmp_path


@pytest.fixture
def phase32_corpus(phase32_single_episode_state: Path) -> CorpusManager:
    return CorpusManager(FileStateStore(phase32_single_episode_state))


@pytest.fixture
def phase32_profiles(phase32_corpus: CorpusManager) -> list[IntelligenceProfile]:
    return phase32_corpus.load_profiles()