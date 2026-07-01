# Theme Evolution

Theme Evolution tracks how emergent themes change between synthesis runs. It compares newly discovered themes against historical theme memory and classifies each theme's trajectory.

Evolution context flows into Intelligence Items (`why_surfaced`, `historical_developments`) and Deep Dive v2 (`theme_evolution`).

## Module

| Path | Class |
|------|-------|
| `knowledge_service.analyst.synthesis.themes.evolution` | `ThemeEvolutionEngine` |

## ThemeEvolution Model

| Field | Purpose |
|-------|---------|
| `theme_id` | Current theme ID |
| `label` | Current theme label |
| `state` | `ThemeEvolutionState` enum value |
| `explanation` | Natural-language evolution summary |
| `prior_theme_id` | Matched historical theme (when found) |
| `similarity_to_prior` | Centroid cosine similarity to prior |
| `claim_count_delta` | Change in member claim count |
| `source_count_delta` | Change in independent source count |
| `recorded_at` | ISO timestamp |

## ThemeEvolutionState Values

| State | Meaning |
|-------|---------|
| `new` | No prior match above threshold |
| `strengthening` | Growing claim or source footprint |
| `fading` | Declining claim count |
| `material_change` | Semantic shift with claim delta |
| `stable` | Consistent theme with minor drift |
| `contradicting` | Reserved enum value (not yet assigned by classifier) |

## Prior Match Algorithm

For each current theme, `_best_prior_match()` scans historical themes:

1. Skip already-matched prior theme IDs (one-to-one assignment).
2. Compute `cosine_similarity(current.centroid, prior.centroid)`.
3. Apply `+0.1` label boost when labels match exactly (case-insensitive).
4. Select highest combined score.
5. Accept match only when `combined ≥ PRIOR_MATCH_THRESHOLD` (0.72).

Unmatched themes receive state `new`.

## Evolution Classification

When a prior match exists, compute deltas:

```text
claim_delta  = len(current.claim_ids) - len(prior.claim_ids)
source_delta = current.source_count - prior.source_count
```

Classification priority:

| Condition | State |
|-----------|-------|
| `claim_delta ≥ STRENGTHENING_DELTA` (2) OR `source_delta ≥ 1` | `strengthening` |
| `claim_delta ≤ FADING_DELTA` (-3) | `fading` |
| `similarity < 0.80` AND `claim_delta ≠ 0` | `material_change` |
| Otherwise | `stable` |

### Example Explanations

- **new:** `'AI Regulation' is a newly emerging theme with 5 supporting claims.`
- **strengthening:** `'Longevity Research' is strengthening: +3 claims, +1 sources since last run.`
- **fading:** `'Crypto Markets' discussion is fading: -4 claims vs prior snapshot.`
- **material_change:** `'Open Source AI' has materially shifted (similarity 0.76, delta 2 claims).`
- **stable:** `'Venture Capital' remains stable with 6 claims across 4 sources.`

## History Merge

`merge_history(current, historical)` maintains theme memory:

- Start with all historical themes keyed by `theme_id`.
- Overwrite/add current run themes by ID.
- Return merged list for persistence.

Current snapshot replaces prior version of the same `theme_id`; unrelated historical themes are retained.

## Thresholds Summary

| Constant | Value |
|----------|-------|
| `PRIOR_MATCH_THRESHOLD` | 0.72 |
| `STRENGTHENING_DELTA` | +2 claims |
| `FADING_DELTA` | -3 claims |
| Material change similarity | < 0.80 |
| Label exact-match boost | +0.10 |

## Storage

| File | Content |
|------|---------|
| `state/analyst/synthesis/themes.json` | Merged current + historical theme snapshots |
| `state/analyst/synthesis/theme_history.jsonl` | Append-only evolution records per run |

## Runtime Inspector

`analyst.synthesis.theme_evolution` reports distribution counts by state for the latest theme batch.

Warnings surface when no themes exist (blocks synthesis certification).

## Pipeline Position

```text
ThemeDiscoveryEngine.discover()
  ↓
SynthesisStore.load_themes()  ← historical memory
  ↓
ThemeEvolutionEngine.evaluate(current, historical)
  ↓
ThemeEvolutionEngine.merge_history()
  ↓
save_themes() + append_theme_history()
  ↓
IntelligenceItemEngine (evolution → why_surfaced)
```

## Design Invariant

Theme evolution is **descriptive, not prescriptive**. States explain trajectory; they do not suppress or promote items. A `fading` theme can still produce a high-importance Intelligence Item if claims remain above thresholds.

## Entry Point

```python
from knowledge_service.analyst.synthesis.themes.evolution import ThemeEvolutionEngine

engine = ThemeEvolutionEngine()
evolutions = engine.evaluate(current_themes, historical_themes)
merged = engine.merge_history(current_themes, historical_themes)
```