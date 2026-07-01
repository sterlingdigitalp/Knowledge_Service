# Claim Extraction

Phase 4 converts processed transcript KnowledgeObjects into atomic, timestamped **Claims** suitable for novelty scoring, relevance matching, and briefing citations.

## Module

| Path | Class |
|------|-------|
| `knowledge_service.analyst.claims.extractor` | `ClaimExtractor` |

## Inputs

Claim extraction consumes Phase 3.2 acquisition output without redesigning acquisition:

- **KnowledgeObjects** (`type == "document"`) with `structured_data.transcript_segments`
- **Episode metadata** from `episodes.json` (profile, participants, route confidence)
- **Intelligence Profiles** (interests and watch-list names for entity/topic inference)

Provenance fields flow directly from corpus objects:

| Claim field | Source |
|-------------|--------|
| `episode_id`, `event_id` | KnowledgeObject metadata / episode record |
| `source_url`, `transcript_reference` | Document source URL + `timestamped_source_url()` |
| `route_confidence` | Information event / episode acquisition metadata |
| `participants` | Event participants or matched watch entries |
| `podcast_name` | Metadata show name or episode venue |
| `knowledge_object_id` | KnowledgeObject `id` |

## Algorithm

1. Iterate transcript segments from each processed document.
2. Split segment text into atomic sentences via `SENTENCE_SPLIT_RE` (`.!?` boundaries).
3. Filter filler utterances (`FILLER_RE`) and sentences shorter than `MIN_CLAIM_CHARS` (35).
4. Extract entities from watch-list names and capitalized proper-noun patterns (`ENTITY_RE`).
5. Infer topic from profile interests, falling back to first entity or `"general"`.
6. Compute claim confidence from speaker confidence, transcript confidence, and sentence length.
7. Embed claim text via `embed_text()` for downstream semantic engines.
8. Emit one `Claim` per qualifying sentence.

## Confidence Formula

```text
confidence = min(0.99, 0.45 + 0.25 × speaker_conf + 0.20 × transcript_conf + 0.10 × length_factor)
length_factor = min(1.0, len(sentence) / 120)
```

Default segment confidences when absent: `speaker_confidence = 0.7`, `transcript_confidence = 0.75`.

## Claim Identity

`claim_id` is a stable hash of:

```text
episode_id + segment_id + speaker + timestamp_start + claim_text[:200]
```

Duplicate sentences across pipeline runs are deduplicated at the store layer.

## Surrounding Context

Each claim carries a one-segment window of adjacent transcript text (`supporting_context`) formatted as `speaker: text` lines. Deep Dive and briefing evidence use this context.

## Corpus Entry Point

```python
ClaimExtractor().extract_from_corpus(knowledge_objects, episodes, profiles)
```

Only `EpisodeStatus.PROCESSED` episodes are considered by the pipeline orchestrator. Extraction is idempotent: previously stored `claim_id` values are not re-scored.

## Explainability Requirements

Every extracted claim must include:

- Verbatim `claim_text` and `evidence` (same sentence)
- `timestamp_label` and `transcript_reference` (deep-linkable URL when source supports timestamps)
- `speaker`, `topic`, `entities`
- `confidence` with deterministic derivation inputs
- Full acquisition provenance (`source_id`, `route_confidence`, `published_at`)

## Storage

Claims persist to `state/analyst/claims.jsonl` via `AnalystStore.append_claims()`.