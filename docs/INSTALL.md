# First-Time Installation

Portable setup for Knowledge_Service on macOS or Linux. The project uses a local virtual environment and `PYTHONPATH=src` instead of an editable install.

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.11+ | Tested with 3.14; 3.11+ recommended |
| `git` | Clone or copy the repository |
| Docker Desktop (optional) | Required for SearXNG and Crawl4AI when running full acquisition |
| `ffmpeg` (optional) | Needed for `yt-dlp` + Whisper audio transcription fallback |

## 1. Clone and enter the project

```bash
git clone <repository-url> Knowledge_Service
cd Knowledge_Service
```

Or use an existing checkout. All paths below are relative to the repository root.

## 2. Create the virtual environment

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

`requirements.txt` lists direct dependencies inferred from `src/` imports and the current `.venv` freeze. Heavy packages (`torch`, `openai-whisper`) support optional Whisper transcription; the default morning pipeline can run without them if acquisition is skipped or uses caption-only routes.

## 3. Set PYTHONPATH

The package lives under `src/knowledge_service/`. Export the source root before running Python or tests:

```bash
export PYTHONPATH="$(pwd)/src"
```

`bin/morning-intelligence.sh` sets this automatically. `conftest.py` also adds `src/` to `sys.path` for pytest.

## 4. Configure secrets (optional but recommended)

Create a gitignored `.env.local` at the repository root:

```bash
cat > .env.local <<'EOF'
XAI_API_KEY=your-key-here
KNOWLEDGE_LLM_PROVIDER=xai_responses
KNOWLEDGE_LLM_FALLBACK_PROVIDER=analyst_heuristic
EOF
```

The morning runner loads `.env.local`, `.env`, or `~/.config/knowledge_service/.env.local` on startup. See [ENVIRONMENT.md](./ENVIRONMENT.md) for every supported variable.

## 5. External providers (SearXNG + Crawl4AI)

Full acquisition uses two local HTTP services. Defaults match the provider specs:

| Service | Default endpoint | Purpose |
|---------|------------------|---------|
| SearXNG | `http://localhost:8080` | Web search for discovery |
| Crawl4AI | `http://localhost:11235` | Page crawl / render |

Provider endpoints are configured in runtime provider initialization (see `integration_tests/test_end_to_end_lifecycle.py` and `data/source_routes.json`), not via environment variables in `src/`.

### Start with Docker (typical PCC setup)

Ensure Docker Desktop is running, then start the provider containers defined in your PCC/Docker stack. Preflight checks verify:

1. Network connectivity
2. Docker + `searxng` + `crawl4ai` containers healthy
3. Knowledge_Service morning intelligence run

If providers are unavailable, the morning runner degrades gracefully and uses the existing on-disk corpus in `state/`.

### Verify providers manually

```bash
curl -s "http://localhost:8080/search?q=test&format=json" | head
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:11235/health
```

Exact health paths depend on your Crawl4AI deployment; see [providers/SEARXNG_PROVIDER_SPEC.md](./providers/SEARXNG_PROVIDER_SPEC.md) and [providers/CRAWL4AI_PROVIDER_SPEC.md](./providers/CRAWL4AI_PROVIDER_SPEC.md).

## 6. Bootstrap state (first run)

On first run, if `state/` is empty, the morning runner copies seed state from `runtime_evidence/phase512_optimization_20260701T074324Z/state/` or initializes profiles from `config/profiles.json`. See [STATE_AND_ARTIFACTS.md](./STATE_AND_ARTIFACTS.md).

## 7. Run morning intelligence

```bash
bin/morning-intelligence.sh run --mode manual
bin/morning-intelligence.sh status
```

Equivalent Python invocation:

```bash
export PYTHONPATH=src
.venv/bin/python3 -m knowledge_service.production.morning run --mode manual
```

Published artifacts appear under `frontend/` (`latest.html`, `latest.md`, `data/latest.json`).

## 8. Run tests

```bash
export PYTHONPATH=src
.venv/bin/python -m pytest tests/production/ -q
.venv/bin/python -m pytest -q
```

End-to-end provider tests require live SearXNG/Crawl4AI and may be skipped when services are down.

## Shell helper: KNOWLEDGE_SERVICE override

`bin/morning-intelligence.sh` resolves the project root from the script location (`bin/..`). Override for non-standard layouts:

```bash
export KNOWLEDGE_SERVICE=/path/to/Knowledge_Service
bin/morning-intelligence.sh run
```

## Optional packages

| Package | When to install |
|---------|-----------------|
| `PyYAML` | Import profiles or routes from `.yaml` files |
| `sentence-transformers` | Use `sentence_transformers` embedding backend (otherwise `local_neural`) |

```bash
.venv/bin/pip install PyYAML sentence-transformers
```

## Related docs

- [ENVIRONMENT.md](./ENVIRONMENT.md) — environment variables
- [STATE_AND_ARTIFACTS.md](./STATE_AND_ARTIFACTS.md) — `state/`, `frontend/`, `runtime_evidence/`
- [DAILY_MORNING_INTELLIGENCE.md](./DAILY_MORNING_INTELLIGENCE.md) — daily workflow
- [PCC_PREFLIGHT_INTEGRATION.md](./PCC_PREFLIGHT_INTEGRATION.md) — launchd automation