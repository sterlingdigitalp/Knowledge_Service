"""Migrate legacy Phase 3 corpus records to Phase 3.1 information-event schema."""

from __future__ import annotations

from typing import Any, Dict, List

from .models import DiscoveredEpisode, InformationEventType
from .route_registry import AcquisitionRouteRegistry
from .state import FileStateStore


def migrate_corpus_state(state: FileStateStore, registry: AcquisitionRouteRegistry) -> Dict[str, Any]:
    """Backfill information-event and route fields without losing KnowledgeObjects."""
    episodes_raw = state.read_json("episodes.json", [])
    migrated_episodes: List[Dict[str, Any]] = []
    changed = 0

    for item in episodes_raw:
        episode = DiscoveredEpisode.from_dict(item)
        before = episode.to_dict()
        if not episode.event_type:
            episode.event_type = InformationEventType.PODCAST_EPISODE
        if not episode.source_id:
            episode.source_id = registry.resolve_source_id(podcast_name=episode.podcast_name, url=episode.url)
        if not episode.route_selection_reason:
            entry = registry.get(episode.source_id)
            if entry:
                episode.route_selection_reason = list(entry.reason)
                episode.route_confidence = entry.transcript_confidence
        after = episode.to_dict()
        if after != before:
            changed += 1
        migrated_episodes.append(after)

    state.write_json("episodes.json", migrated_episodes)
    information_events = [DiscoveredEpisode.from_dict(item).as_information_event().to_dict() for item in migrated_episodes]
    state.write_json("information_events.json", information_events)

    knowledge_rows = state.read_jsonl("knowledge_objects.jsonl")
    ko_changed = 0
    for row in knowledge_rows:
        metadata = (row.get("structured_data") or {}).setdefault("metadata", {})
        episode_id = metadata.get("episode_id")
        if not episode_id:
            continue
        episode_lookup = {item.get("episode_id") or item.get("event_id"): item for item in migrated_episodes}
        episode_data = episode_lookup.get(episode_id)
        if not episode_data:
            continue
        provenance = {
            "information_event_id": episode_data.get("event_id") or episode_data.get("episode_id"),
            "event_type": episode_data.get("event_type"),
            "source_id": episode_data.get("source_id"),
            "acquisition_route": episode_data.get("acquisition_route"),
            "route_confidence": episode_data.get("route_confidence"),
            "transcript_provenance": episode_data.get("transcript_provenance"),
        }
        if metadata.get("transcript_provenance") != provenance:
            metadata.update(provenance)
            ko_changed += 1
    if ko_changed:
        state.write_jsonl("knowledge_objects.jsonl", knowledge_rows)

    return {
        "episodes_migrated": changed,
        "information_events_written": len(information_events),
        "knowledge_objects_updated": ko_changed,
    }