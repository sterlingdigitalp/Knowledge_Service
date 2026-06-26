"""In-Memory Knowledge Store — In-memory implementation of the KnowledgeStore interface for testing"""

from typing import Optional, List, Dict, Any
import uuid
from ...knowledge_object import KnowledgeObject, KnowledgeType, SourceType, IndexStatus
from ..interfaces.store import KnowledgeStore
from ..interfaces.source_store import SourceStore
from ..repositories.source_entry import SourceEntry
from datetime import datetime, timezone


class InMemoryKnowledgeStore(KnowledgeStore):
    """In-memory implementation of the KnowledgeStore interface for testing and demonstration."""

    def __init__(self):
        self._objects: Dict[str, KnowledgeObject] = {}
        self._by_content_hash: Dict[str, str] = {}  # content_hash -> object_id
        self._by_raw_hash: Dict[str, str] = {}  # raw_content_hash -> object_id
        self._by_parent: Dict[str, List[str]] = {}  # parent_id -> list of object_ids
        self._metrics = {
            "objects_stored": 0,
            "objects_retrieved": 0,
            "duplicates_prevented": 0,
        }

    def store(self, ko: KnowledgeObject) -> str:
        # Check for duplicate by content_hash
        if ko.content_hash in self._by_content_hash:
            self._metrics["duplicates_prevented"] += 1
            return self._by_content_hash[ko.content_hash]

        # Store the object
        self._objects[ko.id] = ko
        self._by_content_hash[ko.content_hash] = ko.id
        if ko.raw_content_hash:
            self._by_raw_hash[ko.raw_content_hash] = ko.id
        if ko.parent_id:
            if ko.parent_id not in self._by_parent:
                self._by_parent[ko.parent_id] = []
            self._by_parent[ko.parent_id].append(ko.id)

        self._metrics["objects_stored"] += 1
        return ko.id

    def retrieve_by_id(self, obj_id: str) -> Optional[KnowledgeObject]:
        self._metrics["objects_retrieved"] += 1
        return self._objects.get(obj_id)

    def retrieve_by_hash(self, content_hash: str) -> Optional[KnowledgeObject]:
        self._metrics["objects_retrieved"] += 1
        obj_id = self._by_content_hash.get(content_hash)
        if obj_id:
            return self._objects.get(obj_id)
        return None

    def retrieve_by_raw_hash(self, raw_content_hash: str) -> Optional[KnowledgeObject]:
        self._metrics["objects_retrieved"] += 1
        obj_id = self._by_raw_hash.get(raw_content_hash)
        if obj_id:
            return self._objects.get(obj_id)
        return None

    def retrieve_by_parent(self, parent_id: str) -> List[KnowledgeObject]:
        self._metrics["objects_retrieved"] += len(self._by_parent.get(parent_id, []))
        return [self._objects[obj_id] for obj_id in self._by_parent.get(parent_id, []) if obj_id in self._objects]

    def list_all(self, limit: int = 10000, offset: int = 0) -> List[KnowledgeObject]:
        objs = list(self._objects.values())
        self._metrics["objects_retrieved"] += len(objs[offset:offset+limit])
        return objs[offset:offset+limit]

    def list_by_source(self, source_id: str, limit: int = 100, offset: int = 0) -> List[KnowledgeObject]:
        objs = [ko for ko in self._objects.values() if ko.source_id == source_id]
        self._metrics["objects_retrieved"] += len(objs[offset:offset+limit])
        return objs[offset:offset+limit]

    def list_by_date_range(self, start_date: str, end_date: str, limit: int = 100) -> List[KnowledgeObject]:
        objs = [ko for ko in self._objects.values() if start_date <= ko.acquired_at <= end_date]
        self._metrics["objects_retrieved"] += len(objs[:limit])
        return objs[:limit]

    def delete(self, obj_id: str) -> bool:
        if obj_id not in self._objects:
            return False
        ko = self._objects[obj_id]
        del self._objects[obj_id]
        if ko.content_hash in self._by_content_hash:
            del self._by_content_hash[ko.content_hash]
        if ko.raw_content_hash in self._by_raw_hash:
            del self._by_raw_hash[ko.raw_content_hash]
        if ko.parent_id and obj_id in self._by_parent.get(ko.parent_id, []):
            self._by_parent[ko.parent_id].remove(obj_id)
        return True

    def check_duplicate(self, content_hash: str) -> Optional[str]:
        return self._by_content_hash.get(content_hash)

    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.copy()

    def health(self) -> bool:
        return True


class InMemorySourceStore(SourceStore):
    """In-memory SourceStore implementation for tests and deterministic unit runs."""

    def __init__(self):
        self._sources: Dict[str, SourceEntry] = {}
        self._metrics = {
            "sources_registered": 0,
            "metrics_updated": 0,
            "searches_run": 0,
            "list_requests": 0,
        }

    def register_source(self, source: SourceEntry) -> bool:
        if source.id in self._sources:
            return False
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        source.updated_at = source.created_at or now
        self._sources[source.id] = source
        self._metrics["sources_registered"] += 1
        return True

    def get_source(self, source_id: str) -> Optional[SourceEntry]:
        return self._sources.get(source_id)

    def update_source_metrics(self, source_id: str, trust_score: Optional[float] = None,
                             freshness_score: Optional[float] = None, avg_latency_ms: Optional[int] = None,
                             success_rate: Optional[float] = None, last_acquired_at: Optional[str] = None,
                             status: Optional[str] = None):
        source = self._sources.get(source_id)
        if source is None:
            return False

        if trust_score is not None:
            source.trust_score = trust_score
        if freshness_score is not None:
            source.freshness_score = freshness_score
        if avg_latency_ms is not None:
            source.avg_latency_ms = avg_latency_ms
        if success_rate is not None:
            source.success_rate = success_rate
        if last_acquired_at is not None:
            source.last_acquired_at = last_acquired_at
        if status is not None:
            source.status = status

        source.updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._metrics["metrics_updated"] += 1
        return True

    def list_sources(self, status: Optional[str] = None, limit: int = 100) -> List[SourceEntry]:
        self._metrics["list_requests"] += 1
        result = list(self._sources.values())
        if status:
            normalized_status = status.lower()
            result = [s for s in result if s.status == normalized_status]

        result.sort(key=lambda source: source.updated_at, reverse=True)
        return result[:limit]

    def search_by_topic(self, topic: str, min_confidence: float = 0.3) -> List[SourceEntry]:
        self._metrics["searches_run"] += 1
        normalized_topic = topic.strip().lower()
        if not normalized_topic:
            return []

        matches = []
        for source in self._sources.values():
            confidence = source.topic_scores.get(normalized_topic, 0.0)
            if normalized_topic not in source.topic_scores and normalized_topic in [t.lower() for t in source.topics]:
                confidence = 1.0
            if confidence >= min_confidence:
                matches.append(source)
        matches.sort(key=lambda source: (source.topic_scores.get(normalized_topic, 0.0), source.trust_score), reverse=True)
        return matches

    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.copy()

    def health(self) -> bool:
        return True
