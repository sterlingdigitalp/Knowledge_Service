# Environment Variables

Every environment variable read from `os.environ` or `os.environ.get` under `src/`. Variables loaded generically from `.env.local` via `load_env_local()` are listed in the **Dotenv loader** section.

Shell-only variables (`KNOWLEDGE_SERVICE`, `PYTHONPATH`) are documented in [INSTALL.md](./INSTALL.md) but are not read by Python code in `src/`.

## Summary

| Variable | Default | Required | Count |
|----------|---------|----------|-------|
| LLM / API (13) | see below | `XAI_API_KEY` only when using `xai_responses` | 13 |
| Freshness gate (2) | `7`, `36` | No | 2 |
| Secrets checked at runtime (2) | — | Conditional | 2 |
| **Total unique keys in `src/`** | | | **18** |

---

## LLM provider configuration

Loaded primarily by `knowledge_service.production.llm.config.load_llm_config()` and related modules.

### `KNOWLEDGE_LLM_PROVIDER`

| | |
|---|---|
| **Default** | `analyst_heuristic` |
| **Required** | No |
| **Used in** | `production/llm/config.py`, `production/llm/registry.py` |
| **Effect** | Selects the active LLM backend. Values include `analyst_heuristic` (local, no API), `xai_responses` (Grok via xAI), and `openai_compatible` (when `OPENAI_API_KEY` is set). `get_llm_provider()` reads this on each resolution unless a name is passed explicitly. |

### `KNOWLEDGE_LLM_FALLBACK_PROVIDER`

| | |
|---|---|
| **Default** | `analyst_heuristic` |
| **Required** | No |
| **Used in** | `production/llm/config.py` |
| **Effect** | Provider used when the primary LLM fails or is unavailable. `XAIResponsesProvider` builds its fallback from this value. |

### `KNOWLEDGE_LLM_MODEL`

| | |
|---|---|
| **Default** | `grok-4.3` |
| **Required** | No |
| **Used in** | `production/llm/config.py` |
| **Effect** | Model identifier sent to the xAI Responses API (and exposed in inspector/status output). |

### `XAI_BASE_URL`

| | |
|---|---|
| **Default** | `https://api.x.ai/v1` |
| **Required** | No |
| **Used in** | `production/llm/config.py` |
| **Effect** | Base URL for xAI HTTP requests. Trailing slashes are stripped. |

### `KNOWLEDGE_LLM_TIMEOUT_SECONDS`

| | |
|---|---|
| **Default** | `45` |
| **Required** | No |
| **Used in** | `production/llm/config.py` |
| **Effect** | Per-request HTTP timeout (seconds, float) for live LLM calls. |

### `KNOWLEDGE_LLM_MAX_RETRIES`

| | |
|---|---|
| **Default** | `3` |
| **Required** | No |
| **Used in** | `production/llm/config.py` |
| **Effect** | Maximum retry attempts for transient LLM API failures. |

### `KNOWLEDGE_LLM_RETRY_BACKOFF_SECONDS`

| | |
|---|---|
| **Default** | `1.5` |
| **Required** | No |
| **Used in** | `production/llm/config.py` |
| **Effect** | Base backoff delay (seconds, float) between LLM retries. |

### `KNOWLEDGE_LLM_REASONING_EFFORT`

| | |
|---|---|
| **Default** | `low` |
| **Required** | No |
| **Used in** | `production/llm/config.py` |
| **Effect** | Reasoning effort parameter passed to xAI Responses API requests. |

### `KNOWLEDGE_LLM_TEMPERATURE`

| | |
|---|---|
| **Default** | `0.3` |
| **Required** | No |
| **Used in** | `production/llm/config.py` |
| **Effect** | Sampling temperature for LLM generation (float). |

### `KNOWLEDGE_LLM_PROMPT_VERSION`

| | |
|---|---|
| **Default** | `5.1.2` |
| **Required** | No |
| **Used in** | `production/llm/config.py`, `production/llm/cache.py` |
| **Effect** | Version string included in LLM cache keys. Changing it invalidates cached brief enhancements without deleting `state/production/llm_cache.json`. Read at import time in `cache.py`. |

---

## LLM budget limits

Shared between `production/llm/config.py`, `production/llm/budget.py`, and the production enhancement layer.

### `KNOWLEDGE_LLM_MAX_ITEMS`

| | |
|---|---|
| **Default** | `5` |
| **Required** | No |
| **Used in** | `production/llm/config.py`, `production/llm/budget.py` |
| **Effect** | Maximum number of Morning Brief items that receive **live** (non-cached) Grok/LLM enhancement per run. Additional items use cache or local heuristics. |

### `KNOWLEDGE_LLM_MAX_CALLS`

| | |
|---|---|
| **Default** | `20` |
| **Required** | No |
| **Used in** | `production/llm/config.py`, `production/llm/budget.py` |
| **Effect** | Maximum live LLM HTTP calls per production run. When exhausted, `LLMRuntimeBudget.budget_exhausted` is set and further live calls are skipped. |

### `KNOWLEDGE_LLM_MAX_RUNTIME_SECONDS`

| | |
|---|---|
| **Default** | `300` |
| **Required** | No |
| **Used in** | `production/llm/config.py`, `production/llm/budget.py` |
| **Effect** | Wall-clock budget (seconds, float) for live LLM work in a single run. Exceeding it sets `timed_out` and stops live calls. |

---

## API keys and endpoints

### `XAI_API_KEY`

| | |
|---|---|
| **Default** | *(unset)* |
| **Required** | Yes, when `KNOWLEDGE_LLM_PROVIDER=xai_responses` |
| **Used in** | `production/llm/config.py`, `production/llm/xai_responses.py` |
| **Effect** | Bearer token for xAI API. When missing, `XAIResponsesProvider` reports `unconfigured` and falls back to `KNOWLEDGE_LLM_FALLBACK_PROVIDER`. Never logged or written to state (see `redact_secrets()`). |

### `OPENAI_API_KEY`

| | |
|---|---|
| **Default** | *(unset)* |
| **Required** | Only when using `openai_compatible` provider |
| **Used in** | `production/llm/config.py`, `production/llm/openai_compatible.py`, `production/llm/registry.py` |
| **Effect** | Enables `OpenAICompatibleProvider` when `KNOWLEDGE_LLM_PROVIDER=openai_compatible` or when registry selects that backend. Without it, registry falls back to `AnalystLLMProvider`. |

### `OPENAI_BASE_URL`

| | |
|---|---|
| **Default** | `https://api.openai.com/v1` |
| **Required** | No |
| **Used in** | `production/llm/openai_compatible.py` |
| **Effect** | Base URL for OpenAI-compatible chat completions (supports proxies and alternate gateways). |

---

## Freshness gate

Used by `production/morning/freshness_gate.py` to filter stale intelligence from the daily brief.

### `KNOWLEDGE_FRESHNESS_MAX_AGE_DAYS`

| | |
|---|---|
| **Default** | `7` |
| **Required** | No |
| **Used in** | `production/morning/freshness_gate.py` |
| **Effect** | Maximum age (days) for headline-eligible intelligence items based on supporting claim timestamps. Older items are excluded unless they qualify via new-claim rules. |

### `KNOWLEDGE_FRESHNESS_NEW_CLAIM_HOURS`

| | |
|---|---|
| **Default** | `36` |
| **Required** | No |
| **Used in** | `production/morning/freshness_gate.py` |
| **Effect** | Window (hours) in which newly extracted claims can qualify an item as fresh even when theme-level signal is older. |

---

## Dotenv loader

`production/morning/env.py` → `load_env_local()` reads these files in order (first wins per key; existing `os.environ` values are never overwritten):

1. `<repo>/.env.local`
2. `<repo>/.env`
3. `~/.config/knowledge_service/.env.local`

Any `KEY=VALUE` pair in those files is injected into `os.environ`. Common keys placed there:

```bash
XAI_API_KEY=...
KNOWLEDGE_LLM_PROVIDER=xai_responses
KNOWLEDGE_LLM_FALLBACK_PROVIDER=analyst_heuristic
KNOWLEDGE_LLM_MAX_ITEMS=5
KNOWLEDGE_LLM_MAX_CALLS=20
KNOWLEDGE_FRESHNESS_MAX_AGE_DAYS=7
```

Secret keys (`*api_key*`, `*token*`, `*secret*`) are redacted in loader return values but are set in the process environment.

---

## Variables not in `src/` (reference only)

These appear in tests, examples, or shell scripts but are **not** read by `src/`:

| Variable | Where | Purpose |
|----------|-------|---------|
| `KNOWLEDGE_SERVICE` | `bin/morning-intelligence.sh` | Override project root path |
| `PYTHONPATH` | shell / pytest | Must include `src/` for imports |
| `KNOWLEDGE_SERVICE_PCC_PREFLIGHT` | `tests/production/test_morning_preflight_integration.py` | Override path to PCC preflight script |
| `KNOWLEDGE_SERVICE_CRAWL4AI_ENDPOINT` | `tests/end_to_end/test_real_provider_lifecycle.py` | E2E test Crawl4AI URL |
| `KNOWLEDGE_SERVICE_CRAWL4AI_TOKEN` | `tests/end_to_end/test_real_provider_lifecycle.py` | E2E test auth token |

Provider endpoints for SearXNG (`localhost:8080`) and Crawl4AI (`localhost:11235`) are passed via provider `initialize()` config dicts and route registry JSON/YAML, not environment variables in `src/`.