# Morning Intelligence Brief v2

Morning Intelligence Brief v2 is the Phase 4.1 human-facing output. It surfaces **Intelligence Items** — synthesized developments — not individual claims. Target reading time is ~60 seconds with 5–15 items and 10:1+ claim compression.

Phase 4 `MorningBrief` (claim-level, profile sections) remains available. Brief v2 is the certified primary output for Phase 4.1.

## Modules

| Path | Class | Role |
|------|-------|------|
| `knowledge_service.analyst.synthesis.briefing.morning_brief_v2` | `IntelligenceBriefGenerator` | Brief v2 assembly |
| `knowledge_service.analyst.synthesis.briefing.deep_dive_v2` | `IntelligenceDeepDiveGenerator` | "Tell me more" for items |

## IntelligenceBrief Structure

| Field | Purpose |
|-------|---------|
| `brief_id` | Stable identifier |
| `generated_at` | ISO timestamp |
| `reading_time_seconds` | Estimated read time (45–60s) |
| `total_items` | Selected entry count |
| `items` | Flat list of `IntelligenceBriefEntry` |
| `compression_ratio` | `claims_synthesized / total_items` |
| `claims_synthesized` | Input claim count for ratio |
| `pipeline_run_id` | Link to analyst run |
| `version` | `"2.0"` |

Unlike v1, brief v2 uses a **flat ranked list** rather than profile-organized sections. Profile association is preserved per entry.

## IntelligenceBriefEntry Fields

Each entry answers four briefing questions:

| Field | Question |
|-------|----------|
| `what_changed` | What changed? (from `executive_summary`) |
| `why_you_care` | Why should I care? (from `why_it_matters`) |
| `why_surfaced` | Why am I seeing this? |
| `evidence_summary` | What is the evidence? |

Plus: `title`, `star_rating`, `importance_band`, `corroborated_by`, `intelligence_item_id`, `profile_id`, `profile_name`, and `explainability`.

## Selection Algorithm

1. Rank all Intelligence Items by `(importance_score, corroboration_count, star_rating)` descending.
2. Convert each item to `IntelligenceBriefEntry` via `_to_entry()`.
3. Accumulate entries until `MAX_ITEMS` (15) or word budget exhausted.
4. Skip entries that would exceed `MAX_WORDS` once `MIN_ITEMS` (5) are selected.
5. If still below `MIN_ITEMS`, backfill from ranked list (ignore word budget).

### Word Budget

```text
TARGET_READING_SECONDS = 60
WORDS_PER_SECOND       = 3.2
MAX_WORDS              = 192  (60 × 3.2)
```

Word count per entry: `title + what_changed + why_you_care + why_surfaced`.

### Reading Time

```text
reading_time = max(45, min(60, int(word_budget / WORDS_PER_SECOND) + 5))
```

Certification enforces `reading_time_seconds ≤ 60`.

## Item Count Bounds

| Constant | Value |
|----------|-------|
| `MIN_ITEMS` | 5 |
| `MAX_ITEMS` | 15 |

Certification fails when `total_items < 5` or `total_items > 15`.

## Explainability Payload

Every entry's `explainability` includes:

```json
{
  "matched": "theme label",
  "keywords": ["top evidence excerpts"],
  "novelty": "classification value",
  "importance": "band value",
  "corroborated_by": 0,
  "historical_context": [],
  "evidence_type": "timestamped_transcript_citations",
  "claim_count": 4,
  "confidence": 0.72
}
```

Evidence type is `timestamped_transcript_citations` — items must cite speakers and sources via synthesized evidence records.

## Deep Dive v2 ("Tell me more")

`IntelligenceDeepDiveGenerator.generate(intelligence_item_id)` returns `IntelligenceDeepDive`:

| Field | Content |
|-------|---------|
| `analyst_briefing` | Markdown analyst narrative with stars, confidence, evolution |
| `executive_summary` | Item executive summary |
| `supporting_claims` | Full claim payloads with novelty/importance |
| `historical_context` | Theme evolution records |
| `contradictions` | Item contradiction list |
| `corroboration` | Independent voice mapping |
| `related_transcripts` | Timestamped citation URLs |
| `timeline` | Chronological claim events |
| `timestamped_sources` | Deep-linkable references |
| `theme_evolution` | Evolution state and explanation |
| `explainability` | Scores, theme ID, cluster ID, claim count |

Entry point via orchestrator:

```python
pipeline.intelligence_deep_dive(brief.items[0].intelligence_item_id)
```

## Storage

Briefs append to `state/analyst/synthesis/intelligence_briefs.json`. Latest via `SynthesisStore.latest_brief()`.

## Certification Artifacts

`examples/certify_phase41_runtime.py` writes:

- `MORNING_INTELLIGENCE_BRIEF.json`
- `MORNING_INTELLIGENCE_BRIEF.md`

Markdown export format:

```markdown
## {title}
★★★★☆

**What changed?** {executive_summary}
**Why should I care?** {why_it_matters}
**Why am I seeing this?** {why_surfaced}
**Evidence:** {evidence_summary}
```

## Thresholds Summary

| Constant | Value |
|----------|-------|
| `MIN_ITEMS` | 5 |
| `MAX_ITEMS` | 15 |
| `TARGET_READING_SECONDS` | 60 |
| `WORDS_PER_SECOND` | 3.2 |
| `MAX_WORDS` | 192 |
| Reading time floor/ceiling | 45–60s |
| Compression target | ≥ 10:1 |

## Design Invariant

Brief v2 is a **compression filter**, not a claim digest. Low-importance claims are absorbed into items upstream; the brief selects top developments by importance and corroboration. Word budget enforces the ~60-second attention contract.

## Entry Point

```python
from knowledge_service.analyst.synthesis.briefing.morning_brief_v2 import IntelligenceBriefGenerator

generator = IntelligenceBriefGenerator()
brief = generator.generate(items, pipeline_run_id=run_id, claims_synthesized=len(claims))
```