# Personalization Engine

The Personalization Engine adapts Intelligence Item ranking from observed user behavior. Phase 5 applies learned preferences after Phase 4.1 synthesis and before Morning Brief v3 selection.

## Modules

| Path | Class | Role |
|------|-------|------|
| `knowledge_service.production.personalization.store` | `PersonalizationStore` | Feedback, preferences, session persistence |
| `knowledge_service.production.personalization.ranking` | `PersonalizedRankingEngine` | Score adjustment and re-ranking |
| `knowledge_service.production.personalization.feedback` | `UserFeedbackEngine` | Event capture (see `USER_FEEDBACK_ENGINE.md`) |

## Ranking Flow

```text
Intelligence Items (Phase 4.1 synthesis)
  ↓
learn_from_feedback() — update topic/profile weights
  ↓
rank() — apply boosts, penalties, dismissals
  ↓
Persist re-ranked items → synthesis/intelligence_items.json
  ↓
Morning Brief v3 selection
```

`ProductionEnhancementLayer.enhance()` calls `learn_from_feedback()` then `rank()` on every pipeline run.

## Score Adjustments

Base score: `item.importance_score` from Phase 4.1 synthesis.

| Signal | Constant | Effect |
|--------|----------|--------|
| Tell me more | `TELL_ME_MORE_BOOST` | +0.12 |
| Save | `SAVE_BOOST` | +0.08 |
| Dismiss / ignore | — | Item excluded from ranked list |
| Topic weight | learned | Added from `preferences.topic_weights` |
| Profile weight | `PROFILE_BOOST` × weight | +0.06 × `profile_weights[profile]` |

Final score capped at `0.99`. Sort key: `(importance_score, corroboration_count, star_rating)` descending.

## Learning Algorithm

`learn_from_feedback()` walks `production/feedback.jsonl` and updates weights:

| Event type | Topic weight | Profile weight |
|------------|--------------|----------------|
| `tell_me_more`, `save` | +0.05 (max 0.35) | +0.04 per profile (max 0.5) |
| `dismiss`, `ignore` | −0.06 (min −0.35) | — |

Weights keyed by `item.theme_label.lower()` and `item.profile_names`.

## Preferences Model

Persisted in `state/production/preferences.json`:

| Field | Purpose |
|-------|---------|
| `topic_weights` | Theme-label affinity scores |
| `profile_weights` | Profile-name affinity scores |
| `dismissed_items` | Excluded intelligence item IDs |
| `saved_items` | Saved item IDs |
| `tell_me_more_items` | Engaged item IDs |
| `deep_dive_seconds` | Cumulative deep-dive time per item |

## Persistent Storage

| File | Content |
|------|---------|
| `production/preferences.json` | Learned weights and item lists |
| `production/feedback.jsonl` | Append-only event log |
| `production/conversation_sessions.json` | Multi-turn deep dive sessions |

## Pipeline Integration

```python
from knowledge_service.production.pipeline import ProductionIntelligencePipeline

pipeline = ProductionIntelligencePipeline(state_dir)
result = pipeline.run()

# Record engagement, trigger learning
pipeline.record_tell_me_more(item_id, duration_seconds=420)

# Re-run with adapted ranking
second = pipeline.rerun_with_learning()
```

`record_tell_me_more()` records feedback and calls `ranking.learn_from_feedback()` immediately.

## Certification Learning Loop

`certify_phase5_runtime.py` simulates:

1. `tell_me_more` on lead brief item (+420s duration)
2. `save` on lead item
3. `dismiss` on third item (when present)
4. `brief_view` (52s, all items viewed)
5. Second pipeline run via `rerun_with_learning()`

Pass criterion: boosted item appears as lead on second brief (or was already lead).

## Runtime Inspector

`inspect_production_runtime()` exposes:

- `personalization` — event counts, tell-me-more/dismiss/save totals, weights
- `preferences` — `topic_weights`, `profile_weights`

## Entry Point

```python
from knowledge_service.production.personalization.ranking import PersonalizedRankingEngine
from knowledge_service.production.personalization.store import PersonalizationStore

store = PersonalizationStore(state)
ranking = PersonalizedRankingEngine(store)
ranking.learn_from_feedback(items)
ranked = ranking.rank(items)
```

## Design Invariant

Personalization **re-ranks** items; it does not regenerate synthesis. Dismissed items are filtered before brief selection. Learning is incremental — each feedback event nudges topic and profile weights within bounded ranges.