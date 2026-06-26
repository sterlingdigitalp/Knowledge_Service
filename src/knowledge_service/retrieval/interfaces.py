"""Retrieval Layer — Interfaces, Query Objects, and Retrieval Results

The Retrieval Layer provides deterministic access to stored Knowledge Objects.
It depends only upon repository interfaces, not storage or acquisition layers.
"""

from typing import Optional, List, Dict, Any, Protocol, runtime_checkable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class SortOrder(Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"


class SortField(Enum):
    ACQUIRED_AT = "acquired_at"
    UPDATED_AT = "updated_at"
    CONFIDENCE = "confidence"
    WORD_COUNT = "word_count"
    VERSION = "version"
    TITLE = "title"


@dataclass
class QueryFilter:
    field: str
    value: Any
    operator: str = "eq"  # eq, neq, gt, gte, lt, lte, in, contains


@dataclass
class KnowledgeQuery:
    object_types: Optional[List[str]] = None
    source_ids: Optional[List[str]] = None
    parent_ids: Optional[List[str]] = None
    confidence_min: Optional[float] = None
    confidence_max: Optional[float] = None
    acquired_after: Optional[str] = None
    acquired_before: Optional[str] = None
    updated_after: Optional[str] = None
    updated_before: Optional[str] = None
    content_hash: Optional[str] = None
    raw_content_hash: Optional[str] = None
    request_id: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    filters: List[QueryFilter] = field(default_factory=list)

    limit: int = 100
    offset: int = 0
    sort_field: SortField = SortField.ACQUIRED_AT
    sort_order: SortOrder = SortOrder.DESCENDING

    projection_fields: Optional[List[str]] = None

    include_validation: bool = False
    include_metrics: bool = False
    include_timing: bool = True


@dataclass
class RetrievalWarning:
    code: str
    message: str
    object_id: Optional[str] = None


@dataclass
class RetrievalTiming:
    start: float = 0.0
    query_preparation: float = 0.0
    repository_query: float = 0.0
    validation: float = 0.0
    assembly: float = 0.0
    total: float = 0.0


@dataclass
class RetrievalSourceSummary:
    source_id: str
    object_count: int
    source_type: str


@dataclass
class RetrievalResult:
    objects: List[Any]  # KnowledgeObject or dict
    total_count: int
    returned_count: int
    offset: int
    limit: int
    warnings: List[RetrievalWarning] = field(default_factory=list)
    timing: Optional[RetrievalTiming] = None
    source_summary: List[RetrievalSourceSummary] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


class KnowledgeRetriever(Protocol):
    """Protocol for Knowledge Retrieval implementations."""

    def retrieve_by_id(self, obj_id: str) -> RetrievalResult:
        ...

    def retrieve_by_content_hash(self, content_hash: str) -> RetrievalResult:
        ...

    def retrieve_by_raw_hash(self, raw_hash: str) -> RetrievalResult:
        ...

    def retrieve_by_parent(self, parent_id: str, query: Optional[KnowledgeQuery] = None) -> RetrievalResult:
        ...

    def retrieve_by_source(self, source_id: str, query: Optional[KnowledgeQuery] = None) -> RetrievalResult:
        ...

    def retrieve_by_acquisition(self, request_id: str) -> RetrievalResult:
        ...

    def retrieve_by_time_range(self, start: str, end: str, query: Optional[KnowledgeQuery] = None) -> RetrievalResult:
        ...

    def retrieve_by_type(self, obj_type: str, query: Optional[KnowledgeQuery] = None) -> RetrievalResult:
        ...

    def retrieve_by_confidence(self, min_conf: float, max_conf: float = 1.0, query: Optional[KnowledgeQuery] = None) -> RetrievalResult:
        ...

    def retrieve_hierarchy(self, document_id: str) -> RetrievalResult:
        ...

    def retrieve_query(self, query: KnowledgeQuery) -> RetrievalResult:
        ...

    def list_all(self, query: Optional[KnowledgeQuery] = None) -> RetrievalResult:
        ...

    def exists(self, obj_id: str) -> bool:
        ...

    def count(self, query: Optional[KnowledgeQuery] = None) -> int:
        ...

    def get_metrics(self) -> Dict[str, Any]:
        ...
