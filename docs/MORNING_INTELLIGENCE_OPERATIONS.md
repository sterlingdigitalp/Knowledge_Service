# Morning Intelligence Operations

## Output Files (updated every successful run)

| File | URL |
|------|-----|
| `frontend/latest.html` | `file:///Users/sterlingdigital/Knowledge_Service/frontend/latest.html` |
| `frontend/latest.md` | Markdown edition |
| `frontend/data/latest.json` | Machine-readable payload |

Bookmark **never changes** — always `latest.html`.

## Archive Structure

```
frontend/archive/YYYY-MM-DD/
  morning.html
  morning.md
  morning.json
  run_summary.json
```

Archives are created automatically on each publish.

## Persistent State

| Path | Purpose |
|------|---------|
| `Knowledge_Service/state/` | Production corpus + analyst + production artifacts |
| `config/profiles.json` | Watch universe profiles |
| `data/source_routes.json` | Acquisition route registry |

State bootstraps from Phase 5.1.2 runtime evidence on first run if empty.

## Environment

Create gitignored `Knowledge_Service/.env.local`:

```bash
XAI_API_KEY=...
KNOWLEDGE_LLM_PROVIDER=xai_responses
KNOWLEDGE_LLM_FALLBACK_PROVIDER=analyst_heuristic
KNOWLEDGE_LLM_MAX_ITEMS=5
KNOWLEDGE_LLM_MAX_CALLS=20
```

Secrets are never logged or printed.

## LLM Budget (Phase 5.1.2)

- Deterministic intelligence first
- Grok edits **only** final selected Morning Brief items (max 5)
- Cache-first enhancement
- Deep Dive remains on-demand only

## Runtime Inspection

```bash
bin/morning-intelligence.sh status
```

Returns artifact presence, last run summary, and public LLM configuration.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Empty brief every day | Acquisition connectivity; watch universe sources |
| Stale headlines | Freshness gate logs in `morning-intelligence.log` |
| No Grok polish | `XAI_API_KEY` in `.env.local`; budget metrics in status |
| Missing HTML | `bin/morning-intelligence.sh run` manually; inspect log |