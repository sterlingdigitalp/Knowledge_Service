# Phase 4 Runtime Certification

Phase 4 certification validates the full analyst pipeline chain: claim extraction through morning brief and deep dive, integrated with Phase 3.2 acquisition corpus.

## Certifier

| Script | Purpose |
|--------|---------|
| `examples/certify_phase4_runtime.py` | End-to-end Phase 4 runtime certification |

## Pipeline Chain Validated

1. **Information Event** — seeded from Phase 3.2 certified corpus (or live acquisition fallback)
2. **Transcript** — present in processed KnowledgeObjects
3. **Claims extracted** — atomic claims from transcript segments
4. **Novelty scored** — semantic comparison against historical corpus
5. **Relevance scored** — every claim × every enabled profile
6. **Importance scored** — explainable weighted formula
7. **Cross-source correlation** — independent source clusters
8. **Morning Brief generated** — profile-organized briefing with explainability
9. **Deep dive available** — "Tell me more" for first brief item

## Acquisition Modes

The certifier supports two acquisition paths:

| Mode | Trigger | Behavior |
|------|---------|----------|
| `seeded_from_phase32` | Default prior state exists at `runtime_evidence/phase32_intelligence_20260701T011651Z/state` | Copies Phase 3.2 state; no live re-acquisition |
| `live_acquisition` | Prior state absent | Runs `RuntimeScheduler.run_scheduled_once()` |

Phase 4 certification does not redesign acquisition — it verifies analyst readiness on a valid corpus.

## Blockers

Certification fails when any blocker is present:

| Blocker | Condition |
|---------|-----------|
| Analyst status | `inspector.analyst.status != "pass"` |
| Claims extracted | `pipeline_result.claims_extracted <= 0` |
| Claims scored | `pipeline_result.claims_scored <= 0` |
| Morning brief | No brief or `total_items <= 0` |
| Deep dive | `pipeline.deep_dive()` returns `None` for first brief item |
| Processed episodes | Zero processed episodes in corpus |
| System summary | `inspector.system_summary.status != "pass"` |

## Pass Criteria

| Requirement | Inspector / result field |
|-------------|--------------------------|
| Claims persisted | `analyst.claims.total > 0` |
| Scored claims | `analyst` novelty/importance distributions populated |
| Brief generated | `analyst.briefing.latest_total_items > 0` |
| Reading time | `analyst.briefing.reading_time_seconds` in 30–90s range |
| Cross-source | `analyst.cross_source.clusters` reported |
| Latency recorded | `analyst.pipeline.latency_seconds` from latest run |

## Output Artifacts

Evidence directory: `runtime_evidence/phase4_intelligence_<timestamp>/`

| File | Content |
|------|---------|
| `PHASE4_RUNTIME_CERTIFICATION.md` | Pass/fail report |
| `RUNTIME_INSPECTOR_OUTPUT.json` | Full inspector including `analyst` section |
| `RUNTIME_INSPECTOR_OUTPUT.md` | Markdown inspector export |
| `MORNING_INTELLIGENCE_BRIEF.json` | Latest brief payload |
| `MORNING_INTELLIGENCE_BRIEF.md` | Human-readable brief |
| `raw/acquisition.json` | Acquisition mode and episode counts |
| `raw/pipeline_result.json` | Claims, clusters, latency |
| `raw/deep_dive.json` | Deep dive for first brief item |
| `raw/blockers.json` | Blocker list |

## Analyst Inspector Section

The integrated runtime inspector exposes `analyst` with:

- `status` — `pass` when claims and briefs exist
- `claims` — totals by speaker, topic, episode
- `novelty` — classification distribution and average score
- `importance` — band distribution and average score
- `relevance` — profile match counts (score ≥ 0.35)
- `cross_source` — cluster count and top clusters
- `briefing` — latest brief metadata and section counts
- `pipeline` — run count, latest run ID, latency breakdown
- `storage` — analyst artifact file paths
- `warnings` — operational alerts

## Reproduce

```bash
PYTHONPATH=src ./.venv/bin/python examples/certify_phase4_runtime.py
```

Exit code `0` = pass; `1` = blockers present. Script prints evidence directory path on completion.

## Performance Reporting

The certification report includes:

- Total elapsed time (acquisition + analyst)
- Analyst pipeline elapsed time
- Per-stage latency from `PipelineResult.latency_seconds`:
  - `claim_extraction`
  - `scoring`
  - `cross_source`
  - `brief_generation`
  - `total`

## Relationship to Phase 3.2

Phase 4 certification depends on Phase 3.2 corpus integrity:

- Seeded state from `phase32_intelligence_20260701T011651Z` when available
- `system_summary.corpus_integrity` must be `pass`
- `route_confidence` on claims derives from Phase 3.2 route registry

Re-run Phase 3.2 certification if seeded state is missing or corrupt:

```bash
PYTHONPATH=src ./.venv/bin/python examples/certify_phase32_runtime.py
```