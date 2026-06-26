# Retrieval Architecture — Phase 1.5

## Overview

The Retrieval Layer provides deterministic access to stored Knowledge Objects. It is the platform's memory recall mechanism — answering the question "Given the knowledge already stored, what should be returned?"

## Layer Boundaries

```
┌─────────────────────────────────────┐
│         Retrieval Layer             │
│  (KnowledgeRetrieverImpl)           │
├─────────────────────────────────────┤
│         Repository Layer            │
│  (KnowledgeRepository)              │
├─────────────────────────────────────┤
│         Storage Layer               │
│  (KnowledgeStore interface)         │
├─────────────────────────────────────┤
│    PostgreSQL / InMemory Store      │
└─────────────────────────────────────┘
```

## Key Design Decisions

### 1. Repository Dependency Only
The Retrieval Layer depends only on `KnowledgeRepository` — never on `KnowledgeStore` directly. This ensures that no SQL or storage implementation details leak into the retrieval logic.

### 2. Query Objects, Not Raw Params
All retrieval operations accept `KnowledgeQuery` objects that encapsulate filters, pagination, sorting, limits, and projection. No raw SQL or dict-based querying.

### 3. Canonical Result Objects
Retrieval operations return `RetrievalResult` — never raw lists. This ensures consistent metadata, warnings, timing, and source summaries.

### 4. Validation at Retrieval Time
Every retrieved object is validated for hash integrity, confidence range, version validity, and structural completeness. Corrupted objects are reported via warnings, never silently returned.

### 5. No Semantic Understanding
All retrieval is purely deterministic — hash-based, field-based, filter-based. No embeddings, vectors, or semantic similarity.

## Retrieval Operations

| Operation | Method | Deterministic |
|-----------|--------|:---:|
| Retrieve by ID | `retrieve_by_id` | ✓ |
| Retrieve by Content Hash | `retrieve_by_content_hash` | ✓ |
| Retrieve by Raw Hash | `retrieve_by_raw_hash` | ✓ |
| Retrieve by Parent | `retrieve_by_parent` | ✓ |
| Retrieve by Source | `retrieve_by_source` | ✓ |
| Retrieve by Acquisition | `retrieve_by_acquisition` | ✓ |
| Retrieve by Time Range | `retrieve_by_time_range` | ✓ |
| Retrieve by Type | `retrieve_by_type` | ✓ |
| Retrieve by Confidence | `retrieve_by_confidence` | ✓ |
| Retrieve Hierarchy | `retrieve_hierarchy` | ✓ |
| Custom Query | `retrieve_query` | ✓ |
| List All | `list_all` | ✓ |
| Exists | `exists` | ✓ |
| Count | `count` | ✓ |

## Determinism Guarantee

Identical queries produce identical results:
- Identical ordering (sorted by specified field, default descending by `acquired_at`)
- Identical objects (no randomness in filtering or pagination)
- Identical metadata (source summaries, warning count)
- Timing within reasonable tolerance (sub-millisecond variance)

## Architecture Compliance

- **No provider imports**: Retrieval never references providers or acquisition
- **No processing logic**: Retrieval does not transform or enrich objects
- **No storage implementation details**: Retrieval uses repository interfaces
- **No semantic search**: All operations are field/hash-based
