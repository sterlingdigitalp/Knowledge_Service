# Semantic Clustering

IL2 semantic clustering merges duplicate discussions before canonical resolution and editorial synthesis.

## Engine

`intelligence_v2/semantic_cluster.py`

## Algorithm

1. **Pairwise similarity** across all `IntelligenceItem` pairs
2. **Jaccard token overlap** on title, theme label, and entities
3. **Source overlap** bonus when items share podcast/source
4. **Threshold merge** at `cluster_similarity_threshold` (default 0.62)

### Similarity Formula

```
score = 0.35 × title_jaccard
      + 0.30 × theme_jaccard
      + 0.25 × entity_jaccard
      + 0.10 × source_overlap
```

## Cluster Output

Each cluster receives:

- `cluster_id` — stable hash
- `member_ids` — merged item IDs
- `canonical_member_id` — primary item
- `merged_keywords` / `merged_entities`

## Merge Behavior

When items merge:

- Corroboration count takes the maximum
- Claim counts accumulate
- Sources and speakers deduplicate onto canonical item
- Runtime 1 scores are **not** recalculated (non-invasive)

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `KNOWLEDGE_IL2_CLUSTER_SIM` | 0.62 | Merge threshold |

## Relationship to Runtime 1

Runtime 1 `_dedupe_items()` only dedupes exact title matches. IL2 catches:

- Alias titles (e.g., "Enterprise AI Agents" vs "Agents Better")
- Cross-theme duplicates with overlapping entities
- Repeated podcast topics across episodes