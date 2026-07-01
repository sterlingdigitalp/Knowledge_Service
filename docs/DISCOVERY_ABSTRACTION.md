# Discovery Abstraction

Phase 3.2 introduces `InformationEventDiscoverer` so the collector no longer knows where events originate.

## Interface

```python
class InformationEventDiscoverer(ABC):
    discoverer_id: str
    event_types: List[str]
    def discover(profile, context) -> List[DiscoveryResult]
```

## Implementations

| Discoverer | Status | Event Types |
|------------|--------|-------------|
| `PodcastDiscoverer` | **Fully implemented** | podcast_episode |
| `ConferenceDiscoverer` | Interface stub | conference_keynote, panel_discussion |
| `InterviewDiscoverer` | Interface stub | interview, fireside_chat, ama |
| `LivestreamDiscoverer` | Interface stub | livestream |
| `EarningsCallDiscoverer` | Interface stub | earnings_call |
| `PresentationDiscoverer` | Interface stub | research_presentation, university_lecture, product_launch, congressional_testimony |

## Registry

`DiscovererRegistry` coordinates all discoverers. `DiscoveryEngine` delegates to the registry — adding a new venue type requires only a new discoverer implementation and registry registration, not collector changes.