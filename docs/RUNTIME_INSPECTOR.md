# Runtime Inspector

The Runtime Inspector now exposes both transcript runtime state and Phase 3 intelligence collection state.

## Commands
Standalone Phase 3 inspector:

```bash
PYTHONPATH=src ./.venv/bin/python examples/phase3_runtime_inspector.py --state-dir <state-dir> --format json
```

Integrated runtime inspector:

```bash
PYTHONPATH=src ./.venv/bin/python examples/runtime_inspector.py --format json --phase3-state-dir <state-dir>
```

## Phase 3 Sections
- profiles
- sources
- discovery
- corpus
- runtime
- deduplication
- storage

## Reported Runtime State
- configured/enabled/disabled profiles
- watch-list size and interest count
- people/source graphs
- podcast source statistics
- transcript provider availability
- episodes found, queued, skipped, failed, and already processed
- KnowledgeObjects, chunks, embeddings, transcripts, and growth history
- scheduler status, jobs, queue state, errors, and warnings

## Certification Output
Latest inspector output:
- `runtime_evidence/phase3_intelligence_20260701T002459Z/RUNTIME_INSPECTOR_OUTPUT.json`
- `runtime_evidence/phase3_intelligence_20260701T002459Z/RUNTIME_INSPECTOR_OUTPUT.md`
