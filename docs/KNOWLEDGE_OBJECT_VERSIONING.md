# Knowledge Object Versioning — Immutability & Revision Architecture

> Defines how Knowledge Objects become immutable and how revisions track changes over time.

## Design Rationale

Knowledge Objects are the canonical representation of knowledge. Once created, they must not be silently modified — doing so would violate Principle 5 (Reproducibility). However, knowledge may need to be corrected, supplemented, or refreshed. The solution is a strict immutability policy with explicit revision tracking.

### Guiding Principles

1. **Knowledge Objects are immutable after creation.** No field on a stored Knowledge Object may be modified in place.
2. **Changes produce new revisions.** A corrected or refreshed Knowledge Object is a new object with a new `id` and a link to its predecessor.
3. **The revision chain is preserved.** Every revision carries its complete acquisition history, enabling full provenance reconstruction.
4. **Deprecation is explicit.** Outdated revisions are marked deprecated but never deleted. Consumers may choose to use or ignore them.

## Revision Model

```
KnowledgeObject (immutable)
├── id: UUID v7          ← stable identity of the knowledge
├── version: 1            ← schema version (not revision)
├── revision_id: UUID v7  ← unique identity of this revision
├── supersedes: UUID      ← previous revision this replaces (null for initial)
├── superseded_by: UUID   ← next revision that replaces this (null if current)
├── deprecation_reason: str
│
├── [all other Knowledge Object fields]
│
└── acquisition_chain [...]  ← accumulated across revisions
```

### Revision Identity

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `revision_id` | UUID v7 | Yes | Unique identity of this specific revision. Changes every time content or metadata changes. |
| `supersedes` | UUID | Conditional | `revision_id` of the revision this object replaces. `null` for initial acquisitions. |
| `superseded_by` | UUID | Conditional | `revision_id` of the revision that replaced this one. `null` for the current revision. |
| `deprecation_reason` | String | Conditional | Why this revision was superseded. Required when `superseded_by` is set. |

### Object Identity vs. Revision Identity

- **Object identity** (`id`): The stable identifier for a piece of knowledge. Remains the same across revisions. Applications use this to request knowledge.
- **Revision identity** (`revision_id`): The unique identifier for a specific version. Changes with every update. Used for provenance and change tracking.

This separation allows applications to always request the latest revision by `id` while also being able to pin to a specific revision by `revision_id`.

## Revision Chain

```
Initial acquisition:
  KO_A (id=X, revision_id=r1, supersedes=null, superseded_by=null)

Correction/refresh:
  KO_B (id=X, revision_id=r2, supersedes=r1, superseded_by=null)
  KO_A.superseded_by = r2  ← previous revision updated

Further refresh:
  KO_C (id=X, revision_id=r3, supersedes=r2, superseded_by=null)
  KO_B.superseded_by = r3

Chain: r1 ← r2 ← r3
```

The chain is traversable in both directions:
- Forward: follow `supersedes` to find the predecessor
- Backward: follow `superseded_by` to find the successor

## When Revisions Are Created

| Event | Action | New revision? |
|-------|--------|---------------|
| Initial acquisition | Create KO with `revision_id`, `supersedes=null` | Yes (initial) |
| Content refresh (same source, updated content) | New KO with new `revision_id`, `supersedes` = old revision ID | Yes |
| Content correction (error fixed) | New KO with new `revision_id`, `supersedes` = old revision ID | Yes |
| Metadata enrichment (topics, relationships) | New KO with new `revision_id`, `supersedes` = old revision ID | Yes |
| Schema migration | New KO with updated `version`, new `revision_id` | Yes |
| Manual deprecation | Set `superseded_by` and `deprecation_reason` on old revision | No (metadata-only) |

## Replacement Policy

When a new revision supersedes an old one:

1. **The old revision is NOT deleted.** It remains in storage with `superseded_by` set to the new revision's ID and `deprecation_reason` populated.
2. **The old revision is marked deprecated.** Downstream consumers that request by `id` receive the latest revision by default but can request specific revisions.
3. **The acquisition chain accumulates.** The new revision's `acquisition_chain` includes both the new acquisition record AND all records from the superseded revision's chain. This ensures full provenance.
4. **Confidence is re-evaluated.** The new revision gets its own confidence score based on the combined evidence of both revisions.

### Confidence During Replacement

```
initial_confidence = 0.75  ← initial acquisition
refresh_confidence = 0.85  ← refresh with more evidence

combined_confidence = max(initial_confidence, refresh_confidence) + 0.02
                      ↘ corroboration bonus for consistent evidence
```

If the refresh produces contradictory content, confidence uses the lower of the two scores and documents the contradiction.

## Deprecation

### Deprecation Reasons

| Reason | Meaning | Example |
|--------|---------|---------|
| `content_updated` | New content from same source | Web page was updated |
| `content_corrected` | Error in previous revision was fixed | Wrong version number corrected |
| `source_unavailable` | Source no longer accessible | URL returns 404 |
| `manually_deprecated` | Administrator marked as outdated | Information is no longer accurate |
| `superseded_by_merger` | Multiple KOs merged into one | Two documents about same topic consolidated |

### Deprecation Timeline

```
active → deprecated → archived → (eventually) deleted
  ↑          ↑            ↑
  current    no longer    past retention
  revision   current      policy
```

- **Active**: The latest revision. Returned by default for `get(id)` queries.
- **Deprecated**: Has a `superseded_by` value. Returned only for specific `get(revision_id)` queries.
- **Archived**: Past retention policy threshold. Moved to cold storage but still retrievable.

## Future Graph Compatibility

The revision model is designed to support future graph traversal:

```
KO_A (r1) ──supersedes──→ KO_A (r2) ──supersedes──→ KO_A (r3)
  │                          │                          │
  ├── cites ───────────────→ KO_B (r1)
  │                          │
  └── supplements ─────────→ KO_C (r1) ──supersedes──→ KO_C (r2)
```

Graph queries can follow both revision chains and relationship edges, enabling queries like:
- "Show me the evolution of this knowledge object"
- "What was known about X before the correction?"
- "Find all current revisions that cite deprecated revisions"

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| `revision_id` field | NOT YET IMPLEMENTED | Needs schema version bump to 2 |
| `supersedes` field | NOT YET IMPLEMENTED | Needs schema version bump to 2 |
| `superseded_by` field | NOT YET IMPLEMENTED | Needs schema version bump to 2 |
| `deprecation_reason` field | NOT YET IMPLEMENTED | Needs schema version bump to 2 |
| Revision chain traversal | NOT YET IMPLEMENTED | Requires Knowledge Layer query support |
| Auto-revision on refresh | NOT YET IMPLEMENTED | Requires Planning Layer coordination |
| Deprecation lifecycle | NOT YET IMPLEMENTED | Requires retention policy in Knowledge Layer |

**Current Phase (1.2B)**: Architecture defined. No implementation changes to Knowledge Object schema.

## Migration Path

| Step | Phase | Description |
|------|-------|-------------|
| 1 | 1.3 | Add `revision_id`, `supersedes`, `superseded_by`, `deprecation_reason` to schema (version 2) |
| 2 | 1.3 | Update KO creation to generate `revision_id` (initially equals `id`) |
| 3 | 2.0 | Implement revision creation on content refresh |
| 4 | 2.0 | Implement revision chain traversal in Knowledge Layer |
| 5 | 2.0 | Implement deprecation lifecycle and archival |
