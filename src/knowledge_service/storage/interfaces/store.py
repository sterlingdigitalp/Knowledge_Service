"""Knowledge Store Interface — Abstract storage layer for Knowledge Objects

Defines the contract for all knowledge store implementations.
No SQL should escape this interface; it is purely abstract.
"""

from typing import Optional, List, Dict, Any
from ...knowledge_object import KnowledgeObject


class KnowledgeStore:
    """Abstract interface for knowledge object persistence."""

    def store(self, ko: KnowledgeObject) -> str:
        """Store a knowledge object. Returns the stored object's ID."""
        raise NotImplementedError

    def retrieve_by_id(self, obj_id: str) -> Optional[KnowledgeObject]:
        """Retrieve a knowledge object by its ID."""
        raise NotImplementedError

    def retrieve_by_hash(self, content_hash: str) -> Optional[KnowledgeObject]:
        """Retrieve a knowledge object by its content hash."""
        raise NotImplementedError

    def retrieve_by_raw_hash(self, raw_content_hash: str) -> Optional[KnowledgeObject]:
        """Retrieve a knowledge object by its raw content hash."""
        raise NotImplementedError

    def retrieve_by_parent(self, parent_id: str) -> List[KnowledgeObject]:
        """Retrieve all child knowledge objects for a given parent ID."""
        raise NotImplementedError

    def list_all(self, limit: int = 10000, offset: int = 0) -> List[KnowledgeObject]:
        """List all knowledge objects with pagination."""
        raise NotImplementedError

    def list_by_source(self, source_id: str, limit: int = 100, offset: int = 0) -> List[KnowledgeObject]:
        """List knowledge objects by source ID."""
        raise NotImplementedError

    def list_by_date_range(self, start_date: str, end_date: str, limit: int = 100) -> List[KnowledgeObject]:
        """List knowledge objects by acquisition date range."""
        raise NotImplementedError

    def delete(self, obj_id: str) -> bool:
        """Delete a knowledge object by ID. Returns True if deleted, False if not found."""
        raise NotImplementedError

    def check_duplicate(self, content_hash: str) -> Optional[str]:
        """Check if an object with the given content_hash already exists. Returns ID if found, None otherwise."""
        raise NotImplementedError

    def get_metrics(self) -> Dict[str, Any]:
        """Get storage metrics: objects stored, retrieved, duplicates prevented."""
        raise NotImplementedError

    def health(self) -> bool:
        """Check if the storage backend is healthy."""
        raise NotImplementedError
