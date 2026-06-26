# Knowledge Object — Canonical Knowledge Representation

## Purpose

This document defines the canonical Knowledge Object schema that serves as the single source of truth for knowledge representation within Knowledge_Service. Every piece of acquired information, regardless of its origin or acquisition method, is transformed into this format before storage or retrieval.

## Scope

This document specifies:
- The complete structure of a Knowledge Object
- All mandatory and optional fields
- Field types, constraints, and semantics
- Versioning strategy for schema evolution
- Relationship model between objects
- Hash computation for deduplication

## Design Rationale

The Knowledge Object is designed around three core requirements derived from the architectural principles:

1. **Standardization (Principle 3)**: Every subsystem consumes identical objects regardless of source
2. **Evidence First (Principle 4)**: Every object carries its provenance, confidence, and acquisition history
3. **Reproducibility (Principle 5)**: Every object contains sufficient context to reconstruct how it was acquired

The schema is designed for forward and backward compatibility. New fields can be added without breaking existing consumers. Unknown fields are preserved during serialization/deserialization.

## Knowledge Object Schema

A Knowledge Object consists of the following top-level sections:

### Core Identity

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID v7 | Yes | Unique identifier for this knowledge object. Generated at creation time using UUID v7 for sortability by creation time. |
| `version` | Integer | Yes | Schema version number. Starts at 1. Incremented only on breaking schema changes. Default: 1. |
| `type` | Enum | Yes | Classification of the knowledge object. Values: `document`, `chunk`, `summary`, `citation`, `relationship`. |

### Source Information

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_id` | String | Yes | Identifier for the source from which this knowledge was acquired. Maps to an entry in the Source Registry. |
| `source_url` | URI | Conditional | Original URL or identifier of the source material. Required when the source has a retrievable location. Omitted for sources without URLs (e.g., databases, APIs with opaque identifiers). |
| `source_type` | Enum | Yes | Type of the original source. Values: `web_page`, `api_response`, `rss_feed`, `github_repository`, `pdf_document`, `video_transcript`, `database_record`, `email`, `other`. |

### Temporal Information

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `acquired_at` | ISO 8601 timestamp | Yes | Timestamp when this knowledge was acquired by Knowledge_Service. Always in UTC. Format: `YYYY-MM-DDTHH:mm:ssZ`. |
| `published_at` | ISO 8601 timestamp | Conditional | When the original content was published or created. Extracted from source metadata when available. Omitted if not determinable. |
| `updated_at` | ISO 8601 timestamp | Yes | Timestamp of last modification to this knowledge object. Initially equals `acquired_at`. Updated when the object is refreshed or corrected. |

### Content

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `markdown` | String | Conditional | Canonical markdown representation of the content. Required for `document` and `chunk` types. Omitted for `summary`, `citation`, and `relationship` types. May be truncated if content exceeds maximum size; full content stored separately with reference. |
| `structured_data` | Object | Optional | Structured extraction from the content (e.g., parsed tables, extracted fields, typed data). Format is flexible but should use standard JSON types. Populated when processing can extract structured information. |
| `raw_content_hash` | SHA-256 hex string | Yes | Cryptographic hash of the original raw content received from the provider. Used for deduplication and integrity verification. Computed as: `SHA256(raw_bytes)`. |
| `content_hash` | SHA-256 hex string | Yes | Cryptographic hash of the processed markdown content. Used to detect when content has been updated at the source. Computed as: `SHA256(markdown_content)`. |

### Metadata

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | String | Conditional | Human-readable title of the knowledge object. Extracted from source metadata or generated from content. Required for `document` type. Optional for other types. |
| `authors` | Array of Strings | Optional | Authors or creators of the original content. Populated when available from source metadata. |
| `language` | BCP 47 tag | Conditional | Primary language of the content (e.g., `en`, `zh-CN`, `es`). Required for `document` type. Detected automatically if not provided by source. |
| `topics` | Array of Strings | Optional | Topic classifications assigned during processing. Populated by topic classification or entity extraction. |
| `word_count` | Integer | Conditional | Number of words in the markdown content. Computed during processing. Required for `document` and `chunk` types. |

### Evidence and Confidence

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `confidence` | Float (0.0 - 1.0) | Yes | Confidence score representing the reliability of this knowledge object. Computed based on source trust, content completeness, processing success, and evidence quality. Range: 0.0 (no confidence) to 1.0 (full confidence). |
| `evidence_count` | Integer | Yes | Number of distinct evidence items attached to this object. Includes citations, source references, and acquisition records. |
| `citations` | Array of Citation objects | Optional | List of citations linking to other knowledge objects or external sources. Populated during relationship detection in processing. |

#### Citation Object Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target_id` | UUID | Yes | ID of the referenced knowledge object. Null for external citations. |
| `target_url` | URI | Conditional | External URL being cited. Used when target is not a Knowledge Object in this system. |
| `context` | String | Optional | Brief context explaining why this citation is relevant (e.g., "supports claim about X", "provides source data for Y"). |
| `citation_type` | Enum | Yes | Type of citation. Values: `reference`, `supporting_evidence`, `contradictory_evidence`, `supplementary`, `derived_from`. |

### Acquisition History

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `acquisition_chain` | Array of AcquisitionRecord objects | Yes | Complete record of how this knowledge was acquired. Each entry represents one acquisition attempt or source used. Preserved for reproducibility (Principle 5). |

#### Acquisition Record Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider_name` | String | Yes | Name of the provider that contributed this record (e.g., `crawl4ai`, `searxng`, `github`). |
| `provider_type` | Enum | Yes | Type classification of the provider. Values: `crawler`, `search`, `api`, `rss`, `file_processor`, `database`. |
| `request_id` | String | Yes | Unique identifier for this acquisition request, used for tracing and debugging. |
| `timestamp` | ISO 8601 timestamp | Yes | When this acquisition attempt occurred. |
| `status` | Enum | Yes | Result of the acquisition attempt. Values: `success`, `partial`, `failed`, `cached`. |
| `response_size_bytes` | Integer | Conditional | Size of the provider response in bytes. Recorded when available. |
| `latency_ms` | Integer | Conditional | Time taken for this acquisition in milliseconds. Recorded when available. |
| `error_message` | String | Conditional | Error message if status is `failed`. Omitted on success. |

### Chunking Information (for chunk type objects)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `parent_id` | UUID | Conditional | ID of the parent document this chunk belongs to. Required for `chunk` type. |
| `chunk_index` | Integer | Yes | Position of this chunk within its parent document (0-indexed). |
| `chunk_total` | Integer | Yes | Total number of chunks in the parent document. |
| `overlap_with_next_id` | UUID | Optional | ID of the next overlapping chunk, if overlap was used during chunking. |

### Relationship Information

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `related_to` | Array of UUIDs | Optional | IDs of knowledge objects that this object has a relationship with. Populated by relationship detection during processing. |
| `relationship_types` | Array of Enums | Conditional | Types of relationships this object participates in. Values: `references`, `cites`, `contradicts`, `supplements`, `derives_from`, `part_of`, `related_to`. Used when `related_to` is present. |

### System Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `storage_backend` | String | Yes | Identifier of the storage backend where this object is stored. Used in multi-backend deployments. |
| `index_status` | Enum | Yes | Indexing status for retrieval. Values: `pending`, `indexed`, `failed`. |
| `retention_policy_id` | String | Optional | Identifier of the retention policy applied to this object. Determines archival and deletion schedule. |

## Complete Schema Example (Conceptual)

```
Knowledge Object {
  id: "019a5c3e-7f2d-7b4a-a8e1-3c5d6e7f8a9b",
  version: 1,
  type: "document",

  source_id: "nextjs-blog-001",
  source_url: "https://nextjs.org/blog/next-15",
  source_type: "web_page",

  acquired_at: "2026-06-25T14:30:00Z",
  published_at: "2026-06-20T09:00:00Z",
  updated_at: "2026-06-25T14:30:00Z",

  markdown: "# Next.js 15 Released...\n\nNext.js 15 introduces...",
  structured_data: {
    framework: "Next.js",
    version: "15.0.0",
    release_date: "2026-06-20"
  },
  raw_content_hash: "a1b2c3d4e5f6...",
  content_hash: "f6e5d4c3b2a1...",

  title: "Next.js 15 Release Announcement",
  authors: ["Vercel Team"],
  language: "en",
  topics: ["web_frameworks", "javascript", "react"],
  word_count: 3500,

  confidence: 0.92,
  evidence_count: 3,
  citations: [
    {
      target_id: null,
      target_url: "https://github.com/vercel/next.js/releases/tag/v15.0.0",
      context: "Official release notes for Next.js 15",
      citation_type: "reference"
    }
  ],

  acquisition_chain: [
    {
      provider_name: "crawl4ai",
      provider_type: "crawler",
      request_id: "req-abc-123",
      timestamp: "2026-06-25T14:30:00Z",
      status: "success",
      response_size_bytes: 45200,
      latency_ms: 1200
    }
  ],

  related_to: ["019a5c3e-7f2d-7b4a-a8e1-3c5d6e7f8a9c"],
  relationship_types: ["references", "supplements"],

  storage_backend: "primary-store-01",
  index_status: "indexed",
  retention_policy_id: "default-long-term"
}
```

## Schema Evolution Strategy

### Versioning Rules

The `version` field follows semantic versioning principles for schema evolution:

| Change Type | Version Action | Backward Compatible? |
|-------------|---------------|---------------------|
| New optional fields added | Minor (1 → 2) | Yes — consumers ignore unknown fields |
| New required fields added | Major (breaking) | No — requires migration strategy |
| Field type changed | Major (breaking) | No — requires data migration |
| Enum values extended | Minor | Yes — old values still valid |
| Enum values removed | Major | No — may break existing objects |
| Field removed | Deprecated then removed | Transition period required |

### Migration Policy

When a breaking schema change is necessary:
1. Both old and new schema versions are supported during a transition period (minimum 2 major releases)
2. Data migration tools are provided to convert objects from old to new schema
3. The API Layer handles version negotiation — consumers specify desired schema version
4. Storage layer supports multiple schema versions simultaneously during transition

### Forward Compatibility Guarantee

Knowledge Objects must always be deserializable even when they contain fields unknown to the consumer. This is achieved by:
- Using serialization formats that preserve unknown fields (JSON, protobuf with well-known types)
- Documenting all field names and types in this specification
- Never reusing field names for different purposes across versions

## Hash Computation Details

### Raw Content Hash (`raw_content_hash`)

Computed from the exact bytes received from the provider, before any processing:
```
raw_content_hash = SHA256(provider_response_bytes)
```

Purpose: Detect when a source's raw content changes. Useful for cache invalidation and change detection.

### Content Hash (`content_hash`)

Computed from the processed markdown content after normalization:
```
content_hash = SHA256(normalized_markdown_string)
```

Purpose: Detect when the canonical representation of content has changed. Used to identify updated knowledge during re-acquisition.

### Deduplication Logic

When a new Knowledge Object is created:
1. Compute `raw_content_hash` and compare against existing objects from the same source
2. If match found, skip storage — the object already exists
3. If no raw match but `content_hash` matches an object from a different source, create relationship (`supplements`) rather than duplicate

## Chunking Strategy

When content exceeds retrievable size limits or for granular search:
1. Parent document is created with full content
2. Content is split into chunks using the configured chunking strategy (semantic, fixed-size, or hierarchical)
3. Each chunk becomes a `chunk` type Knowledge Object
4. Chunks reference their parent via `parent_id`
5. Overlap between adjacent chunks preserves context continuity

Chunking parameters are configurable and documented in PROCESSING_PIPELINE.md.

## Confidence Computation

Confidence is computed as a weighted combination of factors:

```
confidence = w1 * source_trust + w2 * content_completeness + w3 * processing_quality + w4 * evidence_strength
```

Where weights (w1-w4) are configurable and default values are defined in the configuration specification. Each factor is normalized to 0.0-1.0 before weighting.

### Factor Definitions

| Factor | Source | Computed By |
|--------|--------|-------------|
| `source_trust` | Source Registry trust score | Processing Layer (reads from registry) |
| `content_completeness` | Ratio of expected content present vs. total available | Processing Layer (analyzes raw vs. processed content) |
| `processing_quality` | Success indicators during normalization and extraction | Processing Layer (pipeline stage metrics) |
| `evidence_strength` | Number and quality of citations and acquisition records | Processing Layer (counts evidence items) |

## Constraints and Limits

| Field | Constraint | Rationale |
|-------|-----------|-----------|
| `markdown` | Maximum 10 MB per object | Storage efficiency; larger content should be chunked |
| `citations` | Maximum 1000 citations per object | Prevents unbounded growth; sufficient for any realistic use case |
| `acquisition_chain` | Unlimited (append-only) | Reproducibility requires complete history |
| `authors` | Maximum 50 authors | Practical limit for most publications |
| `topics` | Maximum 20 topics | Prevents tag sprawl; sufficient classification granularity |
| `word_count` | Computed, no explicit maximum | Derived field |

## Extension Points

### Adding New Knowledge Types

New types (e.g., `image`, `audio_transcript`, `spreadsheet`) can be added by:
1. Extending the `type` enum
2. Defining type-specific fields in an extension section
3. Updating processing handlers for the new type

Existing consumers that don't recognize the new type will ignore unknown fields (forward compatibility).

### Adding New Citation Types

New citation types extend the `citation_type` enum without breaking existing citations. The meaning of each type is documented alongside its addition.

### Adding New Relationship Types

Relationship types are extensible through the same mechanism as citation types. The relationship model supports arbitrary directed edges between knowledge objects.

## Assumptions

- UUID v7 is available in the implementation language
- SHA-256 is available for hash computation
- ISO 8601 timestamps are supported by all storage backends
- JSON is the primary serialization format (other formats must preserve unknown fields)

## Future Evolution

Future phases may add:
- Multi-language support with translation metadata
- Image/video content with embedded OCR/transcript data
- Real-time knowledge objects from streaming sources
- Collaborative annotations and corrections on knowledge objects
- Version history tracking for corrected or updated knowledge

All future additions must maintain forward/backward compatibility with this schema.
