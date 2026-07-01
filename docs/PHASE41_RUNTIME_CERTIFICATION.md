# Phase 4.1 Runtime Certification

Phase 4.1 certification validates the full synthesis pipeline chain: scored claims through theme discovery, Intelligence Item synthesis, Morning Brief v2, and Deep Dive v2 — integrated with Phase 3.2 acquisition corpus.

## Certifier

| Script | Purpose |
|--------|---------|
| `examples/certify_phase41_runtime.py` | End-to-end Phase 4.1 runtime certification |

## Pipeline Chain Validated

1. **Information Event** — seeded from Phase 3.2 certified corpus
2. **Claims extracted** — atomic claims from transcript segments (Phase 4)
3. **Themes discovered** — emergent clustering from scored claims
4. **Intelligence Items synthesized** — claim merges into developments
5. **Morning Brief v2 generated** — 5–15 item development brief
6. **Deep dive available** — `intelligence_deep_dive()` for first brief item

## Acquisition Mode

| Mode | Trigger | Behavior |
|------|---------|----------|
| `seeded_from_phase32` | Default prior state at `runtime_evidence/phase32_intelligence_20260701T011651Z/state` | Copies Phase 3.2 state; no live re-acquisition |

Phase 4.1 certification does not redesign acquisition — it verifies synthesis readiness on a valid processed corpus.

## Blockers

Certification fails when any blocker is present:

| Blocker | Condition |
|---------|-----------|
| Analyst status | `inspector.analyst.status != "pass"` |
| Claims extracted | `pipeline_result.claims_extracted <= 0` |
| Themes discovered | `analyst.synthesis.themes <= 0` |
| Intelligence items | `analyst.synthesis.intelligence_items <= 0` |
| Intelligence brief | No brief or `total_items <= 0` |
| Brief minimum | `total_items < 5` |
| Brief maximum | `total_items > 15` |
| Reading time | `analyst.briefing.reading_time_seconds > 60` |
| Deep dive | `intelligence_deep_dive()` returns `None` |
| Processed episodes | Zero processed episodes in corpus |
| Compression ratio | `analyst.synthesis.compression_ratio < 10` |

## Pass Criteria

| Requirement | Inspector / result field |
|-------------|--------------------------|
| Claims persisted | `analyst.claims.total > 0` |
| Themes discovered | `analyst.synthesis.themes > 0` |
| Items synthesized | `analyst.synthesis.intelligence_items > 0` |
| Brief generated | `analyst.briefing.latest_total_items` in 5–15 |
| Brief version | `analyst.briefing.version == "2.0"` |
| Reading time | `analyst.briefing.reading_time_seconds ≤ 60` |
| Compression | `analyst.synthesis.compression_ratio ≥ 10` |
| Deep dive | Generated for first brief item |
| Latency recorded | `analyst.pipeline.synthesis_latency_seconds` populated |

## Compression Metrics

The certification report includes:

| Metric | Source |
|--------|--------|
| Total claims | `analyst.claims.total` |
| Intelligence items | `analyst.synthesis.intelligence_items` |
| Compression ratio | `claims / brief_items` (target ≥ 10:1) |
| Claims per item | `analyst.synthesis.claims_per_item` |
| Reading time | `analyst.briefing.reading_time_seconds` |

## Output Artifacts

Evidence directory: `runtime_evidence/phase41_intelligence_<timestamp>/`

| File | Content |
|------|---------|
| `PHASE41_RUNTIME_CERTIFICATION.md` | Pass/fail report |
| `RUNTIME_INSPECTOR_OUTPUT.json` | Full inspector including `analyst.synthesis` |
| `RUNTIME_INSPECTOR_OUTPUT.md` | Markdown inspector export |
| `MORNING_INTELLIGENCE_BRIEF.json` | Latest brief v2 payload |
| `MORNING_INTELLIGENCE_BRIEF.md` | Human-readable brief v2 |
| `raw/acquisition.json` | Acquisition mode and episode counts |
| `raw/pipeline_result.json` | Claims, synthesis, latency |
| `raw/deep_dive.json` | Deep Dive v2 for first brief item |
| `raw/blockers.json` | Blocker list |

## Analyst Inspector Section

Phase 4.1 inspector (`inspect_analyst_runtime`) exposes:

- `phase` — `"4.1"`
- `status` — `pass` when claims, items, and briefs exist
- `synthesis` — themes, items, compression, evolution, evidence totals
- `briefing` — v2 count, reading time, compression, version
- `pipeline.synthesis_latency_seconds` — `theme_discovery`, `item_synthesis`, `brief_generation`, `total`
- `warnings` — operational alerts (missing themes, brief bounds, reading time)

## Reproduce

```bash
PYTHONPATH=src ./.venv/bin/python examples/certify_phase41_runtime.py
```

Exit code `0` = pass; `1` = blockers present. Script prints evidence directory path on completion.

## Performance Reporting

The certification report includes:

- Total elapsed time (seed + analyst + synthesis)
- Pipeline elapsed time
- Synthesis latency breakdown from `SynthesisResult.latency_seconds`:
  - `theme_discovery`
  - `item_synthesis`
  - `brief_generation`
  - `total`

## Relationship to Phase 4

Phase 4.1 extends Phase 4 certification:

| Phase 4 validates | Phase 4.1 adds |
|-------------------|----------------|
| Claim extraction and scoring | Theme discovery |
| Cross-source clusters | Theme evolution |
| Claim-level morning brief | Intelligence Items |
| Claim deep dive | Morning Brief v2 |
| — | Deep Dive v2 |
| — | ≥ 10:1 compression |

Phase 4 certifier: `examples/certify_phase4_runtime.py`

Both brief generations run during `IntelligenceAnalystPipeline.run()`. Phase 4.1 certification gates on `intelligence_brief`, not claim-level `brief`.

## Relationship to Phase 3.2

Phase 4.1 certification depends on Phase 3.2 corpus integrity:

- Seeded state from `phase32_intelligence_20260701T011651Z` when available
- Processed episodes required for claim extraction input

Re-run Phase 3.2 certification if seeded state is missing or corrupt:

```bash
PYTHONPATH=src ./.venv/bin/python examples/certify_phase32_runtime.py
```

## Certification Report Format

Generated `PHASE41_RUNTIME_CERTIFICATION.md` sections:

1. **Status** — PASS or FAIL
2. **Pipeline Chain** — counts per stage
3. **Compression Metrics** — claims, items, ratio, reading time
4. **Performance** — elapsed and synthesis latency
5. **Blockers** — failure reasons or "None"