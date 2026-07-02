# Daily Morning Intelligence

Phase 6 publishes a static Morning Intelligence edition every day via the PCC Morning Preflight orchestration.

## User Workflow

```
Wake up
  ↓
Open bookmark: file:///Users/sterlingdigital/Knowledge_Service/frontend/latest.html
  ↓
Read Morning Intelligence
  ↓
Copy AI Prompt → Paste into Grok
  ↓
Done
```

No localhost, npm, or development server is required.

## Daily Runner

Entry point:

```bash
/Users/sterlingdigital/Knowledge_Service/bin/morning-intelligence.sh run --mode scheduled
```

Python module equivalent:

```bash
cd /Users/sterlingdigital/Knowledge_Service
export PYTHONPATH=src
.venv/bin/python3 -m knowledge_service.production.morning run
```

## Pipeline Stages

1. Load `.env.local` (gitignored) when launchd cannot inherit shell environment
2. Verify network connectivity
3. Acquire **only new** information (deduplicated collection)
4. Run deterministic analyst + synthesis pipeline on corpus
5. Apply **freshness gate** to ranked Intelligence Items
6. Select final Morning Brief items
7. Grok enhancement on **final selected items only** (Phase 5.1.2 budget)
8. Publish `latest.html`, `latest.md`, `frontend/data/latest.json`
9. Archive edition under `frontend/archive/YYYY-MM-DD/`
10. Write runtime logs and exit cleanly

## Manual Commands

| Command | Purpose |
|---------|---------|
| `bin/morning-intelligence.sh run` | Full manual run (same as scheduled) |
| `bin/morning-intelligence.sh run --mode manual` | Explicit manual mode |
| `bin/morning-intelligence.sh status` | Artifact + last-run status |

## Failure Handling

| Failure | Behavior |
|---------|----------|
| Acquisition fails | Use existing corpus; degraded briefing |
| Grok fails | Cache → heuristic fallback |
| No fresh signal | Explicit empty-signal brief (no stale headlines) |
| LLM budget exhausted | Stop enhancement; finalize artifacts immediately |

The Morning Brief **always** exists after a run.