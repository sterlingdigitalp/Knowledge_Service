# Phase 5 Architecture

Phase 5 adds a **Production Personal Intelligence Analyst** layer on top of Phase 4.1 synthesis. Acquisition (Phase 3.2), claim scoring (Phase 4), and Intelligence Item synthesis (Phase 4.1) are unchanged — Phase 5 enhances embeddings, summarization, personalization, trends, and briefing quality.

## Pipeline Flow

```text
Information Event (Phase 3.2 corpus)
  ↓
Transcript → Claims → Scoring → Cross-Source (Phase 4)
  ↓
Theme Discovery → Intelligence Items → Brief v2 (Phase 4.1)
  ↓
── Phase 5 Production Enhancement ──
  ↓
Neural Re-embedding (claims, scored claims, theme centroids)
  ↓
Analyst Summarization (LLM titles + executive summaries)
  ↓
Personalized Ranking (feedback-driven re-rank)
  ↓
Trend Acceleration (theme velocity + consensus)
  ↓
Morning Intelligence Brief v3 + Quality Evaluation
  ↓
Multi-turn Deep Dive v3 (on demand)
```

## Components

### Phase 4.1 (unchanged)

| Module | Responsibility |
|--------|----------------|
| `analyst.pipeline.IntelligenceAnalystPipeline` | End-to-end analyst + synthesis orchestration |
| `analyst.synthesis.pipeline.IntelligenceSynthesisPipeline` | Themes, items, brief v2 |
| `analyst.synthesis.store.SynthesisStore` | Synthesis artifact persistence |

### Phase 5 (new)

| Module | Responsibility |
|--------|----------------|
| `production.pipeline.ProductionIntelligencePipeline` | Phase 5 orchestration |
| `production.enhancement.ProductionEnhancementLayer` | Neural embed, LLM enhance, rank, trends, brief v3 |
| `production.embeddings.registry` | Swappable embedding backends |
| `production.llm.registry` | Swappable LLM backends |
| `production.personalization.ranking` | Feedback-driven item ranking |
| `production.personalization.feedback` | User behavior capture |
| `production.trends.acceleration` | Theme velocity tracking |
| `production.briefing.morning_brief_v3` | Brief v3 generation |
| `production.briefing.quality` | Brief self-evaluation |
| `production.conversation.deep_dive_v3` | Multi-turn analyst conversation |
| `production.scheduler.brief_scheduler` | Daily brief scheduling |
| `production.benchmark.PhaseBenchmark` | Phase 4.1 comparison metrics |
| `production.store.ProductionStore` | Phase 5 artifact persistence |
| `production.inspector.inspect_production_runtime` | Phase 5 diagnostics |

## Data Models

### Phase 5 (new)

| Model | Role |
|-------|------|
| `IntelligenceBriefV3` | Publication-quality personalized brief |
| `ProductionResult` | Enhancement run output (brief, trends, quality, providers) |
| `ProductionPipelineResult` | Analyst + production + benchmark + latency |

### Inherited from Phase 4.1

| Model | Phase 5 use |
|-------|-------------|
| `IntelligenceItem` | LLM-enhanced in place (title, summary, surfacing) |
| `IntelligenceBriefEntry` | Brief v3 row format |
| `Theme` | Centroid re-embedding, trend analysis |

## Orchestration Details

`ProductionIntelligencePipeline.run()`:

1. Invokes `IntelligenceAnalystPipeline.run()` (Phase 4 + 4.1).
2. Invokes `ProductionEnhancementLayer.enhance(analyst_result)`.
3. Benchmarks embeddings and briefs vs Phase 4.1 baseline.
4. Records scheduler run when manual or `should_run()`.
5. Returns `ProductionPipelineResult` with combined latency.

`ProductionEnhancementLayer.enhance()` stages:

| Stage | Latency key |
|-------|-------------|
| Neural re-embedding | `neural_reembedding` |
| Analyst summarization | `analyst_summarization` |
| Personalized ranking | `personalized_ranking` |
| Trend acceleration | `trend_acceleration` |
| Brief v3 generation | `brief_v3` |
| Total | `total` |

## Integration with Phase 4.1

| Upstream artifact | Phase 5 use |
|-------------------|-------------|
| `IntelligenceItem` records | LLM title/summary enhancement |
| `intelligence_brief` (v2) | Benchmark comparison baseline |
| `Theme` records | Centroid re-embed, trend velocity |
| `ThemeEvolution` | Trend explanation and state |
| `ScoredClaim` embeddings | Neural re-embedding |
| Synthesis pipeline run ID | Brief v3 `pipeline_run_id` |

## Persistent Storage

### Phase 5 (`state/production/`)

| File | Content |
|------|---------|
| `intelligence_briefs_v3.json` | Brief v3 history |
| `trend_history.jsonl` | Theme velocity snapshots |
| `benchmark_vs_phase41.json` | Embedding and brief comparison |
| `pipeline_runs.json` | Production enhancement run log |
| `feedback.jsonl` | User behavior events |
| `preferences.json` | Learned topic/profile weights |
| `conversation_sessions.json` | Deep dive v3 sessions |
| `brief_scheduler.json` | Schedule configuration |
| `brief_schedule_history.jsonl` | Scheduler run history |

## Key Thresholds

| Stage | Constant | Value |
|-------|----------|-------|
| Brief item bounds | `MIN_ITEMS` / `MAX_ITEMS` | 5 / 10 |
| Importance gate | selection | ≥ 0.62 |
| Star rating gate | selection | ≥ 3 |
| Reading time | certification | ≤ 60s |
| Quality score | certification | ≥ 0.4 |
| Tell me more boost | `TELL_ME_MORE_BOOST` | 0.12 |
| Dismiss penalty | exclusion | filtered from rank |
| Trend accelerating | `claim_velocity` | ≥ 3 or `source_velocity` ≥ 1 |

## Scheduler

`MorningBriefScheduler` supports:

| Schedule | Behavior |
|----------|----------|
| `daily` | Run once per UTC day after `hour_utc` |
| `weekdays` | Monday–Friday only |
| `manual` | Never auto-run |

## Runtime Inspector

`inspect_intelligence_runtime()` embeds `production` from `inspect_production_runtime()`:

- `phase` — `"5.0"`
- `status` — `pass` when brief exists and analyst passes
- `production` — brief counts, quality, benchmark
- `personalization` — feedback summary
- `preferences` — learned weights
- `scheduler` — config and run history
- `trends` — snapshot count and latest
- `brief_quality` — latest brief payload

See `PHASE5_RUNTIME_CERTIFICATION.md`.

## Explainability Invariant

Phase 5 extends Phase 4.1 explainability:

- LLM summaries cite convergence, corroboration, and novelty — not fabricated quotes
- Personalized surfacing prefixes `why_surfaced` with matched title
- Brief v3 entries retain full `explainability` payloads
- Deep dive v3 exposes timeline, contradictions, and watch points
- Quality metrics are structured and inspectable

## Invariants

- Phase 5 runs on every `ProductionIntelligencePipeline.run()` after synthesis
- Neural embeddings replace hash vectors on every enhancement run
- Personalized ranking filters dismissed items before brief selection
- Brief v3 enforces 5–10 items and ≤ 60s reading time
- Brief v2 and claim-level outputs remain available
- Learning loop demonstrable across two pipeline runs

## Entry Points

```python
from knowledge_service.production.pipeline import ProductionIntelligencePipeline

pipeline = ProductionIntelligencePipeline(state_dir)
result = pipeline.run()

# Phase 5 outputs
brief_v3 = result.production.intelligence_brief_v3
trends = result.production.trends
quality = result.production.quality_metrics
benchmark = result.benchmark

# Learning and conversation
pipeline.record_tell_me_more(item_id, duration_seconds=300)
second = pipeline.rerun_with_learning()
session = pipeline.start_conversation(item_id)
```

```python
ProductionIntelligencePipeline.run_on_state(state_dir)
```

## Related Documentation

| Doc | Topic |
|-----|-------|
| `NEURAL_EMBEDDINGS.md` | Embedding providers |
| `ANALYST_SUMMARIZATION.md` | LLM generation |
| `PERSONALIZATION_ENGINE.md` | Ranking engine |
| `USER_FEEDBACK_ENGINE.md` | Behavior capture |
| `TREND_ACCELERATION.md` | Theme velocity |
| `MORNING_BRIEF_V3.md` | Brief v3 format |
| `PHASE5_RUNTIME_CERTIFICATION.md` | Certification procedure |