# Editorial Synthesis

IL2 editorial synthesis transforms evidence-backed `IntelligenceItem` records into analyst-grade brief cards.

## Engine

`intelligence_v2/editorial_synthesis.py`

## Pipeline Step

```
IntelligenceItem + ResolutionResult → AnalystBriefCard → IntelligenceItem (if accepted)
```

## Card Fields

| Field | Source |
|-------|--------|
| title | CanonicalTopicResolver |
| executive_summary | Synthesized from what_happened + why_it_matters |
| what_happened | Source count, speakers, lead evidence excerpt |
| why_it_matters | Importance band, corroboration, contradictions, novelty |
| confidence_explanation | Importance + corroboration + source diversity |
| what_to_watch | Contradiction-aware or corroboration-aware |
| suggested_action | Profile-conditioned recommendation |
| supporting_sources | Item sources (max 8) |
| evidence | Timestamped supporting_evidence (max 6) |

## Canonical Resolution

`canonical_resolver.py` uses evidence patterns, not raw theme labels:

- Sponsor CTAs → reject or override (Mercury → banking platform)
- Speech fragments → entity/keyword merge or claim extraction
- Intro filler → podcast coverage or low-signal label
- Pattern library → Enterprise AI Agents, Byzantine Empire, etc.

## Quality Gate

`quality_gate.py` rejects cards with:

- Fragment titles (score < 0.55)
- Sponsor-only evidence
- Boilerplate summaries (≥3 boilerplate phrases)
- Low evidence density

Rejected cards are logged in `IL2Result` but not written back to items.

## Boilerplate Detection

Phrases like "are converging on", "why it matters:", "not stale repetition" trigger summary score penalties.

## Example Transformation

| Field | Runtime 1 | IL2 |
|-------|-----------|-----|
| Title | Visit Mercury | Mercury Startup Banking Platform |
| Title | Roman Empire | Byzantine Empire Historical Analysis |
| Title | Enterprise AI Agents | Enterprise AI Agent Adoption |
| Status | Published | Rejected (sponsor CTA) |