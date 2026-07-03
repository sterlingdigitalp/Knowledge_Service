"""Agent D — Event Object engine."""

from __future__ import annotations

from typing import Dict, List, Sequence

from ..models import DetectedEvent, ResolvedEntity, SemanticClaim
from ..thinking.models import EventObject, GraphEdge
from .detector import EventDetector


class EventEngine:
    """Produce first-class Event Objects from claims."""

    def __init__(self):
        self.detector = EventDetector()

    def build(
        self,
        claims: Sequence[SemanticClaim],
        entities: Sequence[ResolvedEntity],
    ) -> tuple[List[EventObject], List[GraphEdge]]:
        detected = self.detector.detect(claims, entities)
        entity_index = {entity.entity_id: entity for entity in entities}
        events = [EventObject.from_detected(event, entities) for event in detected]
        edges = self._build_edges(events, entity_index)
        return events, edges

    def _build_edges(
        self,
        events: Sequence[EventObject],
        entity_index: Dict[str, ResolvedEntity],
    ) -> List[GraphEdge]:
        edges: List[GraphEdge] = []
        for event in events:
            for entity_id in event.participant_entity_ids:
                edges.append(GraphEdge(
                    source_id=event.event_id,
                    target_id=entity_id,
                    edge_type="event_participant",
                    confidence=event.confidence,
                ))
            for claim_id in event.claim_ids:
                edges.append(GraphEdge(
                    source_id=event.event_id,
                    target_id=claim_id,
                    edge_type="supported_by_claim",
                    confidence=event.confidence,
                ))
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                shared = set(events[i].participant_entity_ids) & set(events[j].participant_entity_ids)
                if shared:
                    edges.append(GraphEdge(
                        source_id=events[i].event_id,
                        target_id=events[j].event_id,
                        edge_type="related_event",
                        confidence=0.60,
                        metadata={"shared_entities": list(shared)},
                    ))
        return edges