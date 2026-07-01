# Phase 5.1 Runtime Certification

## Command

```bash
python examples/certify_phase51_runtime.py
```

## Prerequisites

- Phase 3.2 seeded corpus at `runtime_evidence/phase32_intelligence_20260701T011651Z/state`
- Environment variables exported (see `PROVIDER_SELECTION.md`)

## Flow

1. Seed real corpus (no fixtures)
2. Run analyst pipeline (deterministic intelligence)
3. Enhance items with `analyst_heuristic`
4. Enhance same items with `xai_responses`
5. Run full production pipeline with configured provider
6. Multi-turn Deep Dive conversation
7. Learning loop + second pipeline run
8. LLM benchmark comparison
9. Runtime inspector with LLM metrics
10. Secret leak scan on all artifacts

## Outputs

Written to `runtime_evidence/phase51_intelligence_<timestamp>/`:

- `PHASE51_RUNTIME_CERTIFICATION.md`
- `BENCHMARK_LLM.json`
- `RUNTIME_INSPECTOR_OUTPUT.json`
- `MORNING_INTELLIGENCE_BRIEF.json`
- `DEEP_DIVE_COMPARISON.md`

## Pass Criteria

- Production inspector status: pass
- Brief v3: 5–10 items, ≤60s reading time
- Multi-turn conversation demonstrated
- LLM provider section present in inspector
- No secrets in artifacts
- LLM benchmark pairs generated