# Query Objects — Phase 1.5

## Overview

Query Objects are the canonical way to specify retrieval parameters. They encapsulate all filtering, pagination, sorting, and projection concerns — replacing raw parameter passing or SQL fragments.

## KnowledgeQuery

```python
@dataclass
class KnowledgeQuery:
    object_types: Optional[List[str]]
    source_ids: Optional[List[str]]
    parent_ids: Optional[List[str]]
    confidence_min: Optional[float]
    confidence_max: Optional[float]
    acquired_after: Optional[str]       # ISO 8601
    acquired_before: Optional[str]      # ISO 8601
    updated_after: Optional[str]         # ISO 8601
    updated_before: Optional[str]        # ISO 8601
    content_hash: Optional[str]
    raw_content_hash: Optional[str]
    request_id: Optional[str]
    labels: Optional[Dict[str, str]]
    filters: List[QueryFilter]           # Custom field filters

    limit: int = 100
    offset: int = 0
    sort_field: SortField = SortField.ACQUIRED_AT
    sort_order: SortOrder = SortOrder.DESCENDING

    projection_fields: Optional[List[str]]

    include_validation: bool = False
    include_metrics: bool = False
    include_timing: bool = True
```

## QueryFilter

```python
@dataclass
class QueryFilter:
    field: str
    value: Any
    operator: str = "eq"  # eq, neq, gt, gte, lt, lte, in, contains
```

## SortField and SortOrder

```python
class SortField(Enum):
    ACQUIRED_AT = "acquired_at"
    UPDATED_AT = "updated_at"
    CONFIDENCE = "confidence"
    WORD_COUNT = "word_count"
    VERSION = "version"
    TITLE = "title"

class SortOrder(Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"
```

## Examples

### Retrieve all chunks of a document with pagination:
```python
query = KnowledgeQuery(
    parent_ids=["doc-123"],
    object_types=["chunk"],
    limit=50,
    offset=0,
    sort_field=SortField.ACQUIRED_AT,
    sort_order=SortOrder.ASCENDING,
)
result = retriever.retrieve_query(query)
```

### Retrieve high-confidence documents from specific sources:
```python
query = KnowledgeQuery(
    source_ids=["src-github-main"],
    confidence_min=0.8,
    object_types=["document"],
    limit=20,
)
result = retriever.retrieve_query(query)
```

### Count documents by type with projection:
```python
query = KnowledgeQuery(
    object_types=["document"],
    projection_fields=["id", "title", "confidence"],
    include_validation=False,
)
result = retriever.retrieve_query(query)
```
