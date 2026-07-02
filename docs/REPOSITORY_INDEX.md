# Repository Index

Complete knowledge-graph map of the Knowledge_Service repository: directories, executables, CLIs, documentation categories, subsystems, generated artifacts, and state folders.

**Navigation:** [README.md](../README.md) · [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) · [CURRENT_STATE.md](CURRENT_STATE.md) · [STARTING.md](../STARTING.md)

---

## Top-Level Directory Map

| Path | Type | Description |
|------|------|-------------|
| [bin/](../bin/) | Executables | Shell entrypoints |
| [config/](../config/) | Configuration | Intelligence profiles, watch universe builder |
| [data/](../data/) | Configuration | Source route registry |
| [docs/](.) | Documentation | 104+ architecture & certification specs |
| [examples/](../examples/) | Certification CLIs | Phase runtime certification scripts |
| [failure_tests/](../failure_tests/) | Tests | Failure-injection tests |
| [frontend/](../frontend/) | Generated + static UI | Morning Brief artifacts & viewer |
| [integration_tests/](../integration_tests/) | Tests | Cross-subsystem integration |
| [performance_tests/](../performance_tests/) | Tests | Performance benchmarks |
| [property_tests/](../property_tests/) | Tests | Fuzz/property tests |
| [runtime_evidence/](../runtime_evidence/) | Generated artifacts | Timestamped certification outputs |
| [src/knowledge_service/](../src/knowledge_service/) | Source code | 154 Python modules |
| [state/](../state/) | Persistent state | File-backed production corpus |
| [tests/](../tests/) | Tests | 71+ unit/integration test files |
| [STARTING.md](../STARTING.md) | Documentation | Phase 0 vision & foundation |
| [conftest.py](../conftest.py) | Test bootstrap | Adds `src/` to sys.path |
| [.venv/](../.venv/) | Environment | Python 3.14 virtualenv (gitignored) |
| [.env.local](../.env.local) | Secrets | LLM keys (gitignored, create locally) |

---

## Executables & CLI Entry Points

### Shell executables (`bin/`)

| Script | Command | Description |
|--------|---------|-------------|
| [verify.sh](../bin/verify.sh) | `bin/verify.sh` | Canonical one-command verification (all test suites + inspector + status) |
| | `VERIFY_FULL=1 bin/verify.sh` | Includes Phase 5.1 certification |
| [morning-intelligence.sh](../bin/morning-intelligence.sh) | `bin/morning-intelligence.sh run` | Full daily morning intelligence workflow |
| | `bin/morning-intelligence.sh run --mode manual` | Manual acquisition mode |
| | `bin/morning-intelligence.sh status` | JSON status, artifacts, LLM config |

Sets `PYTHONPATH=src`, uses `.venv/bin/python3`, delegates to `knowledge_service.production.morning`.

### Python module CLIs

| Module | Command | Description |
|--------|---------|-------------|
| `production.morning` | `python -m knowledge_service.production.morning run` | Morning runner (same as shell script) |
| | `python -m knowledge_service.production.morning status` | Status JSON |

### Certification scripts (`examples/`)

| Script | Phase | Purpose |
|--------|-------|---------|
| [certify_acquisition_ladder.py](../examples/certify_acquisition_ladder.py) | 1.x | Transcript acquisition ladder certification |
| [certify_phase3_intelligence_collection.py](../examples/certify_phase3_intelligence_collection.py) | 3 | Profile-driven collection |
| [certify_phase31_runtime.py](../examples/certify_phase31_runtime.py) | 3.1 | Source route registry |
| [certify_phase32_runtime.py](../examples/certify_phase32_runtime.py) | 3.2 | Discovery expansion |
| [certify_phase4_runtime.py](../examples/certify_phase4_runtime.py) | 4 | Personal intelligence analyst |
| [certify_phase4_intelligence.py](../examples/certify_phase4_intelligence.py) | 4 | Analyst intelligence certification |
| [certify_phase41_runtime.py](../examples/certify_phase41_runtime.py) | 4.1 | Intelligence synthesis |
| [certify_phase5_runtime.py](../examples/certify_phase5_runtime.py) | 5 | Production enhancement |
| [certify_phase51_runtime.py](../examples/certify_phase51_runtime.py) | 5.1 | xAI/Grok integration |
| [certify_phase511_live.py](../examples/certify_phase511_live.py) | 5.1.1 | Live LLM certification |
| [certify_phase512_runtime.py](../examples/certify_phase512_runtime.py) | 5.1.2 | LLM budget & cache optimization |
| [runtime_inspector.py](../examples/runtime_inspector.py) | 1.x | Transcript citation runtime inspector |
| [phase3_runtime_inspector.py](../examples/phase3_runtime_inspector.py) | 3 | Phase 3 collection inspector |
| [search_quotes.py](../examples/search_quotes.py) | — | Search timestamped transcript quotes |
| [generate_runtime_evidence.py](../examples/generate_runtime_evidence.py) | — | Comprehensive evidence generator |

**Standard invocation:**

```bash
export PYTHONPATH=src
python examples/certify_phase512_runtime.py
```

### Config utilities

| Script | Path | Purpose |
|--------|------|---------|
| `build_watch_universe.py` | [config/](../config/build_watch_universe.py) | Build intelligence profiles |
| `prepare_frontend_data.py` | [frontend/scripts/](../frontend/scripts/prepare_frontend_data.py) | Embed runtime data into `latest.html` (dev/legacy) |

### External integration (outside repo)

| Script | Location | Role |
|--------|----------|------|
| `pcc-morning-preflight.sh` | `~/bin/` | PCC preflight; invokes `bin/morning-intelligence.sh` as final stage |

---

## Source Package (`src/knowledge_service/`)

### Subsystem index

| Subsystem | Directory | Phase | Key modules |
|-----------|-----------|-------|-------------|
| Knowledge Object | `knowledge_object.py` | 1 | Canonical schema |
| Acquisition | `acquisition/` | 1 | `acquisition_bundle.py` |
| Planning | `planning/` | 1 | `planner.py`, `executor.py` |
| Processing | `processing/` | 1 | `pipeline.py`, `transcript.py`, `chunk.py` |
| Providers | `providers/` | 1 | `crawl4ai_provider.py`, `searxng_search_provider.py`, `transcript_provider.py` |
| Interfaces | `interfaces/` | 0–1 | `provider.py` |
| Registry | `registry/` | 1 | `provider_registry.py` |
| Retrieval | `retrieval/` | 1 | `retriever.py`, `quotes.py`, `hierarchy.py` |
| Storage | `storage/` | 1 | `postgres/`, `repositories/`, `interfaces/` |
| Intelligence | `intelligence/` | 3–3.2 | `collector.py`, `route_registry.py`, `discoverers/` |
| Analyst | `analyst/` | 4 | `pipeline.py`, `claims/`, `novelty/`, `relevance/` |
| Synthesis | `analyst/synthesis/` | 4.1 | `pipeline.py`, `themes/`, `items/` |
| Production | `production/` | 5–6 | `pipeline.py`, `enhancement.py`, `morning/` |
| LLM | `production/llm/` | 5.1–5.1.2 | `xai_responses.py`, `budget.py`, `cache.py` |
| Embeddings | `production/embeddings/` | 5 | `neural.py`, `sentence_transformer.py` |
| Personalization | `production/personalization/` | 5 | `ranking.py`, `feedback.py` |
| Trends | `production/trends/` | 5 | `acceleration.py` |
| Briefing | `production/briefing/` | 5 | `morning_brief_v3.py`, `quality.py` |
| Conversation | `production/conversation/` | 5 | `deep_dive_v3.py` |
| Morning ops | `production/morning/` | 6 | `daily_runner.py`, `publisher.py`, `freshness_gate.py` |
| Scheduler | `production/scheduler/` | 5 | `brief_scheduler.py` |

### `intelligence/` module detail

| Module | Role |
|--------|------|
| `collector.py` | Discovery → dedupe → acquire → process orchestration |
| `corpus.py` | Persistent corpus & growth history |
| `dedupe.py` | Source/acquisition/transcript hash deduplication |
| `discovery.py` | Person-centric event discovery |
| `discoverers/` | Podcast, conference, earnings, interview, livestream, presentation |
| `route_registry.py` | Deterministic acquisition route lookup |
| `route_confidence.py` | Route confidence scoring |
| `registry_evolution.py` | Registry mutation & evolution |
| `corpus_audit.py` | Corpus health auditing |
| `recertification.py` | Route recertification workflow |
| `scheduler.py` | Manual/scheduled/daemon collection loops |
| `inspector.py` | Runtime state exposure |
| `state.py` | `FileStateStore` — JSON/JSONL persistence |
| `config.py` | Profile load/save |
| `models.py` | Profiles, episodes, information events, jobs |

### `analyst/` module detail

| Module | Role |
|--------|------|
| `pipeline.py` | `IntelligenceAnalystPipeline` orchestration |
| `claims/extractor.py` | Atomic claim extraction |
| `novelty/engine.py` | Semantic novelty |
| `relevance/engine.py` | Per-profile relevance |
| `contradiction/detector.py` | Conflict detection |
| `importance/engine.py` | Explainable importance |
| `cross_source/engine.py` | Corroboration clustering |
| `briefing/` | Morning Brief v1, Deep Dive v1 |
| `synthesis/` | Phase 4.1 themes, items, Brief v2 |
| `store.py` | Analyst artifact persistence |

### `production/` module detail

| Module | Role |
|--------|------|
| `pipeline.py` | `ProductionIntelligencePipeline` |
| `enhancement.py` | `ProductionEnhancementLayer` |
| `store.py` | Production artifact store |
| `inspector.py` | Production runtime inspector |
| `benchmark.py`, `benchmark_llm.py` | Quality/LLM benchmarks |
| `morning/daily_runner.py` | Phase 6 morning orchestration |
| `morning/publisher.py` | `FrontendPublisher` |
| `morning/freshness_gate.py` | Stale headline prevention |
| `morning/markdown.py` | Brief markdown rendering |
| `morning/logger.py` | Structured morning logging |
| `morning/env.py` | `.env.local` loader |

---

## Test Directories

| Directory | Test files | Coverage |
|-----------|------------|----------|
| [tests/](../tests/) | 71+ | Primary unit tests |
| [tests/processing/](../tests/processing/) | 6+ | Pipeline stages |
| [tests/providers/](../tests/providers/) | 2+ | Provider contracts |
| [tests/planning/](../tests/planning/) | 1+ | Planning engine |
| [tests/intelligence/](../tests/intelligence/) | 10+ | Phase 3→3.2 |
| [tests/analyst/](../tests/analyst/) | 10+ | Phase 4 engines |
| [tests/analyst/synthesis/](../tests/analyst/synthesis/) | 6+ | Phase 4.1 |
| [tests/production/](../tests/production/) | 20+ | Phase 5→6 |
| [tests/retrieval/](../tests/retrieval/) | — | Quote search, retrieval |
| [tests/storage/](../tests/storage/) | — | Storage adapters |
| [tests/end_to_end/](../tests/end_to_end/) | — | E2E lifecycle |
| [tests/smoke/](../tests/smoke/) | — | Smoke tests |
| [tests/duplicate/](../tests/duplicate/) | — | Dedup behavior |
| [tests/restart/](../tests/restart/) | — | Restart persistence |
| [tests/failure/](../tests/failure/) | — | Failure modes |
| [tests/integration/](../tests/integration/) | — | In-package integration |
| [integration_tests/](../integration_tests/) | 4 | Cross-layer integration |
| [failure_tests/](../failure_tests/) | 1 | `test_failure_injection.py` |
| [property_tests/](../property_tests/) | 1 | `test_fuzzing.py` |
| [performance_tests/](../performance_tests/) | 1 | `test_performance.py` |

---

## Configuration Directories

### `config/`

| File | Purpose |
|------|---------|
| [profiles.json](../config/profiles.json) | Intelligence profiles (watch universe) |
| [profiles.yaml](../config/profiles.yaml) | YAML profile alternate |
| [build_watch_universe.py](../config/build_watch_universe.py) | Profile builder script |

### `data/`

| File | Purpose |
|------|---------|
| [source_routes.json](../data/source_routes.json) | Acquisition route registry |
| [source_routes.yaml](../data/source_routes.yaml) | YAML route alternate |

---

## State Directory (`state/`)

Persistent file-backed state. Written by collectors, analysts, and production pipeline.

| File / Directory | Writer | Contents |
|------------------|--------|----------|
| `profiles.json` | Intelligence config | Runtime profile snapshot |
| `collector_config.json` | Collector | Collector configuration |
| `episodes.json` | Collector | Discovered episodes |
| `knowledge_objects.jsonl` | Pipeline | Processed KnowledgeObjects |
| `jobs.json` | Scheduler | Collection job history |
| `dedupe.json` | Dedupe engine | Persistent hash registry |
| `discovery_runs.json` | Discovery | Discovery run log |
| `growth_history.json` | Corpus | Corpus growth metrics |
| `information_events.json` | Discovery | Person-centric events |
| `route_registry.json` | Route registry | Live routes |
| `route_diagnostics.json` | Route registry | Route health diagnostics |
| `source_graphs.json` | Corpus | Source relationship graphs |
| `certification_history.json` | Recertification | Route certification history |
| `analyst/claims.jsonl` | Analyst | Extracted claims |
| `analyst/scored_claims.jsonl` | Analyst | Scored claims |
| `analyst/corroboration_clusters.json` | Cross-source | Cluster data |
| `analyst/morning_briefs.json` | Analyst | Brief v1 history |
| `analyst/pipeline_runs.json` | Analyst | Analyst run log |
| `analyst/synthesis/` | Synthesis | Theme & item artifacts |
| `production/intelligence_briefs_v3.json` | Production | Brief v3 history |
| `production/pipeline_runs.json` | Production | Production run log |
| `production/llm_cache.json` | LLM cache | Cached LLM responses |
| `production/llm_budget.json` | LLM budget | Token/call accounting |
| `production/morning_runs.json` | Morning runner | Daily run summaries |
| `production/preferences.json` | Personalization | User preferences |
| `production/trend_history.jsonl` | Trends | Theme velocity history |

---

## Generated Artifacts

### Frontend (`frontend/`)

| Path | Producer | Updated |
|------|----------|---------|
| [latest.html](../frontend/latest.html) | `FrontendPublisher` | Every successful morning run |
| [latest.md](../frontend/latest.md) | `FrontendPublisher` | Every successful morning run |
| [data/latest.json](../frontend/data/latest.json) | `FrontendPublisher` | Every successful morning run |
| [archive/YYYY-MM-DD/](../frontend/archive/) | `FrontendPublisher` | Daily archive rotation |
| `archive/.../run_summary.json` | `FrontendPublisher` | Per-run metadata |
| [index.html](../frontend/index.html) | Static template | Manual edits |
| [app.js](../frontend/app.js) | Static | Manual edits |
| [styles.css](../frontend/styles.css) | Static | Manual edits |
| [screenshots/](../frontend/screenshots/) | Manual | UI screenshots |
| [SCREENSHOT_GALLERY.md](../frontend/SCREENSHOT_GALLERY.md) | Manual | Screenshot index |
| [TEST_RESULTS.md](../frontend/TEST_RESULTS.md) | Manual | Frontend test notes |

**Stable URL:** `file:///Users/sterlingdigital/Knowledge_Service/frontend/latest.html`

### Runtime evidence (`runtime_evidence/`)

31+ timestamped run directories. Naming patterns:

| Pattern | Phase | Example |
|---------|-------|---------|
| `acquisition_ladder_*` | 1.x | Transcript ladder runs |
| `runtime_*` | 1.x | Early runtime evidence |
| `phase3_intelligence_*` | 3 | Collection certification |
| `phase31_intelligence_*` | 3.1 | Route registry certification |
| `phase32_intelligence_*` | 3.2 | Discovery expansion |
| `phase4_intelligence_*` | 4 | Analyst certification |
| `phase41_intelligence_*` | 4.1 | Synthesis certification |
| `phase5_intelligence_*` | 5 | Production certification |
| `phase51_intelligence_*` | 5.1 | xAI integration |
| `phase511_live_*` | 5.1.1 | Live LLM runs |
| `phase512_optimization_*` | 5.1.2 | Budget optimization (**state bootstrap source**) |

**Typical subdirectory layout:**

```
runtime_evidence/<run_id>/
  config/     # Configuration snapshot
  logs/       # Certification logs
  raw/        # Raw payloads
  reports/    # JSON reports
  state/      # Point-in-time state copy
```

Special layouts:
- `acquisition_ladder_*`: adds `audio/`, `transcripts/`, `segments/`, `knowledge_objects/`, `search_results/`
- `runtime_*`: adds `inputs/`, `intermediate/`, `raw_runtime/`, `transcripts/`

### External logs (not in repo)

| Path | Producer |
|------|----------|
| `~/Library/Logs/pcc/morning-intelligence.log` | `MorningIntelligenceLogger` |
| `~/Library/Logs/pcc/morning-preflight.log` | PCC preflight |

### Cache / build artifacts (gitignored)

| Path | Purpose |
|------|---------|
| `.pytest_cache/` | Pytest cache |
| `**/__pycache__/` | Python bytecode |
| `.venv/` | Virtual environment |

---

## Documentation Index (`docs/`)

**104** markdown files in `docs/` root, plus subdirectories.

### Category 1: Vision, Principles & Strategy

| Document | Topic |
|----------|-------|
| [VISION.md](VISION.md) | Product vision |
| [PRINCIPLES.md](PRINCIPLES.md) | Immutable design principles |
| [KNOWLEDGE_STRATEGY.md](KNOWLEDGE_STRATEGY.md) | Knowledge philosophy |
| [SUCCESS_CRITERIA.md](SUCCESS_CRITERIA.md) | Success metrics |
| [KNOWLEDGE_OLYMPICS.md](KNOWLEDGE_OLYMPICS.md) | Use-case scenarios |
| [ROADMAP.md](ROADMAP.md) | Future phases (mostly unimplemented) |

### Category 2: Core Architecture

| Document | Topic |
|----------|-------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Six-layer architecture |
| [SYSTEM_DIAGRAM.md](SYSTEM_DIAGRAM.md) | System diagrams |
| [DATA_MODEL.md](DATA_MODEL.md) | Data model spec |
| [API_SPEC.md](API_SPEC.md) | Public API (spec only) |
| [CONFIGURATION.md](CONFIGURATION.md) | Configuration philosophy |
| [ERROR_STRATEGY.md](ERROR_STRATEGY.md) | Error handling |
| [SECURITY.md](SECURITY.md) | Security model |
| [OBSERVABILITY.md](OBSERVABILITY.md) | Metrics, tracing, logging |
| [QUERY_OBJECTS.md](QUERY_OBJECTS.md) | Query object spec |

### Category 3: Knowledge Object & Processing (Phase 1)

| Document | Topic |
|----------|-------|
| [KNOWLEDGE_OBJECT.md](KNOWLEDGE_OBJECT.md) | Canonical schema |
| [KNOWLEDGE_OBJECT_VERSIONING.md](KNOWLEDGE_OBJECT_VERSIONING.md) | Versioning |
| [KNOWLEDGE_OBJECT_CERTIFICATION.md](KNOWLEDGE_OBJECT_CERTIFICATION.md) | KO certification |
| [PROCESSING_PIPELINE.md](PROCESSING_PIPELINE.md) | 7-stage pipeline |
| [PROCESSING_PIPELINE_CERTIFICATION.md](PROCESSING_PIPELINE_CERTIFICATION.md) | Pipeline certification |
| [PROCESSING_PERFORMANCE.md](PROCESSING_PERFORMANCE.md) | Performance |
| [PLANNING_ENGINE.md](PLANNING_ENGINE.md) | Planning layer |
| [PROVIDER_INTERFACE.md](PROVIDER_INTERFACE.md) | Provider contract |
| [PROVIDER_SELECTION.md](PROVIDER_SELECTION.md) | Provider selection |
| [ACQUISITION_BUNDLE.md](ACQUISITION_BUNDLE.md) | Acquisition bundle |
| [TRANSCRIPT_CITATION_ENGINE.md](TRANSCRIPT_CITATION_ENGINE.md) | Transcript citations |

### Category 4: Storage & Retrieval

| Document | Topic |
|----------|-------|
| [RETRIEVAL_ARCHITECTURE.md](RETRIEVAL_ARCHITECTURE.md) | Retrieval design |
| [RETRIEVAL_CERTIFICATION.md](RETRIEVAL_CERTIFICATION.md) | Retrieval certification |
| [RETRIEVAL_METRICS.md](RETRIEVAL_METRICS.md) | Retrieval metrics |
| [SOURCE_REGISTRY_SPEC.md](SOURCE_REGISTRY_SPEC.md) | Source registry |
| [SOURCE_GRAPH.md](SOURCE_GRAPH.md) | Source graphs |
| [CORPUS_MANAGER.md](CORPUS_MANAGER.md) | Corpus management |

### Category 5: Intelligence Collection (Phase 3)

| Document | Topic |
|----------|-------|
| [PHASE3_ARCHITECTURE.md](PHASE3_ARCHITECTURE.md) | Phase 3 architecture ✅ live |
| [PHASE3_RUNTIME_CERTIFICATION.md](PHASE3_RUNTIME_CERTIFICATION.md) | Phase 3 certification |
| [INTELLIGENCE_PROFILES.md](INTELLIGENCE_PROFILES.md) | Profile spec |
| [PROFILE_WATCHLISTS.md](PROFILE_WATCHLISTS.md) | Watch lists |
| [DISCOVERY_ENGINE.md](DISCOVERY_ENGINE.md) | Discovery engine |
| [DISCOVERY_ABSTRACTION.md](DISCOVERY_ABSTRACTION.md) | Discoverer abstraction |
| [WATCH_UNIVERSE_V1.md](WATCH_UNIVERSE_V1.md) | Watch universe v1 |
| [SOURCE_PLAYBOOK.md](SOURCE_PLAYBOOK.md) | Source playbook |

### Category 6: Route Registry (Phase 3.1)

| Document | Topic |
|----------|-------|
| [PHASE31_ARCHITECTURE.md](PHASE31_ARCHITECTURE.md) | Phase 3.1 architecture ✅ live |
| [PHASE31_RUNTIME_CERTIFICATION.md](PHASE31_RUNTIME_CERTIFICATION.md) | Phase 3.1 certification |
| [SOURCE_ROUTE_REGISTRY.md](SOURCE_ROUTE_REGISTRY.md) | Route registry spec |
| [INFORMATION_EVENTS.md](INFORMATION_EVENTS.md) | Information events |
| [ROUTE_CERTIFICATION.md](ROUTE_CERTIFICATION.md) | Route certification |
| [ROUTE_BENCHMARKS.md](ROUTE_BENCHMARKS.md) | Route benchmarks |
| [ROUTE_CONFIDENCE_ENGINE.md](ROUTE_CONFIDENCE_ENGINE.md) | Route confidence |

### Category 7: Discovery Expansion (Phase 3.2)

| Document | Topic |
|----------|-------|
| [PHASE32_RUNTIME_CERTIFICATION.md](PHASE32_RUNTIME_CERTIFICATION.md) | Phase 3.2 certification |
| [CORPUS_AUDIT.md](CORPUS_AUDIT.md) | Corpus audit |

### Category 8: Personal Analyst (Phase 4)

| Document | Topic |
|----------|-------|
| [PHASE4_ARCHITECTURE.md](PHASE4_ARCHITECTURE.md) | Phase 4 architecture ✅ live |
| [PHASE4_RUNTIME_CERTIFICATION.md](PHASE4_RUNTIME_CERTIFICATION.md) | Phase 4 certification |
| [CLAIM_EXTRACTION.md](CLAIM_EXTRACTION.md) | Claim extraction |
| [NOVELTY_ENGINE.md](NOVELTY_ENGINE.md) | Novelty scoring |
| [RELEVANCE_ENGINE.md](RELEVANCE_ENGINE.md) | Relevance scoring |
| [IMPORTANCE_ENGINE.md](IMPORTANCE_ENGINE.md) | Importance scoring |
| [CROSS_SOURCE_INTELLIGENCE.md](CROSS_SOURCE_INTELLIGENCE.md) | Cross-source clustering |
| [ANALYST_SUMMARIZATION.md](ANALYST_SUMMARIZATION.md) | Analyst summarization |
| [MORNING_INTELLIGENCE_BRIEF.md](MORNING_INTELLIGENCE_BRIEF.md) | Brief v1 |
| [MORNING_INTELLIGENCE_BRIEF_V2.md](MORNING_INTELLIGENCE_BRIEF_V2.md) | Brief v2 |

### Category 9: Intelligence Synthesis (Phase 4.1)

| Document | Topic |
|----------|-------|
| [PHASE41_ARCHITECTURE.md](PHASE41_ARCHITECTURE.md) | Phase 4.1 architecture ✅ live |
| [PHASE41_RUNTIME_CERTIFICATION.md](PHASE41_RUNTIME_CERTIFICATION.md) | Phase 4.1 certification |
| [INTELLIGENCE_SYNTHESIS.md](INTELLIGENCE_SYNTHESIS.md) | Synthesis overview |
| [INTELLIGENCE_ITEMS.md](INTELLIGENCE_ITEMS.md) | Intelligence Items |
| [THEME_DISCOVERY.md](THEME_DISCOVERY.md) | Theme discovery |
| [THEME_EVOLUTION.md](THEME_EVOLUTION.md) | Theme evolution |

### Category 10: Production Enhancement (Phase 5)

| Document | Topic |
|----------|-------|
| [PHASE5_ARCHITECTURE.md](PHASE5_ARCHITECTURE.md) | Phase 5 architecture ✅ live |
| [PHASE5_RUNTIME_CERTIFICATION.md](PHASE5_RUNTIME_CERTIFICATION.md) | Phase 5 certification |
| [MORNING_BRIEF_V3.md](MORNING_BRIEF_V3.md) | Brief v3 format |
| [NEURAL_EMBEDDINGS.md](NEURAL_EMBEDDINGS.md) | Neural embeddings |
| [PERSONALIZATION_ENGINE.md](PERSONALIZATION_ENGINE.md) | Personalization |
| [USER_FEEDBACK_ENGINE.md](USER_FEEDBACK_ENGINE.md) | Feedback engine |
| [TREND_ACCELERATION.md](TREND_ACCELERATION.md) | Trend acceleration |
| [PRODUCTION_BUDGET.md](PRODUCTION_BUDGET.md) | Production budget |
| [RUNTIME_SCHEDULER.md](RUNTIME_SCHEDULER.md) | Brief scheduler |
| [RUNTIME_INSPECTOR.md](RUNTIME_INSPECTOR.md) | Runtime inspector |
| [PROMPT_LIBRARY.md](PROMPT_LIBRARY.md) | LLM prompts |

### Category 11: LLM Integration (Phase 5.1 → 5.1.2)

| Document | Topic |
|----------|-------|
| [PHASE51_ARCHITECTURE.md](PHASE51_ARCHITECTURE.md) | Phase 5.1 architecture ✅ live |
| [PHASE51_RUNTIME_CERTIFICATION.md](PHASE51_RUNTIME_CERTIFICATION.md) | Phase 5.1 certification |
| [PHASE512_BENCHMARK.md](PHASE512_BENCHMARK.md) | Phase 5.1.2 benchmarks |
| [PHASE512_RUNTIME_CERTIFICATION.md](PHASE512_RUNTIME_CERTIFICATION.md) | Phase 5.1.2 certification |
| [XAI_PROVIDER.md](XAI_PROVIDER.md) | xAI/Grok provider |
| [LLM_CACHE.md](LLM_CACHE.md) | LLM response cache |
| [TOKEN_ACCOUNTING.md](TOKEN_ACCOUNTING.md) | Token accounting |

### Category 12: Morning Operations (Phase 6) ✅ LIVE

| Document | Topic |
|----------|-------|
| [PHASE6_DELIVERABLES.md](PHASE6_DELIVERABLES.md) | Phase 6 deliverables |
| [DAILY_MORNING_INTELLIGENCE.md](DAILY_MORNING_INTELLIGENCE.md) | Daily workflow |
| [MORNING_INTELLIGENCE_OPERATIONS.md](MORNING_INTELLIGENCE_OPERATIONS.md) | Operations runbook |
| [FRESHNESS_GATE.md](FRESHNESS_GATE.md) | Freshness gate |
| [PCC_PREFLIGHT_INTEGRATION.md](PCC_PREFLIGHT_INTEGRATION.md) | PCC integration |

### Category 13: End-to-End Validation & Certification

| Document | Topic |
|----------|-------|
| [END_TO_END_CERTIFICATION.md](END_TO_END_CERTIFICATION.md) | E2E certification |
| [END_TO_END_METRICS.md](END_TO_END_METRICS.md) | E2E metrics |
| [END_TO_END_TIMELINE.md](END_TO_END_TIMELINE.md) | E2E timeline |
| [REAL_END_TO_END_VALIDATION.md](REAL_END_TO_END_VALIDATION.md) | Real E2E validation |
| [FUNCTIONAL_VALIDATION.md](FUNCTIONAL_VALIDATION.md) | Functional validation |
| [ARCHITECTURE_VALIDATION.md](ARCHITECTURE_VALIDATION.md) | Architecture validation |
| [VALIDATION_SUMMARY.md](VALIDATION_SUMMARY.md) | Validation summary |
| [RUNTIME_CERTIFICATION_REPORT.md](RUNTIME_CERTIFICATION_REPORT.md) | Runtime cert report |
| [LIFECYCLE_VALIDATION.md](LIFECYCLE_VALIDATION.md) | Lifecycle validation |

### Category 14: Historical Reports & Debug Traces

| Document | Topic |
|----------|-------|
| [PHASE_1.1B_COMPLIANCE_REVIEW.md](PHASE_1.1B_COMPLIANCE_REVIEW.md) | Phase 1.1b review |
| [PHASE_1.2_REPORT.md](PHASE_1.2_REPORT.md) | Phase 1.2 report |
| [PHASE_1.2B_REPORT.md](PHASE_1.2B_REPORT.md) | Phase 1.2b report |
| [FOUNDATION_DEBUG_REPORT.md](FOUNDATION_DEBUG_REPORT.md) | Foundation debug |
| [LIFECYCLE_DEBUG_TRACE.md](LIFECYCLE_DEBUG_TRACE.md) | Lifecycle debug |
| [LIFECYCLE_EXECUTION_TRACE.md](LIFECYCLE_EXECUTION_TRACE.md) | Lifecycle execution |
| [P1_6B_FIXES.md](P1_6B_FIXES.md) | P1.6b fixes |

### Category 15: Meta Documentation (this knowledge graph)

| Document | Topic |
|----------|-------|
| [REPOSITORY_INDEX.md](REPOSITORY_INDEX.md) | This file |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | Developer operations |
| [CURRENT_STATE.md](CURRENT_STATE.md) | Live vs historical |

### Subdirectories

#### `docs/providers/`

| Document | Topic |
|----------|-------|
| [PROVIDER_INVENTORY.md](providers/PROVIDER_INVENTORY.md) | Provider inventory |
| [PROVIDER_DISCOVERY.md](providers/PROVIDER_DISCOVERY.md) | Provider discovery |
| [PROVIDER_CERTIFICATION.md](providers/PROVIDER_CERTIFICATION.md) | Provider certification |
| [CRAWL4AI_PROVIDER_SPEC.md](providers/CRAWL4AI_PROVIDER_SPEC.md) | Crawl4AI spec |
| [SEARXNG_PROVIDER_SPEC.md](providers/SEARXNG_PROVIDER_SPEC.md) | SearXNG spec |

#### `docs/examples/`

| Document | Topic |
|----------|-------|
| [README.md](examples/README.md) | Examples documentation index |

---

## Root-Level Files (outside `docs/`)

| File | Type | Notes |
|------|------|-------|
| [STARTING.md](../STARTING.md) | Vision | Phase 0 foundation — read first |
| [README.md](../README.md) | Onboarding | Repository entry point |
| [conftest.py](../conftest.py) | Test config | Pytest path bootstrap |
| ~~`_debug_store.py`~~ | *(removed)* | Was unused debug script; see `TECHNICAL_DEBT_REGISTER.md` |
| [PHASE_3_1_SOURCE_ROUTE_REGISTRY_AND_PERSON_CENTRIC_COLLECTION.md](../PHASE_3_1_SOURCE_ROUTE_REGISTRY_AND_PERSON_CENTRIC_COLLECTION.md) | Historical | Superseded by `docs/PHASE31_ARCHITECTURE.md` |

---

## Subsystem Dependency Graph

```
                    ┌─────────────┐
                    │  frontend/  │ ← Phase 6 publisher
                    └──────▲──────┘
                           │
              ┌────────────┴────────────┐
              │  production/morning/    │ Phase 6
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  production/          │ Phase 5 → 5.1.2
              │  (LLM, embeddings)    │
              └────────────┬────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
┌────────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
│ analyst/       │ │ analyst/      │ │ intelligence/ │
│ synthesis/     │ │ (Phase 4)     │ │ (Phase 3→3.2)│
│ (Phase 4.1)    │ └───────┬───────┘ └───────┬───────┘
└────────┬───────┘         │                 │
         │                 └────────┬────────┘
         │                          │
         └────────────┬─────────────┘
                      │
         ┌────────────▼────────────┐
         │  processing/ + providers/│ Phase 1
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │  state/ + config/ + data/│
         └─────────────────────────┘
```

---

## Quick Reference: "Where do I find…?"

| Looking for | Location |
|-------------|----------|
| Morning brief HTML | `frontend/latest.html` |
| Run morning intelligence | `bin/morning-intelligence.sh run` |
| Intelligence profiles | `config/profiles.json` |
| Route registry | `data/source_routes.json` |
| Persistent corpus | `state/knowledge_objects.jsonl` |
| Claims & scores | `state/analyst/` |
| Brief v3 history | `state/production/intelligence_briefs_v3.json` |
| LLM cache | `state/production/llm_cache.json` |
| Certification evidence | `runtime_evidence/` |
| Phase 5.1.2 baseline state | `runtime_evidence/phase512_optimization_20260701T074324Z/state/` |
| Vision & principles | `STARTING.md` |
| What's implemented | `docs/CURRENT_STATE.md` |
| How to develop | `docs/DEVELOPER_GUIDE.md` |
| All 104+ docs | This file, Categories 1–15 |