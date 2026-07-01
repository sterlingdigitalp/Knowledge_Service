# Trend Acceleration

The Trend Acceleration Engine tracks whether emergent themes are **accelerating**, **decaying**, or **forming consensus** across pipeline runs. Phase 5 surfaces top trends alongside enhanced Intelligence Items and Brief v3.

## Module

| Path | Class |
|------|-------|
| `knowledge_service.production.trends.acceleration` | `TrendAccelerationEngine` |

## Inputs

| Input | Source |
|-------|--------|
| `Theme` records | `analyst/synthesis/themes.json` |
| `ThemeEvolution` records | Current synthesis run (`pipeline_result.synthesis.theme_evolutions`) |
| Prior snapshots | `production/trend_history.jsonl` |

## Analysis Algorithm

For each current theme:

1. Load prior snapshot by `theme.label.lower()` from trend history.
2. Compute velocities:
   - `claim_velocity = len(theme.claim_ids) - prior_claim_count`
   - `source_velocity = theme.source_count - prior_source_count`
3. Classify acceleration:

| Condition | Classification |
|-----------|----------------|
| `claim_velocity >= 3` or `source_velocity >= 1` | `accelerating` |
| `claim_velocity <= -2` | `decaying` |
| Otherwise | `stable` |

4. Classify consensus:

| `source_count` | Consensus |
|----------------|-----------|
| ≥ 3 | `forming` |
| ≥ 2 | `emerging` |
| < 2 | `early` |

5. Attach `evolution_state` from matching `ThemeEvolution` when present.
6. Generate natural-language `explanation`.

Results sorted by `(claim_velocity, source_count)` descending. Top 10 returned in `ProductionResult.trends`.

## Output Record

```json
{
  "theme_id": "theme-abc",
  "label": "Frontier Model Scaling",
  "acceleration": "accelerating",
  "claim_velocity": 4,
  "source_velocity": 1,
  "consensus": "forming",
  "source_count": 3,
  "claim_count": 12,
  "evolution_state": "strengthening",
  "explanation": "Frontier Model Scaling is accelerating; consensus forming across 3 sources; ...",
  "recorded_at": "2026-06-30T12:00:00Z"
}
```

## Snapshot Persistence

`TrendAccelerationEngine.snapshot()` writes a history row after each analysis:

```json
{
  "recorded_at": "...",
  "themes": [
    {"theme_id": "...", "label": "...", "claim_count": 12, "source_count": 3}
  ],
  "trends": [ "... full trend records ..." ]
}
```

Appended to `state/production/trend_history.jsonl` via `ProductionStore.append_trend_snapshot()`.

## Pipeline Integration

`ProductionEnhancementLayer.enhance()`:

1. Loads themes and synthesis evolutions from current analyst run.
2. Loads prior trend history.
3. Calls `trends.analyze(themes, evolutions, history)`.
4. Persists snapshot; attaches top 10 to `ProductionResult.trends`.

Latency: `production.latency_seconds.trend_acceleration`.

## Runtime Inspector

`inspect_production_runtime()` exposes:

| Field | Content |
|-------|---------|
| `trends.snapshots` | Count of historical snapshots |
| `trends.latest` | Most recent snapshot |
| `production.trend_snapshots` | Same count via `ProductionStore.summary()` |

## Storage

| File | Content |
|------|---------|
| `production/trend_history.jsonl` | Append-only theme velocity snapshots |

## Entry Point

```python
from knowledge_service.production.trends.acceleration import TrendAccelerationEngine

engine = TrendAccelerationEngine()
trends = engine.analyze(themes, evolutions, history)
snapshot = engine.snapshot(themes, trends)
```

## Design Invariant

Trend acceleration is **inter-run comparative** — velocities require at least one prior snapshot. First run establishes baseline counts; subsequent runs compute deltas. Theme matching is label-based (case-insensitive), not embedding-based.