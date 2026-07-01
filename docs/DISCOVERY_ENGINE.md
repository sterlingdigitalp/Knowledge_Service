# Discovery Engine

The Discovery Engine continuously finds candidate content from configured profile sources.

## Inputs
- enabled Intelligence Profiles
- required, optional, and ignored podcast lists
- watch-list entries and interests
- persistent deduplication state

## Supported Discovery Modes
- `podscripts`: parse live Podscripts podcast index pages and extract episode transcript links.
- `page` / `html`: parse episode links from a configured HTML page.
- `episode_urls`: deterministic configured episode URL list, primarily for tests and controlled feeds.

## Episode Lifecycle
1. Candidate found on a configured podcast page.
2. Candidate normalized into a `DiscoveredEpisode`.
3. Watch-list and interest matches are calculated.
4. Optional podcasts without a match are skipped.
5. Required podcasts are queued unless dedupe state says they were already seen.
6. Discovery run is persisted in `state/discovery_runs.json`.

## Persistent No-Repeat Behavior
The discovery engine checks source and acquisition hashes through `DeduplicationStore` before queueing work.

## Real-World Certification
The Phase 3 certifier uses live Podscripts podcast indexes for Dwarkesh, All-In, Founders, and The Peter Attia Drive.
