# Phase 4.1 Architecture

Phase 4.1 adds an **Intelligence Synthesis** layer on top of Phase 4 claim scoring. Acquisition (Phase 3.2) and claim-level analyst engines are unchanged — Phase 4.1 reads merged `ScoredClaim` records and produces themes, Intelligence Items, Morning Brief v2, and Deep Dive v2.

## Pipeline Flow

```text
Information Event (Phase 3.2 corpus)
  ↓
Transcript (KnowledgeObject with transcript_segments)
  ↓
Claim Extraction
  ↓
Novelty Scoring
  ↓
Relevance Scoring (every claim × every profile)
  ↓
Contradiction Detection
  ↓
Importance Scoring (explainable weighted formula)
  ↓
Cross-Source Clustering + Corroboration
  ↓
Importance Re-score (with corroboration)
  ↓
Morning Intelligence Brief v1 (claim-level, backward compatible)
  ↓
── Phase 4.1 Synthesis ──
  ↓
Theme Discovery
  ↓
Theme Evolution
  ↓
Intelligence Item Synthesis
  ↓
Morning Intelligence Brief v2
  ↓
Deep Dive v2 (on demand)
```

## Components

### Phase 4 (unchanged)

| Module | Responsibility |
|--------|----------------|
| `analyst.pipeline.IntelligenceAnalystPipeline` | End-to-end orchestration |
| `analyst.claims.extractor.ClaimExtractor` | Atomic claims from transcripts |
| `analyst.novelty.engine.NoveltyEngine` | Semantic novelty classification |
| `analyst.relevance.engine.RelevanceEngine` | Per-profile relevance scoring |
| `analyst.contradiction.detector.ContradictionDetector` | Conflict surfacing |
| `analyst.importance.engine.ImportanceEngine` | Explainable importance ranking |
| `analyst.cross_source.engine.CrossSourceEngine` | Independent source convergence |
| `analyst.briefing.morning_brief.MorningBriefGenerator` | Claim-level brief (v1) |
| `analyst.briefing.deep_dive.DeepDiveGenerator` | Claim-level deep dive |
| `analyst.store.AnalystStore` | Phase 4 persistent artifacts |

### Phase 4.1 (new)

| Module | Responsibility |
|--------|----------------|
| `analyst.synthesis.pipeline.IntelligenceSynthesisPipeline` | Synthesis orchestration |
| `analyst.synthesis.themes.discovery.ThemeDiscoveryEngine` | Emergent theme clustering |
| `analyst.synthesis.themes.evolution.ThemeEvolutionEngine` | Inter-run theme tracking |
| `analyst.synthesis.items.engine.IntelligenceItemEngine` | Claim → development synthesis |
| `analyst.synthesis.briefing.morning_brief_v2.IntelligenceBriefGenerator` | Brief v2 assembly |
| `analyst.synthesis.briefing.deep_dive_v2.IntelligenceDeepDiveGenerator` | Item-level deep dive |
| `analyst.synthesis.store.SynthesisStore` | Synthesis artifact persistence |
| `analyst.synthesis.models` | Theme, IntelligenceItem, IntelligenceBrief, etc. |
| `analyst.inspector.inspect_analyst_runtime` | Phase 4.1 diagnostics |

## Data Models

### Phase 4 (existing)

| Model | Role |
|-------|------|
| `Claim` | Atomic timestamped assertion |
| `ScoredClaim` | Claim + novelty + relevance + importance + contradictions |
| `CorroborationCluster` | Multi-source convergence group |
| `MorningBrief` | Profile-organized claim brief (v1) |
| `DeepDiveResponse` | Claim-level expansion |

### Phase 4.1 (new)

| Model | Role |
|-------|------|
| `Theme` | Emergent claim cluster with centroid embedding |
| `ThemeEvolution` | Theme trajectory between runs |
| `IntelligenceItem` | Synthesized development |
| `IntelligenceBriefEntry` | Single brief v2 row |
| `IntelligenceBrief` | Flat ranked brief v2 |
| `IntelligenceDeepDive` | Item-level analyst expansion |
| `SynthesisResult` | Synthesis run metrics |

## Orchestration Details

`IntelligenceAnalystPipeline.run()` after Phase 4 scoring:

1. Merges new scored claims with historical scored claims.
2. Generates claim-level brief v1 (unchanged).
3. Invokes `IntelligenceSynthesisPipeline.run(merged_scored, clusters)`.
4. Attaches `synthesis` and `intelligence_brief` to `PipelineResult`.
5. Records combined run to `analyst/pipeline_runs.json`.

`IntelligenceSynthesisPipeline.run()`:

1. Discovers themes from merged scored claims.
2. Loads historical themes; evaluates evolution.
3. Merges and persists theme snapshots + evolution history.
4. Synthesizes Intelligence Items from themes, clusters, evolutions.
5. Generates and persists Intelligence Brief v2.
6. Records synthesis run to `analyst/synthesis/pipeline_runs.json`.

## Integration with Phase 3.2 Acquisition

Phase 4.1 does **not** redesign acquisition. It consumes Phase 4 outputs:

| Upstream artifact | Phase 4.1 use |
|-------------------|---------------|
| `ScoredClaim` records | Theme discovery and item synthesis input |
| `CorroborationCluster` | Cluster-based items and corroboration counts |
| Intelligence Profiles | Item profile association (relevance ≥ 0.35) |
| Claim embeddings | Theme clustering and evolution matching |

## Persistent Storage

### Phase 4 (`state/analyst/`)

| File | Content |
|------|---------|
| `claims.jsonl` | Extracted claims |
| `scored_claims.jsonl` | Fully scored claims |
| `corroboration_clusters.json` | Cross-source clusters |
| `morning_briefs.json` | Claim brief v1 history |
| `pipeline_runs.json` | Analyst run log |

### Phase 4.1 (`state/analyst/synthesis/`)

| File | Content |
|------|---------|
| `themes.json` | Merged theme snapshots |
| `theme_history.jsonl` | Evolution audit trail |
| `intelligence_items.json` | Synthesized items |
| `intelligence_briefs.json` | Brief v2 history |
| `pipeline_runs.json` | Synthesis run log |

## Key Thresholds

| Stage | Constant | Value |
|-------|----------|-------|
| Theme candidate gate | importance score | ≥ 0.35 |
| Theme clustering | `THEME_CLUSTER_THRESHOLD` | 0.50 |
| Theme minimum size | `MIN_THEME_CLAIMS` | 3 |
| Prior theme match | `PRIOR_MATCH_THRESHOLD` | 0.72 |
| Item minimum importance | `MIN_ITEM_IMPORTANCE` | 0.55 |
| Brief item bounds | `MIN_ITEMS` / `MAX_ITEMS` | 5 / 15 |
| Compression target | certification | ≥ 10:1 |
| Reading time target | certification | ≤ 60s |

## Explainability Invariant

Phase 4.1 extends Phase 4 explainability to developments:

- Intelligence Items link to supporting claim IDs and timestamped citations
- Theme evolution explanations appear in surfacing rationale
- Corroboration and contradiction counts remain explicit
- Brief v2 entries carry structured explainability payloads
- Deep Dive v2 exposes item-level and per-claim factor breakdowns

## Runtime Inspector

`inspect_analyst_runtime()` reports Phase `4.1` with:

- `synthesis` — themes, items, compression, evolution distribution
- `briefing` — v2 item count, reading time, version
- `pipeline.synthesis_latency_seconds` — per-stage synthesis timing

See `PHASE41_RUNTIME_CERTIFICATION.md`.

## Invariants

- Synthesis runs on every analyst pipeline execution
- Themes are emergent — no hardcoded taxonomy
- Intelligence Items require minimum claim and importance thresholds
- Brief v2 enforces 5–15 items and ~60s reading time
- Claim-level brief v1 and deep dive remain available
- Compression ratio must meet ≥ 10:1 certification target

## Entry Points

```python
from knowledge_service.analyst.pipeline import IntelligenceAnalystPipeline

pipeline = IntelligenceAnalystPipeline(state_dir)
result = pipeline.run()

# Phase 4.1 outputs
brief_v2 = result.intelligence_brief
synthesis = result.synthesis
deep_dive = pipeline.intelligence_deep_dive(brief_v2.items[0].intelligence_item_id)

# Phase 4 outputs (unchanged)
claim_brief = result.brief
claim_deep_dive = pipeline.deep_dive(claim_id)
```

```python
from knowledge_service.analyst.synthesis import IntelligenceSynthesisPipeline

synthesis = IntelligenceSynthesisPipeline(state_dir)
result = synthesis.run(scored_claims, clusters)
```