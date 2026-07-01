# Novelty Engine

The Novelty Engine scores each claim against the historical claim corpus to classify what is genuinely new versus repeated, refined, updated, or contradictory.

## Module

| Path | Class |
|------|-------|
| `knowledge_service.analyst.novelty.engine` | `NoveltyEngine` |

## Classification

| `NoveltyClass` | Meaning |
|----------------|---------|
| `new` | No close semantic match in historical corpus |
| `refinement` | Related prior claim; this adds or refines detail |
| `update` | Refinement with temporal update markers |
| `repeat` | Highly similar claim already recorded |
| `contradiction` | Semantically related claim with opposing position |

## Thresholds

| Constant | Value | Role |
|----------|-------|------|
| `REPEAT_THRESHOLD` | 0.82 | Cosine similarity at or above → `repeat` |
| `REFINEMENT_THRESHOLD` | 0.62 | Minimum similarity to consider a prior match |
| `CONTRADICTION_TOPIC_THRESHOLD` | 0.55 | Minimum similarity for contradiction detection |

## Algorithm

1. Ensure claim embedding exists (`embed_text` if absent).
2. Compare against all historical claims **excluding same-episode claims** (intra-episode repetition is not novelty signal).
3. Select best-match prior by highest cosine similarity.
4. Apply classification rules in order:
   - Below `REFINEMENT_THRESHOLD` → `new` (score 1.0)
   - At or above `REFINEMENT_THRESHOLD` with negation conflict → `contradiction` (score 0.85)
   - At or above `REPEAT_THRESHOLD` without contradiction → `repeat` (score 0.15)
   - Otherwise → `refinement` or `update` (score `1.0 - similarity + 0.35`, capped at 1.0)

## Contradiction Heuristics

`_has_contradiction()` checks:

- Paired negation terms (`will`/`won't`, `increase`/`decrease`, `bullish`/`bearish`, etc.)
- Asymmetric `not` presence with ≥ 4 shared tokens between claim texts

## Update Detection

`_looks_like_update()` scans for markers: `now`, `updated`, `revised`, `changed`, `instead`, `no longer`, `recently`, `latest`. Update classification floors novelty score at 0.7.

## Output Model

`NoveltyResult` fields:

| Field | Purpose |
|-------|---------|
| `score` | 0.0–1.0 novelty magnitude |
| `classification` | `NoveltyClass` enum value |
| `explanation` | Human-readable rationale |
| `evidence` | Structured prior-claim references |
| `prior_claim_id` | Best-match historical claim |
| `prior_similarity` | Cosine similarity to prior |

## Explainability Requirements

Every novelty result must:

- State classification and numeric score
- Name the prior speaker and source when a match exists
- Include `evidence` with `type`, `claim_id`, and `similarity`
- Never suppress contradictions — they surface as first-class `contradiction` class

## Downstream Effects

- **Importance Engine** — repeat claims receive novelty factor 0.1; contradictions floor at 0.75
- **Contradiction Detector** — materializes `Contradiction` records when classification is `contradiction`
- **Morning Brief** — `repeat` claims are excluded from briefing sections

## Batch Scoring

`score_batch()` scores a list incrementally, appending non-repeat claims to the working corpus so within-batch novelty is preserved.