"""Knowledge Repository — Repository pattern for Knowledge Objects

Repositories persist and retrieve KnowledgeObjects without business logic.
"""

from typing import Optional, List, Dict, Any
from ...knowledge_object import KnowledgeObject
from ..interfaces.store import KnowledgeStore


class KnowledgeRepository:
    """Repository for KnowledgeObjects using a KnowledgeStore backend."""

    def __init__(self, store: KnowledgeStore):
        self._store = store

    def store(self, ko: KnowledgeObject) -> str:
        """Store a knowledge object. Returns the stored object's ID."""
        return self._store.store(ko)

    def get_by_id(self, obj_id: str) -> Optional[KnowledgeObject]:
        """Retrieve a knowledge object by its ID."""
        return self._store.retrieve_by_id(obj_id)

    def get_by_content_hash(self, content_hash: str) -> Optional[KnowledgeObject]:
        """Retrieve a knowledge object by its content hash."""
        return self._store.retrieve_by_hash(content_hash)

    def get_by_raw_hash(self, raw_content_hash: str) -> Optional[KnowledgeObject]:
        """Retrieve a knowledge object by its raw content hash."""
        return self._store.retrieve_by_raw_hash(raw_content_hash)

    def get_children(self, parent_id: str) -> List[KnowledgeObject]:
        """Retrieve all child knowledge objects for a given parent ID."""
        return self._store.retrieve_by_parent(parent_id)

    def list_all(self, limit: int = 10000, offset: int = 0) -> List[KnowledgeObject]:
        """List all knowledge objects with pagination."""
        return self._store.list_all(limit, offset)

    def list_by_source(self, source_id: str, limit: int = 100, offset: int = 0) -> List[KnowledgeObject]:
        """List knowledge objects by source ID."""
        return self._store.list_by_source(source_id, limit, offset)

    def list_by_date_range(self, start_date: str, end_date: str, limit: int = 100) -> List[KnowledgeObject]:
        """List knowledge objects by acquisition date range."""
        return self._store.list_by_date_range(start_date, end_date, limit)

    def delete(self, obj_id: str) -> bool:
        """Delete a knowledge object by ID."""
        return self._store.delete(obj_id)

    def check_duplicate(self, content_hash: str) -> Optional[str]:
        """Check if an object with the given content_hash already exists. Returns ID if found."""
        return self._store.check_duplicate(content_hash)

    def get_metrics(self) -> Dict[str, Any]:
        """Get storage metrics."""
        return self._store.get_metrics()
