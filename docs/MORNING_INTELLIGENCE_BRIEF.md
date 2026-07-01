# Morning Intelligence Brief

The Morning Intelligence Brief is a ~60-second attention filter that surfaces high-signal claims organized by Intelligence Profile. It is the primary human-facing output of Phase 4.

## Modules

| Path | Class | Role |
|------|-------|------|
| `knowledge_service.analyst.briefing.morning_brief` | `MorningBriefGenerator` | Brief assembly |
| `knowledge_service.analyst.briefing.deep_dive` | `DeepDiveGenerator` | Interactive "Tell me more" |

## Brief Structure

`MorningBrief`:

| Field | Purpose |
|-------|---------|
| `brief_id` | Stable identifier |
| `generated_at` | ISO timestamp |
| `reading_time_seconds` | Estimated read time (30–90s) |
| `sections` | `Dict[profile_name, List[BriefItem]]` |
| `total_items` | Sum of section items |
| `pipeline_run_id` | Link to analyst run |

Section order follows enabled profiles from configuration. Default fallback order: AI, Investing, Founders, Longevity.

## BriefItem Fields

Each item answers four briefing questions:

| Field | Question |
|-------|----------|
| `what_is_new` | What is new? |
| `why_you_see_this` | Why am I seeing this? |
| `why_it_matters` | Why might this matter? |
| `evidence_summary` | What is the evidence? |

Plus provenance: `source`, `source_url`, `timestamp_label`, `claim_id`, scores, and `explainability` payload.

## Selection Algorithm

Per enabled profile:

1. Skip claims already used in another section (`used_claims` set).
2. Exclude `repeat` novelty classification.
3. Exclude `ignore` importance band.
4. Require `importance.score ≥ MIN_IMPORTANCE` (0.35).
5. Require profile relevance `≥ MIN_RELEVANCE` (0.2).
6. Sort by importance score descending.
7. Take top `MAX_ITEMS_PER_SECTION` (2) candidates.

## Reading Time

```text
word_count = sum(headline + what_is_new + why_it_matters words)
reading_time = max(30, min(90, word_count / WORDS_PER_SECOND))
WORDS_PER_SECOND = 3.0
```

## Explainability Requirements

Every `BriefItem.explainability` must include:

```json
{
  "matched": ["interest or participant names"],
  "novelty": "classification value",
  "importance": "band value",
  "corroborated_by": 0,
  "evidence_type": "timestamped_transcript",
  "importance_factors": { "...seven factors..." },
  "novelty_explanation": "..."
}
```

Evidence type is always `timestamped_transcript` — briefing items must cite speaker, timestamp, and verbatim excerpt.

## Deep Dive ("Tell me more")

`DeepDiveGenerator.generate(claim_id)` returns `DeepDiveResponse`:

| Field | Content |
|-------|---------|
| `analyst_summary` | Multi-sentence analyst narrative |
| `transcript_excerpt` | Verbatim claim evidence |
| `surrounding_context` | Adjacent segment window |
| `previous_appearances` | Same speaker + topic prior claims |
| `related_claims` | Semantically similar claims (similarity ≥ 0.45) |
| `corroborating_evidence` | Different-source matches (≥ 0.55) |
| `contradictory_evidence` | From `Contradiction` records |
| `timestamped_sources` | Deep-linkable source references |
| `explainability` | Full novelty, importance, relevance payloads |

Unscored claims receive a `_minimal_response` with transcript evidence only.

## Storage

- Briefs: `state/analyst/morning_briefs.json` (append-only list)
- Latest brief available via `AnalystStore.latest_brief()`

## Certification Artifacts

`examples/certify_phase4_runtime.py` writes:

- `MORNING_INTELLIGENCE_BRIEF.json`
- `MORNING_INTELLIGENCE_BRIEF.md`

## Design Invariant

The brief is a **filter**, not a digest. Low-importance and repeat claims are intentionally suppressed. Empty sections render `_No high-signal items today._` in markdown export.