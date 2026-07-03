"""Agent D — detect events from semantic claims."""

from __future__ import annotations

from typing import Dict, List, Sequence

from ..models import DetectedEvent, EventType, ResolvedEntity, SemanticClaim
from .patterns import EVENT_RULES


class EventDetector:
    """Connect claims into typed events."""

    def detect(
        self,
        claims: Sequence[SemanticClaim],
        entities: Sequence[ResolvedEntity],
    ) -> List[DetectedEvent]:
        entity_index = {entity.entity_id: entity for entity in entities}
        events: List[DetectedEvent] = []
        seen_signatures: Dict[str, DetectedEvent] = {}

        for claim in claims:
            matched_types = self._match_event_types(claim.claim_text)
            if not matched_types:
                continue
            for event_type in matched_types:
                title = self._event_title(claim, entity_index, event_type)
                signature = f"{event_type.value}:{title.lower()}"
                existing = seen_signatures.get(signature)
                if existing:
                    if claim.claim_id not in existing.claim_ids:
                        existing.claim_ids.append(claim.claim_id)
                    if claim.episode_id and claim.episode_id not in existing.episode_ids:
                        existing.episode_ids.append(claim.episode_id)
                    for entity_id in claim.resolved_entity_ids:
                        if entity_id not in existing.entity_ids:
                            existing.entity_ids.append(entity_id)
                    existing.confidence = min(0.99, existing.confidence + 0.08)
                    claim.event_references.append(existing.event_id)
                    continue

                event = DetectedEvent(
                    event_id="",
                    event_type=event_type,
                    title=title,
                    description=claim.claim_text[:300],
                    claim_ids=[claim.claim_id],
                    entity_ids=list(claim.resolved_entity_ids),
                    episode_ids=[claim.episode_id] if claim.episode_id else [],
                    confidence=claim.confidence,
                    timestamp_start=claim.timestamp_start,
                )
                seen_signatures[signature] = event
                events.append(event)
                claim.event_references.append(event.event_id)

        return sorted(events, key=lambda event: event.confidence, reverse=True)

    def _match_event_types(self, text: str) -> List[EventType]:
        matched: List[EventType] = []
        for event_type, pattern, _ in EVENT_RULES:
            if pattern.search(text):
                matched.append(event_type)
        return matched or []

    def _event_title(
        self,
        claim: SemanticClaim,
        entity_index: Dict[str, ResolvedEntity],
        event_type: EventType,
    ) -> str:
        entity_names = []
        for entity_id in claim.resolved_entity_ids[:3]:
            entity = entity_index.get(entity_id)
            if entity:
                entity_names.append(entity.canonical_name)
        label = EVENT_RULES_LABELS.get(event_type, event_type.value)
        if entity_names:
            return f"{entity_names[0]} — {label.replace('_', ' ').title()}"
        words = claim.claim_text.split()[:8]
        return f"{' '.join(words)}…" if len(claim.claim_text.split()) > 8 else claim.claim_text[:80]


EVENT_RULES_LABELS = {rule[0]: rule[2] for rule in EVENT_RULES}