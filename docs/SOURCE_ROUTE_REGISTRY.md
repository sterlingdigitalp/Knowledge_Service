# Source Route Registry

The Acquisition Route Registry is a permanent subsystem that answers:

> What is the best way to acquire evidence from this source?

before any transcript fetch occurs.

## Registry Entry Fields

Each source defines:

- `source_id` — canonical identifier (e.g. `dwarkesh`, `lex_fridman`)
- `preferred_route` — deterministic first choice
- `fallbacks` — ordered fallback chain
- `reason` — explicit justification for the preferred route
- `parser` — acquisition parser (`transcript_provider`)
- `validation_rules` — minimum quality checks
- `transcript_confidence` — baseline confidence score
- `quirks`, `dependencies`, `reliability_notes`
- `certification` — evidence-backed certification record

## Route Types

| Route | Provider mapping |
|-------|------------------|
| `official_transcript` | published HTML/text extraction |
| `published_transcript` | published transcript pages (e.g. podscripts) |
| `youtube_transcript_api` | YouTube captions |
| `yt_dlp_whisper` | yt-dlp audio + Whisper |
| `transcript_mirror` | published mirror pages |
| `apple_podcast_transcript` | Apple Podcast transcript (when available) |

## Deterministic Selection

```text
source_id = registry.resolve_source_id(venue, url)
selection = registry.select_route(source_id, target_url)
for route in selection.fallback_chain:
    try route
    on success: record provenance and stop
```

No ad hoc transcript searching. No guessing.

## Persistence

- Config seed: `data/source_routes.yaml`
- Runtime state: `state/route_registry.json`
- Diagnostics: `state/route_diagnostics.json`

Registry state survives process restart.