# Phase 1.6B — Processing & Retrieval Hardening

## Defects Corrected

### 1. Acquisition Timestamp Semantics
**File**: `src/knowledge_service/processing/pipeline.py:82`

**Issue**: `AcquisitionRecord.timestamp` was incorrectly set to `exec_rec.latency_ms` (an integer) instead of an ISO 8601 timestamp string.

**Fix**: Changed `timestamp=exec_rec.latency_ms` to `timestamp=acquired_at`, where `acquired_at` is the ISO 8601 timestamp from `doc.acquired_at`. Also fixed `latency_ms` to be `exec_rec.latency_ms if exec_rec.latency_ms else None` to ensure it's optionally an integer or `None`.

### 2. Processing Validation
**File**: `src/knowledge_service/processing/validate.py`

Validation stage correctly rejects objects with:
- Missing `id`, `raw_content_hash`, `content_hash`, `source_id`, `acquired_at`, `updated_at`
- Confidence outside `[0.0, 1.0]` range
- Chunk types missing `parent_id`, `chunk_index`, or `chunk_total`

Validation stage issues warnings for:
- Empty acquisition_chain
- Missing source_url for non-other source types
- Document type without markdown content

### 3. Storage Validation
**File**: `src/knowledge_service/storage/postgres/in_memory_store.py`

In-memory store correctly:
- Detects duplicates by `content_hash` and returns existing ID
- Tracks metrics: `objects_stored`, `objects_retrieved`, `duplicates_prevented`
- Maintains parent-child relationships via `_by_parent` index

### 4. Chunk Parent Retrieval
**File**: `src/knowledge_service/retrieval/hierarchy.py`

Hierarchy assembly correctly:
- Reconstructs document trees from flat dictionaries of objects
- Filters children by `parent_id == document_id`
- Orders chunks by `(chunk_index, id)`

### 5. Retrieval Consistency
**File**: `src/knowledge_service/retrieval/retriever.py`

Retriever correctly:
- Is deterministic and stateless
- Depends only on `KnowledgeRepository` (not store directly)
- Validates objects and issues warnings for hash mismatches, invalid confidence

## Tests Rerun

### Determinism Tests
- `tests/processing/test_chunk.py::TestChunkStage::test_chunk_determinism` — PASSED
- `tests/processing/test_markdown.py::TestMarkdownStage::test_hash_determinism` — PASSED
- `tests/processing/test_pipeline.py::TestPipelineEndToEnd::test_pipeline_hashing_determinism` — PASSED

### Failure Testing
- `tests/failure/test_failure_e2e.py::TestFailureInjectionE2E::test_malformed_html_processed_gracefully` — PASSED
- `tests/failure/test_failure_e2e.py::TestFailureInjectionE2E::test_empty_document_handled_gracefully` — PASSED
- `tests/failure/test_failure_e2e.py::TestFailureInjectionE2E::test_large_document_handled_gracefully` — PASSED

### Duplicate Content Testing
- `tests/duplicate/test_duplicate_e2e.py::TestDuplicatePreventionE2E::test_acquire_identical_document_twice_only_one_stored` — PASSED

### Retrieval Tests
- 83 retrieval tests — ALL PASSED

### Processing Validation Tests
- 5 processing validation tests — ALL PASSED

### Storage Tests
- 10 storage tests (store/retrieve, duplicate detection, parent lookup, persistence) — ALL PASSED

## Determinism Results

| Item | Status |
|------|--------|
| Hashes (raw_content_hash, content_hash) | Deterministic — SHA-256 based on content bytes |
| Markdown extraction | Deterministic — consistent HTML to markdown conversion |
| Chunks | Deterministic — semantic or fixed-size chunking with consistent overlap |
| Retrieval order | Deterministic — sorting by `(chunk_index, id)` for chunks |
| Confidence bounds | Deterministic — computed from stage impacts, capped at `[0.0, 1.0]` |
| Timestamps | ISO 8601 format — `acquired_at` from document record preserved accurately |

## Validation Results

| Layer | Status |
|-------|--------|
| Provider Layer | PASS — abstract, replaceable, types don't leak |
| Planning Layer | PASS — capability-based selection, no implementation knowledge |
| Acquisition Layer | PASS — `AcquisitionBundle` canonical, executor produces bundles |
| Processing Layer | PASS — 7-stage pipeline, deterministic, validation rejects bad objects |
| Knowledge (Storage) Layer | PASS — abstract `KnowledgeStore`, repository pattern, duplicate detection |
| Retrieval Layer | PASS — 14 operations, depends only on repository interface |

## Remaining Technical Debt

1. **Source Repository** — implemented in `src/knowledge_service/storage/repositories/source_repository.py` with in-memory and PostgreSQL-aware stores. Execution-side metric updates are now wired via `AcquisitionExecutor` for provider-level success/latency tracking.

2. **Docker integration infrastructure** — Crawl4AI (`localhost:11235`) and SearXNG (`localhost:8080`) Docker containers not running. Integration tests skip gracefully when infrastructure unavailable.

3. **PostgreSQL operational testing** — all tests currently use `InMemoryKnowledgeStore`. PostgreSQL store implementation exists but not exercised in test suite.

## Test Summary

**Total tests passing**: 190 (169 existing + 21 planning unit tests)  
**Integration tests skipped**: 19 (requires Docker infrastructure)  
**Failure injection tests**: 3 passed  
**Duplicate prevention test**: 1 passed  
**Determinism tests**: 3 passed

Phase 1.6B completed successfully — all defects corrected, determinism verified, failure handling validated.
