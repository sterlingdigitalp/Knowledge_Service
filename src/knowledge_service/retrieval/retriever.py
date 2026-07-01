"""Knowledge Retriever — Deterministic Retrieval Engine for Knowledge Objects

The Retriever provides deterministic access to stored Knowledge Objects
without knowledge of acquisition, processing, or storage internals.
It depends only on repository interfaces.
"""

import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from ..knowledge_object import KnowledgeObject, KnowledgeType
from ..storage.repositories.knowledge_repository import KnowledgeRepository
from .interfaces import (
    KnowledgeQuery, RetrievalResult, RetrievalWarning, RetrievalTiming,
    RetrievalSourceSummary, SortField, SortOrder, QueryFilter,
)
from .validation import RetrievalValidator
from .hierarchy import assemble_hierarchy


@dataclass
class RetrievalMetrics:
    queries_executed: int = 0
    objects_returned: int = 0
    total_latency_ms: float = 0.0
    duplicate_retrievals_prevented: int = 0
    validation_warnings_issued: int = 0
    hierarchy_assemblies: int = 0
    _last_request_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "queries_executed": self.queries_executed,
            "objects_returned": self.objects_returned,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "avg_latency_ms": round(self.total_latency_ms / max(self.queries_executed, 1), 2),
            "duplicate_retrievals_prevented": self.duplicate_retrievals_prevented,
            "validation_warnings_issued": self.validation_warnings_issued,
            "hierarchy_assemblies": self.hierarchy_assemblies,
        }


def _build_timing(start: float, stages: Dict[str, float]) -> RetrievalTiming:
    return RetrievalTiming(
        start=start,
        query_preparation=stages.get("prepare", 0.0),
        repository_query=stages.get("query", 0.0),
        validation=stages.get("validation", 0.0),
        assembly=stages.get("assembly", 0.0),
        total=time.time() - start,
    )


class KnowledgeRetrieverImpl:
    """Deterministic retrieval engine for Knowledge Objects.

    Depends only on KnowledgeRepository (not the store directly).
    All retrieval operations are deterministic and stateless."""
    def __init__(self, repository: KnowledgeRepository):
        self._repo = repository
        self._validator = RetrievalValidator()
        self._metrics = RetrievalMetrics()

    def retrieve_by_id(self, obj_id: str) -> RetrievalResult:
        start = time.time()
        stages: Dict[str, float] = {}
        t0 = time.time()

        obj = self._repo.get_by_id(obj_id)
        stages["query"] = time.time() - t0

        self._metrics.queries_executed += 1
        self._metrics.objects_returned += 1 if obj else 0

        if obj is None:
            result = RetrievalResult(
                objects=[], total_count=0, returned_count=0,
                offset=0, limit=1,
                timing=_build_timing(start, stages),
                metadata={"request_type": "retrieve_by_id"},
            )
            self._record_timing(result.timing)
            return result

        t1 = time.time()
        warnings = self._validator.validate(obj)
        stages["validation"] = time.time() - t1
        self._metrics.validation_warnings_issued += len(warnings)

        result = RetrievalResult(
            objects=[obj],
            total_count=1,
            returned_count=1,
            offset=0, limit=1,
            warnings=warnings,
            timing=_build_timing(start, stages),
            metadata={"request_type": "retrieve_by_id"},
        )
        self._record_timing(result.timing)
        return result

    def retrieve_by_content_hash(self, content_hash: str) -> RetrievalResult:
        start = time.time()
        stages: Dict[str, float] = {}
        t0 = time.time()

        obj = self._repo.get_by_content_hash(content_hash)
        stages["query"] = time.time() - t0

        self._metrics.queries_executed += 1
        self._metrics.objects_returned += 1 if obj else 0

        if obj is None:
            return RetrievalResult(
                objects=[], total_count=0, returned_count=0,
                offset=0, limit=1,
                timing=_build_timing(start, stages),
                metadata={"request_type": "retrieve_by_hash"},
            )

        t1 = time.time()
        warnings = self._validator.validate(obj)
        stages["validation"] = time.time() - t1
        self._metrics.validation_warnings_issued += len(warnings)

        result = RetrievalResult(
            objects=[obj],
            total_count=1, returned_count=1,
            offset=0, limit=1,
            warnings=warnings,
            timing=_build_timing(start, stages),
            metadata={"request_type": "retrieve_by_content_hash"},
        )
        self._record_timing(result.timing)
        return result

    def retrieve_by_raw_hash(self, raw_hash: str) -> RetrievalResult:
        start = time.time()
        stages: Dict[str, float] = {}
        t0 = time.time()

        obj = self._repo.get_by_raw_hash(raw_hash)
        stages["query"] = time.time() - t0

        self._metrics.queries_executed += 1
        self._metrics.objects_returned += 1 if obj else 0

        if obj is None:
            result = RetrievalResult(
                objects=[], total_count=0, returned_count=0,
                offset=0, limit=1,
                timing=_build_timing(start, stages),
                metadata={"request_type": "retrieve_by_raw_hash"},
            )
            self._record_timing(result.timing)
            return result

        t1 = time.time()
        warnings = self._validator.validate(obj)
        stages["validation"] = time.time() - t1

        result = RetrievalResult(
            objects=[obj],
            total_count=1, returned_count=1,
            offset=0, limit=1,
            warnings=warnings,
            timing=_build_timing(start, stages),
            metadata={"request_type": "retrieve_by_raw_hash"},
        )
        self._record_timing(result.timing)
        return result

    def retrieve_by_parent(self, parent_id: str, query: Optional[KnowledgeQuery] = None) -> RetrievalResult:
        start = time.time()
        stages: Dict[str, float] = {}
        q = query or KnowledgeQuery()
        t0 = time.time()

        children = self._repo.get_children(parent_id)
        stages["query"] = time.time() - t0

        self._metrics.queries_executed += 1
        return self._apply_query_to_list(children, q, start, stages, "retrieve_by_parent")

    def retrieve_by_source(self, source_id: str, query: Optional[KnowledgeQuery] = None) -> RetrievalResult:
        start = time.time()
        stages: Dict[str, float] = {}
        q = query or KnowledgeQuery()
        t0 = time.time()

        objs = self._repo.list_by_source(source_id, limit=10000, offset=0)
        stages["query"] = time.time() - t0

        self._metrics.queries_executed += 1
        return self._apply_query_to_list(objs, q, start, stages, "retrieve_by_source")

    def retrieve_by_acquisition(self, request_id: str) -> RetrievalResult:
        start = time.time()
        stages: Dict[str, float] = {}
        t0 = time.time()

        all_objs = self._list_all_objects_raw()
        matched = [ko for ko in all_objs if any(
            a.request_id == request_id for a in ko.acquisition_chain
        )]
        stages["query"] = time.time() - t0

        self._metrics.queries_executed += 1
        self._metrics.objects_returned += len(matched)

        t1 = time.time()
        warnings = []
        for obj in matched:
            warnings.extend(self._validator.validate(obj))
        stages["validation"] = time.time() - t1
        self._metrics.validation_warnings_issued += len(warnings)

        src_summary = self._build_source_summary(matched)
        result = RetrievalResult(
            objects=matched,
            total_count=len(matched),
            returned_count=len(matched),
            offset=0, limit=len(matched),
            warnings=warnings,
            source_summary=src_summary,
            timing=_build_timing(start, stages),
            metadata={"request_type": "retrieve_by_acquisition", "request_id": request_id},
        )
        self._record_timing(result.timing)
        return result

    def retrieve_by_time_range(self, start_dt: str, end_dt: str,
                               query: Optional[KnowledgeQuery] = None) -> RetrievalResult:
        start = time.time()
        stages: Dict[str, float] = {}
        q = query or KnowledgeQuery()
        t0 = time.time()

        objs = self._repo.list_by_date_range(start_dt, end_dt, limit=10000)
        stages["query"] = time.time() - t0

        self._metrics.queries_executed += 1
        return self._apply_query_to_list(objs, q, start, stages, "retrieve_by_time_range")

    def retrieve_by_type(self, obj_type: str, query: Optional[KnowledgeQuery] = None) -> RetrievalResult:
        type_filter = KnowledgeType(obj_type)
        start = time.time()
        stages: Dict[str, float] = {}
        q = query or KnowledgeQuery()
        t0 = time.time()

        all_objs = self._list_all_objects_raw()
        matched = [ko for ko in all_objs if ko.type == type_filter]
        stages["query"] = time.time() - t0

        self._metrics.queries_executed += 1
        return self._apply_query_to_list(matched, q, start, stages, "retrieve_by_type")

    def retrieve_by_confidence(self, min_conf: float, max_conf: float = 1.0,
                               query: Optional[KnowledgeQuery] = None) -> RetrievalResult:
        start = time.time()
        stages: Dict[str, float] = {}
        q = query or KnowledgeQuery()
        t0 = time.time()

        all_objs = self._list_all_objects_raw()
        matched = [ko for ko in all_objs if min_conf <= ko.confidence <= max_conf]
        stages["query"] = time.time() - t0

        self._metrics.queries_executed += 1
        return self._apply_query_to_list(matched, q, start, stages, "retrieve_by_confidence")

    def retrieve_hierarchy(self, document_id: str) -> RetrievalResult:
        start = time.time()
        stages: Dict[str, float] = {}
        t0 = time.time()

        doc = self._repo.get_by_id(document_id)
        if doc is None:
            stages["query"] = time.time() - t0
            self._metrics.queries_executed += 1
            result = RetrievalResult(
                objects=[], total_count=0, returned_count=0,
                offset=0, limit=1,
                warnings=[RetrievalWarning(
                    code="DOCUMENT_NOT_FOUND", message=f"Document {document_id} not found"
                )],
                timing=_build_timing(start, stages),
                metadata={"request_type": "retrieve_hierarchy"},
            )
            self._record_timing(result.timing)
            return result

        children = self._repo.get_children(document_id)
        stages["query"] = time.time() - t0

        self._metrics.queries_executed += 1
        self._metrics.hierarchy_assemblies += 1

        t1 = time.time()
        tree = assemble_hierarchy(doc, children)
        stages["assembly"] = time.time() - t1

        self._metrics.objects_returned += len(tree)

        t2 = time.time()
        all_warnings = []
        for obj in tree:
            all_warnings.extend(self._validator.validate(obj))
        stages["validation"] = time.time() - t2
        self._metrics.validation_warnings_issued += len(all_warnings)

        result = RetrievalResult(
            objects=tree,
            total_count=len(tree),
            returned_count=len(tree),
            offset=0, limit=len(tree),
            warnings=all_warnings,
            timing=_build_timing(start, stages),
            metadata={"request_type": "retrieve_hierarchy", "document_id": document_id},
        )
        self._record_timing(result.timing)
        return result

    def retrieve_query(self, query: KnowledgeQuery) -> RetrievalResult:
        start = time.time()
        stages: Dict[str, float] = {}
        t0 = time.time()

        objs = self._list_all_objects_raw()
        stages["query"] = time.time() - t0

        self._metrics.queries_executed += 1
        return self._apply_query_to_list(objs, query, start, stages, "query")

    def list_all(self, query: Optional[KnowledgeQuery] = None) -> RetrievalResult:
        return self.retrieve_query(query or KnowledgeQuery())

    def exists(self, obj_id: str) -> bool:
        obj = self._repo.get_by_id(obj_id)
        self._metrics.queries_executed += 1
        return obj is not None

    def count(self, query: Optional[KnowledgeQuery] = None) -> int:
        q = query or KnowledgeQuery()
        all_objs = self._list_all_objects_raw()
        filtered = self._apply_filters(all_objs, q)
        self._metrics.queries_executed += 1
        return len(filtered)

    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.to_dict()

    def _record_timing(self, timing: Optional[RetrievalTiming]):
        if timing is not None:
            self._metrics.total_latency_ms += timing.total * 1000

    def _list_all_objects_raw(self) -> List[KnowledgeObject]:
        return self._repo.list_all(limit=100000, offset=0)

    def _apply_filters(self, objs: List[KnowledgeObject],
                       query: KnowledgeQuery) -> List[KnowledgeObject]:
        result = list(objs)

        if query.object_types:
            types_set = set(query.object_types)
            result = [ko for ko in result if ko.type.value in types_set]

        if query.source_ids:
            src_set = set(query.source_ids)
            result = [ko for ko in result if ko.source_id in src_set]

        if query.parent_ids:
            parent_set = set(query.parent_ids)
            result = [ko for ko in result if ko.parent_id in parent_set]

        if query.confidence_min is not None:
            result = [ko for ko in result if ko.confidence >= query.confidence_min]

        if query.confidence_max is not None:
            result = [ko for ko in result if ko.confidence <= query.confidence_max]

        if query.acquired_after:
            result = [ko for ko in result if ko.acquired_at >= query.acquired_after]

        if query.acquired_before:
            result = [ko for ko in result if ko.acquired_at <= query.acquired_before]

        if query.updated_after:
            result = [ko for ko in result if ko.updated_at >= query.updated_after]

        if query.updated_before:
            result = [ko for ko in result if ko.updated_at <= query.updated_before]

        if query.content_hash:
            result = [ko for ko in result if ko.content_hash == query.content_hash]

        if query.raw_content_hash:
            result = [ko for ko in result if ko.raw_content_hash == query.raw_content_hash]

        if query.request_id:
            result = [ko for ko in result if any(
                a.request_id == query.request_id for a in ko.acquisition_chain
            )]

        for f in query.filters:
            if f.operator == "eq":
                result = [ko for ko in result if getattr(ko, f.field, None) == f.value]
            elif f.operator == "neq":
                result = [ko for ko in result if getattr(ko, f.field, None) != f.value]
            elif f.operator == "gt":
                result = [ko for ko in result if (getattr(ko, f.field, None) or 0) > f.value]
            elif f.operator == "gte":
                result = [ko for ko in result if (getattr(ko, f.field, None) or 0) >= f.value]
            elif f.operator == "lt":
                result = [ko for ko in result if (getattr(ko, f.field, None) or 0) < f.value]
            elif f.operator == "lte":
                result = [ko for ko in result if (getattr(ko, f.field, None) or 0) <= f.value]
            elif f.operator == "in":
                if hasattr(f.value, '__iter__') and not isinstance(f.value, str):
                    result = [ko for ko in result if getattr(ko, f.field, None) in f.value]
            elif f.operator == "contains":
                result = [ko for ko in result if self._contains_filter_value(getattr(ko, f.field, None), f.value)]

        return result

    def _contains_filter_value(self, current: Any, expected: Any) -> bool:
        if current is None:
            return False
        if isinstance(current, str):
            return str(expected) in current
        if isinstance(current, dict):
            return expected in current.values() or expected in current.keys()
        if hasattr(current, "__iter__"):
            return expected in current
        return False

    def _apply_sorting(self, objs: List[KnowledgeObject],
                       query: KnowledgeQuery) -> List[KnowledgeObject]:
        field_map = {
            SortField.ACQUIRED_AT: lambda ko: ko.acquired_at or "",
            SortField.UPDATED_AT: lambda ko: ko.updated_at or "",
            SortField.CONFIDENCE: lambda ko: ko.confidence,
            SortField.WORD_COUNT: lambda ko: ko.word_count,
            SortField.VERSION: lambda ko: ko.version,
            SortField.TITLE: lambda ko: ko.title or "",
        }
        key_fn = field_map.get(query.sort_field, field_map[SortField.ACQUIRED_AT])
        reverse = query.sort_order == SortOrder.DESCENDING
        return sorted(objs, key=key_fn, reverse=reverse)

    def _apply_projection(self, objs: List[KnowledgeObject],
                          fields: Optional[List[str]]) -> List[KnowledgeObject]:
        if not fields:
            return objs
        projected = []
        for ko in objs:
            d = ko.to_dict()
            filtered = {k: v for k, v in d.items() if k in fields}
            projected.append(filtered)
        return projected

    def _build_source_summary(self, objs: List[KnowledgeObject]) -> List[RetrievalSourceSummary]:
        src_counts: Dict[str, Dict[str, Any]] = {}
        for ko in objs:
            if ko.source_id not in src_counts:
                src_counts[ko.source_id] = {"count": 0, "type": ko.source_type.value}
            src_counts[ko.source_id]["count"] += 1
        return [
            RetrievalSourceSummary(source_id=sid, object_count=info["count"], source_type=info["type"])
            for sid, info in src_counts.items()
        ]

    def _apply_query_to_list(self, objs: List[KnowledgeObject], query: KnowledgeQuery,
                              start: float, stages: Dict[str, float],
                              request_type: str) -> RetrievalResult:
        t_pre = time.time()
        filtered = self._apply_filters(objs, query)
        stages["query"] = stages.get("query", 0.0) + (time.time() - t_pre)

        sorted_objs = self._apply_sorting(filtered, query)
        total = len(sorted_objs)

        paginated = sorted_objs[query.offset:query.offset + query.limit]

        projected = self._apply_projection(paginated, query.projection_fields)

        self._metrics.objects_returned += len(projected)

        t_val = time.time()
        all_warnings = []
        if query.include_validation:
            for obj in (paginated if not query.projection_fields else objs):
                all_warnings.extend(self._validator.validate(obj))
        stages["validation"] = time.time() - t_val
        self._metrics.validation_warnings_issued += len(all_warnings)

        src_summary = self._build_source_summary(projected if not query.projection_fields else paginated)

        result = RetrievalResult(
            objects=projected,
            total_count=total,
            returned_count=len(projected),
            offset=query.offset,
            limit=query.limit,
            warnings=all_warnings if query.include_validation else [],
            source_summary=src_summary,
            timing=_build_timing(start, stages) if query.include_timing else None,
            metadata={"request_type": request_type},
        )
        self._record_timing(result.timing)
        return result
