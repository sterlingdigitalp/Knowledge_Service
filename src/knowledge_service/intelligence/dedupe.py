"""Persistent deduplication for discovered episodes and transcripts."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .models import DiscoveredEpisode, content_hash, now_iso
from .state import FileStateStore


class DeduplicationStore:
    def __init__(self, state: FileStateStore):
        self.state = state
        self.data: Dict[str, Dict[str, Any]] = self.state.read_json("dedupe.json", {
            "acquisition_hashes": {},
            "transcript_hashes": {},
            "source_hashes": {},
            "events": [],
        })

    def save(self) -> None:
        self.state.write_json("dedupe.json", self.data)

    def source_seen(self, source_hash: str) -> Optional[str]:
        entry = self.data["source_hashes"].get(source_hash)
        return entry.get("episode_id") if entry else None

    def acquisition_seen(self, acquisition_hash: str) -> Optional[str]:
        entry = self.data["acquisition_hashes"].get(acquisition_hash)
        return entry.get("episode_id") if entry else None

    def transcript_seen(self, transcript_hash: str) -> Optional[str]:
        entry = self.data["transcript_hashes"].get(transcript_hash)
        return entry.get("episode_id") if entry else None

    def should_queue(self, episode: DiscoveredEpisode) -> tuple[bool, Optional[str], Optional[str]]:
        for key, checker in [
            ("source_hash", self.source_seen),
            ("acquisition_hash", self.acquisition_seen),
        ]:
            duplicate = checker(getattr(episode, key))
            if duplicate:
                return False, key, duplicate
        return True, None, None

    def register_discovery(self, episode: DiscoveredEpisode) -> None:
        self.data["source_hashes"].setdefault(episode.source_hash, {
            "episode_id": episode.episode_id,
            "profile_id": episode.profile_id,
            "url": episode.url,
            "first_seen_at": now_iso(),
        })

    def register_acquisition(self, episode: DiscoveredEpisode, transcript: str) -> tuple[str, Optional[str]]:
        transcript_hash = content_hash(transcript)
        duplicate = self.transcript_seen(transcript_hash)
        now = now_iso()
        self.data["source_hashes"][episode.source_hash] = {
            "episode_id": episode.episode_id,
            "profile_id": episode.profile_id,
            "url": episode.url,
            "first_seen_at": self.data["source_hashes"].get(episode.source_hash, {}).get("first_seen_at", now),
            "last_seen_at": now,
        }
        self.data["acquisition_hashes"][episode.acquisition_hash] = {
            "episode_id": episode.episode_id,
            "profile_id": episode.profile_id,
            "url": episode.url,
            "created_at": now,
        }
        if not duplicate:
            self.data["transcript_hashes"][transcript_hash] = {
                "episode_id": episode.episode_id,
                "profile_id": episode.profile_id,
                "url": episode.url,
                "created_at": now,
            }
        self.data["events"].append({
            "type": "acquisition_registered",
            "episode_id": episode.episode_id,
            "profile_id": episode.profile_id,
            "transcript_hash": transcript_hash,
            "duplicate_of": duplicate,
            "created_at": now,
        })
        self.save()
        return transcript_hash, duplicate

    def summary(self) -> Dict[str, Any]:
        return {
            "acquisition_hash_count": len(self.data.get("acquisition_hashes", {})),
            "transcript_hash_count": len(self.data.get("transcript_hashes", {})),
            "source_hash_count": len(self.data.get("source_hashes", {})),
            "event_count": len(self.data.get("events", [])),
        }
