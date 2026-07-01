# Phase 5.1 Architecture

Phase 5.1 replaces heuristic language generation with production xAI/Grok while preserving every upstream subsystem.

## Unchanged

- Acquisition
- Claims extraction
- Novelty and importance scoring
- Theme discovery and evolution
- Neural embeddings
- Personalization and ranking
- Morning Brief v3 selection logic
- Scheduler

## Changed

Only the final human-facing language layer:

```
Intelligence Items (deterministic)
        ↓
ProductionEnhancementLayer._enhance_items()
        ↓
LLM Provider (config-selected)
        ↓
Theme titles + executive summaries
        ↓
Morning Brief v3 + Deep Dive v3
```

## Provider Stack

```
get_llm_provider()
    → XAIResponsesProvider
        → POST /v1/responses
        → accounting + retries
        → AnalystLLMProvider (fallback)
```

## New Modules

| Module | Role |
|--------|------|
| `llm/xai_responses.py` | Native xAI provider |
| `llm/prompts.py` | Analyst prompt library |
| `llm/config.py` | Environment configuration |
| `llm/accounting.py` | Token and cost tracking |
| `benchmark_llm.py` | Heuristic vs xAI comparison |
| `inspector.py` | Phase 5.1 LLM health section |

## Conversation Continuity

Deep Dive sessions store `last_response_id` from xAI and pass `previous_response_id` on follow-up turns.