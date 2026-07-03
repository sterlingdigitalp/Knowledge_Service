"""Match daily stories to persistent cross-day memory."""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from ...intelligence.models import stable_id
from ...retrieval.embedding import cosine_similarity, tokenize
from ..models import StoryObject
from ..thinking.models import (
    MemoryMatchAction,
    PersistentStoryRecord,
    StoryEvolution,
    StoryEvolutionState,
    StoryMemory,
)


class StoryMemoryMatcher:
    """Extend existing stories across days instead of creating duplicates."""

    MATCH_THRESHOLD = 0.40

    def reconcile(
        self,
        date: str,
        stories: Sequence[StoryObject],
        memory: StoryMemory,
    ) -> Tuple[StoryMemory, List[Dict[str, object]], Dict[str, str]]:
        """Return updated memory, action log, and story_id → persistent_id map."""
        actions: List[Dict[str, object]] = []
        persistent_map: Dict[str, str] = {}
        active = {record.persistent_story_id: record for record in memory.records if record.evolution_state.value != "retired"}
        matched_persistent: set[str] = set()

        for story in stories:
            signature_entities = [entity.canonical_name.lower() for entity in story.entities[:6]]
            signature_events = [event.event_type.value for event in story.events[:4]]
            match = self._find_match(story, list(active.values()), signature_entities, signature_events)

            if match:
                record = active[match.persistent_story_id]
                matched_persistent.add(record.persistent_story_id)
                prior_conf = record.confidence
                record.last_seen_date = date
                record.daily_story_ids[date] = story.story_id
                record.claim_count += len(story.supporting_claims)
                record.source_count = len(set(
                    list(story.supporting_sources) + record.episode_ids,
                ))
                record.episode_ids = list(dict.fromkeys(record.episode_ids + story.episode_ids))
                record.confidence = round(min(0.99, (record.confidence + story.confidence) / 2 + 0.05), 3)
                record.importance = max(record.importance, story.importance)

                if story.confidence > prior_conf + 0.05:
                    evolution = StoryEvolutionState.STRENGTHENED
                    explanation = f"New evidence on {date} increased confidence."
                elif story.contradictions:
                    evolution = StoryEvolutionState.CONTRADICTED
                    explanation = f"Contradictions detected on {date}."
                else:
                    evolution = StoryEvolutionState.STABLE
                    explanation = f"Story extended on {date} with additional evidence."

                record.evolution_state = evolution
                record.evolution_history.append(StoryEvolution(
                    state=evolution,
                    explanation=explanation,
                    prior_confidence=prior_conf,
                    new_confidence=record.confidence,
                ))
                persistent_map[story.story_id] = record.persistent_story_id
                story.editorial_notes = (
                    f"Persistent story {record.persistent_story_id} "
                    f"(first seen {record.first_seen_date}, state: {evolution.value})"
                )
                actions.append({
                    "action": MemoryMatchAction.EXTEND.value,
                    "story_id": story.story_id,
                    "persistent_story_id": record.persistent_story_id,
                    "headline": story.headline,
                    "evolution": evolution.value,
                })
            else:
                persistent_id = stable_id(
                    "pstory",
                    story.headline.lower(),
                    *signature_entities[:3],
                )
                record = PersistentStoryRecord(
                    persistent_story_id=persistent_id,
                    headline=story.headline,
                    story_type=story.story_type.value,
                    entity_signature=signature_entities,
                    event_signature=signature_events,
                    first_seen_date=date,
                    last_seen_date=date,
                    evolution_state=StoryEvolutionState.FIRST_SEEN,
                    confidence=story.confidence,
                    importance=story.importance,
                    claim_count=len(story.supporting_claims),
                    source_count=len(story.supporting_sources),
                    episode_ids=list(story.episode_ids),
                    daily_story_ids={date: story.story_id},
                    evolution_history=[StoryEvolution(
                        state=StoryEvolutionState.FIRST_SEEN,
                        explanation=f"Story first seen on {date}.",
                        new_confidence=story.confidence,
                    )],
                )
                memory.records.append(record)
                active[persistent_id] = record
                persistent_map[story.story_id] = persistent_id
                story.editorial_notes = f"New persistent story {persistent_id} (first seen {date})."
                actions.append({
                    "action": MemoryMatchAction.CREATE.value,
                    "story_id": story.story_id,
                    "persistent_story_id": persistent_id,
                    "headline": story.headline,
                })

        for record in memory.records:
            if record.evolution_state.value == "retired":
                continue
            if record.persistent_story_id not in matched_persistent and record.last_seen_date < date:
                if record.evolution_state != StoryEvolutionState.RETIRED:
                    record.evolution_state = StoryEvolutionState.WEAKENED
                    record.evolution_history.append(StoryEvolution(
                        state=StoryEvolutionState.WEAKENED,
                        explanation=f"No new evidence on {date}.",
                        prior_confidence=record.confidence,
                        new_confidence=max(0.1, record.confidence - 0.08),
                    ))
                    record.confidence = max(0.1, record.confidence - 0.08)
                    actions.append({
                        "action": "weakened",
                        "persistent_story_id": record.persistent_story_id,
                        "headline": record.headline,
                    })

        return memory, actions, persistent_map

    def _find_match(
        self,
        story: StoryObject,
        records: Sequence[PersistentStoryRecord],
        entity_sig: List[str],
        event_sig: List[str],
    ) -> PersistentStoryRecord | None:
        best: PersistentStoryRecord | None = None
        best_score = 0.0
        story_tokens = set(tokenize(story.headline.lower()))

        for record in records:
            entity_overlap = len(set(entity_sig) & set(record.entity_signature))
            event_overlap = len(set(event_sig) & set(record.event_signature))
            record_tokens = set(tokenize(record.headline.lower()))
            token_overlap = len(story_tokens & record_tokens) / max(len(story_tokens | record_tokens), 1)

            entity_denom = max(len(entity_sig), len(record.entity_signature), 1)
            entity_score = entity_overlap / entity_denom
            event_score = event_overlap / max(len(event_sig), len(record.event_signature), 1) if (event_sig or record.event_signature) else 0.0
            score = (
                0.35 * entity_score
                + 0.15 * event_score
                + 0.40 * token_overlap
            )
            if story.story_type.value == record.story_type:
                score += 0.08

            if score > best_score and score >= self.MATCH_THRESHOLD:
                best_score = score
                best = record
        return best