# Analyst Summarization

Phase 5 adds **analyst-quality LLM generation** for Intelligence Item titles, executive summaries, and multi-turn deep dive responses. Default backend is local heuristic prose — no API key required. Optional OpenAI-compatible HTTP backend when configured.

## Modules

| Path | Class | Role |
|------|-------|------|
| `knowledge_service.production.llm.provider` | `LLMProvider` | Abstract generation interface |
| `knowledge_service.production.llm.analyst_provider` | `AnalystLLMProvider` | Pattern-based local analyst prose |
| `knowledge_service.production.llm.openai_compatible` | `OpenAICompatibleProvider` | HTTP chat completions (optional) |
| `knowledge_service.production.llm.registry` | `get_llm_provider`, `configure_llm` | Provider selection |

## Request Models

| Model | Used for |
|-------|----------|
| `ThemeNamingRequest` | Item title generation |
| `SummaryRequest` | Executive summary generation |
| `ConversationRequest` | Multi-turn deep dive replies |

### ThemeNamingRequest

| Field | Source |
|-------|--------|
| `keywords` | Evidence excerpts, theme label tokens |
| `entities` | Item speakers |
| `sample_claims` | Supporting evidence excerpts |
| `sources`, `speakers` | Item provenance |

### SummaryRequest

| Field | Source |
|-------|--------|
| `title` | Newly generated theme title |
| `claim_excerpts` | Up to 5 evidence excerpts |
| `novelty_classification`, `importance_band` | Item scoring |
| `corroboration_count`, `contradictions` | Cross-source signals |
| `theme_evolution` | Evolution explanation when present |

## Analyst Heuristic Provider

`AnalystLLMProvider` (`name = "analyst_heuristic"`) — default Phase 5 backend.

### Theme Naming

1. Match keywords/entities against `ANALYST_PATTERNS` (e.g. inference economics, GLP-1 landscape, frontier scaling).
2. Fall back to substantive concept pairing (`{Concept1} {Concept2}`).
3. Final fallback: `"Emerging Intelligence Signal"`.

### Executive Summary Structure

Four-part analyst narrative:

```text
What changed  — source convergence and lead signal
Why it matters — corroboration or importance rationale
Why now       — novelty class or theme evolution
What to watch — contradictions, third-source confirmation, or decision-maker follow-through
```

### Conversation Routing

`converse()` dispatches on user message intent:

| Intent trigger | Response |
|----------------|----------|
| Empty / "tell me more" | Opening analyst briefing |
| "contradict", "conflict" | Tension summary |
| "timeline", "history", "when" | Chronological evidence list |
| "evidence", "source" | Evidence map |
| Contains `?` | Analyst view + follow-up angles |
| Default | Continuation with suggested prompts |

## OpenAI-Compatible Provider

`OpenAICompatibleProvider` extends `AnalystLLMProvider` with HTTP fallback.

| Env var | Purpose |
|---------|---------|
| `KNOWLEDGE_LLM_PROVIDER` | Set to `openai_compatible` to attempt API |
| `OPENAI_API_KEY` | Required for API calls |
| `OPENAI_BASE_URL` | Optional custom endpoint |

When API unavailable or request fails, all methods fall back to `AnalystLLMProvider`.

## Enhancement Integration

`ProductionEnhancementLayer._enhance_items()` for each `IntelligenceItem`:

1. Build `ThemeNamingRequest` from evidence and speakers.
2. `llm.name_theme()` → `item.title`
3. `llm.executive_summary()` → `item.executive_summary`
4. Update `item.why_surfaced` with matched title prefix

Latency recorded as `production.latency_seconds.analyst_summarization`.

## Conversation Integration

`DeepDiveConversationEngine` uses the same LLM provider for multi-turn sessions. See `conversation/deep_dive_v3.py`.

## Registry

```python
from knowledge_service.production.llm.registry import get_llm_provider

llm = get_llm_provider()  # analyst_heuristic unless OPENAI_API_KEY + openai_compatible
title = llm.name_theme(naming_request)
summary = llm.executive_summary(summary_request)
reply = llm.converse(conversation_request)
```

## Benchmark Signal

`PhaseBenchmark.compare_briefs()` reports:

- `title_quality_improved` — Phase 5 titles score higher on word-count heuristics
- `summary_quality_improved` — `quality_score >= 0.5`

## Runtime Inspector

`production.llm_provider` on `ProductionResult` — `analyst_heuristic` or `openai_compatible`.

## Entry Point

```python
from knowledge_service.production.llm.registry import get_llm_provider
from knowledge_service.production.llm.provider import SummaryRequest

llm = get_llm_provider()
summary = llm.executive_summary(request)
```

## Design Invariant

Summarization **enhances** Phase 4.1 Intelligence Items in place — claim provenance, evidence records, and scoring metadata are preserved. Titles and summaries are regenerated; supporting evidence is not fabricated.