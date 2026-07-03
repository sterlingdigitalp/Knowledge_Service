"""Agent F — relationship graph across stories, entities, events."""

from __future__ import annotations

from typing import Dict, List, Sequence, Set

from ..models import StoryObject
from ..thinking.models import EventObject, GraphEdge, RelationshipGraph


class RelationshipGraphBuilder:
    """Build cross-layer relationship graph."""

    def build(
        self,
        stories: Sequence[StoryObject],
        events: Sequence[EventObject],
    ) -> RelationshipGraph:
        edges: List[GraphEdge] = []
        story_links: List[Dict[str, object]] = []
        contradictions: List[Dict[str, object]] = []
        follow_ups: List[Dict[str, object]] = []

        for i in range(len(stories)):
            for j in range(i + 1, len(stories)):
                link = self._story_link(stories[i], stories[j])
                if link:
                    story_links.append(link)
                    edges.append(GraphEdge(
                        source_id=stories[i].story_id,
                        target_id=stories[j].story_id,
                        edge_type="related_story",
                        confidence=float(link.get("confidence", 0.5)),
                        metadata=link,
                    ))

        for story in stories:
            for event in story.events:
                edges.append(GraphEdge(
                    source_id=story.story_id,
                    target_id=event.event_id,
                    edge_type="story_contains_event",
                    confidence=story.confidence,
                ))
            for entity in story.entities:
                edges.append(GraphEdge(
                    source_id=story.story_id,
                    target_id=entity.entity_id,
                    edge_type="story_mentions_entity",
                    confidence=entity.confidence,
                ))
            for contradiction in story.contradictions:
                contradictions.append({
                    "story_id": story.story_id,
                    "headline": story.headline,
                    "text": contradiction,
                })

        follow_ups = self._detect_follow_ups(stories)

        return RelationshipGraph(
            edges=edges,
            story_links=story_links,
            contradictions=contradictions,
            follow_ups=follow_ups,
        )

    def _story_link(self, left: StoryObject, right: StoryObject) -> Dict[str, object] | None:
        left_entities = {entity.entity_id for entity in left.entities}
        right_entities = {entity.entity_id for entity in right.entities}
        shared_entities = left_entities & right_entities
        shared_sources = set(left.supporting_sources) & set(right.supporting_sources)
        shared_events = {event.event_id for event in left.events} & {event.event_id for event in right.events}

        if not shared_entities and not shared_events:
            return None

        confidence = min(0.95, 0.40 + len(shared_entities) * 0.10 + len(shared_events) * 0.15)
        return {
            "left_story_id": left.story_id,
            "right_story_id": right.story_id,
            "shared_entities": [
                entity.canonical_name
                for entity in left.entities
                if entity.entity_id in shared_entities
            ],
            "shared_sources": list(shared_sources),
            "shared_events": list(shared_events),
            "confidence": round(confidence, 3),
        }

    def _detect_follow_ups(self, stories: Sequence[StoryObject]) -> List[Dict[str, object]]:
        follow_ups: List[Dict[str, object]] = []
        by_entity: Dict[str, List[StoryObject]] = {}
        for story in stories:
            for entity in story.entities[:3]:
                by_entity.setdefault(entity.entity_id, []).append(story)

        seen: Set[str] = set()
        for entity_id, grouped in by_entity.items():
            if len(grouped) < 2:
                continue
            grouped = sorted(grouped, key=lambda story: story.importance, reverse=True)
            key = f"{grouped[0].story_id}:{grouped[1].story_id}"
            if key in seen:
                continue
            seen.add(key)
            follow_ups.append({
                "entity": grouped[0].entities[0].canonical_name if grouped[0].entities else "",
                "primary_story": grouped[0].headline,
                "follow_up_story": grouped[1].headline,
                "reason": "shared_entity_multi_story",
            })
        return follow_ups