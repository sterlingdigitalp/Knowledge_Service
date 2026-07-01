# Phase 3 Architecture

Phase 3 adds a profile-driven collection layer above the existing acquisition and processing pipeline. The core acquisition contract remains unchanged: providers still return `ProviderResponse`, transcripts still enter `AcquisitionBundle`, and `Pipeline` still creates `KnowledgeObject` documents, chunks, citations, and embeddings.

## Components
- `knowledge_service.intelligence.models`: Intelligence Profiles, watch-list entries, podcast sources, discovered episodes, source graphs, and jobs.
- `knowledge_service.intelligence.discovery`: finds new podcast transcript pages from configured podcast indexes.
- `knowledge_service.intelligence.dedupe`: persists source, acquisition, and transcript hashes.
- `knowledge_service.intelligence.collector`: orchestrates discovery, dedupe, transcript acquisition, processing, and corpus persistence.
- `knowledge_service.intelligence.corpus`: maintains persistent corpus state, source graphs, growth history, and per-profile statistics.
- `knowledge_service.intelligence.scheduler`: runs manual, scheduled, and daemon collection loops.
- `knowledge_service.intelligence.inspector`: exposes Phase 3 runtime state for certification and operations.

## Runtime Flow
1. Load profiles from JSON/YAML configuration.
2. Discover candidate episodes from each enabled profile podcast list.
3. Match candidates against profile watch lists and interests.
4. Check persistent source and acquisition hashes before queueing.
5. Acquire transcripts with `TranscriptProvider`.
6. Register transcript hashes to prevent repeated ingestion after restart.
7. Process transcripts through the existing `Pipeline`.
8. Persist KnowledgeObjects and corpus growth history.
9. Update source graphs and runtime inspector output.

## Invariants
- Profiles and podcast lists are configuration-driven.
- Providers remain synchronous and isolated behind the existing provider interface.
- Unknown speakers remain unknown; collection does not infer speakers.
- Deduplication is persistent and survives process restart.
- Phase 4 can consume the corpus without re-solving acquisition.

## Certified Evidence
Latest certification: `runtime_evidence/phase3_intelligence_20260701T002459Z`.
