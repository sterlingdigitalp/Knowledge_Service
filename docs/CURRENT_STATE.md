# Current State — What Is Live vs Historical

**As of:** 2026-07-02  
**Authoritative for:** engineers onboarding to the repository today

This document separates **implemented, running subsystems** from **historical specification and certification artifacts**. Historical docs remain valuable for design rationale but must not be read as a feature checklist.

---

## Executive Summary

| Status | Phases |
|--------|--------|
| **Live & certified** | Phase 0 (foundation docs), Phase 1 core pipeline, Phase 3 → 3.2 collection, Phase 4 → 4.1 analyst, Phase 5 → 5.1.2 production, **Phase 6 morning operations** |
| **Partially live** | Retrieval layer, storage (in-memory + postgres adapters), API layer (spec only) |
| **Historical / not implemented** | Full public HTTP API, autonomous agent streaming, graph store, multi-modal acquisition, Phase 2 "advanced acquisition" roadmap items |

**Daily production path:** PCC preflight → `bin/morning-intelligence.sh` → acquire → analyze → freshness gate → LLM enhance → publish `frontend/latest.*`

---

## Phase Implementation Matrix

### Phase 0 — Architecture & Foundation ✅ LIVE (documentation)

- **What:** Immutable principles, six-layer model, provider isolation, Knowledge Object contract
- **Where:** [STARTING.md](../STARTING.md), [ARCHITECTURE.md](ARCHITECTURE.md), [PRINCIPLES.md](PRINCIPLES.md)
- **Code:** Design constraints reflected across all packages; no standalone "Phase 0" module
- **Note:** Historical — defines *how* the system was designed, not a deployable artifact

### Phase 1 — Core Platform ✅ LIVE (subset)

| Component | Status | Package / Evidence |
|-----------|--------|-------------------|
| Knowledge Object schema | ✅ Live | `knowledge_object.py` |
| Processing pipeline (7 stages) | ✅ Live | `processing/pipeline.py` |
| Providers (Crawl4AI, SearXNG, Transcript) | ✅ Live | `providers/` |
| Planning engine | ✅ Live | `planning/` |
| Storage interfaces + in-memory store | ✅ Live | `storage/` |
| Retrieval (quotes, hierarchy) | ✅ Live | `retrieval/` |
| Public HTTP API | ❌ Spec only | [API_SPEC.md](API_SPEC.md) — not a running service |
| PostgreSQL/Qdrant production deploy | ⚠️ Adapters exist | Not the primary file-based production path |

**Historical docs:** [PHASE_1.1B_COMPLIANCE_REVIEW.md](PHASE_1.1B_COMPLIANCE_REVIEW.md), [PHASE_1.2_REPORT.md](PHASE_1.2_REPORT.md), [PHASE_1.2B_REPORT.md](PHASE_1.2B_REPORT.md), [PROCESSING_PIPELINE_CERTIFICATION.md](PROCESSING_PIPELINE_CERTIFICATION.md)

### Phase 2 — Advanced Acquisition ❌ NOT IMPLEMENTED (roadmap)

- **What:** GitHub/RSS/PDF providers, adaptive planning, multi-level cache, LLM enrichment
- **Where:** [ROADMAP.md](ROADMAP.md) § Phase 2
- **Status:** Future direction only. Do not expect these capabilities in `src/`.

### Phase 3 — Intelligence Collection ✅ LIVE

| Component | Status | Module |
|-----------|--------|--------|
| Intelligence profiles & watch lists | ✅ Live | `intelligence/models.py`, `config/profiles.json` |
| Podcast discovery | ✅ Live | `intelligence/discovery.py`, `discoverers/podcast.py` |
| Persistent dedupe | ✅ Live | `intelligence/dedupe.py` |
| Collector orchestration | ✅ Live | `intelligence/collector.py` |
| Corpus + source graphs | ✅ Live | `intelligence/corpus.py`, `state/` |
| Scheduler (manual/daemon) | ✅ Live | `intelligence/scheduler.py` |
| Runtime inspector | ✅ Live | `intelligence/inspector.py` |

**Certification:** `examples/certify_phase3_intelligence_collection.py`  
**Evidence:** `runtime_evidence/phase3_intelligence_*`  
**Doc:** [PHASE3_ARCHITECTURE.md](PHASE3_ARCHITECTURE.md) — **live architecture reference**

### Phase 3.1 — Source Route Registry ✅ LIVE

| Component | Status | Module |
|-----------|--------|--------|
| Information events | ✅ Live | `intelligence/models.py` |
| Route registry | ✅ Live | `intelligence/route_registry.py`, `data/source_routes.json` |
| Person-centric discovery | ✅ Live | `intelligence/discovery.py` |
| Route diagnostics | ✅ Live | `state/route_diagnostics.json` |

**Certification:** `examples/certify_phase31_runtime.py`  
**Evidence:** `runtime_evidence/phase31_intelligence_*`  
**Doc:** [PHASE31_ARCHITECTURE.md](PHASE31_ARCHITECTURE.md) — **live**

### Phase 3.2 — Discovery Expansion & Registry Evolution ✅ LIVE

| Component | Status | Module |
|-----------|--------|--------|
| Multi-type discoverers | ✅ Live | `intelligence/discoverers/` (conference, earnings, interview, livestream, presentation) |
| Registry evolution | ✅ Live | `intelligence/registry_evolution.py` |
| Corpus audit | ✅ Live | `intelligence/corpus_audit.py` |
| Route confidence | ✅ Live | `intelligence/route_confidence.py` |
| Recertification | ✅ Live | `intelligence/recertification.py` |

**Certification:** `examples/certify_phase32_runtime.py`  
**Evidence:** `runtime_evidence/phase32_intelligence_*`  
**Doc:** [PHASE32_RUNTIME_CERTIFICATION.md](PHASE32_RUNTIME_CERTIFICATION.md) — **live**

### Phase 4 — Personal Intelligence Analyst ✅ LIVE

| Component | Status | Module |
|-----------|--------|--------|
| Claim extraction | ✅ Live | `analyst/claims/extractor.py` |
| Novelty / relevance / importance | ✅ Live | `analyst/novelty/`, `relevance/`, `importance/` |
| Contradiction detection | ✅ Live | `analyst/contradiction/` |
| Cross-source clustering | ✅ Live | `analyst/cross_source/` |
| Morning Brief v1 (claim-level) | ✅ Live | `analyst/briefing/morning_brief.py` |
| Deep Dive v1 | ✅ Live | `analyst/briefing/deep_dive.py` |
| Analyst pipeline | ✅ Live | `analyst/pipeline.py` |

**Certification:** `examples/certify_phase4_runtime.py`, `certify_phase4_intelligence.py`  
**Evidence:** `runtime_evidence/phase4_intelligence_*`  
**Doc:** [PHASE4_ARCHITECTURE.md](PHASE4_ARCHITECTURE.md) — **live**

### Phase 4.1 — Intelligence Synthesis ✅ LIVE

| Component | Status | Module |
|-----------|--------|--------|
| Theme discovery & evolution | ✅ Live | `analyst/synthesis/themes/` |
| Intelligence Item engine | ✅ Live | `analyst/synthesis/items/` |
| Morning Brief v2 | ✅ Live | `analyst/synthesis/briefing/morning_brief_v2.py` |
| Deep Dive v2 | ✅ Live | `analyst/synthesis/briefing/deep_dive_v2.py` |
| Synthesis store | ✅ Live | `analyst/synthesis/store.py`, `state/analyst/synthesis/` |

**Certification:** `examples/certify_phase41_runtime.py`  
**Evidence:** `runtime_evidence/phase41_intelligence_*`  
**Doc:** [PHASE41_ARCHITECTURE.md](PHASE41_ARCHITECTURE.md) — **live**

### Phase 5 — Production Enhancement ✅ LIVE

| Component | Status | Module |
|-----------|--------|--------|
| Neural re-embedding | ✅ Live | `production/embeddings/` |
| Production store | ✅ Live | `production/store.py`, `state/production/` |
| Personalization & feedback | ✅ Live | `production/personalization/` |
| Trend acceleration | ✅ Live | `production/trends/` |
| Morning Brief v3 | ✅ Live | `production/briefing/morning_brief_v3.py` |
| Quality evaluator | ✅ Live | `production/briefing/quality.py` |
| Deep Dive v3 | ✅ Live | `production/conversation/deep_dive_v3.py` |
| Production pipeline | ✅ Live | `production/pipeline.py` |
| Brief scheduler | ✅ Live | `production/scheduler/brief_scheduler.py` |

**Certification:** `examples/certify_phase5_runtime.py`  
**Evidence:** `runtime_evidence/phase5_intelligence_*`  
**Doc:** [PHASE5_ARCHITECTURE.md](PHASE5_ARCHITECTURE.md) — **live**

### Phase 5.1 — xAI/Grok LLM Integration ✅ LIVE

| Component | Status | Module |
|-----------|--------|--------|
| LLM provider registry | ✅ Live | `production/llm/registry.py` |
| xAI Responses provider | ✅ Live | `production/llm/xai_responses.py` |
| Analyst heuristic fallback | ✅ Live | `production/llm/analyst_provider.py` |
| Enhancement layer | ✅ Live | `production/enhancement.py` |

**Certification:** `examples/certify_phase51_runtime.py`, `certify_phase511_live.py`  
**Evidence:** `runtime_evidence/phase51_intelligence_*`, `phase511_live_*`  
**Doc:** [PHASE51_ARCHITECTURE.md](PHASE51_ARCHITECTURE.md), [XAI_PROVIDER.md](XAI_PROVIDER.md) — **live**

### Phase 5.1.2 — LLM Budget & Cache Optimization ✅ LIVE

| Component | Status | Module |
|-----------|--------|--------|
| Token accounting | ✅ Live | `production/llm/accounting.py` |
| LLM budget enforcement | ✅ Live | `production/llm/budget.py` |
| Response cache | ✅ Live | `production/llm/cache.py` |
| Brief-first enhancement | ✅ Live | `production/llm/brief_enhancer.py` |

**Certification:** `examples/certify_phase512_runtime.py`  
**Evidence:** `runtime_evidence/phase512_optimization_*` (also **bootstrap source** for empty `state/`)  
**Doc:** [PHASE512_BENCHMARK.md](PHASE512_BENCHMARK.md), [LLM_CACHE.md](LLM_CACHE.md), [TOKEN_ACCOUNTING.md](TOKEN_ACCOUNTING.md) — **live**

### Phase 6 — Automated Morning Intelligence ✅ LIVE (current production)

| Component | Status | Module / Path |
|-----------|--------|---------------|
| Daily runner CLI | ✅ Live | `production/morning/daily_runner.py` |
| Shell entrypoint | ✅ Live | `bin/morning-intelligence.sh` |
| Freshness gate | ✅ Live | `production/morning/freshness_gate.py` |
| Frontend publisher | ✅ Live | `production/morning/publisher.py` |
| PCC preflight integration | ✅ Live | External: `~/bin/pcc-morning-preflight.sh` |
| Static frontend | ✅ Live | `frontend/latest.html`, `latest.md`, `data/latest.json` |
| Archive rotation | ✅ Live | `frontend/archive/YYYY-MM-DD/` |

**Tests:** `tests/production/test_daily_runner.py`, `test_morning_*`  
**Doc:** [PHASE6_DELIVERABLES.md](PHASE6_DELIVERABLES.md), [DAILY_MORNING_INTELLIGENCE.md](DAILY_MORNING_INTELLIGENCE.md), [MORNING_INTELLIGENCE_OPERATIONS.md](MORNING_INTELLIGENCE_OPERATIONS.md) — **live operations runbook**

---

## What Runs Every Morning (Production Path)

```
PCC LaunchAgent (06:26)
  → pcc-morning-preflight.sh
    → bin/morning-intelligence.sh run
      → IntelligenceCollector.run_once()      # Phase 3.2
      → ProductionIntelligencePipeline          # Phase 4 → 5
      → FreshnessGate.filter_items()            # Phase 6
      → ProductionEnhancementLayer.enhance()    # Phase 5.1.2 (budget-aware)
      → FrontendPublisher.publish()             # Phase 6
```

State persists in `state/`. First-run bootstrap copies from `runtime_evidence/phase512_optimization_20260701T074324Z/state/` if empty.

---

## Historical Documents (Read for Context, Not as Feature List)

These are **certification reports, debug traces, and phase-gate reviews** from development. They document *what was verified at a point in time*, not necessarily what runs unattended today.

| Category | Examples | How to use |
|----------|----------|------------|
| Phase 1 compliance reports | `PHASE_1.1B_COMPLIANCE_REVIEW.md`, `PHASE_1.2_REPORT.md`, `PHASE_1.2B_REPORT.md` | Pipeline determinism history |
| Debug / validation traces | `FOUNDATION_DEBUG_REPORT.md`, `LIFECYCLE_DEBUG_TRACE.md`, `LIFECYCLE_EXECUTION_TRACE.md`, `P1_6B_FIXES.md` | Debugging methodology |
| End-to-end certification snapshots | `END_TO_END_CERTIFICATION.md`, `REAL_END_TO_END_VALIDATION.md`, `VALIDATION_SUMMARY.md`, `FUNCTIONAL_VALIDATION.md` | Point-in-time E2E evidence |
| Roadmap (future) | `ROADMAP.md` Phases 2+ | **Not implemented** |
| API / deployment specs | `API_SPEC.md`, full PostgreSQL/Qdrant topology in `ARCHITECTURE.md` | Design targets |
| Knowledge Olympics / strategy essays | `KNOWLEDGE_OLYMPICS.md`, `KNOWLEDGE_STRATEGY.md` | Product vision, not code map |
| Root-level phase note | `PHASE_3_1_SOURCE_ROUTE_REGISTRY_AND_PERSON_CENTRIC_COLLECTION.md` | Superseded by `docs/PHASE31_ARCHITECTURE.md` |

**Rule of thumb:** If a doc has `RUNTIME_CERTIFICATION`, `REPORT`, `DEBUG`, or `VALIDATION` in the title, treat it as **evidence of a past gate** unless cross-referenced here as live.

---

## Live Architecture Docs (Prefer These)

| Topic | Document |
|-------|----------|
| Layer model | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Phase 3 collection | [PHASE3_ARCHITECTURE.md](PHASE3_ARCHITECTURE.md) |
| Phase 3.1 routes | [PHASE31_ARCHITECTURE.md](PHASE31_ARCHITECTURE.md), [SOURCE_ROUTE_REGISTRY.md](SOURCE_ROUTE_REGISTRY.md) |
| Phase 4 analyst | [PHASE4_ARCHITECTURE.md](PHASE4_ARCHITECTURE.md) |
| Phase 4.1 synthesis | [PHASE41_ARCHITECTURE.md](PHASE41_ARCHITECTURE.md) |
| Phase 5 production | [PHASE5_ARCHITECTURE.md](PHASE5_ARCHITECTURE.md) |
| Phase 5.1 LLM | [PHASE51_ARCHITECTURE.md](PHASE51_ARCHITECTURE.md) |
| Phase 6 operations | [PHASE6_DELIVERABLES.md](PHASE6_DELIVERABLES.md), [MORNING_INTELLIGENCE_OPERATIONS.md](MORNING_INTELLIGENCE_OPERATIONS.md) |
| Morning brief format | [MORNING_BRIEF_V3.md](MORNING_BRIEF_V3.md) |
| Freshness | [FRESHNESS_GATE.md](FRESHNESS_GATE.md) |
| Repository map | [REPOSITORY_INDEX.md](REPOSITORY_INDEX.md) |

---

## Test Coverage vs Live Features

| Test directory | Covers |
|----------------|--------|
| `tests/processing/` | Phase 1 pipeline |
| `tests/providers/` | Provider contracts |
| `tests/intelligence/` | Phase 3 → 3.2 |
| `tests/analyst/` | Phase 4 |
| `tests/analyst/synthesis/` | Phase 4.1 |
| `tests/production/` | Phase 5 → 6 (including morning runner) |
| `integration_tests/` | Cross-layer integration |
| `failure_tests/`, `property_tests/`, `performance_tests/` | Resilience & perf |

---

## Generated Artifacts (Not Source Code)

| Location | Produced by | Purpose |
|----------|-------------|---------|
| `frontend/latest.*` | Morning publisher | User-facing daily brief |
| `frontend/archive/` | Morning publisher | Historical briefs |
| `state/` | Collectors, analysts, production | Persistent corpus |
| `runtime_evidence/` | `examples/certify_*.py` | Certification snapshots |
| `~/Library/Logs/pcc/morning-intelligence.log` | Morning logger | Operations log |

---

## Next Steps for New Contributors

1. Read [STARTING.md](../STARTING.md) for vision (15 min)
2. Read this document to know what's live (10 min)
3. Follow [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) to run tests and morning intelligence
4. Use [REPOSITORY_INDEX.md](REPOSITORY_INDEX.md) to navigate the full doc corpus