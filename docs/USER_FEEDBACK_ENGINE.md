# User Feedback Engine

The User Feedback Engine captures behavioral signals that drive personalized ranking. Every interaction is append-only, persisted, and reflected in preference state on the next pipeline run.

## Module

| Path | Class |
|------|-------|
| `knowledge_service.production.personalization.feedback` | `UserFeedbackEngine` |

Persistence via `PersonalizationStore` — see `PERSONALIZATION_ENGINE.md`.

## Event Types

| Method | `event_type` | Preference side effect |
|--------|--------------|------------------------|
| `tell_me_more(id, duration_seconds)` | `tell_me_more` | Append to `tell_me_more_items`; accumulate `deep_dive_seconds` |
| `save(id)` | `save` | Append to `saved_items` |
| `dismiss(id)` | `dismiss` | Append to `dismissed_items` |
| `ignore(id)` | `ignore` | Append to `dismissed_items` |
| `brief_view(seconds, items_viewed)` | `brief_view` | Feedback log only |

All item-scoped events accept optional `profile_id`.

## Event Record Schema

```json
{
  "event_type": "tell_me_more",
  "intelligence_item_id": "item-abc123",
  "recorded_at": "2026-06-30T12:00:00Z",
  "duration_seconds": 420,
  "profile_id": ""
}
```

`brief_view` events omit `intelligence_item_id`:

```json
{
  "event_type": "brief_view",
  "seconds": 52,
  "items_viewed": 8,
  "recorded_at": "2026-06-30T12:00:00Z"
}
```

## Write Path

1. `store.record_feedback(event)` — append to `production/feedback.jsonl`
2. `store.load_preferences()` — read current preferences
3. Update item lists (`tell_me_more_items`, `dismissed_items`, `saved_items`)
4. `store.save_preferences(prefs)` — persist

## Downstream Consumers

| Consumer | Usage |
|----------|-------|
| `PersonalizedRankingEngine.learn_from_feedback()` | Topic/profile weight updates |
| `PersonalizedRankingEngine.rank()` | Boosts, penalties, dismissals |
| `BriefQualityEvaluator` | `personal_relevance_hits` metric |
| `ProductionIntelligencePipeline.record_tell_me_more()` | Immediate learning trigger |
| `DeepDiveConversationEngine.start()` | Auto-records `tell_me_more` on session start |

## Pipeline API

```python
from knowledge_service.production.pipeline import ProductionIntelligencePipeline

pipeline = ProductionIntelligencePipeline(state_dir)

# Explicit feedback
pipeline.feedback.tell_me_more(item_id, duration_seconds=300)
pipeline.feedback.save(item_id)
pipeline.feedback.dismiss(item_id)
pipeline.feedback.brief_view(seconds=45, items_viewed=6)

# Convenience: feedback + immediate learning
pipeline.record_tell_me_more(item_id, duration_seconds=420)

# Conversation auto-records tell_me_more on start
session = pipeline.start_conversation(item_id)
follow_up = pipeline.continue_conversation(session["session_id"], "Show me the timeline")
```

## Runtime Inspector

`inspect_production_runtime()` → `personalization`:

| Field | Content |
|-------|---------|
| `event_count` | Total feedback events |
| `event_types` | Counts per event type |
| `tell_me_more_items` | Engaged item count |
| `dismissed_items` | Dismissed item count |
| `saved_items` | Saved item count |
| `topic_weights` | Learned topic affinities |
| `profile_weights` | Learned profile affinities |

## Certification Simulation

`certify_phase5_runtime._simulate_learning_loop()`:

1. `tell_me_more` on lead item (420s)
2. `save` on lead item
3. `dismiss` on third item (when ≥ 3 items)
4. `brief_view` (52s, all items)

Blocker: `"Learning loop not demonstrated"` when `events` is empty.

## Storage

| File | Content |
|------|---------|
| `production/feedback.jsonl` | Append-only event log |
| `production/preferences.json` | Derived preference state |

## Entry Point

```python
from knowledge_service.production.personalization.feedback import UserFeedbackEngine
from knowledge_service.production.personalization.store import PersonalizationStore

feedback = UserFeedbackEngine(PersonalizationStore(state))
event = feedback.tell_me_more("item-id", duration_seconds=120)
summary = feedback.summary()
```

## Design Invariant

Feedback is **append-only** — events are never deleted. Preference lists deduplicate by item ID. Dismiss and ignore are equivalent for ranking (both exclude items). Learning weights update on pipeline run, not synchronously on every event (except `record_tell_me_more()` which triggers immediate `learn_from_feedback()`).