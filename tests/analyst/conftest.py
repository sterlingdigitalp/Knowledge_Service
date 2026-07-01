"""Shared fixtures for Phase 4 analyst tests using phase32 runtime evidence."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

import pytest

from knowledge_service.analyst.claims.extractor import ClaimExtractor
from knowledge_service.analyst.models import Claim
from knowledge_service.intelligence.corpus import CorpusManager
from knowledge_service.intelligence.models import DiscoveredEpisode, EpisodeStatus, IntelligenceProfile
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


def _filter_episodes(source: Path, destination: Path, episode_ids: set[str] | None = None) -> List[Dict[str, Any]]:
    episodes = json.loads(source.read_text(encoding="utf-8"))
    if episode_ids is not None:
        episodes = [episode for episode in episodes if episode.get("episode_id") in episode_ids]
    destination.write_text(json.dumps(episodes), encoding="utf-8")
    return episodes


@pytest.fixture
def phase32_state_dir(tmp_path: Path) -> Path:
    """Copy minimal phase32 state: profiles, episodes, and document knowledge objects only."""
    shutil.copy2(PHASE32_STATE_DIR / "profiles.json", tmp_path / "profiles.json")
    _filter_episodes(PHASE32_STATE_DIR / "episodes.json", tmp_path / "episodes.json")
    _copy_document_knowledge_objects(
        PHASE32_STATE_DIR / "knowledge_objects.jsonl",
        tmp_path / "knowledge_objects.jsonl",
    )
    return tmp_path


@pytest.fixture
def phase32_single_episode_state(tmp_path: Path) -> Path:
    """Smaller phase32 copy with one processed episode for fast unit-style tests."""
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
def phase32_profiles(phase32_corpus: CorpusManager) -> List[IntelligenceProfile]:
    return phase32_corpus.load_profiles()


@pytest.fixture
def phase32_episodes(phase32_corpus: CorpusManager) -> List[Dict[str, Any]]:
    return [
        episode.to_dict()
        for episode in phase32_corpus.episodes()
        if episode.status == EpisodeStatus.PROCESSED
    ]


@pytest.fixture
def phase32_documents(phase32_corpus: CorpusManager) -> List[Dict[str, Any]]:
    return [obj for obj in phase32_corpus.knowledge_objects() if obj.get("type") == "document"]


@pytest.fixture
def extracted_claims(
    phase32_profiles: List[IntelligenceProfile],
    phase32_documents: List[Dict[str, Any]],
    phase32_episodes: List[Dict[str, Any]],
) -> List[Claim]:
    return ClaimExtractor().extract_from_corpus(phase32_documents, phase32_episodes, phase32_profiles)


@pytest.fixture
def sample_claim(extracted_claims: List[Claim]) -> Claim:
    assert extracted_claims, "phase32 single-episode fixture should yield claims"
    return extracted_claims[0]


def make_claim(
    text: str,
    *,
    episode_id: str = "episode-a",
    speaker: str = "Analyst",
    topic: str = "AI",
    podcast_name: str = "Test Podcast",
) -> Claim:
    return Claim(
        claim_text=text,
        speaker=speaker,
        timestamp_start=12.0,
        timestamp_end=24.0,
        timestamp_label="00:00:12",
        transcript_reference="https://example.com/episode#t=12",
        evidence=text,
        confidence=0.9,
        topic=topic,
        entities=["OpenAI"],
        supporting_context=f"{speaker}: {text}",
        episode_id=episode_id,
        profile_id="ai",
        source_id=f"source-{episode_id}",
        podcast_name=podcast_name,
        published_at="2026-06-30T00:00:00Z",
    )