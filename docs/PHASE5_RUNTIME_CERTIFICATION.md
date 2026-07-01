# Phase 5 Runtime Certification

Phase 5 certification validates the full production pipeline chain: Phase 4.1 synthesis through neural embeddings, analyst summarization, personalized ranking, trend acceleration, Morning Brief v3, learning loop, and multi-turn deep dive — integrated with Phase 3.2 acquisition corpus.

## Certifier

| Script | Purpose |
|--------|---------|
| `examples/certify_phase5_runtime.py` | End-to-end Phase 5 runtime certification |

## Pipeline Chain Validated

1. **Corpus seeded** — Phase 3.2 certified state copied
2. **First pipeline run** — `ProductionIntelligencePipeline.run(manual=True)`
3. **Brief v3 generated** — 5–10 items, quality-scored
4. **Learning loop simulated** — tell me more, save, dismiss, brief view
5. **Second pipeline run** — `rerun_with_learning()` with adapted ranking
6. **Multi-turn conversation** — `start_conversation()` + `continue_conversation("Show me the timeline")`
7. **Inspector pass** — `production.status == "pass"`

## Acquisition Mode

| Mode | Trigger | Behavior |
|------|---------|----------|
| `seeded_from_phase32` | Default prior state at `runtime_evidence/phase32_intelligence_20260701T011651Z/state` | Copies Phase 3.2 state; profiles saved to evidence `config/` |

Phase 5 certification does not redesign acquisition — it verifies production readiness on a valid processed corpus.

## Certification Procedure

`certify_phase5_runtime.py` executes:

```text
1. Create evidence directory  →  runtime_evidence/phase5_intelligence_<timestamp>/
2. Seed corpus from Phase 3.2 state + certification profiles
3. First run: ProductionIntelligencePipeline.run(manual=True)
4. Simulate learning loop (_simulate_learning_loop)
5. Second run: pipeline.rerun_with_learning()
6. Start conversation on first brief item
7. Continue conversation with "Show me the timeline"
8. inspect_intelligence_runtime(state_dir)
9. Evaluate blockers
10. Write artifacts (report, inspector, brief, benchmark, raw JSON)
```

### Learning Loop Simulation

| Step | Action |
|------|--------|
| Tell me more | Lead item, `duration_seconds=420` |
| Save | Lead item |
| Dismiss | Third item (when ≥ 3 items) |
| Brief view | 52 seconds, all items viewed |

### Conversation Demonstration

When brief v3 has items:

```python
session = pipeline.start_conversation(brief.items[0].intelligence_item_id)
follow_up = pipeline.continue_conversation(session["session_id"], "Show me the timeline")
```

Stored in `raw/conversation.json` as `{"start": ..., "follow_up": ...}`.

## Blockers

Certification fails when any blocker is present:

| Blocker | Condition |
|---------|-----------|
| Production status | `inspector.production.status != "pass"` |
| Brief minimum | No brief or `total_items < 5` |
| Brief maximum | `total_items > 10` |
| Reading time | `reading_time_seconds > 60` |
| Multi-turn deep dive | `conversation` is `None` |
| Learning loop | `learning.events` empty |
| Neural embeddings | `production.embedding_provider == "hash"` |
| Quality score | `quality_metrics.overall_score < 0.4` |
| Processed episodes | `acquisition.processed_episodes <= 0` |
| Personalized ranking | Boosted item not promoted to lead on second run |

## Pass Criteria

| Requirement | Inspector / result field |
|-------------|--------------------------|
| Production pass | `inspector.production.status == "pass"` |
| Brief generated | `production.intelligence_brief_v3` with 5–10 items |
| Brief version | `version == "3.0"` |
| Reading time | `reading_time_seconds ≤ 60` |
| Quality score | `quality_metrics.overall_score ≥ 0.4` |
| Neural embeddings | `embedding_provider != "hash"` |
| Learning demonstrated | Second run after feedback simulation |
| Ranking adapted | Boosted item leads second brief (or was already lead) |
| Conversation | Multi-turn session with timeline follow-up |
| Benchmark recorded | `BENCHMARK_VS_PHASE41.json` present |
| Latency recorded | `latency_seconds` on both pipeline results |

## Benchmark Metrics

`BENCHMARK_VS_PHASE41.json` includes:

| Metric | Source |
|--------|--------|
| Neural embedding delta | `improvement_delta` |
| Hash vs neural similarity | `hash_similarity_avg`, `neural_similarity_avg` |
| Title quality improved | `brief.title_quality_improved` |
| Phase 5 compression | `brief.phase5_compression` |
| Phase 5 quality score | `brief.phase5_quality_score` |

## Output Artifacts

Evidence directory: `runtime_evidence/phase5_intelligence_<timestamp>/`

| File | Content |
|------|---------|
| `PHASE5_RUNTIME_CERTIFICATION.md` | Pass/fail report |
| `RUNTIME_INSPECTOR_OUTPUT.json` | Full inspector including `production` |
| `RUNTIME_INSPECTOR_OUTPUT.md` | Markdown inspector export |
| `MORNING_INTELLIGENCE_BRIEF.json` | Latest brief v3 payload |
| `MORNING_INTELLIGENCE_BRIEF.md` | Human-readable brief v3 |
| `BENCHMARK_VS_PHASE41.json` | Embedding and brief comparison |
| `raw/acquisition.json` | Acquisition mode and episode counts |
| `raw/first_pipeline_result.json` | First run metrics |
| `raw/second_pipeline_result.json` | Learning-adapted run metrics |
| `raw/learning_loop.json` | Simulated feedback events |
| `raw/conversation.json` | Multi-turn deep dive session |
| `raw/blockers.json` | Blocker list |

## Production Inspector Section

`inspect_production_runtime()` exposes:

- `phase` — `"5.0"`
- `status` — `pass` when brief exists, analyst passes, item count and reading time in bounds
- `analyst` — full Phase 4.1 analyst section
- `production` — brief counts, quality score, benchmark, trend snapshots
- `personalization` — event counts and learned weights
- `preferences` — `topic_weights`, `profile_weights`
- `scheduler` — config, history, `should_run_now`
- `trends` — snapshot count and latest velocity data
- `brief_quality` — latest brief v3 dict
- `warnings` — operational alerts

## Reproduce

```bash
PYTHONPATH=src ./.venv/bin/python examples/certify_phase5_runtime.py
```

Exit code `0` = pass; `1` = blockers present. Script prints evidence directory path on completion.

## Performance Reporting

The certification report includes:

- Total elapsed time (seed + two pipeline runs + conversation)
- First run elapsed time
- Second run elapsed time (learning-adapted)
- Quality metrics (items, reading time, quality score, providers)
- Benchmark vs Phase 4.1 (embedding delta, compression, title improvement)

## Certification Report Format

Generated `PHASE5_RUNTIME_CERTIFICATION.md` sections:

1. **Status** — PASS or FAIL
2. **Learning Loop** — five-step validation summary
3. **Quality** — items, reading time, quality score, providers
4. **Benchmark vs Phase 4.1** — embedding delta, title quality, compression
5. **Performance** — total, first run, second run elapsed
6. **Blockers** — failure reasons or "None"

## Relationship to Phase 4.1

Phase 5 extends Phase 4.1 certification:

| Phase 4.1 validates | Phase 5 adds |
|---------------------|--------------|
| Theme discovery and items | Neural re-embedding |
| Brief v2 (5–15 items) | Brief v3 (5–10 items) |
| Deep dive v2 (single-shot) | Deep dive v3 (multi-turn) |
| Compression ≥ 10:1 | Quality score ≥ 0.4 |
| — | Personalized ranking + learning loop |
| — | Trend acceleration |
| — | Benchmark vs Phase 4.1 |

Phase 4.1 certifier: `examples/certify_phase41_runtime.py`

Both brief generations occur during pipeline execution. Phase 5 certification gates on `intelligence_brief_v3`, not brief v2.

## Relationship to Phase 3.2

Phase 5 certification depends on Phase 3.2 corpus integrity:

- Seeded state from `phase32_intelligence_20260701T011651Z` when available
- Processed episodes required for claim extraction input

Re-run Phase 3.2 certification if seeded state is missing or corrupt:

```bash
PYTHONPATH=src ./.venv/bin/python examples/certify_phase32_runtime.py
```