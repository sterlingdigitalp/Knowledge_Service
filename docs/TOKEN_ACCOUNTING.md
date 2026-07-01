# Token Accounting

Phase 5.1 tracks LLM usage in `src/knowledge_service/production/llm/accounting.py`.

## Captured Metrics

Per request:
- Prompt tokens (`input_tokens`)
- Completion tokens (`output_tokens`)
- Total tokens
- Latency (ms)
- Model
- Estimated cost (USD)
- Actual cost when xAI returns `cost_in_usd_ticks` or `cost_in_nano_usd`
- Fallback events
- Retries
- Failure counts

## Persistence

Events append to `state/production/llm_usage.jsonl` when a state directory is bound via the registry.

## Cost Estimation

When xAI returns usage cost fields, those values are used directly.

Otherwise:
- Input: $0.003 / 1K tokens
- Output: $0.015 / 1K tokens

Daily cost estimate equals cumulative estimated cost for the session.

## Inspector

The Phase 5.1 runtime inspector exposes:

- `llm.token_usage`
- `llm.estimated_cost_usd`
- `llm.fallback_events`
- `llm.retries`
- `llm.failure_count`