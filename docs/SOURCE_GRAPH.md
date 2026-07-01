# Source Graph

The Source Graph models watched people as information sources, not social accounts.

## Node Types
Every watch-list entry creates a graph with standard source lanes:
- `x`
- `podcast_appearances`
- `youtube`
- `company_blog`
- `conference_talks`
- `papers`
- `interviews`

## Appearance Updates
When discovery detects a watched person in a podcast episode, the corpus manager records the episode under that person's `podcast_appearances` lane.

## Persistence
Source graphs are stored in `state/source_graphs.json` inside the configured Phase 3 state directory.

## Inspector Coverage
The Phase 3 inspector reports:
- people/source graphs
- podcast counts
- transcript provider availability
- acquisition status through discovered and processed episodes

## Current Scope
Phase 3 records configured handles and podcast appearances. Future phases can extend the same graph with papers, blogs, talks, and social sources without changing profile semantics.
