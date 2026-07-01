# Phase 4 Architecture

Phase 4 adds a **Personal Intelligence Analyst** layer on top of the Phase 3.2 acquisition corpus. Acquisition, routing, and transcript processing are unchanged — Phase 4 reads processed KnowledgeObjects and produces scored claims, cross-source clusters, morning briefs, and deep dives.

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
Morning Intelligence Brief
  ↓
Deep Dive (on demand)
```

## Components

| Module | Responsibility |
|--------|----------------|
| `analyst.pipeline.IntelligenceAnalystPipeline` | End-to-end orchestration |
| `analyst.claims.extractor.ClaimExtractor` | Atomic claims from transcripts |
| `analyst.novelty.engine.NoveltyEngine` | Semantic novelty classification |
| `analyst.relevance.engine.RelevanceEngine` | Per-profile relevance scoring |
| `analyst.contradiction.detector.ContradictionDetector` | Conflict surfacing |
| `analyst.importance.engine.ImportanceEngine` | Explainable importance ranking |
| `analyst.cross_source.engine.CrossSourceEngine` | Independent source convergence |
| `analyst.briefing.morning_brief.MorningBriefGenerator` | ~60s attention filter |
| `analyst.briefing.deep_dive.DeepDiveGenerator` | Evidence-backed deep dives |
| `analyst.store.AnalystStore` | Persistent analyst artifacts |
| `analyst.inspector.inspect_analyst_runtime` | Phase 4 diagnostics |
| `analyst.models` | Claim, ScoredClaim, MorningBrief, etc. |

## Data Models

| Model | Role |
|-------|------|
| `Claim` | Atomic timestamped assertion with provenance |
| `NoveltyResult` | Novelty score, class, prior-claim evidence |
| `RelevanceResult` | Per-profile relevance with match explanation |
| `ImportanceResult` | Weighted score, band, seven factors |
| `Contradiction` | Conflicting claim pair |
| `CorroborationCluster` | Multi-source convergence group |
| `ScoredClaim` | Claim + novelty + relevance + importance + contradictions |
| `BriefItem` | Single morning-brief entry with explainability |
| `MorningBrief` | Profile-organized briefing |
| `DeepDiveResponse` | Interactive analyst expansion |
| `PipelineResult` | Run metrics and latency breakdown |

## Orchestration Details

`IntelligenceAnalystPipeline.run()`:

1. Loads profiles and `EpisodeStatus.PROCESSED` episodes from `CorpusManager`.
2. Extracts claims from document KnowledgeObjects.
3. Deduplicates against `analyst/claims.jsonl` by `claim_id`.
4. Scores only **new** claims (not previously in store).
5. Builds cross-source clusters over **all** claims.
6. Merges new scored claims with historical scored claims.
7. Generates and persists morning brief.
8. Records run to `analyst/pipeline_runs.json`.

Optional `episode_ids` filter limits processing to specific episodes.

## Integration with Phase 3.2 Acquisition

Phase 4 does **not** redesign acquisition. It consumes:

| Phase 3.2 artifact | Phase 4 use |
|--------------------|-------------|
| Processed KnowledgeObjects | Claim extraction input |
| `transcript_segments` | Sentence-level claim atoms |
| `route_confidence` | Source credibility factor |
| `information_events.json` | Event/participant provenance on claims |
| Intelligence Profiles | Relevance and brief section organization |
| `episodes.json` | Episode metadata and processing gate |

## Persistent Storage

All artifacts under `state/analyst/`:

| File | Content |
|------|---------|
| `claims.jsonl` | Extracted claims |
| `scored_claims.jsonl` | Fully scored claims |
| `corroboration_clusters.json` | Cross-source clusters |
| `morning_briefs.json` | Brief history |
| `pipeline_runs.json` | Run log with latency |

## Explainability Invariant

No intelligence output is a black box. Every scored claim, brief item, and deep dive must carry:

- Structured factor breakdowns (importance weights)
- Natural-language explanations (novelty, relevance, importance)
- Verbatim transcript evidence with timestamped source URLs
- Explicit contradiction and corroboration counts

## Runtime Inspector

`inspect_intelligence_runtime()` (Phase 3 inspector) embeds an `analyst` section from `inspect_analyst_runtime()`. See `RUNTIME_INSPECTOR.md` and `PHASE4_RUNTIME_CERTIFICATION.md`.

## Invariants

- Only processed episodes enter the analyst pipeline
- Claim IDs are stable and deduplicated across runs
- Relevance is profile-local; importance is global with profile-relevance factor
- Repeat claims never appear in morning briefs
- Contradictions are surfaced, not suppressed
- Cross-source corroboration requires ≥ 2 independent episodes

## Entry Points

```python
from knowledge_service.analyst.pipeline import IntelligenceAnalystPipeline

pipeline = IntelligenceAnalystPipeline(state_dir)
result = pipeline.run()
deep_dive = pipeline.deep_dive(claim_id)
```

```python
IntelligenceAnalystPipeline.run_on_state(state_dir)
```