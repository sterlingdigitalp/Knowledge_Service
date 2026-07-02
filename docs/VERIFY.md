# Verification — Canonical Commands

One command verifies the repository after health, hardening, or principal-engineer changes.

## Quick Verify

```bash
cd Knowledge_Service
bin/verify.sh
```

**Exit 0** = all required steps passed. Integration SearXNG skips are OK.

## Full Verify (includes slow certifier)

```bash
VERIFY_FULL=1 bin/verify.sh
```

Adds `examples/certify_phase51_runtime.py` (~20–30s).

---

## What `bin/verify.sh` Runs

| Step | Command | Expected |
|------|---------|----------|
| 1. Syntax | `python -m compileall -q src/knowledge_service` | Exit 0 |
| 2. Offline tests | `pytest tests/ failure_tests/ property_tests/ performance_tests/` | All pass (~600+) |
| 3. Smoke | `pytest tests/smoke/` | 5 pass |
| 4. Production | `pytest tests/production/` | 62 pass |
| 5. Intelligence | `pytest tests/intelligence/` | 22 pass |
| 6. Integration | `pytest integration_tests/` | Pass; up to 3 SearXNG skips |
| 7. Runtime inspector | `examples/runtime_inspector.py --format json --timeout-ms 30000` | `status: pass`, 5/5 checks |
| 8. Morning CLI | `bin/morning-intelligence.sh status` | Valid JSON, all artifacts true |
| 9. Phase 5.1 cert | `certify_phase51_runtime.py` | PASS (only with `VERIFY_FULL=1`) |

---

## Individual Commands

### Offline full suite

```bash
export PYTHONPATH=src
.venv/bin/python -m pytest tests/ failure_tests/ property_tests/ performance_tests/ -q
```

### Smoke tests

```bash
.venv/bin/python -m pytest tests/smoke/ -q
```

### Production tests

```bash
.venv/bin/python -m pytest tests/production/ -q
```

### Intelligence tests

```bash
.venv/bin/python -m pytest tests/intelligence/ -q
```

### Integration (provider-aware)

```bash
.venv/bin/python -m pytest integration_tests/ -q -rs
```

**Expected skips** when SearXNG engines are suspended:

```
SKIPPED: SearXNG at http://localhost:8080 returned zero results.
Unresponsive engines: [['brave', '...'], ['duckduckgo', 'CAPTCHA'], ...]
```

### Transcript certification subset

```bash
.venv/bin/python -m pytest \
  tests/processing/test_transcript.py \
  tests/providers/test_transcript_provider.py \
  tests/retrieval/test_quote_search.py \
  tests/end_to_end/test_transcript_citation_lifecycle.py -q
```

### Runtime inspector

```bash
.venv/bin/python examples/runtime_inspector.py --format json --timeout-ms 30000
```

### Morning intelligence

```bash
bin/morning-intelligence.sh status
bin/morning-intelligence.sh run --mode manual   # full run; requires network
```

### Phase certification scripts

| Script | Phase |
|--------|-------|
| `examples/certify_phase31_runtime.py` | 3.1 |
| `examples/certify_phase32_runtime.py` | 3.2 |
| `examples/certify_phase41_runtime.py` | 4.1 |
| `examples/certify_phase4_runtime.py` | 4 |
| `examples/certify_phase51_runtime.py` | 5.1 |
| `examples/certify_phase512_runtime.py` | 5.1.2 |
| `examples/certify_phase511_live.py` | 5.1.1 live xAI (requires `XAI_API_KEY`) |

### Collect test count

```bash
.venv/bin/python -m pytest --collect-only -q
```

---

## PASS / FAIL Criteria

| Result | Meaning |
|--------|---------|
| **PASS** | Zero pytest failures across all suites; inspector `pass`; morning status OK |
| **SKIP (OK)** | SearXNG integration tests skip when engines return zero results |
| **FAIL** | Any pytest failure, inspector check failure, or morning status error |

---

## Provider Requirements (Integration)

| Provider | Endpoint | Required for |
|----------|----------|--------------|
| SearXNG | `http://localhost:8080` | 3 integration tests (skip if engines down) |
| Crawl4AI | `http://localhost:11235` | Crawl integration tests (skip if down) |

See [INSTALL.md](INSTALL.md) for provider setup.

---

## Environment

Verification uses `PYTHONPATH=src` and `.venv/bin/python` when present. No secrets required for standard verify (heuristic LLM provider).

See [ENVIRONMENT.md](ENVIRONMENT.md) for optional variables.