# Builder A --- PHASE 3.1: Source Route Registry & Person-Centric Collection

## Knowledge_Service

------------------------------------------------------------------------

# Mission

Phase 3 successfully proved that Knowledge_Service can maintain
Intelligence Profiles and continuously collect a deduplicated corpus.

However, one architectural ambiguity remains.

The current implementation is still biased toward **podcast page
discovery**.

The product vision is **not** podcast-centric.

The product is **person-centric**.

Knowledge_Service should monitor **people**, detect **new information
events**, then acquire transcripts using the **best known acquisition
strategy** for that source.

The objective of Phase 3.1 is to harden the collection architecture
before we begin building the intelligence engine.

This is the final collection phase.

When complete, Knowledge_Service should know:

-   who to monitor
-   where they appeared
-   how to obtain the best transcript
-   why that acquisition route was selected

without guessing.

------------------------------------------------------------------------

# Engineering Protocol

You are Engineering Lead.

Use every available subagent.

Parallelize aggressively.

Suggested workstreams:

-   Source Route Registry
-   Person-centric discovery
-   Information Event model
-   Acquisition certification
-   Runtime Inspector
-   Registry persistence
-   Scheduler integration
-   Corpus migration
-   Testing
-   Documentation
-   Runtime certification

Operate continuously using:

Plan

↓

Implement

↓

Runtime test

↓

Observe failures

↓

Repair

↓

Retest

↓

Repeat

Continue until:

-   no architectural ambiguity remains
-   every source has a certified acquisition strategy
-   all tests pass
-   runtime certification passes

------------------------------------------------------------------------

# Product Philosophy

Knowledge_Service should never ask:

> Where can I find a transcript?

Instead it should ask:

> Someone on my watch list appeared somewhere.

↓

What is the best way to acquire evidence from that source?

The acquisition decision should be deterministic.

------------------------------------------------------------------------

# Phase 3.1 Architecture

Replace:

``` text
Podcast
↓
Transcript
```

with

``` text
Person
↓
Information Event
↓
Acquisition Route Registry
↓
Transcript
↓
Knowledge_Service
```

------------------------------------------------------------------------

# Information Event Model

Introduce a first-class Information Event.

Examples:

-   Podcast episode
-   Conference keynote
-   Interview
-   Livestream
-   Panel discussion
-   AMA
-   Earnings call
-   Research presentation
-   University lecture
-   Product launch
-   Congressional testimony
-   Fireside chat

Knowledge_Service should no longer think in terms of podcasts.

Podcasts are simply one Information Event type.

------------------------------------------------------------------------

# Person-Centric Discovery

The primary monitored entity becomes:

**Person**

Every watched person should maintain a Source Graph.

Example:

Sam Altman

↓

Podcast appearances

↓

Conference talks

↓

Interviews

↓

Company blog

↓

Livestreams

↓

Future sources

The collector should discover new Information Events involving watched
people.

The venue is secondary.

------------------------------------------------------------------------

# Acquisition Route Registry

Implement a new subsystem:

**Acquisition Route Registry**

This becomes a permanent part of Knowledge_Service.

Every monitored source should define:

-   canonical source id
-   preferred acquisition route
-   ordered fallback routes
-   parser
-   validation rules
-   transcript confidence
-   known quirks
-   dependency requirements
-   reliability notes
-   route certification history

The collector must consult this registry before attempting transcript
acquisition.

No ad hoc transcript searching.

No guessing.

------------------------------------------------------------------------

# Route Certification Matrix

For every monitored podcast/source perform real-world certification.

Do not assume the best route.

Test it.

For every source evaluate:

1.  Official transcript
2.  YouTube captions
3.  Apple Podcast transcript (if available and accessible)
4.  yt-dlp + Whisper
5.  Third-party transcript mirrors

Measure:

-   acquisition success
-   transcript completeness
-   timestamp quality
-   speaker attribution quality
-   retrieval quality
-   runtime
-   reliability
-   maintenance burden
-   dependency requirements
-   failure modes

Then choose:

-   Preferred Route
-   Fallback Chain

Justify the decision.

Every decision must be evidence-backed.

------------------------------------------------------------------------

# Registry Examples

``` yaml
all_in:
  preferred_route: youtube_transcript_api
  reason:
    - fastest
    - timestamped
    - complete
    - consistently available
  fallbacks:
    - yt_dlp_whisper
    - transcript_mirror
```

``` yaml
lex_fridman:
  preferred_route: official_transcript
  reason:
    - highest quality
    - official
    - excellent speaker formatting
  fallbacks:
    - youtube_transcript_api
    - yt_dlp_whisper
```

``` yaml
dwarkesh:
  preferred_route: official_transcript
  fallbacks:
    - youtube_transcript_api
    - yt_dlp_whisper
```

Every registry entry should contain an explicit explanation.

------------------------------------------------------------------------

# Corpus Migration

Update existing corpus objects to reference:

-   Information Event
-   Source Route
-   Acquisition Route
-   Route Confidence
-   Transcript Provenance

Do not lose existing KnowledgeObjects.

------------------------------------------------------------------------

# Runtime Inspector

Expand Runtime Inspector.

Include:

## Route Registry

-   Every source
-   Preferred route
-   Fallbacks
-   Certification status
-   Last runtime
-   Route confidence

## Information Events

-   Recent events
-   Participants
-   Acquisition route
-   Transcript status
-   KnowledgeObjects

## Discovery

-   New events
-   Skipped
-   Duplicates
-   Pending
-   Failed

## Route Diagnostics

-   Per-route statistics
-   Success rate
-   Failure rate
-   Average runtime
-   Average transcript quality
-   Warnings

------------------------------------------------------------------------

# Route Certification Report

Generate:

-   ROUTE_CERTIFICATION.md

For every source include:

-   Source
-   Preferred route
-   Fallback chain
-   Evidence
-   Measured metrics
-   Decision rationale
-   Certification date

------------------------------------------------------------------------

# Real-World Runtime Certification

Use real podcast episodes and real transcript acquisition.

Demonstrate:

Watched person

↓

New appearance

↓

Information Event

↓

Registry lookup

↓

Preferred acquisition route

↓

Transcript

↓

KnowledgeObject

↓

Corpus update

↓

Runtime Inspector

------------------------------------------------------------------------

# Testing

Implement:

-   Unit
-   Integration
-   Runtime
-   Restart
-   Registry persistence
-   Route selection
-   Route fallback
-   Regression

Continue repairing until all tests pass.

------------------------------------------------------------------------

# Documentation

Produce:

-   SOURCE_ROUTE_REGISTRY.md
-   INFORMATION_EVENTS.md
-   ROUTE_CERTIFICATION.md
-   PHASE31_ARCHITECTURE.md
-   PHASE31_RUNTIME_CERTIFICATION.md

------------------------------------------------------------------------

# Deliverables

1.  Executive Summary
2.  Updated architecture
3.  Information Event model
4.  Source Route Registry
5.  Route Certification Matrix
6.  Files created
7.  Files modified
8.  Runtime Inspector output
9.  Runtime certification
10. Registry statistics
11. Performance metrics
12. Test results
13. Remaining limitations
14. Phase 4 readiness

------------------------------------------------------------------------

# Acceptance Criteria

Phase 3.1 is complete only when:

-   Knowledge_Service is person-centric rather than podcast-centric.
-   Information Events are first-class entities.
-   Acquisition Route Registry exists.
-   Every monitored source has a certified preferred acquisition route.
-   Every preferred route is backed by real-world testing.
-   Every source has an ordered fallback chain.
-   Route selection is deterministic.
-   Transcript provenance is preserved.
-   Runtime Inspector exposes route decisions.
-   Registry survives restart.
-   Existing corpus remains intact.
-   Regression suite passes.
-   Runtime certification passes.

------------------------------------------------------------------------

# Product Standard

This phase is not about collecting more transcripts.

It is about institutionalizing **how Knowledge_Service acquires
evidence**.

When Phase 3.1 is complete, the system should no longer "search for
transcripts."

It should already know the best acquisition strategy for every trusted
source it monitors, explain **why** that strategy was chosen with
measured evidence, and automatically adapt to fallback routes when
necessary. This creates a deterministic, maintainable acquisition layer
that Phase 4 can treat as a reliable foundation for novelty detection,
relevance ranking, and personalized intelligence briefings.
