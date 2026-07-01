"""Persistent intelligence corpus management."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional

from ..knowledge_object import KnowledgeObject
from .models import DiscoveredEpisode, EpisodeStatus, IntelligenceProfile, SourceGraph, now_iso
from .state import FileStateStore


class CorpusManager:
    def __init__(self, state: FileStateStore):
        self.state = state

    def save_profiles(self, profiles: Iterable[IntelligenceProfile]) -> None:
        self.state.write_json("profiles.json", {"profiles": [profile.to_dict() for profile in profiles]})
        graphs = self._load_graphs()
        for profile in profiles:
            for entry in profile.watch_list:
                graph = SourceGraph.from_watch_entry(profile.profile_id, entry)
                graphs.setdefault(graph.graph_id, graph)
        self._save_graphs(graphs)

    def load_profiles(self) -> List[IntelligenceProfile]:
        data = self.state.read_json("profiles.json", {"profiles": []})
        return [IntelligenceProfile.from_dict(item) for item in data.get("profiles", [])]

    def record_discovered_episodes(self, episodes: Iterable[DiscoveredEpisode]) -> None:
        existing = {item["episode_id"]: DiscoveredEpisode.from_dict(item) for item in self.state.read_json("episodes.json", [])}
        graphs = self._load_graphs()
        for episode in episodes:
            current = existing.get(episode.episode_id)
            if current and current.status == EpisodeStatus.PROCESSED and episode.status != EpisodeStatus.PROCESSED:
                continue
            existing[episode.episode_id] = episode
            for person in episode.matched_watch_entries:
                graph = self._graph_for_person(graphs, episode.profile_id, person)
                graph.record_appearance(episode)
        episode_rows = [episode.to_dict() for episode in existing.values()]
        self.state.write_json("episodes.json", episode_rows)
        self.state.write_json(
            "information_events.json",
            [DiscoveredEpisode.from_dict(item).as_information_event().to_dict() for item in episode_rows],
        )
        self._save_graphs(graphs)

    def record_processed_episode(self, episode: DiscoveredEpisode, knowledge_objects: List[KnowledgeObject]) -> None:
        episode.status = EpisodeStatus.PROCESSED
        episode.processed_at = now_iso()
        episode.knowledge_object_ids = [item.id for item in knowledge_objects]
        self.record_discovered_episodes([episode])
        self._store_knowledge_objects(episode, knowledge_objects)
        self._record_growth(episode, knowledge_objects)

    def record_failed_episode(self, episode: DiscoveredEpisode, error: str) -> None:
        episode.status = EpisodeStatus.FAILED
        episode.error = error
        episode.processed_at = now_iso()
        self.record_discovered_episodes([episode])

    def record_duplicate_episode(self, episode: DiscoveredEpisode, duplicate_of: Optional[str]) -> None:
        episode.status = EpisodeStatus.DUPLICATE
        episode.duplicate_of = duplicate_of
        episode.processed_at = now_iso()
        self.record_discovered_episodes([episode])

    def episodes(self) -> List[DiscoveredEpisode]:
        return [DiscoveredEpisode.from_dict(item) for item in self.state.read_json("episodes.json", [])]

    def information_events(self) -> List[Dict[str, Any]]:
        stored = self.state.read_json("information_events.json", None)
        if stored is not None:
            return stored
        return [episode.as_information_event().to_dict() for episode in self.episodes()]

    def knowledge_objects(self) -> List[Dict[str, Any]]:
        return self.state.read_jsonl("knowledge_objects.jsonl")

    def source_graphs(self) -> List[SourceGraph]:
        return list(self._load_graphs().values())

    def summary(self) -> Dict[str, Any]:
        episodes = self.episodes()
        objects = self.knowledge_objects()
        profiles = self.load_profiles()
        discovery_runs = self.state.read_json("discovery_runs.json", [])
        duplicate_detections = sum(run.get("duplicates", 0) for run in discovery_runs)
        object_types = Counter(item.get("type") for item in objects)
        chunks = [item for item in objects if item.get("type") == "chunk"]
        docs = [item for item in objects if item.get("type") == "document"]
        embeddings = sum(1 for item in chunks if (item.get("structured_data") or {}).get("embedding"))
        profile_stats: Dict[str, Dict[str, Any]] = {}
        for profile in profiles:
            profile_episodes = [episode for episode in episodes if episode.profile_id == profile.profile_id]
            profile_objects = [item for item in objects if (item.get("structured_data") or {}).get("metadata", {}).get("profile_id") == profile.profile_id]
            profile_stats[profile.profile_id] = {
                "name": profile.name,
                "enabled": profile.enabled,
                "interest_count": len(profile.interests),
                "watch_list_size": len(profile.watch_list),
                "episode_count": len(profile_episodes),
                "processed_episodes": sum(1 for episode in profile_episodes if episode.status == EpisodeStatus.PROCESSED),
                "duplicate_episodes": sum(1 for episode in profile_episodes if episode.status == EpisodeStatus.DUPLICATE),
                "knowledge_object_count": len(profile_objects),
            }
        source_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"episodes": 0, "processed": 0, "failed": 0})
        for episode in episodes:
            source_stats[episode.podcast_name]["episodes"] += 1
            if episode.status == EpisodeStatus.PROCESSED:
                source_stats[episode.podcast_name]["processed"] += 1
            if episode.status == EpisodeStatus.FAILED:
                source_stats[episode.podcast_name]["failed"] += 1
        return {
            "episodes": len(episodes),
            "processed_episodes": sum(1 for episode in episodes if episode.status == EpisodeStatus.PROCESSED),
            "queued_episodes": sum(1 for episode in episodes if episode.status == EpisodeStatus.QUEUED),
            "duplicate_episodes": sum(1 for episode in episodes if episode.status == EpisodeStatus.DUPLICATE),
            "duplicate_detections": duplicate_detections,
            "failed_episodes": sum(1 for episode in episodes if episode.status == EpisodeStatus.FAILED),
            "transcripts": len(docs),
            "knowledge_objects": len(objects),
            "documents": object_types.get("document", 0),
            "chunks": object_types.get("chunk", 0),
            "embeddings": embeddings,
            "profiles": profile_stats,
            "sources": dict(source_stats),
            "source_graphs": len(self.source_graphs()),
            "growth_history": self.state.read_json("growth_history.json", []),
        }

    def _store_knowledge_objects(self, episode: DiscoveredEpisode, knowledge_objects: List[KnowledgeObject]) -> None:
        rows = self.state.read_jsonl("knowledge_objects.jsonl")
        existing_ids = {row.get("id") for row in rows}
        for item in knowledge_objects:
            data = item.to_dict()
            data.setdefault("structured_data", {})
            data["structured_data"].setdefault("metadata", {})
            data["structured_data"]["metadata"].update({
                "profile_id": episode.profile_id,
                "episode_id": episode.episode_id,
                "event_id": episode.episode_id,
                "event_type": episode.event_type.value if hasattr(episode.event_type, "value") else episode.event_type,
                "podcast_name": episode.podcast_name,
                "venue": episode.podcast_name,
                "source_id": episode.source_id,
                "participants": list(episode.matched_watch_entries),
                "acquisition_route": episode.acquisition_route,
                "route_confidence": episode.route_confidence,
                "transcript_provenance": dict(episode.transcript_provenance),
                "intelligence_collection": True,
            })
            if data.get("id") not in existing_ids:
                rows.append(data)
                existing_ids.add(data.get("id"))
        self.state.write_jsonl("knowledge_objects.jsonl", rows)

    def _record_growth(self, episode: DiscoveredEpisode, knowledge_objects: List[KnowledgeObject]) -> None:
        history = self.state.read_json("growth_history.json", [])
        history.append({
            "created_at": now_iso(),
            "profile_id": episode.profile_id,
            "episode_id": episode.episode_id,
            "podcast_name": episode.podcast_name,
            "knowledge_objects_added": len(knowledge_objects),
            "chunks_added": sum(1 for item in knowledge_objects if item.type.value == "chunk"),
            "documents_added": sum(1 for item in knowledge_objects if item.type.value == "document"),
        })
        self.state.write_json("growth_history.json", history)

    def _load_graphs(self) -> Dict[str, SourceGraph]:
        graphs = {}
        for item in self.state.read_json("source_graphs.json", []):
            graph = SourceGraph.from_dict(item)
            graphs[graph.graph_id] = graph
        return graphs

    def _save_graphs(self, graphs: Dict[str, SourceGraph]) -> None:
        self.state.write_json("source_graphs.json", [graph.to_dict() for graph in graphs.values()])

    def _graph_for_person(self, graphs: Dict[str, SourceGraph], profile_id: str, person: str) -> SourceGraph:
        probe = SourceGraph(profile_id=profile_id, person=person)
        if probe.graph_id not in graphs:
            graphs[probe.graph_id] = probe
        return graphs[probe.graph_id]
