# Morning Brief v3

Morning Intelligence Brief v3 is the Phase 5 human-facing output. It delivers **5–10 publication-quality developments** with narrative flow, quality scoring, and personalized ranking — tighter than Brief v2's 5–15 item window.

Phase 4.1 `IntelligenceBrief` (v2) remains available. Brief v3 is the certified primary output for Phase 5.

## Modules

| Path | Class | Role |
|------|-------|------|
| `knowledge_service.production.briefing.morning_brief_v3` | `MorningBriefV3Generator`, `IntelligenceBriefV3` | Brief v3 assembly |
| `knowledge_service.production.briefing.quality` | `BriefQualityEvaluator` | Self-evaluation metrics |
| `knowledge_service.production.conversation.deep_dive_v3` | `DeepDiveConversationEngine` | Multi-turn "Tell me more" |

## IntelligenceBriefV3 Structure

| Field | Purpose |
|-------|---------|
| `brief_id` | Stable identifier |
| `generated_at` | ISO timestamp |
| `reading_time_seconds` | Estimated read time (45–60s) |
| `total_items` | Selected entry count (5–10) |
| `items` | `IntelligenceBriefEntry` list |
| `compression_ratio` | `claims_synthesized / total_items` |
| `claims_synthesized` | Input claim count |
| `quality_score` | Overall brief quality (0.0–1.0) |
| `version` | `"3.0"` |
| `pipeline_run_id` | Link to analyst run |
| `narrative_flow` | Lead / supporting / also-watch structure |

## Entry Fields

Each entry answers four briefing questions (inherited from v2 `IntelligenceBriefEntry`):

| Field | Question |
|-------|----------|
| `what_changed` | What changed? (LLM-enhanced `executive_summary`) |
| `why_you_care` | Why should I care? (`why_it_matters`) |
| `why_surfaced` | Why am I seeing this? (personalized surfacing) |
| `evidence_summary` | What is the evidence? |

Plus: `title`, `star_rating`, `importance_band`, `corroborated_by`, `intelligence_item_id`, profile fields, and `explainability`.

## Selection Algorithm

1. Iterate personalized ranked items.
2. Skip duplicate titles (case-insensitive).
3. Gate: `importance_score >= 0.62` and `star_rating >= 3`.
4. Convert to entry; accumulate word budget.
5. Stop at `MAX_ITEMS` (10) or when word budget exceeded (once `MIN_ITEMS` met).
6. Backfill to `MIN_ITEMS` (5) if needed, ignoring gates.

### Word Budget

```text
TARGET_SECONDS  = 60
WORDS_PER_SECOND = 3.3
MAX_WORDS        = 198  (60 × 3.3)
MIN_ITEMS        = 5
MAX_ITEMS        = 10
```

Word count per entry: `title + what_changed + why_you_care`.

### Reading Time

```text
reading_time = max(45, min(60, int(word_budget / WORDS_PER_SECOND) + 3))
```

### Narrative Flow

| Item count | Flow structure |
|------------|----------------|
| 1 | `Lead development: {title}` |
| 2 | `Lead: {first}`, `Also watch: {second}` |
| ≥ 3 | `Lead: {first}`, `Supporting: {middle}`, `Also watch: {last}` |

## Quality Evaluation

`BriefQualityEvaluator.evaluate()` produces:

| Metric | Computation |
|--------|-------------|
| `signal_to_noise` | Importance × 0.4 + novelty × 0.35 + corroboration × 0.15 + duplicate bonus |
| `overall_score` | `signal_to_noise × 0.7` + reading-time bonus + item-count bonus |
| `personal_relevance_hits` | Items matching learned topic weights or tell-me-more list |
| `evidence_quality` | Corroboration-normalized score |
| `reading_time_ok` | 45 ≤ seconds ≤ 60 |
| `item_count_ok` | 5 ≤ items ≤ 10 |

Certification threshold: `overall_score >= 0.4`.

## Deep Dive v3

Multi-turn analyst conversation via `DeepDiveConversationEngine`:

| Session field | Content |
|---------------|---------|
| `messages` | User/assistant turn history |
| `suggested_followups` | Context-aware prompts |
| `timeline` | Timestamped evidence events |
| `competing_viewpoints` | Item contradictions |
| `watch_points` | Analyst watch-list |

```python
session = pipeline.start_conversation(item_id)
follow_up = pipeline.continue_conversation(session["session_id"], "Show me the timeline")
```

## Storage

Briefs append to `state/production/intelligence_briefs_v3.json`. Latest via `ProductionStore.latest_brief()`.

## Certification Artifacts

`examples/certify_phase5_runtime.py` writes:

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
| `MAX_ITEMS` | 10 |
| `TARGET_SECONDS` | 60 |
| `WORDS_PER_SECOND` | 3.3 |
| `MAX_WORDS` | 198 |
| Importance gate | ≥ 0.62 |
| Star rating gate | ≥ 3 |
| Reading time range | 45–60s |
| Quality score floor | ≥ 0.4 (certification) |

## v2 vs v3 Comparison

| Dimension | Brief v2 | Brief v3 |
|-----------|----------|----------|
| Item bounds | 5–15 | 5–10 |
| Title/summary | Synthesis defaults | LLM-enhanced |
| Ranking | Importance only | Personalized |
| Quality score | — | `quality_score` + evaluator |
| Narrative flow | — | Lead/supporting/watch |
| Deep dive | Single-shot v2 | Multi-turn v3 |

## Entry Point

```python
from knowledge_service.production.briefing.morning_brief_v3 import MorningBriefV3Generator

generator = MorningBriefV3Generator()
brief = generator.generate(ranked_items, pipeline_run_id=run_id, claims_synthesized=count)
```

## Design Invariant

Brief v3 is a **quality-filtered, personalized compression layer**. Items are LLM-enhanced upstream; the brief selects top personalized developments within a tighter attention contract than v2.