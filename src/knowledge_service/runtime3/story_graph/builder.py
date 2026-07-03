"""Agent E — build Story Objects from claims, entities, and events."""

from __future__ import annotations

from typing import Dict, List, Sequence, Set

from ...intelligence.models import stable_id
from ..config import Runtime3Config
from ..models import (
    DetectedEvent,
    ResolvedEntity,
    SemanticClaim,
    StoryGraph,
    StoryObject,
    StoryRelationship,
    StoryTimelineEntry,
    StoryType,
)
from .clustering import cluster_claims, collect_story_entities, collect_story_events


class StoryGraphBuilder:
    """Cluster claims into Story Objects — replaces theme labels."""

    def __init__(self, config: Runtime3Config | None = None):
        self.config = config or Runtime3Config()

    def build(
        self,
        claims: Sequence[SemanticClaim],
        entities: Sequence[ResolvedEntity],
        events: Sequence[DetectedEvent],
    ) -> StoryGraph:
        entity_index = {entity.entity_id: entity for entity in entities}
        event_index = {event.event_id: event for event in events}

        clusters = cluster_claims(
            claims,
            threshold=self.config.story_cluster_threshold,
            min_cluster_size=self.config.min_story_claims,
            max_claims=self.config.max_claims_for_clustering,
        )

        stories: List[StoryObject] = []
        used_claim_ids: Set[str] = set()

        for cluster in clusters:
            story_entities = collect_story_entities(cluster, entity_index)
            story_events = collect_story_events(cluster, event_index)
            story_type = self._infer_story_type(story_entities, story_events)
            title = self._generate_title(story_entities, story_events, cluster)
            confidence = self._story_confidence(cluster, story_entities, story_events)

            if confidence < self.config.min_story_confidence:
                continue

            episode_ids = list(dict.fromkeys(claim.episode_id for claim in cluster if claim.episode_id))
            sources = list(dict.fromkeys(claim.podcast_name for claim in cluster if claim.podcast_name))
            lead_claim = max(cluster, key=lambda claim: claim.confidence)

            story = StoryObject(
                story_id=stable_id("story", title, *sorted(claim.claim_id for claim in cluster)[:3]),
                title=title,
                summary=lead_claim.claim_text,
                story_type=story_type,
                supporting_claims=list(cluster),
                supporting_claim_ids=[claim.claim_id for claim in cluster],
                episode_ids=episode_ids,
                entities=story_entities,
                events=story_events,
                supporting_sources=sources,
                evidence=[claim.claim_text for claim in cluster[:5]],
                confidence=confidence,
                importance=self._importance_score(cluster, story_entities, story_events),
                novelty=0.85,
                timeline=self._build_timeline(cluster, story_events),
                relationships=self._build_relationships(story_entities, cluster),
            )
            stories.append(story)
            used_claim_ids.update(claim.claim_id for claim in cluster)

        stories.sort(key=lambda story: story.importance, reverse=True)
        stories = stories[: self.config.max_stories_per_run]

        orphan_ids = [claim.claim_id for claim in claims if claim.claim_id not in used_claim_ids]
        edges = self._build_edges(stories)

        return StoryGraph(stories=stories, orphan_claim_ids=orphan_ids, edges=edges)

    def _infer_story_type(
        self,
        entities: Sequence[ResolvedEntity],
        events: Sequence[DetectedEvent],
    ) -> StoryType:
        if events:
            event_type = events[0].event_type.value
            mapping = {
                "election": StoryType.POLICY,
                "policy": StoryType.POLICY,
                "scientific_discovery": StoryType.SCIENCE,
                "research_paper": StoryType.SCIENCE,
                "launch": StoryType.TECHNOLOGY,
                "product_announcement": StoryType.TECHNOLOGY,
                "release": StoryType.TECHNOLOGY,
                "acquisition": StoryType.BUSINESS,
                "funding": StoryType.BUSINESS,
                "partnership": StoryType.BUSINESS,
            }
            return mapping.get(event_type, StoryType.ANALYSIS)
        if any("empire" in entity.canonical_name.lower() for entity in entities):
            return StoryType.CULTURE
        if any(entity.entity_type.value in {"person"} for entity in entities):
            return StoryType.PROFILE
        return StoryType.GENERAL

    def _generate_title(
        self,
        entities: Sequence[ResolvedEntity],
        events: Sequence[DetectedEvent],
        claims: Sequence[SemanticClaim],
    ) -> str:
        if events and entities:
            primary = entities[0].canonical_name
            event_label = events[0].event_type.value.replace("_", " ").title()
            return f"{primary} — {event_label}"
        if len(entities) >= 2:
            return f"{entities[0].canonical_name} and {entities[1].canonical_name}"
        if entities:
            return f"{entities[0].canonical_name} Developments"
        lead = max(claims, key=lambda claim: claim.confidence)
        words = lead.claim_text.split()
        if len(words) > 10:
            return " ".join(words[:8]) + "…"
        return lead.claim_text[:80]

    def _story_confidence(
        self,
        claims: Sequence[SemanticClaim],
        entities: Sequence[ResolvedEntity],
        events: Sequence[DetectedEvent],
    ) -> float:
        claim_conf = sum(claim.confidence for claim in claims) / len(claims)
        entity_bonus = min(0.15, len(entities) * 0.03)
        event_bonus = min(0.12, len(events) * 0.04)
        source_bonus = min(0.10, len({claim.episode_id for claim in claims}) * 0.03)
        return round(min(0.99, claim_conf + entity_bonus + event_bonus + source_bonus), 3)

    def _importance_score(
        self,
        claims: Sequence[SemanticClaim],
        entities: Sequence[ResolvedEntity],
        events: Sequence[DetectedEvent],
    ) -> float:
        base = sum(claim.confidence for claim in claims) / len(claims)
        multi_source = len({claim.episode_id for claim in claims})
        return round(min(0.99, base * 0.6 + min(0.25, multi_source * 0.08) + len(events) * 0.05 + len(entities) * 0.02), 3)

    def _build_timeline(
        self,
        claims: Sequence[SemanticClaim],
        events: Sequence[DetectedEvent],
    ) -> List[StoryTimelineEntry]:
        entries: List[StoryTimelineEntry] = []
        for claim in sorted(claims, key=lambda row: row.timestamp_start or 0.0):
            entries.append(StoryTimelineEntry(
                timestamp_label=claim.timestamp_label,
                description=claim.claim_text[:200],
                claim_id=claim.claim_id,
            ))
        for event in events:
            if event.timestamp_start is not None:
                entries.append(StoryTimelineEntry(
                    timestamp_label="",
                    description=event.title,
                    event_id=event.event_id,
                ))
        return entries[:12]

    def _build_relationships(
        self,
        entities: Sequence[ResolvedEntity],
        claims: Sequence[SemanticClaim],
    ) -> List[StoryRelationship]:
        if len(entities) < 2:
            return []
        relationships: List[StoryRelationship] = []
        claim_ids = [claim.claim_id for claim in claims]
        for index in range(len(entities) - 1):
            relationships.append(StoryRelationship(
                source_entity_id=entities[index].entity_id,
                target_entity_id=entities[index + 1].entity_id,
                relationship_type="co_occurrence",
                confidence=0.65,
                evidence_claim_ids=claim_ids[:3],
            ))
        return relationships

    def _build_edges(self, stories: Sequence[StoryObject]) -> List[Dict[str, object]]:
        edges: List[Dict[str, object]] = []
        for index, story in enumerate(stories):
            for claim_id in story.supporting_claim_ids:
                edges.append({
                    "story_id": story.story_id,
                    "claim_id": claim_id,
                    "edge_type": "supports",
                })
            for event in story.events:
                edges.append({
                    "story_id": story.story_id,
                    "event_id": event.event_id,
                    "edge_type": "contains_event",
                })
            if index > 0:
                shared_entities = set(story.people + story.organizations) & set(
                    stories[index - 1].people + stories[index - 1].organizations
                )
                if shared_entities:
                    edges.append({
                        "story_id": story.story_id,
                        "related_story_id": stories[index - 1].story_id,
                        "edge_type": "related",
                        "shared": list(shared_entities),
                    })
        return edges