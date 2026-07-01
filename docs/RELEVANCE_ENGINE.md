# Relevance Engine

The Relevance Engine evaluates **every claim against every enabled Intelligence Profile**. A claim may be globally interesting but irrelevant to a specific profile; relevance is profile-local, not universal.

## Module

| Path | Class |
|------|-------|
| `knowledge_service.analyst.relevance.engine` | `RelevanceEngine` |

## Inputs

| Input | Role |
|-------|------|
| `Claim` | Text, topic, entities, participants, embedding, profile origin |
| `IntelligenceProfile` | Interests, watch list, enabled state |

## Matching Signals

For each enabled profile, the engine builds a haystack:

```text
claim_text + topic + entities + supporting_context  (lowercased)
```

Three explicit match channels:

1. **Interest keyword match** — profile interest substring in haystack
2. **Participant match** — watch-list entry matches haystack text or claim `participants`
3. **Semantic interest match** — cosine similarity between claim embedding and each interest phrase

## Score Formula

```text
interest_score      = min(1.0, matched_interests × 0.22)
participant_score   = min(1.0, matched_participants × 0.28)
semantic_score      = max(cosine_similarity(claim, interest) for interest in profile.interests)
profile_origin_boost = 0.15 if claim.profile_id == profile.profile_id else 0.0

score = min(1.0, interest_score + participant_score + semantic_score × 0.35 + profile_origin_boost)
```

Results are sorted descending by score.

## Output Model

`RelevanceResult` per profile:

| Field | Purpose |
|-------|---------|
| `profile_id`, `profile_name` | Target profile |
| `score` | 0.0–1.0 relevance |
| `matched_interests` | Interest strings that matched |
| `matched_participants` | Watch-list names that matched |
| `matched_topics` | Claim topic when it aligns with profile interests |
| `explanation` | Semicolon-joined match rationale |

## Explainability Requirements

Every relevance result must explain **why** the claim appears for a profile:

- List matched interests when present
- List matched watch-list participants when present
- Note profile-origin collection boost when applicable
- State `"No strong profile signal detected"` when score derives only from weak semantic overlap

Explanations propagate to:

- `BriefItem.why_you_see_this`
- `DeepDiveResponse.explainability.relevance`
- Runtime inspector `relevance.profile_matches` (counts where score ≥ 0.35)

## Downstream Thresholds

| Consumer | Threshold | Effect |
|----------|-----------|--------|
| Importance Engine | Uses `max(relevance.score)` | `profile_relevance` factor |
| Morning Brief | `MIN_RELEVANCE = 0.2` | Claim excluded from profile section |
| Runtime Inspector | `0.35` | Counted as profile match |

## Design Invariant

Relevance is computed independently per profile. A single claim may score highly for "Investing" and poorly for "Longevity" in the same pipeline run. The Morning Brief selects the best claims **per profile section**, not globally.