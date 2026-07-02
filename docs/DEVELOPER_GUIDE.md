# Developer Guide

How to develop, test, verify, and operate Knowledge_Service on a local machine.

**See also:** [CURRENT_STATE.md](CURRENT_STATE.md) (what's live), [REPOSITORY_INDEX.md](REPOSITORY_INDEX.md) (full map), [STARTING.md](../STARTING.md) (vision).

---

## Prerequisites

- **Python 3.14** (project uses `.venv` at repo root)
- **zsh** (morning shell script is `#!/bin/zsh`)
- Network access for acquisition and xAI API (morning run degrades gracefully offline)
- Optional: PCC preflight LaunchAgent for scheduled 06:26 runs

---

## Environment Setup

See [INSTALL.md](INSTALL.md) for full first-time setup. Quick version:

```bash
cd Knowledge_Service   # repository root

python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
source .venv/bin/activate

# Required for all Python invocations
export PYTHONPATH=src

# LLM keys (gitignored — create if missing)
cat > .env.local <<'EOF'
XAI_API_KEY=your_key_here
KNOWLEDGE_LLM_PROVIDER=xai_responses
KNOWLEDGE_LLM_FALLBACK_PROVIDER=analyst_heuristic
KNOWLEDGE_LLM_MAX_ITEMS=5
KNOWLEDGE_LLM_MAX_CALLS=20
EOF
```

`conftest.py` at repo root adds `src/` to `sys.path` for pytest — no editable install required.

---

## Repository Layout for Developers

### Source package (`src/knowledge_service/`)

| Package | Responsibility |
|---------|----------------|
| `knowledge_object.py` | Canonical document schema |
| `acquisition/` | Acquisition bundle types |
| `planning/` | Acquisition planning & execution |
| `processing/` | 7-stage pipeline (clean → validate) |
| `providers/` | Crawl4AI, SearXNG, Transcript providers |
| `retrieval/` | Quote search, hierarchy retrieval |
| `storage/` | Store interfaces, postgres adapters, repositories |
| `registry/` | Provider registry |
| `intelligence/` | Phase 3→3.2 collection, corpus, routes |
| `analyst/` | Phase 4 claim scoring & briefs |
| `analyst/synthesis/` | Phase 4.1 themes & Intelligence Items |
| `production/` | Phase 5→6 enhancement, LLM, morning ops |
| `interfaces/` | Shared interface contracts |

### Configuration & data

| Path | Format | Purpose |
|------|--------|---------|
| `config/profiles.json` | JSON | Intelligence profiles & watch universe |
| `config/profiles.yaml` | YAML | Alternate profile source |
| `config/build_watch_universe.py` | Script | Profile builder utility |
| `data/source_routes.json` | JSON | Acquisition route registry |
| `data/source_routes.yaml` | YAML | Alternate route source |

### Persistent state (`state/`)

File-backed JSON/JSONL store via `intelligence.state.FileStateStore`:

| File / Dir | Contents |
|------------|----------|
| `profiles.json` | Runtime profile copy |
| `episodes.json` | Discovered episodes |
| `knowledge_objects.jsonl` | Processed corpus |
| `route_registry.json` | Live route table |
| `information_events.json` | Person-centric events |
| `dedupe.json` | Hash deduplication |
| `source_graphs.json` | Source relationship graphs |
| `analyst/` | Claims, scored claims, briefs, synthesis |
| `production/` | Brief v3, LLM cache, budget, morning runs |

**Bootstrap:** If `state/` is empty on first morning run, copies from `runtime_evidence/phase512_optimization_20260701T074324Z/state/`.

### Frontend (`frontend/`)

| Path | Role |
|------|------|
| `index.html` | Template shell |
| `latest.html` | **Stable bookmark target** (regenerated daily) |
| `latest.md` | Markdown edition |
| `data/latest.json` | Machine-readable brief |
| `app.js`, `styles.css` | Static UI |
| `archive/YYYY-MM-DD/` | Daily archives + `run_summary.json` |
| `scripts/prepare_frontend_data.py` | Manual frontend data prep (legacy/dev) |

### Runtime evidence (`runtime_evidence/`)

Timestamped certification outputs. Each run directory typically contains:

```
runtime_evidence/<run_id>/
  config/       # Snapshotted configuration
  logs/         # Certification logs
  raw/          # Raw acquisition payloads
  reports/      # JSON certification reports
  state/        # Point-in-time state snapshot
```

---

## Verification

**Canonical one-command verify:**

```bash
bin/verify.sh
```

See [VERIFY.md](VERIFY.md) for step breakdown, skip conditions, and individual commands.

---

## Running Tests

### Full suite

```bash
source .venv/bin/activate
export PYTHONPATH=src

python -m pytest tests/ failure_tests/ property_tests/ performance_tests/ -q
```

### By subsystem

```bash
# Phase 1 — processing & providers
python -m pytest tests/processing/ tests/providers/ tests/planning/ -q

# Phase 3 → 3.2 — intelligence collection
python -m pytest tests/intelligence/ -q

# Phase 4 — analyst engines
python -m pytest tests/analyst/ -q

# Phase 4.1 — synthesis
python -m pytest tests/analyst/synthesis/ -q

# Phase 5 → 6 — production & morning
python -m pytest tests/production/ -q

# Retrieval & storage
python -m pytest tests/retrieval/ tests/storage/ -q

# Integration (repo root integration_tests/)
python -m pytest integration_tests/ -q

# Resilience
python -m pytest failure_tests/ property_tests/ performance_tests/ -q
```

### Test directory map

| Directory | Files | Focus |
|-----------|-------|-------|
| `tests/` | 71+ `test_*.py` | Primary unit tests |
| `tests/production/` | 20+ | Morning runner, LLM, embeddings, scheduler |
| `tests/intelligence/` | 10+ | Collector, routes, discoverers |
| `tests/analyst/` | 15+ | Claim engines, briefs |
| `integration_tests/` | 4 | E2E lifecycle, provider compliance |
| `failure_tests/` | 1 | Failure injection |
| `property_tests/` | 1 | Fuzz testing |
| `performance_tests/` | 1 | Performance benchmarks |

### Demo script

```bash
python tests/demo.py
```

---

## Runtime Certification (Verify Subsystems)

Certification scripts write evidence to `runtime_evidence/` and print pass/fail reports.

```bash
export PYTHONPATH=src

# Acquisition ladder (transcript citation)
python examples/certify_acquisition_ladder.py

# Phase 3 — intelligence collection
python examples/certify_phase3_intelligence_collection.py

# Phase 3.1 — route registry
python examples/certify_phase31_runtime.py

# Phase 3.2 — discovery expansion
python examples/certify_phase32_runtime.py

# Phase 4 — personal analyst
python examples/certify_phase4_runtime.py
python examples/certify_phase4_intelligence.py

# Phase 4.1 — synthesis
python examples/certify_phase41_runtime.py

# Phase 5 — production enhancement
python examples/certify_phase5_runtime.py

# Phase 5.1 — xAI integration
python examples/certify_phase51_runtime.py
python examples/certify_phase511_live.py

# Phase 5.1.2 — LLM budget (latest production baseline)
python examples/certify_phase512_runtime.py
```

### Inspectors & utilities

```bash
# Transcript citation runtime inspector
python examples/runtime_inspector.py --format json --timeout-ms 30000

# Phase 3 collection inspector
python examples/phase3_runtime_inspector.py

# Search timestamped quotes
python examples/search_quotes.py "query text"

# Generate comprehensive runtime evidence bundle
python examples/generate_runtime_evidence.py
```

---

## Morning Intelligence

### CLI entrypoints

| Entry | Command |
|-------|---------|
| Shell wrapper | `bin/morning-intelligence.sh [run\|status]` |
| Python module | `python -m knowledge_service.production.morning [run\|status]` |

The shell script sets `PYTHONPATH=src` and uses `.venv/bin/python3` when present.

### Commands

```bash
# Full daily workflow (acquire → analyze → enhance → publish)
bin/morning-intelligence.sh run

# Manual mode (passed to collector)
bin/morning-intelligence.sh run --mode manual

# JSON status: artifacts, last run, LLM config (secrets redacted)
bin/morning-intelligence.sh status
```

### Pipeline (what `run` does)

```
MorningIntelligenceRunner.run()
  ├── load_env_local()                    # .env.local for launchd
  ├── bootstrap state/ if empty
  ├── network check (api.x.ai + fallback)
  ├── IntelligenceCollector.run_once()    # new episodes only
  ├── ProductionIntelligencePipeline      # analyst + synthesis + production
  ├── FreshnessGate.filter_items()        # drop stale headlines
  ├── ProductionEnhancementLayer.enhance() # brief-first LLM (max 5 items)
  ├── FrontendPublisher.publish()         # latest.* + archive
  └── MorningIntelligenceLogger.finalize()
```

### Output locations

| Artifact | Path |
|----------|------|
| Browser bookmark | `file:///Users/sterlingdigital/Knowledge_Service/frontend/latest.html` |
| Markdown | `frontend/latest.md` |
| JSON | `frontend/data/latest.json` |
| Daily archive | `frontend/archive/YYYY-MM-DD/morning.{html,md,json}` |
| Run summary | `frontend/archive/YYYY-MM-DD/run_summary.json` |
| Run history | `state/production/morning_runs.json` |

### Logs

| Log | Contents |
|-----|----------|
| `~/Library/Logs/pcc/morning-intelligence.log` | Full structured morning run |
| `~/Library/Logs/pcc/morning-preflight.log` | PCC preflight summary line |

### Scheduled production

Triggered by PCC Morning Preflight LaunchAgent at **06:26 local** — not a separate Knowledge_Service LaunchAgent. See [PCC_PREFLIGHT_INTEGRATION.md](PCC_PREFLIGHT_INTEGRATION.md).

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Empty brief | Check network; inspect `config/profiles.json` watch universe |
| Stale headlines | Review freshness gate section in `morning-intelligence.log` |
| No Grok polish | Verify `XAI_API_KEY` in `.env.local`; run `status` for budget metrics |
| Missing HTML | Run `bin/morning-intelligence.sh run` manually; check log for errors |
| Degraded status | Expected when network or LLM fails; heuristic fallback still publishes |

---

## Development Workflow

### Adding a new intelligence discoverer (Phase 3.2 pattern)

1. Implement in `src/knowledge_service/intelligence/discoverers/`
2. Register in `discoverers/registry.py`
3. Add tests in `tests/intelligence/`
4. Run `examples/certify_phase32_runtime.py`
5. Document in `docs/DISCOVERY_ABSTRACTION.md` if behavior is novel

### Adding an analyst engine (Phase 4 pattern)

1. Implement under `src/knowledge_service/analyst/<engine>/`
2. Wire into `analyst/pipeline.py`
3. Add tests in `tests/analyst/`
4. Run `examples/certify_phase4_runtime.py`

### Modifying morning behavior (Phase 6)

1. Edit `production/morning/` modules
2. Add/update tests in `tests/production/`
3. Run `python -m pytest tests/production/test_daily_runner.py -q`
4. Manual verify: `bin/morning-intelligence.sh run` then open `frontend/latest.html`

### LLM provider changes (Phase 5.1+)

1. Implement provider in `production/llm/`
2. Register in `production/llm/registry.py`
3. Configure via `.env.local` / `production/llm/config.py`
4. Test: `tests/production/test_xai_provider.py`, `test_llm_budget.py`, `test_llm_cache.py`
5. Certify: `examples/certify_phase512_runtime.py`

---

## Key Design Constraints (from Phase 0)

When developing, preserve these invariants:

1. **Applications never talk to providers directly** — always through Knowledge_Service layers
2. **Providers are replaceable** — interface contracts in `interfaces/provider.py`
3. **Knowledge is standardized** — all content becomes `KnowledgeObject`
4. **Evidence is first-class** — provenance, confidence, timestamps preserved
5. **Deterministic intelligence first** — LLM only polishes final brief items (Phase 5.1.2 budget)
6. **State is persistent** — dedupe and corpus survive restarts (`state/`)

---

## Python Module Entry Points

| Module | Invocation |
|--------|------------|
| Morning intelligence | `python -m knowledge_service.production.morning` |
| (No HTTP server) | API is spec-only — see [API_SPEC.md](API_SPEC.md) |

---

## Common Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `KNOWLEDGE_SERVICE` | repo path | Root override for `bin/morning-intelligence.sh` |
| `PYTHONPATH` | — | Must include `src/` |
| `XAI_API_KEY` | — | Grok/xAI API key |
| `KNOWLEDGE_LLM_PROVIDER` | `xai_responses` | Primary LLM provider |
| `KNOWLEDGE_LLM_FALLBACK_PROVIDER` | `analyst_heuristic` | Offline/failure fallback |
| `KNOWLEDGE_LLM_MAX_ITEMS` | `5` | Max brief items enhanced |
| `KNOWLEDGE_LLM_MAX_CALLS` | `20` | Per-run LLM call budget |

---

## Documentation Navigation

| Need | Document |
|------|----------|
| Full file index | [REPOSITORY_INDEX.md](REPOSITORY_INDEX.md) |
| Live vs historical | [CURRENT_STATE.md](CURRENT_STATE.md) |
| Architecture layers | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Morning operations | [MORNING_INTELLIGENCE_OPERATIONS.md](MORNING_INTELLIGENCE_OPERATIONS.md) |
| Freshness gate spec | [FRESHNESS_GATE.md](FRESHNESS_GATE.md) |
| LLM budget | [TOKEN_ACCOUNTING.md](TOKEN_ACCOUNTING.md), [LLM_CACHE.md](LLM_CACHE.md) |
| Phase architectures | `docs/PHASE*_ARCHITECTURE.md` |

---

## Quick Verification Checklist

After making changes:

- [ ] `export PYTHONPATH=src`
- [ ] `python -m pytest tests/<relevant>/ -q` passes
- [ ] Relevant `examples/certify_phase*.py` passes (if touching that phase)
- [ ] `bin/morning-intelligence.sh status` shows healthy artifacts
- [ ] No secrets in logs or committed files
- [ ] Update docs if behavior changed (this guide, CURRENT_STATE, or phase doc)