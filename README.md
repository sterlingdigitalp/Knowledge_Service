# Knowledge_Service

An intelligent knowledge acquisition, processing, storage, and retrieval platform. Transforms unstructured information (podcasts, transcripts, web content) into trustworthy, reusable knowledge — culminating in a **daily Morning Intelligence Brief** published to static frontend artifacts.

## Quick Start

```bash
cd Knowledge_Service          # or: cd "$(git rev-parse --show-toplevel)"
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
source .venv/bin/activate
export PYTHONPATH=src

# Canonical verification (one command)
bin/verify.sh

# Run morning intelligence manually
bin/morning-intelligence.sh run
bin/morning-intelligence.sh status
```

**Bookmark (never changes):** `frontend/latest.html` (open via `file://` absolute path on your machine)

See [docs/INSTALL.md](docs/INSTALL.md) for first-time setup and [docs/VERIFY.md](docs/VERIFY.md) for all verification commands.

## What to Read First

| Audience | Document | Purpose |
|----------|----------|---------|
| Vision & principles | [STARTING.md](STARTING.md) | What Knowledge_Service is, immutable design principles, layer model |
| Repository map | [docs/REPOSITORY_INDEX.md](docs/REPOSITORY_INDEX.md) | Every directory, CLI, subsystem, artifact, and doc category |
| Day-to-day development | [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | Setup, test, verify, run morning intelligence, layout |
| What's live today | [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) | Implemented phases vs historical specification docs |

## Repository Layout (Top Level)

```
Knowledge_Service/
├── bin/                    # Shell entrypoints (morning-intelligence.sh)
├── config/                 # Watch-universe profiles (profiles.json/yaml)
├── data/                   # Source route registry (source_routes.json/yaml)
├── docs/                   # 100+ architecture, engine, and certification specs
├── examples/               # Runtime certification scripts (certify_phase*.py)
├── frontend/               # Static Morning Brief UI + latest.* artifacts
├── runtime_evidence/       # Timestamped certification run outputs
├── src/knowledge_service/  # Python package (154 modules)
├── state/                  # Persistent production corpus + analyst artifacts
├── tests/                  # Unit, integration, and production tests (71+ files)
├── integration_tests/      # Cross-subsystem integration tests
├── failure_tests/          # Failure-injection tests
├── performance_tests/      # Performance benchmarks
├── property_tests/         # Fuzz/property tests
└── STARTING.md             # Phase 0 vision and foundation
```

## Subsystems (Live)

| Layer | Package | Role |
|-------|---------|------|
| Acquisition & processing | `processing/`, `providers/`, `planning/` | Transcript → KnowledgeObject pipeline |
| Intelligence collection | `intelligence/` | Profile-driven discovery, dedupe, corpus |
| Personal analyst | `analyst/` | Claims, scoring, cross-source, briefs |
| Intelligence synthesis | `analyst/synthesis/` | Themes, Intelligence Items, Brief v2 |
| Production enhancement | `production/` | Embeddings, LLM polish, personalization, trends, Brief v3 |
| Morning operations | `production/morning/` | Daily runner, freshness gate, publisher |

## Morning Intelligence (Phase 6)

Scheduled via **PCC Morning Preflight** (`06:26` local) or run manually:

```bash
bin/morning-intelligence.sh run          # full daily workflow
bin/morning-intelligence.sh run --mode manual
bin/morning-intelligence.sh status       # JSON status + artifact paths
```

**Outputs:** `frontend/latest.html`, `frontend/latest.md`, `frontend/data/latest.json`  
**Archives:** `frontend/archive/YYYY-MM-DD/`  
**Logs:** `~/Library/Logs/pcc/morning-intelligence.log`

See [docs/MORNING_INTELLIGENCE_OPERATIONS.md](docs/MORNING_INTELLIGENCE_OPERATIONS.md) and [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md).

## Runtime Certification

Phase certification scripts live in `examples/`:

```bash
PYTHONPATH=src python examples/certify_phase512_runtime.py   # latest production cert
PYTHONPATH=src python examples/certify_phase51_runtime.py
PYTHONPATH=src python examples/certify_phase41_runtime.py
# ... see docs/REPOSITORY_INDEX.md for full list
```

Evidence is written to `runtime_evidence/<run_id>/`.

## Environment

Create gitignored `.env.local` at repo root for LLM keys (never committed):

```bash
XAI_API_KEY=...
KNOWLEDGE_LLM_PROVIDER=xai_responses
KNOWLEDGE_LLM_FALLBACK_PROVIDER=analyst_heuristic
KNOWLEDGE_LLM_MAX_ITEMS=5
KNOWLEDGE_LLM_MAX_CALLS=20
```

## Documentation Index

- **104** markdown specs in `docs/` — indexed by category in [docs/REPOSITORY_INDEX.md](docs/REPOSITORY_INDEX.md)
- Phase architecture: `docs/PHASE{3,31,32,4,41,5,51,512}_ARCHITECTURE.md`
- Phase 6 deliverables: [docs/PHASE6_DELIVERABLES.md](docs/PHASE6_DELIVERABLES.md)

## Historical vs Live

Many docs describe design intent from earlier phases. **Do not assume every spec is implemented.**  
See [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) for the authoritative live/historical boundary.