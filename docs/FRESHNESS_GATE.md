# Freshness Gate

The freshness gate ensures Morning Brief headlines reflect **genuinely new** intelligence — never stale interviews repackaged as today's news.

## Rules

1. Headline items must tie to **new acquisitions**, **new claims**, or **active theme evolution**
2. `repeat` novelty with low score is **rejected**
3. Source material older than `KNOWLEDGE_FRESHNESS_MAX_AGE_DAYS` (default **7**) cannot headline
4. Historical transcripts may appear only as supporting context inside eligible items
5. Every eligible item must answer: **"Why does this matter TODAY?"**

## Eligibility Signals

| Signal | Reason code |
|--------|-------------|
| Supporting claim from newly processed episode | `new_acquisition` |
| Supporting claim extracted this run | `new_claim` |
| Theme evolution: new / strengthening / material_change / contradicting | `theme_evolution` |
| High novelty + recent source material | `high_novelty_recent` |

## Rejection Signals

| Signal | Reason code |
|--------|-------------|
| Repeat novelty, no new episode | `repeat_no_new_signal` |
| Source material older than max age | `stale_source_material` |
| No today signal | `no_today_signal` |

## Empty Signal Brief

When **zero** items pass the gate:

- Publish explicit **"No significant new intelligence today"** edition
- `empty_signal: true` in `frontend/data/latest.json`
- **Never** backfill with stale ranked items

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `KNOWLEDGE_FRESHNESS_MAX_AGE_DAYS` | 7 | Maximum source age for headlines |
| `KNOWLEDGE_FRESHNESS_NEW_CLAIM_HOURS` | 36 | New-claim window reference |

Implementation: `src/knowledge_service/production/morning/freshness_gate.py`