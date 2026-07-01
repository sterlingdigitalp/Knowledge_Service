# xAI Responses Provider

Phase 5.1 adds native xAI/Grok generation via the Responses API.

## Endpoint

```
POST https://api.x.ai/v1/responses
```

The provider uses the native Responses API — not Chat Completions — unless parsing requires a compatibility fallback shape.

## Class

`XAIResponsesProvider` in `src/knowledge_service/production/llm/xai_responses.py`

## Scope

xAI is used only for human-facing language:

- Theme titles
- Executive summaries
- Deep Dive conversation
- Suggested follow-up questions

Acquisition, claims, novelty, importance, themes, embeddings, and routing remain deterministic.

## Runtime Behavior

- Configurable timeout (default 45s)
- Retries with exponential backoff on 429 and 5xx
- Graceful degradation to `AnalystLLMProvider`
- Malformed or incomplete responses trigger fallback
- Conversation continuity via `previous_response_id`

## Configuration

Read from environment (never hardcoded):

| Variable | Purpose |
|----------|---------|
| `XAI_API_KEY` | API authentication |
| `KNOWLEDGE_LLM_PROVIDER=xai_responses` | Select provider |
| `XAI_BASE_URL` | API base (default `https://api.x.ai/v1`) |
| `KNOWLEDGE_LLM_MODEL` | Model (default `grok-4.3`) |
| `KNOWLEDGE_LLM_FALLBACK_PROVIDER` | Fallback (default `analyst_heuristic`) |

## Security

Secrets are never logged, serialized in inspector output, or written to certification artifacts.