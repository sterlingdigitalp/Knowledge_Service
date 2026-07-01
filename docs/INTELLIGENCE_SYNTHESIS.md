# Intelligence Synthesis

Intelligence Synthesis is the Phase 4.1 layer that transforms scored claims into idea-centric developments. It sits atop Phase 4 claim scoring and cross-source clustering, producing themes, Intelligence Items, Morning Brief v2, and Deep Dive v2.

## Package Layout

```text
src/knowledge_service/analyst/synthesis/
├── __init__.py
├── models.py              # Theme, IntelligenceItem, IntelligenceBrief, etc.
├── pipeline.py            # IntelligenceSynthesisPipeline
├── store.py               # SynthesisStore
├── themes/
│   ├── discovery.py       # ThemeDiscoveryEngine
│   └── evolution.py       # ThemeEvolutionEngine
├── items/
│   └── engine.py          # IntelligenceItemEngine
└── briefing/
    ├── morning_brief_v2.py   # IntelligenceBriefGenerator
    └── deep_dive_v2.py       # IntelligenceDeepDiveGenerator
```

## Pipeline Flow

```text
Scored Claims + Corroboration Clusters (Phase 4 output)
  ↓
Theme Discovery
  ↓
Theme Evolution (vs historical memory)
  ↓
Intelligence Item Synthesis
  ↓
Morning Intelligence Brief v2
  ↓
Deep Dive v2 (on demand)
```

## Orchestration

`IntelligenceSynthesisPipeline.run()`:

| Step | Engine | Persist |
|------|--------|---------|
| 1. Discover themes | `ThemeDiscoveryEngine` | — |
| 2. Evaluate evolution | `ThemeEvolutionEngine` | `themes.json`, `theme_history.jsonl` |
| 3. Synthesize items | `IntelligenceItemEngine` | `intelligence_items.json` |
| 4. Generate brief | `IntelligenceBriefGenerator` | `intelligence_briefs.json` |
| 5. Record run | — | `pipeline_runs.json` |

### SynthesisResult

| Field | Purpose |
|-------|---------|
| `run_id` | Stable synthesis run identifier |
| `themes_discovered` | Theme count from current run |
| `intelligence_items` | Item count emitted |
| `brief` | `IntelligenceBrief` v2 payload |
| `compression_ratio` | `claims_synthesized / brief_items` |
| `claims_synthesized` | Input claim count |
| `theme_evolutions` | Evolution records for current themes |
| `latency_seconds` | Per-stage timing |
| `status` | `"completed"` |

### Latency Stages

| Key | Stage |
|-----|-------|
| `theme_discovery` | Discovery + evolution + persist |
| `item_synthesis` | Intelligence item build |
| `brief_generation` | Brief v2 assembly |
| `total` | End-to-end synthesis |

## Integration with IntelligenceAnalystPipeline

Phase 4 orchestrator invokes synthesis after claim-level briefing:

```text
Claim Extraction → Scoring → Cross-Source → Claim Brief (v1)
  ↓
IntelligenceSynthesisPipeline.run(merged_scored, clusters)
  ↓
intelligence_brief on PipelineResult
```

`IntelligenceAnalystPipeline` exposes:

| Method | Returns |
|--------|---------|
| `run()` | `PipelineResult` with `synthesis` and `intelligence_brief` |
| `intelligence_deep_dive(item_id)` | `IntelligenceDeepDive` |
| `deep_dive(claim_id)` | Phase 4 claim-level `DeepDiveResponse` (unchanged) |

Both brief generations run each pipeline execution — claim brief (v1) for backward compatibility, intelligence brief (v2) as the primary Phase 4.1 output.

## Compression Target

Phase 4.1 certification requires **≥ 10:1** compression:

```text
compression_ratio = claims_synthesized / intelligence_brief_items
```

Inspector and `SynthesisStore.summary()` also report `claims_per_item` (average claims merged per Intelligence Item).

## Data Model Summary

| Model | Role |
|-------|------|
| `Theme` | Emergent claim cluster with centroid |
| `ThemeEvolution` | Inter-run theme trajectory |
| `IntelligenceItem` | Synthesized development |
| `IntelligenceBriefEntry` | Single brief v2 row |
| `IntelligenceBrief` | Full brief v2 document |
| `IntelligenceDeepDive` | Item-level analyst expansion |
| `SynthesisResult` | Run metrics and artifacts |

See dedicated docs: `THEME_DISCOVERY.md`, `THEME_EVOLUTION.md`, `INTELLIGENCE_ITEMS.md`, `MORNING_INTELLIGENCE_BRIEF_V2.md`.

## Persistent Storage

All artifacts under `state/analyst/synthesis/`:

| File | Content |
|------|---------|
| `themes.json` | Merged theme snapshots |
| `theme_history.jsonl` | Evolution audit trail |
| `intelligence_items.json` | Latest synthesized items |
| `intelligence_briefs.json` | Brief v2 history |
| `pipeline_runs.json` | Synthesis run log |

Phase 4 claim artifacts remain under `state/analyst/` (claims, scored claims, clusters, morning_briefs).

## Explainability Invariant

Synthesis preserves Phase 4 explainability and extends it to developments:

- Every item links to supporting claim IDs and timestamped citations
- Corroboration and contradiction counts are explicit
- Theme evolution explanations appear in surfacing rationale
- Brief v2 entries carry structured `explainability` payloads
- Deep Dive v2 exposes full item and claim-level factor breakdowns

## Runtime Inspector

`inspect_analyst_runtime()` (Phase 4.1) adds `analyst.synthesis`:

- Theme and item counts
- Compression ratio and claims per item
- Theme labels and item titles (top 10)
- Evolution state distribution
- Evidence and corroboration totals

Briefing section reports v2 metadata: `version`, `reading_time_seconds`, `compression_ratio`.

## Entry Points

```python
from knowledge_service.analyst.synthesis import IntelligenceSynthesisPipeline

pipeline = IntelligenceSynthesisPipeline(state_dir)
result = pipeline.run(scored_claims, clusters, pipeline_run_id="...")
deep_dive = pipeline.deep_dive(item_id, scored_claims, all_claims)
```

```python
from knowledge_service.analyst.pipeline import IntelligenceAnalystPipeline

pipeline = IntelligenceAnalystPipeline(state_dir)
result = pipeline.run()
brief_v2 = result.intelligence_brief
deep_dive = pipeline.intelligence_deep_dive(brief_v2.items[0].intelligence_item_id)
```