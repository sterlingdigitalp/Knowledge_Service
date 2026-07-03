# PCC / Hermes Data Audit

Audit of historical intelligence artifacts for IL2 evaluation corpus construction.

## Repositories Discovered

| Repository | Path | Role |
|------------|------|------|
| Knowledge_Service | `/Users/sterlingdigital/Knowledge_Service` | Primary intelligence pipeline |
| FEGOS | `/Users/sterlingdigital/FEGOS` | Editorial factory |
| hermes-peptide-intelligence | `/Users/sterlingdigital/hermes-peptide-intelligence` | Hermes swarm + PCC bridge |
| PCC (legacy) | `/Users/sterlingdigital/Documents/Codex/2026-06-15/you-are-working-from-the-existing/` | Daily run source (not at repo root) |

## Historical Datasets

### Knowledge_Service

| Artifact | Path | Content |
|----------|------|---------|
| Latest brief JSON | `frontend/data/latest.json` | 5 brief items (2026-07-02) — primary eval corpus |
| Latest HTML/MD | `frontend/latest.html`, `frontend/latest.md` | Published morning brief |
| Production state | `state/production/` | Run history, brief snapshots |
| Analyst state | `state/analyst/`, `state/synthesis/` | Claims, themes, items |

### FEGOS

| Artifact | Path | Content |
|----------|------|---------|
| Daily manifest | `output/daily/2026-06-29-manifest.json` | 12 editorial candidates |
| Observations | `output/debug/2026-06-30-observations.json` | Raw signal observations |
| Execution logs | `output/logs/*-execution-log.json` | Factory run traces |
| Editorial dojo | `output/editorial_dojo/benchmark_dataset_001_reviews.json` | Human review benchmarks |

### Hermes Peptide Intelligence

| Artifact | Path | Content |
|----------|------|---------|
| PCC bridge | `search_agent/services/watch_list_processor.py` | `normalized_title()`, `is_generic_title()` |
| Writing intelligence | `search_agent/services/writing_intelligence_engine.py` | Draft quality gates |
| Manual ingest | `manual_ingest/processed/*.md` | Research packets |
| Verification scripts | `scripts/verify_production_v21_integration.py` | V2.1 gate patterns |

### PCC Logs

| Artifact | Path |
|----------|------|
| PCC logs | `~/Library/Logs/pcc/` |

## Corpus Built

`data/intelligence_v2/evaluation_corpus/manifest.json` — ingested from:

- Knowledge_Service `frontend/data/latest.json` (5 samples)
- FEGOS daily manifest and observations (when present)

## Quality Labels

| Sample | Label | Failure Modes |
|--------|-------|---------------|
| Visit Mercury | bad | fm_sponsor_cta, fm_speech_fragment |
| Figure Where | bad | fm_speech_fragment |
| Welcome Developments | bad | fm_intro_filler, fm_developments_suffix |
| Enterprise AI Agents | mixed | fm_pattern_overmatch |
| Roman Empire | mixed | (resolved well by IL2) |

## High-Value Examples

- **Worst:** Visit Mercury — sponsor read as intelligence
- **Worst:** Welcome Developments — intro filler as theme
- **Best (post-IL2):** Byzantine Empire Historical Analysis — evidence-aligned canonical title

## Regressions Observed

- Runtime 1 quality_score = 1.0 despite fragment titles (scoring does not measure editorial quality)
- `analyst_heuristic` LLM active; live Grok not in publication path
- No title validation gate before `MorningBriefV3Generator`