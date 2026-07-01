# Provider Selection

The LLM registry selects the active provider entirely from configuration.

## Registry

```
LLM Provider
├── XAIResponsesProvider      (xai_responses)
├── OpenAICompatibleProvider  (openai_compatible)
└── AnalystLLMProvider        (analyst_heuristic)
```

## Selection

```python
from knowledge_service.production.llm.registry import get_llm_provider, configure_llm

provider = get_llm_provider()  # reads KNOWLEDGE_LLM_PROVIDER
provider = configure_llm("xai_responses")  # explicit override
```

## Defaults

| `KNOWLEDGE_LLM_PROVIDER` | Requirement |
|--------------------------|-------------|
| `analyst_heuristic` | None (default) |
| `xai_responses` | `XAI_API_KEY` |
| `openai_compatible` | `OPENAI_API_KEY` |

## Fallback

`XAIResponsesProvider` and `OpenAICompatibleProvider` delegate to `KNOWLEDGE_LLM_FALLBACK_PROVIDER` (default `analyst_heuristic`) on:

- Missing API key
- Timeout
- Rate limit exhaustion
- Server errors
- Empty or malformed responses

Fallback never interrupts the intelligence pipeline.