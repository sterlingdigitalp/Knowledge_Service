"""Runtime 3 pipeline orchestrator."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Sequence

from ..intelligence.corpus import CorpusManager
from ..intelligence.models import EpisodeStatus
from ..intelligence.state import FileStateStore
from .claims.extractor import SemanticClaimExtractor
from .config import Runtime3Config, is_runtime3_enabled
from .entities.resolver import EntityResolver
from .events.detector import EventDetector
from .models import Runtime3Result, StoryObject
from .narrative.synthesis import NarrativeSynthesizer
from .segmentation.classifier import SegmentClassifier
from .story_graph.builder import StoryGraphBuilder


class Runtime3Pipeline:
    """Transcript → Segmentation → Claims → Entities → Events → Story Graph → Stories."""

    def __init__(self, config: Runtime3Config | None = None, state_dir: str | None = None):
        self.config = config or Runtime3Config.from_env()
        self.state_dir = state_dir
        self.segment_classifier = SegmentClassifier()
        self.claim_extractor = SemanticClaimExtractor(self.config)
        self.entity_resolver = EntityResolver()
        self.event_detector = EventDetector()
        self.story_builder = StoryGraphBuilder(self.config)
        self.narrative = NarrativeSynthesizer()

    @property
    def enabled(self) -> bool:
        return is_runtime3_enabled()

    def run(
        self,
        *,
        state_dir: str | None = None,
        episode_ids: Sequence[str] | None = None,
        knowledge_objects: Sequence[Dict[str, Any]] | None = None,
        episodes: Sequence[Dict[str, Any]] | None = None,
        profiles: Sequence[Any] | None = None,
    ) -> Runtime3Result:
        started = time.perf_counter()

        if knowledge_objects is None or episodes is None:
            state = FileStateStore(state_dir or self.state_dir or "state")
            corpus = CorpusManager(state)
            episodes = [
                episode.to_dict()
                for episode in corpus.episodes()
                if episode.status == EpisodeStatus.PROCESSED
            ]
            if episode_ids:
                allowed = set(episode_ids)
                episodes = [episode for episode in episodes if episode.get("episode_id") in allowed]
                object_ids = self._collect_object_ids(episodes)
                knowledge_objects = self._load_documents_by_ids(state, object_ids, allowed)
            else:
                knowledge_objects = self._load_all_documents(state)
            if profiles is None:
                profiles = corpus.load_profiles()
        else:
            profiles = profiles or []

        watch_names = self._collect_watch_names(profiles)
        self.entity_resolver = EntityResolver(watch_names)

        segments = self.segment_classifier.classify_corpus(
            knowledge_objects, episodes, episode_ids=episode_ids,
        )
        claims = self.claim_extractor.extract_from_segments(segments)
        entities = self.entity_resolver.resolve_claims(claims)
        events = self.event_detector.detect(claims, entities)
        story_graph = self.story_builder.build(claims, entities, events)
        stories = self.narrative.synthesize(story_graph.stories)

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return Runtime3Result(
            segments=segments,
            claims=claims,
            entities=entities,
            events=events,
            story_graph=story_graph,
            stories=stories,
            episodes_processed=len({segment.episode_id for segment in segments if segment.episode_id}),
            latency_ms=latency_ms,
            enabled=True,
        )

    def run_for_archive_date(
        self,
        date: str,
        *,
        state_dir: str | None = None,
        archive_dir: str | None = None,
    ) -> Runtime3Result:
        """Run Runtime 3 on episodes referenced by an archived morning brief."""
        from pathlib import Path

        root = Path(state_dir or self.state_dir or "state").resolve().parent
        morning_path = Path(archive_dir or root / "frontend" / "archive" / date / "morning.json")
        if not morning_path.exists():
            raise FileNotFoundError(f"Archive not found: {morning_path}")

        import json
        payload = json.loads(morning_path.read_text(encoding="utf-8"))
        podcast_names = set()
        for item in payload.get("items", []):
            podcast_names.update(item.get("sources") or [])
        for entry in (payload.get("brief") or {}).get("items", []):
            explain = entry.get("explainability") or {}
            if explain.get("matched"):
                pass

        episode_ids = self._episode_ids_for_podcasts(
            podcast_names,
            state_dir=state_dir or str(root / "state"),
        )
        return self.run(state_dir=state_dir or str(root / "state"), episode_ids=episode_ids)

    def _episode_ids_for_podcasts(self, podcast_names: set[str], *, state_dir: str) -> List[str]:
        state = FileStateStore(state_dir)
        episodes = state.read_json("episodes.json", [])
        ids: List[str] = []
        for episode in episodes:
            if episode.get("podcast_name") in podcast_names:
                ids.append(episode.get("episode_id"))
        if not ids:
            ids = [episode.get("episode_id") for episode in episodes if episode.get("status") == "processed"][:20]
        return [episode_id for episode_id in ids if episode_id]

    @staticmethod
    def _collect_object_ids(episodes: Sequence[Dict[str, Any]]) -> set[str]:
        object_ids: set[str] = set()
        for episode in episodes:
            for object_id in episode.get("knowledge_object_ids") or []:
                if object_id:
                    object_ids.add(str(object_id))
        return object_ids

    @staticmethod
    def _load_documents_by_ids(
        state: FileStateStore,
        object_ids: set[str],
        episode_ids: set[str],
    ) -> List[Dict[str, Any]]:
        """Stream knowledge_objects.jsonl without loading the full file into memory."""
        if not object_ids and not episode_ids:
            return []
        documents: List[Dict[str, Any]] = []
        found_episodes: set[str] = set()
        path = state.path("knowledge_objects.jsonl")
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                if episode_ids and found_episodes >= episode_ids:
                    break
                row = json.loads(line)
                if row.get("type") != "document":
                    continue
                row_id = str(row.get("id") or "")
                metadata = (row.get("structured_data") or {}).get("metadata") or {}
                episode_id = str(metadata.get("episode_id") or "")
                if episode_id in episode_ids or row_id in object_ids:
                    documents.append(row)
                    if episode_id:
                        found_episodes.add(episode_id)
        return documents

    @staticmethod
    def _load_all_documents(state: FileStateStore) -> List[Dict[str, Any]]:
        documents: List[Dict[str, Any]] = []
        path = state.path("knowledge_objects.jsonl")
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("type") == "document":
                    documents.append(row)
        return documents

    @staticmethod
    def _collect_watch_names(profiles: Sequence[Any]) -> List[str]:
        names: List[str] = []
        for profile in profiles:
            for entry in getattr(profile, "watch_list", []) or []:
                if hasattr(entry, "names"):
                    names.extend(entry.names())
        return list(dict.fromkeys(names))


def stories_to_intelligence_items(stories: Sequence[StoryObject]):
    """Optional bridge: convert Story Objects to IntelligenceItem for brief compatibility."""
    from ..analyst.synthesis.models import IntelligenceItem

    items: List[IntelligenceItem] = []
    for story in stories:
        citations = []
        for claim in story.supporting_claims[:5]:
            citations.append({
                "excerpt": claim.claim_text,
                "speaker": claim.speaker,
                "source": claim.podcast_name,
                "timestamp": claim.timestamp_label,
                "url": claim.source_url,
            })
        items.append(IntelligenceItem(
            item_id=story.story_id,
            title=story.headline,
            executive_summary=story.executive_summary,
            why_surfaced=f"Runtime 3 story: {story.story_type.value}",
            why_it_matters=story.why_it_matters,
            novelty_score=story.novelty,
            novelty_classification="new",
            importance_score=story.importance,
            importance_band="very_high" if story.importance >= 0.75 else "high",
            confidence=story.confidence,
            corroboration_count=len(story.supporting_sources),
            contradiction_count=len(story.contradictions),
            theme_id=story.story_id,
            theme_label=story.headline,
            profile_ids=["ai"],
            profile_names=["AI"],
            supporting_claim_ids=story.supporting_claim_ids,
            supporting_evidence=[{"excerpt": excerpt} for excerpt in story.evidence[:3]],
            timestamped_citations=citations,
            speakers=list(dict.fromkeys(claim.speaker for claim in story.supporting_claims)),
            sources=story.supporting_sources,
            contradictions=[{"text": text} for text in story.contradictions],
            historical_developments=[],
            claim_count=len(story.supporting_claims),
        ))
    return items