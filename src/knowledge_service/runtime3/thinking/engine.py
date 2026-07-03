"""FEGOS Phase 1 — Thinking Engine orchestrator."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from ..claims.extractor import SemanticClaimExtractor
from ..claims.intelligence import ClaimIntelligenceEngine
from ..config import Runtime3Config
from ..entities.registry import EntityRegistry
from ..events.engine import EventEngine
from ..memory.matcher import StoryMemoryMatcher
from ..memory.store import StoryMemoryStore
from ..narrative.synthesis import NarrativeSynthesizer
from ..pipeline import Runtime3Pipeline
from ..ranking.engine import StoryRankingEngine
from ..relationships.graph import RelationshipGraphBuilder
from ..segmentation.boundaries import StoryBoundaryDetector, enrich_segments
from ..segmentation.classifier import SegmentClassifier
from ..story_graph.builder import StoryGraphBuilder
from ..thinking.models import EntityGraph, EventGraph, ThinkingResult


class ThinkingEngine:
    """Complete semantic understanding pipeline for FEGOS Phase 1."""

    def __init__(
        self,
        config: Runtime3Config | None = None,
        state_dir: str | None = None,
        memory_path: str | None = None,
    ):
        self.config = config or Runtime3Config.from_env()
        self.state_dir = state_dir
        self.memory_store = StoryMemoryStore(
            memory_path or "data/runtime3/runtime3_story_memory.json",
        )
        self.base_pipeline = Runtime3Pipeline(self.config, state_dir=state_dir)
        self.segment_classifier = SegmentClassifier()
        self.boundary_detector = StoryBoundaryDetector()
        self.claim_extractor = SemanticClaimExtractor(self.config)
        self.claim_intelligence = ClaimIntelligenceEngine()
        self.entity_registry = EntityRegistry()
        self.event_engine = EventEngine()
        self.story_builder = StoryGraphBuilder(self.config)
        self.narrative = NarrativeSynthesizer()
        self.relationship_builder = RelationshipGraphBuilder()
        self.memory_matcher = StoryMemoryMatcher()
        self.ranker = StoryRankingEngine()

    def run_for_date(
        self,
        date: str,
        *,
        state_dir: str | None = None,
        archive_dir: str | None = None,
        profiles: Sequence | None = None,
    ) -> ThinkingResult:
        started = time.perf_counter()
        state_dir = state_dir or self.state_dir or "state"

        base = self.base_pipeline.run_for_archive_date(
            date, state_dir=state_dir, archive_dir=archive_dir,
        )

        raw_segments = base.segments
        enriched = enrich_segments(raw_segments)
        boundaries = self.boundary_detector.detect(raw_segments)

        claims = self.claim_intelligence.enrich(base.claims)
        watch_names = Runtime3Pipeline._collect_watch_names(profiles or [])
        self.entity_registry = EntityRegistry(watch_names)
        canonical_entities = self.entity_registry.resolve_claims(base.claims)
        entity_edges = self.entity_registry.build_cooccurrence_edges(base.claims)

        events, event_edges = self.event_engine.build(base.claims, base.entities)
        story_graph = base.story_graph
        stories = self.narrative.synthesize(base.stories)
        stories = self._deduplicate_stories(stories)

        memory = self.memory_store.load()
        memory, memory_actions, persistent_map = self.memory_matcher.reconcile(date, stories, memory)
        self.memory_store.save(memory)

        evolution_states = {
            record.persistent_story_id: record.evolution_state.value
            for record in memory.records
        }
        ranked = self.ranker.rank(
            stories,
            date=date,
            persistent_map=persistent_map,
            evolution_states=evolution_states,
        )

        relationship_graph = self.relationship_builder.build(stories, events)
        entity_graph = EntityGraph(entities=canonical_entities, edges=entity_edges)
        event_graph = EventGraph(events=events, edges=event_edges)

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return ThinkingResult(
            date=date,
            segments=enriched,
            boundaries=boundaries,
            claims=claims,
            entities=canonical_entities,
            events=events,
            stories=stories,
            ranked_stories=ranked,
            entity_graph=entity_graph,
            event_graph=event_graph,
            relationship_graph=relationship_graph,
            story_graph=story_graph.to_dict() if story_graph else None,
            story_memory=memory,
            memory_actions=memory_actions,
            latency_ms=latency_ms,
        )

    def _deduplicate_stories(self, stories: Sequence) -> List:
        """Merge stories with identical headlines."""
        seen: Dict[str, object] = {}
        for story in stories:
            key = story.headline.strip().lower()
            if key in seen:
                existing = seen[key]
                existing.supporting_claims.extend(story.supporting_claims)
                existing.supporting_claim_ids.extend(story.supporting_claim_ids)
                existing.supporting_sources = list(dict.fromkeys(
                    existing.supporting_sources + story.supporting_sources,
                ))
                existing.confidence = max(existing.confidence, story.confidence)
            else:
                seen[key] = story
        return list(seen.values())