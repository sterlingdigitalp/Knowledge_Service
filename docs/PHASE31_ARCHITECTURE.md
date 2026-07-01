# Phase 3.1 Architecture

Phase 3.1 hardens collection architecture from podcast-centric discovery to person-centric information event collection with deterministic acquisition routing.

## Flow

```text
Person (watch list)
  ↓
Information Event (discovery)
  ↓
Acquisition Route Registry (lookup)
  ↓
Transcript (preferred route + fallbacks)
  ↓
Knowledge_Service pipeline
  ↓
Corpus + provenance
```

## Components

| Module | Responsibility |
|--------|----------------|
| `intelligence.models.InformationEvent` | First-class monitored appearances |
| `intelligence.route_registry` | Certified routes, selection, diagnostics |
| `intelligence.discovery` | Person-centric event discovery |
| `intelligence.collector` | Registry-driven acquisition with fallback chain |
| `intelligence.migration` | Backfill legacy corpus without data loss |
| `intelligence.inspector` | Route registry, events, diagnostics exposure |

## Invariants

- Route selection is deterministic and registry-backed
- Transcript provenance is preserved on episodes and KnowledgeObjects
- Existing Phase 3 corpus remains intact after migration
- Podcasts are a venue type, not the system metaphor

## Phase 4 Readiness

Phase 4 can consume:

- `information_events.json` for novelty detection inputs
- `route_registry.json` for trusted acquisition metadata
- provenance fields on KnowledgeObjects for relevance ranking and briefing citations