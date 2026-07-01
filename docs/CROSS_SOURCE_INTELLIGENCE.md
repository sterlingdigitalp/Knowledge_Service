# Cross-Source Intelligence

Cross-Source Intelligence detects when multiple independent sources converge on the same topic — a signal distinct from single-source novelty or profile relevance.

## Module

| Path | Class |
|------|-------|
| `knowledge_service.analyst.cross_source.engine` | `CrossSourceEngine` |

## Clustering Algorithm

1. Iterate all claims in store order.
2. Assign each claim to the first cluster whose representative embedding exceeds `CLUSTER_THRESHOLD` (0.58 cosine similarity), or start a new cluster.
3. Representative embedding is always the first member of each cluster.
4. Emit `CorroborationCluster` only when **≥ 2 independent episodes** (`episode_id`) participate.

Clusters with a single episode are discarded — same-source repetition is not corroboration.

## CorroborationCluster Model

| Field | Purpose |
|-------|---------|
| `cluster_id` | Stable ID from topic label and source IDs |
| `topic_label` | Dominant topic, entity, or truncated claim text |
| `claim_ids` | All member claims |
| `source_ids` | Distinct acquisition sources |
| `speakers` | Distinct speakers in cluster |
| `corroboration_count` | `independent_sources - 1` |
| `confidence` | `min(1.0, 0.45 + corroboration_count × 0.18)` |
| `explanation` | Human-readable convergence summary |

## Topic Label Resolution

Priority order:

1. Most frequent non-`general` topic among members
2. Most frequent entity across members
3. First 60 characters of representative claim text

## Apply Corroboration

`apply_corroboration(scored_claims, clusters)` maps cluster membership back to `ScoredClaim`:

- Sets `corroboration_cluster_id`
- Sets `corroboration_count`
- Triggers Importance Engine re-score in pipeline

## Relationship to Contradiction Detection

| Signal | Engine | Meaning |
|--------|--------|---------|
| Convergence | Cross-Source | Multiple sources agree on topic |
| Conflict | Contradiction Detector | Semantically related claims with opposing positions |

Contradictions are never hidden by corroboration. A claim may be both corroborated on topic and flagged as contradictory on position.

## Explainability Requirements

Every cluster must include:

- Named independent sources and speakers
- `corroboration_count` with deterministic derivation (`independent_sources - 1`)
- `confidence` formula exposed in documentation and inspector output

Brief items surface corroboration as `corroborated_by` count. Deep Dive lists `corroborating_evidence` (related claims from different sources with similarity ≥ 0.55).

## Storage

Clusters persist to `state/analyst/corroboration_clusters.json`.

## Runtime Inspector

The `analyst.cross_source` section reports:

- Total cluster count
- Top 5 clusters with full `to_dict()` payloads

## Thresholds Summary

| Constant | Value |
|----------|-------|
| `CLUSTER_THRESHOLD` | 0.58 |
| Deep Dive corroboration similarity | ≥ 0.55 |
| Deep Dive related-claim similarity | ≥ 0.45 |