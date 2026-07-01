# Intelligence Items

Intelligence Items are the primary user-facing unit in Phase 4.1. Each item merges multiple related claims into a single coherent **development** — a synthesized signal with executive summary, evidence, corroboration, contradictions, and theme context.

Phase 4 briefed individual claims. Phase 4.1 briefs Intelligence Items, achieving 10:1+ compression from claims to developments.

## Module

| Path | Class |
|------|-------|
| `knowledge_service.analyst.synthesis.items.engine` | `IntelligenceItemEngine` |

## IntelligenceItem Model

| Field | Purpose |
|-------|---------|
| `item_id` | Stable ID from theme label and theme ID |
| `title` | Theme or cluster label |
| `executive_summary` | Multi-source development narrative |
| `why_surfaced` | Matched keywords/entities + theme evolution |
| `why_it_matters` | Importance explanation + corroboration + contradictions |
| `novelty_score` | Average novelty across supporting claims |
| `novelty_classification` | Dominant novelty class among members |
| `importance_score` | Average importance across supporting claims |
| `importance_band` | Band of highest-importance member |
| `confidence` | Composite synthesis confidence (0–0.99) |
| `corroboration_count` | Independent source corroboration |
| `contradiction_count` | Surfaced contradiction records |
| `theme_id` / `theme_label` | Parent theme linkage |
| `profile_ids` / `profile_names` | Profiles with relevance ≥ 0.35 |
| `supporting_claim_ids` | All merged claim IDs |
| `supporting_evidence` | Up to 6 excerpted evidence records |
| `timestamped_citations` | Deep-linkable source references |
| `speakers` / `sources` | Distinct voices and podcasts |
| `contradictions` | Up to 5 contradiction payloads |
| `historical_developments` | Prior theme evolution context |
| `theme_evolution` | Current `ThemeEvolution` record |
| `cluster_id` | Cross-source cluster when applicable |
| `star_rating` | 1–5 stars from importance score |
| `claim_count` | Number of synthesized claims |

## Synthesis Algorithm

`IntelligenceItemEngine.synthesize()` runs in two passes:

### Pass 1 — Theme-based items

For each discovered `Theme`:

1. Load member `ScoredClaim` records by `theme.claim_ids`.
2. Skip themes with fewer than `MIN_THEME_CLAIMS` (3) members.
3. Build item via `_build_item()`.
4. Emit only when `importance_score ≥ MIN_ITEM_IMPORTANCE` (0.55).
5. Mark theme claim IDs as consumed.

### Pass 2 — Cluster-based items

For each `CorroborationCluster` not fully consumed:

1. Load member claims not already in a theme item.
2. Skip clusters with fewer than `MIN_ITEM_CLAIMS` (2) members.
3. Create a pseudo-theme from `cluster.topic_label`.
4. Build item; emit when importance threshold met and title not duplicated.

### Deduplication

Items with identical titles (case-insensitive) are collapsed — theme items take precedence over cluster items.

## Item Construction (`_build_item`)

| Step | Behavior |
|------|----------|
| Ranking | Members sorted by importance score descending |
| Profiles | Collect profiles where `relevance.score ≥ 0.35` |
| Corroboration | Max of member `corroboration_count` and cluster count |
| Contradictions | All member contradiction records aggregated |
| Novelty | Average score; dominant classification by vote |
| Importance | Average score; band from top member |
| Evidence | Up to 6 claims with excerpt, speaker, timestamp |
| Historical | Prior theme ID and evolution state when available |

### Executive Summary Template

```text
{label}: {N} independent source(s) (including {speakers}) discussed this development
across {claim_count} related claims. Key signal: {lead_claim_excerpt}
```

### Why It Matters

Combines:

1. Top claim's `importance.explanation`
2. Corroboration sentence when `corroboration_count > 0`
3. Contradiction count when conflicts exist
4. Contradiction novelty flag when dominant class is `contradiction`

## Confidence Formula

```text
confidence = min(0.99, 0.4 + avg_importance × 0.3 + min(corroboration, 4) × 0.08 + len(sources) × 0.05)
```

## Star Rating

| Importance Score | Stars |
|------------------|-------|
| ≥ 0.85 | ★★★★★ (5) |
| ≥ 0.72 | ★★★★☆ (4) |
| ≥ 0.58 | ★★★☆☆ (3) |
| ≥ 0.45 | ★★☆☆☆ (2) |
| < 0.45 | ★☆☆☆☆ (1) |

## Thresholds Summary

| Constant | Value | Purpose |
|----------|-------|---------|
| `MIN_THEME_CLAIMS` | 3 | Minimum claims for theme-based item |
| `MIN_ITEM_CLAIMS` | 2 | Minimum claims for cluster-based item |
| `MIN_ITEM_IMPORTANCE` | 0.55 | Minimum average importance to emit |
| Profile relevance gate | ≥ 0.35 | Profile association on item |

## Storage

Items persist to `state/analyst/synthesis/intelligence_items.json`:

```json
{ "items": [ { "item_id": "...", "title": "...", ... } ] }
```

## Pipeline Position

```text
Scored Claims + Themes + Clusters + Theme Evolutions
  ↓
IntelligenceItemEngine.synthesize()
  ↓
Intelligence Items (persisted)
  ↓
IntelligenceBriefGenerator (Morning Brief v2)
```

## Explainability Invariant

Every Intelligence Item must carry:

- Verbatim transcript excerpts with speaker and timestamp
- Explicit corroboration and contradiction counts
- Theme evolution context when historical match exists
- Profile match explanation in `why_surfaced`
- Full factor provenance via supporting claim novelty/importance payloads (in Deep Dive v2)

## Entry Point

```python
from knowledge_service.analyst.synthesis.items.engine import IntelligenceItemEngine

engine = IntelligenceItemEngine()
items = engine.synthesize(scored_claims, themes, clusters, theme_evolutions)
```