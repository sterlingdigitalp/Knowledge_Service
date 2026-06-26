# Data Model — Storage and Retrieval Architecture

## Purpose

This document defines the data model for persistent storage within Knowledge_Service. It specifies how knowledge objects, source registry entries, acquisition plans, and system metadata are stored, indexed, and retrieved across different storage backends.

## Scope

This document covers:
- Primary store schema (knowledge objects and metadata)
- Vector index schema (embeddings for semantic search)
- Cache layer design
- Graph store schema (optional relationship storage)
- Source Registry persistence
- Acquisition plan audit log
- Multi-backend abstraction interface
- Data retention and lifecycle policies

## Design Rationale

The data model is designed around the principle that Knowledge_Service stores knowledge, not application data. The model supports:

1. **Evidence preservation**: Every stored object carries full provenance and evidence
2. **Retrieval flexibility**: Multiple indexing strategies (full-text, vector, graph) support different query patterns
3. **Backend replaceability**: Storage backends are abstracted behind interfaces; the model defines what is stored, not how it's physically laid out in a specific database
4. **Schema evolution**: The model supports versioned knowledge objects and backward-compatible schema changes

## Primary Store

### Purpose

The primary store holds complete Knowledge Objects with all fields intact. It is the source of truth for knowledge content and metadata.

### Collection/Table: `knowledge_objects`

| Field | Type | Indexed | Description |
|-------|------|---------|-------------|
| `id` | UUID | Primary Key | Knowledge Object identifier |
| `version` | Integer | Yes | Schema version |
| `type` | Enum | Yes | Object type (document, chunk, summary, etc.) |
| `source_id` | String | Yes | Source registry reference |
| `acquired_at` | Timestamp | Yes (range) | Acquisition timestamp |
| `updated_at` | Timestamp | Yes (range) | Last update timestamp |
| `content_hash` | SHA-256 | Unique Index | Content hash for deduplication |
| `raw_content_hash` | SHA-256 | Yes | Raw content hash |
| `confidence` | Float | Yes (range) | Confidence score |
| `language` | String | Yes | Content language |
| `word_count` | Integer | No | Word count |
| `parent_id` | UUID | Yes (foreign key) | Parent document ID (for chunks) |
| `storage_backend` | String | Yes | Backend identifier |
| `index_status` | Enum | Yes | Indexing status |

### Content Storage

The markdown content and structured data are stored as part of the Knowledge Object record. For very large objects (>1MB markdown), content may be stored in a separate blob table with a reference from the main record:

**Blob Table: `knowledge_object_content`**
| Field | Type | Description |
|-------|------|-------------|
| `object_id` | UUID | Reference to knowledge_objects.id |
| `markdown` | Text/Blob | Full markdown content (for large objects) |
| `structured_data` | JSON/Blob | Structured extraction data |

### Indexing Strategy

The primary store supports:
- **Full-text search**: On title, markdown content, and structured fields
- **Filter queries**: On source_id, type, date range, confidence, language, topics
- **Range queries**: On acquired_at, updated_at, confidence, word_count
- **Join queries**: Parent-child relationships for chunks

### Retrieval Patterns Supported

| Pattern | Index Used | Description |
|---------|-----------|-------------|
| Get by ID | Primary key | Direct lookup of a specific knowledge object |
| Search by query | Full-text index | Text search across content with optional filters |
| List by source | Source ID index | All objects from a specific source |
| List by date range | Timestamp index | Objects acquired within a time window |
| List by confidence range | Confidence index | Objects within a confidence threshold |
| Get chunks of document | Parent ID index | All chunks belonging to a parent document |

## Vector Index

### Purpose

The vector index stores embeddings for each knowledge object (or chunk) to enable semantic search. It is separate from the primary store because vector databases have different optimization characteristics than relational/document stores.

### Schema

| Field | Type | Description |
|-------|------|-------------|
| `object_id` | UUID | Reference to knowledge_objects.id |
| `embedding` | Vector (float[]) | Dense embedding vector (dimension depends on model) |
| `chunk_index` | Integer | Chunk position within parent document (0 for full documents) |

### Indexing Strategy

- **Approximate Nearest Neighbor (ANN)** search using algorithms like HNSW or IVF
- Distance metric: cosine similarity (default) or dot product
- Metadata filtering: Filter vectors by source_id, type, date range before nearest neighbor search

### Embedding Generation

Embeddings are generated during the Enrich stage of the Processing Pipeline. The embedding model is configurable and replaceable through the Provider Interface (if the vector provider also handles embeddings) or a dedicated embedding service.

**Embedding lifecycle**:
1. Content is processed to Knowledge Object
2. Embedding is computed from markdown content
3. Embedding + object_id are stored in vector index
4. If content_hash changes (content updated), old embedding is replaced

### Vector Store Abstraction

The vector store is accessed through an interface that supports multiple backends:

```
VectorStore Interface:
  - upsert(object_id, embedding, metadata)
  - search(query_embedding, limit, filters)
  - delete(object_ids)
  - health()
```

This abstraction allows replacing the vector database (e.g., Qdrant → Milvus → Pinecone) without changing higher layers.

## Cache Layer

### Purpose

The cache layer stores frequently accessed knowledge objects and query results to reduce latency and storage backend load.

### Cache Types

| Type | Storage | TTL | Invalidation |
|------|---------|-----|--------------|
| Object cache | Redis / In-memory | Configurable (minutes-hours) | On object update or expiration |
| Query result cache | Redis / In-memory | Short (seconds-minutes) | On related object update or expiration |
| Provider response cache | Local disk / Redis | Per source policy | Per Source Registry cache policy |

### Cache Key Design

```
Object cache key:   ks:obj:{version}:{id}
Query cache key:    ks:query:{hash_of_query_params}
Provider cache key: ks:prov:{provider_name}:{target_hash}
```

### Cache Invalidation Strategy

- **Write-through**: When a Knowledge Object is updated, the cached version is invalidated
- **TTL-based**: All caches have configurable time-to-live
- **Source-driven**: If Source Registry marks a source as stale, all cached objects from that source are invalidated
- **Manual invalidation**: Admin API for explicit cache clearing

### Cache Hierarchy

```
L1: In-memory cache (fastest, smallest capacity)
    ↓ miss
L2: Distributed cache / Redis (fast, medium capacity)
    ↓ miss
L3: Primary store (slower, full capacity)
```

Cache hierarchy is configurable. Not all deployments require all levels.

## Graph Store (Optional)

### Purpose

The graph store maintains relationship data between knowledge objects for graph traversal queries. This is optional and enabled only when relationship-based retrieval is needed.

### Schema

| Field | Type | Description |
|-------|------|-------------|
| `source_id` | UUID | Source knowledge object ID |
| `target_id` | UUID | Target knowledge object ID |
| `relationship_type` | Enum | Type of relationship (references, cites, contradicts, etc.) |
| `weight` | Float | Relationship strength (computed from evidence overlap, citation context) |

### Graph Queries Supported

- Find all objects that cite a given object
- Find all objects related to a given object (any relationship type)
- Traverse N hops from a starting object
- Find common ancestors/descendants between two objects

### Graph Store Abstraction

The graph store is accessed through an interface:

```
GraphStore Interface:
  - add_edge(source_id, target_id, relationship_type, weight)
  - get_edges(object_id, direction)     // incoming or outgoing
  - traverse(start_id, max_hops, filters)
  - delete_edges(object_ids)
  - health()
```

## Source Registry Persistence

### Purpose

The Source Registry is persisted in the primary store as a special collection. It tracks source quality metrics and configuration.

### Collection: `source_registry`

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Source identifier (matches Knowledge Object source_id) |
| `name` | String | Human-readable source name |
| `url` | URI | Source URL or location |
| `type` | Enum | Source type classification |
| `trust_score` | Float (0-1) | Historical trust score |
| `freshness_score` | Float (0-1) | How recently the source has been successfully acquired |
| `avg_latency_ms` | Integer | Average acquisition latency |
| `success_rate` | Float (0-1) | Historical success rate of acquisitions from this source |
| `topics` | Array of Strings | Topics where this source has demonstrated expertise |
| `cache_policy` | Object | Cache duration and invalidation rules for this source |
| `status` | Enum | Current status: healthy, degraded, unhealthy |
| `last_acquired_at` | Timestamp | Last successful acquisition timestamp |
| `created_at` | Timestamp | When the source was first registered |
| `updated_at` | Timestamp | Last metadata update timestamp |

### Metrics Storage

Source quality metrics are updated after each acquisition:
- Trust score is a moving average of historical quality signals
- Freshness score decays over time since last successful acquisition
- Latency and success rate are computed from recent acquisition attempts (sliding window)

Detailed acquisition history is stored in the audit log (see below).

## Acquisition Audit Log

### Purpose

The audit log records all acquisition operations for reproducibility and observability. It is append-only and never modified.

### Collection: `acquisition_audit`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique log entry ID |
| `request_id` | String | Correlation with API request |
| `plan_id` | UUID | Associated acquisition plan |
| `timestamp` | Timestamp | When the operation occurred |
| `operation` | Enum | Operation type: plan_created, step_started, step_completed, step_failed, fallback_triggered, plan_completed |
| `provider_name` | String | Provider involved (if applicable) |
| `target` | String | Acquisition target |
| `status` | Enum | Outcome: success, failed, skipped, cached |
| `latency_ms` | Integer | Operation duration |
| `error_code` | String | Error code if status is failed |
| `metadata` | Object | Additional context (response size, cache hit/miss, etc.) |

### Retention

Audit log entries are retained for a configurable period (default: 90 days) before archival to cold storage. The audit log supports time-range queries for operational debugging and reproducibility verification.

## Multi-Backend Abstraction

### Purpose

The Knowledge Layer abstracts multiple storage backends behind interfaces, allowing backend replacement without changing higher layers.

### Interfaces

| Interface | Responsible For | Backends |
|-----------|----------------|----------|
| `KnowledgeStore` | Primary store CRUD | PostgreSQL, MongoDB, etc. |
| `VectorStore` | Embedding storage and search | Qdrant, Milvus, Pinecone, etc. |
| `CacheStore` | Caching layer | Redis, Memcached, in-memory |
| `GraphStore` | Relationship graph (optional) | Neo4j, Nebula Graph, etc. |

### Backend Selection

Backend selection is configured per interface type:

```yaml
storage:
  primary:
    backend: postgresql
    connection: "postgresql://..."
  vector:
    backend: qdrant
    connection: "http://qdrant:6333"
  cache:
    backend: redis
    connection: "redis://redis:6379"
  graph:
    enabled: false  # Optional; enable when needed
```

### Data Migration

When switching backends, migration tools convert data between formats while preserving all Knowledge Object fields and relationships. The KnowledgeStore interface handles format translation during migration.

## Data Retention and Lifecycle

### Retention Policies

Retention policies define how long knowledge objects are kept before archival or deletion:

| Policy | Duration | Action |
|--------|----------|--------|
| `default-short-term` | 30 days | Keep in active storage |
| `default-long-term` | 1 year | Keep in active storage, then archive to cold storage |
| `permanent` | Indefinite | Never expire (for high-trust, high-value sources) |
| `temporary` | 7 days | Delete after expiration (for low-confidence, ephemeral content) |

### Policy Assignment

Retention policies are assigned based on:
- Source trust score (higher trust → longer retention)
- Content type (documents vs. chunks may have different policies)
- Application request options (explicit retention requests)
- Default policy for unconfigured cases

### Lifecycle States

```
Active → Archived → Deleted
  ↑        ↓
  └── Refreshed ──┘
```

| State | Description | Storage Location |
|-------|-------------|------------------|
| `active` | Recently acquired, frequently accessed | Primary store + vector index + cache |
| `archived` | Passed retention threshold, rarely accessed | Cold storage (s3, glacier, etc.) |
| `deleted` | Removed per retention policy or manual deletion | Garbage collected |

### Archive Process

1. Retention policy triggers archive evaluation
2. Knowledge Object is serialized and moved to cold storage
3. Primary store record is replaced with a reference to the archived location
4. Vector embedding is retained in vector index (archived objects are still searchable)
5. On retrieval of archived object, it is loaded from cold storage and re-cached

## Assumptions

- UUIDs are available for unique identifier generation
- SHA-256 hashing is available for content integrity verification
- Vector embeddings have fixed dimensions per model (dimensions may vary between models but are consistent within a model)
- Storage backends support the required data types and indexing capabilities

## Tradeoffs

### Single Primary Store vs. Polyglot Persistence

**Decision**: One primary store interface with pluggable backend implementations.

**Rationale**: Simplifies the data model specification while allowing backend flexibility. A polyglot approach (different stores for different object types within the primary layer) adds complexity without clear benefit at initial scale.

### Embedding Storage: Co-located vs. Separate

**Decision**: Vector embeddings stored in a separate vector database from the primary store.

**Rationale**: Vector databases are optimized for ANN search, which has different performance characteristics than relational/document queries. Separating them allows independent scaling and backend selection. The tradeoff is increased operational complexity (two systems to manage).

### Eager vs. Lazy Embedding Generation

**Decision**: Embeddings generated eagerly during processing pipeline.

**Rationale**: Ensures all stored knowledge objects have embeddings available for search. Lazy generation would save compute on objects that are never searched but adds latency to every search query. Eager generation is better for high-throughput retrieval scenarios.

## Future Evolution

Future phases may add:
- Sharding/partitioning strategies for horizontal scaling of the primary store
- Multi-region replication for geographic distribution
- Real-time sync between active and archived storage
- Automated retention policy optimization based on access patterns
- Compression strategies for long-term archival storage

All additions must work within the interface abstractions defined in this document.
