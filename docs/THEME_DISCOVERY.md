# Theme Discovery

Theme Discovery clusters semantically related claims into emergent themes. Themes are **not** drawn from a hardcoded topic list — labels, keywords, and entities emerge from claim content at runtime.

Themes are the bridge between atomic claims and Intelligence Items in Phase 4.1.

## Module

| Path | Class |
|------|-------|
| `knowledge_service.analyst.synthesis.themes.discovery` | `ThemeDiscoveryEngine` |

## Theme Model

| Field | Purpose |
|-------|---------|
| `theme_id` | Stable ID from label and top source IDs |
| `label` | Emergent human-readable theme name (≤ 60 chars) |
| `claim_ids` | All member claim IDs |
| `keywords` | Top token frequencies (up to 8) |
| `entities` | Top named entities (up to 6) |
| `source_count` | Distinct `episode_id` count |
| `speaker_count` | Distinct non-unknown speakers |
| `centroid_embedding` | Mean embedding vector for evolution matching |
| `created_at` | ISO timestamp |

## Candidate Filtering

Only claims passing all gates enter clustering:

| Gate | Condition |
|------|-----------|
| Novelty | `classification != repeat` |
| Importance band | `band != ignore` |
| Importance score | `score ≥ 0.35` |

## Clustering Algorithm

Greedy first-match clustering over filtered candidates:

1. For each candidate, compute or reuse claim embedding.
2. Compare against each existing group's representative (first member).
3. Assign to first group where `cosine_similarity ≥ THEME_CLUSTER_THRESHOLD` (0.50).
4. Otherwise start a new group.

After grouping, emit `Theme` only when `len(members) ≥ MIN_THEME_CLAIMS` (3).

Themes are sorted by claim count descending.

## Emergent Label Generation

`_emergent_label()` derives label parts from member claims:

| Signal | Use |
|--------|-----|
| Topics | Most frequent non-`general` topic → primary label part |
| Entities | Most frequent entity when no topic dominates |
| Keywords | Token frequency after stopword removal → secondary part |

Label assembly:

1. Primary: top topic, else top entity
2. Secondary: top keyword (title-cased), avoiding duplicate of primary
3. Fallback: `"Emerging Development"` or top-3 title-cased keywords

Stopwords and tokens ≤ 2 characters are excluded. A curated `STOPWORDS` set filters common function words.

## Centroid Embedding

Theme centroid is the arithmetic mean of member claim embeddings. Centroids power theme evolution matching in `ThemeEvolutionEngine`.

## Thresholds Summary

| Constant | Value |
|----------|-------|
| `THEME_CLUSTER_THRESHOLD` | 0.50 |
| `MIN_THEME_CLAIMS` | 3 |
| Candidate importance floor | 0.35 |

## Relationship to Cross-Source Clustering

| Engine | Threshold | Min members | Purpose |
|--------|-----------|-------------|---------|
| Theme Discovery | 0.50 | 3 claims | Emergent topic themes for synthesis |
| Cross-Source | 0.58 | 2 episodes | Independent source corroboration |

Themes use a lower similarity threshold and claim-count gate. Cross-source clusters require independent episodes. Both feed `IntelligenceItemEngine` — themes first, then unconsumed clusters.

## Storage

Current themes: `state/analyst/synthesis/themes.json`

```json
{ "themes": [ { "theme_id": "...", "label": "...", "claim_ids": [...] } ] }
```

Themes are merged with historical snapshots on each synthesis run (see `THEME_EVOLUTION.md`).

## Runtime Inspector

`analyst.synthesis` reports:

- `themes` — total theme count
- `theme_labels` — top 10 labels
- `compression_ratio` — claims-to-items ratio

## Pipeline Position

```text
Scored Claims (merged, post-corroboration)
  ↓
ThemeDiscoveryEngine.discover()
  ↓
Themes (current run)
  ↓
ThemeEvolutionEngine.evaluate()
  ↓
Theme history merge + persist
```

## Design Invariant

Themes must be **emergent** — no predefined taxonomy. Labels derive from corpus token, entity, and topic distributions. Empty candidate sets produce zero themes (certification blocker).

## Entry Point

```python
from knowledge_service.analyst.synthesis.themes.discovery import ThemeDiscoveryEngine

engine = ThemeDiscoveryEngine()
themes = engine.discover(scored_claims)
```