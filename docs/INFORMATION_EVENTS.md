# Information Events

Phase 3.1 introduces **Information Events** as first-class entities. Podcast episodes are one event type among many.

## Model

`InformationEvent` captures:

- `event_type` — podcast_episode, conference_keynote, interview, livestream, and others
- `venue` — where the appearance occurred (podcast name, conference, etc.)
- `participants` — watched people matched in the event
- `source_id` — canonical registry source identifier
- `acquisition_route` — route used to acquire the transcript
- `route_confidence` — measured confidence for the selected route
- `transcript_provenance` — full provenance payload preserved on corpus objects

`DiscoveredEpisode` remains the persisted compatibility type in `episodes.json`, but every episode serializes information-event fields and mirrors to `information_events.json`.

## Person-Centric Discovery

Discovery is framed as:

```
Watched Person -> Appearance in Venue -> Information Event
```

Podcast index pages are discovery **channels**, not the primary entity. Required venues still collect all episodes; optional venues require a watched-person or interest match.

## Storage

- `state/episodes.json` — backward-compatible episode records with event fields
- `state/information_events.json` — first-class event mirror for inspection and Phase 4