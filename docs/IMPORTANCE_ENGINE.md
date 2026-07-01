# Importance Engine

The Importance Engine produces an explainable, weighted ranking score for each claim. Importance determines briefing priority and Deep Dive emphasis — it is not a black-box relevance proxy.

## Module

| Path | Class |
|------|-------|
| `knowledge_service.analyst.importance.engine` | `ImportanceEngine` |

## Weighted Formula

Seven factors combine with fixed weights:

| Factor | Weight | Source |
|--------|--------|--------|
| `novelty` | 0.28 | `NoveltyResult` (repeat → 0.1; contradiction floors at 0.75) |
| `source_credibility` | 0.12 | `claim.route_confidence` or default 0.65 |
| `corroboration` | 0.18 | Cross-source cluster count (applied in second pass) |
| `potential_impact` | 0.12 | Entities, novelty class, claim length |
| `profile_relevance` | 0.18 | `max(relevance.score)` across profiles |
| `freshness` | 0.07 | `published_at` age decay |
| `evidence_quality` | 0.05 | Claim confidence + timestamp + reference URL |

```text
score = Σ (factor × weight), capped at 1.0
```

## Factor Details

### Source Credibility

Uses Phase 3.2 `route_confidence` from acquisition when available. This ties importance to certified route quality without re-evaluating acquisition.

### Corroboration

```text
corroboration_factor = 0.0                    if count == 0
corroboration_factor = min(1.0, 0.35 + count × 0.2)   otherwise
```

Applied after `CrossSourceEngine.apply_corroboration()`; importance is re-scored when `corroboration_count > 0`.

### Potential Impact

Base 0.35, plus:

- +0.20 if claim has entities
- +0.25 if novelty is `new`, `update`, or `contradiction`
- +0.10 if claim text exceeds 120 characters

### Freshness

| Age (days) | Factor |
|------------|--------|
| ≤ 2 | 1.0 |
| ≤ 7 | 0.8 |
| ≤ 30 | 0.55 |
| > 30 | 0.3 |
| Missing/unparseable | 0.5 |

### Evidence Quality

```text
quality = claim.confidence
        + 0.15 if timestamp_start present
        + 0.05 if transcript_reference present
```

## Importance Bands

| Band | Score range |
|------|-------------|
| `very_high` | ≥ 0.82 |
| `high` | ≥ 0.65 |
| `medium` | ≥ 0.45 |
| `low` | ≥ 0.25 |
| `ignore` | < 0.25 |

## Output Model

`ImportanceResult`:

| Field | Purpose |
|-------|---------|
| `score` | Weighted 0.0–1.0 |
| `band` | `ImportanceBand` enum |
| `factors` | `ImportanceFactors` — all seven normalized inputs |
| `explanation` | Factor breakdown string |

## Explainability Requirements

Every importance result must expose:

1. Final band and score in `explanation`
2. All seven factor values in `factors.to_dict()`
3. Deterministic weight constants (`WEIGHTS` dict) for audit replay

Brief items embed `importance_factors` in `explainability`. Deep Dive includes full `importance.to_dict()`.

## Morning Brief Filters

| Filter | Value |
|--------|-------|
| `MIN_IMPORTANCE` | 0.35 |
| Excluded bands | `ignore` |

## Two-Pass Scoring

The pipeline scores importance twice for new claims:

1. **Initial pass** — corroboration_count = 0 during per-claim scoring loop
2. **Post-cluster pass** — re-score when cross-source corroboration is assigned

This ensures corroboration boosts are applied without blocking the scoring pipeline.