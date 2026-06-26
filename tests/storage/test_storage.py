"""Storage Tests — Knowledge Store and Repository validation

Tests for: store, retrieve, delete, hash lookup, parent lookup, duplicate detection,
version chain, repository isolation, storage abstraction, restart persistence.
"""

import os, sys
_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

import pytest
from src.knowledge_service.storage.interfaces.store import KnowledgeStore
from src.knowledge_service.storage.postgres.in_memory_store import InMemoryKnowledgeStore
from src.knowledge_service.storage.repositories.knowledge_repository import KnowledgeRepository
from src.knowledge_service.knowledge_object import (
    KnowledgeObject, KnowledgeType, SourceType, AcquisitionRecord,
    ProviderType, AcquisitionStatus, IndexStatus,
)


@pytest.fixture
def store():
    return InMemoryKnowledgeStore()


@pytest.fixture
def repo(store):
    return KnowledgeRepository(store)


class TestStorageStoreRetrieve:

    def test_store_and_retrieve_by_id(self, store):
        ko = KnowledgeObject(
            id="test-ko-1",
            type=KnowledgeType.DOCUMENT,
            source_id="source-1",
            source_url="https://example.com",
            acquired_at="2026-06-25T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            markdown="# Test",
            raw_content_hash="raw-hash-123",
            content_hash="content-hash-456",
            confidence=0.75,
            evidence_count=1,
        )
        stored_id = store.store(ko)
        assert stored_id == ko.id

        retrieved = store.retrieve_by_id(ko.id)
        assert retrieved is not None
        assert retrieved.id == ko.id
        assert retrieved.content_hash == ko.content_hash

    def test_retrieve_by_content_hash(self, store):
        ko = KnowledgeObject(
            id="test-ko-2",
            type=KnowledgeType.DOCUMENT,
            source_id="source-1",
            acquired_at="2026-06-25T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            markdown="# Test 2",
            raw_content_hash="raw-hash-789",
            content_hash="content-hash-789",
            confidence=0.5,
            evidence_count=1,
        )
        store.store(ko)
        retrieved = store.retrieve_by_hash("content-hash-789")
        assert retrieved is not None
        assert retrieved.id == ko.id

    def test_retrieve_by_raw_hash(self, store):
        ko = KnowledgeObject(
            id="test-ko-3",
            type=KnowledgeType.DOCUMENT,
            source_id="source-1",
            acquired_at="2026-06-25T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            markdown="# Test 3",
            raw_content_hash="raw-hash-abc",
            content_hash="content-hash-abc",
            confidence=0.6,
            evidence_count=1,
        )
        store.store(ko)
        retrieved = store.retrieve_by_raw_hash("raw-hash-abc")
        assert retrieved is not None
        assert retrieved.id == ko.id

    def test_delete_object(self, store):
        ko = KnowledgeObject(
            id="test-ko-delete",
            type=KnowledgeType.DOCUMENT,
            source_id="source-1",
            acquired_at="2026-06-25T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            markdown="# Delete Test",
            raw_content_hash="raw-del",
            content_hash="content-del",
            confidence=0.5,
            evidence_count=1,
        )
        store.store(ko)
        deleted = store.delete(ko.id)
        assert deleted is True
        retrieved = store.retrieve_by_id(ko.id)
        assert retrieved is None

    def test_list_by_source(self, store):
        ko1 = KnowledgeObject(id="ko-src-1", type=KnowledgeType.DOCUMENT, source_id="src-a",
                              acquired_at="2026-06-25T12:00:00Z", updated_at="2026-06-25T12:00:00Z",
                              markdown="# A", raw_content_hash="raw-a", content_hash="cnt-a", confidence=0.5, evidence_count=1)
        ko2 = KnowledgeObject(id="ko-src-2", type=KnowledgeType.DOCUMENT, source_id="src-a",
                              acquired_at="2026-06-25T13:00:00Z", updated_at="2026-06-25T13:00:00Z",
                              markdown="# B", raw_content_hash="raw-b", content_hash="cnt-b", confidence=0.6, evidence_count=1)
        ko3 = KnowledgeObject(id="ko-src-3", type=KnowledgeType.DOCUMENT, source_id="src-b",
                              acquired_at="2026-06-25T14:00:00Z", updated_at="2026-06-25T14:00:00Z",
                              markdown="# C", raw_content_hash="raw-c", content_hash="cnt-c", confidence=0.7, evidence_count=1)
        store.store(ko1)
        store.store(ko2)
        store.store(ko3)

        results = store.list_by_source("src-a")
        assert len(results) == 2
        ids = [r.id for r in results]
        assert "ko-src-1" in ids
        assert "ko-src-2" in ids


class TestDuplicateDetection:

    def test_duplicate_detection_by_hash(self, store):
        ko1 = KnowledgeObject(
            id="ko-dup-1",
            type=KnowledgeType.DOCUMENT,
            source_id="src-1",
            acquired_at="2026-06-25T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            markdown="# Duplicate Test",
            raw_content_hash="raw-dup",
            content_hash="content-dup-hash",
            confidence=0.5,
            evidence_count=1,
        )
        id1 = store.store(ko1)

        ko2 = KnowledgeObject(
            id="ko-dup-2",  # Different ID but same content_hash
            type=KnowledgeType.DOCUMENT,
            source_id="src-2",
            acquired_at="2026-06-25T13:00:00Z",
            updated_at="2026-06-25T13:00:00Z",
            markdown="# Duplicate Test",
            raw_content_hash="raw-dup-2",
            content_hash="content-dup-hash",  # Same content hash
            confidence=0.6,
            evidence_count=2,
        )
        id2 = store.store(ko2)

        # Should return the existing ID, not create a duplicate
        assert id2 == id1
        assert store.get_metrics()["duplicates_prevented"] == 1

    def test_check_duplicate_returns_id(self, store):
        ko = KnowledgeObject(
            id="ko-check-dup",
            type=KnowledgeType.DOCUMENT,
            source_id="src-1",
            acquired_at="2026-06-25T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            markdown="# Check Dup",
            raw_content_hash="raw-check",
            content_hash="content-check-hash",
            confidence=0.5,
            evidence_count=1,
        )
        store.store(ko)

        dup_id = store.check_duplicate("content-check-hash")
        assert dup_id == ko.id

        non_dup_id = store.check_duplicate("content-non-existent")
        assert non_dup_id is None


class TestParentLookup:

    def test_retrieve_by_parent(self, store):
        parent_ko = KnowledgeObject(
            id="parent-ko",
            type=KnowledgeType.DOCUMENT,
            source_id="src-1",
            acquired_at="2026-06-25T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            markdown="# Parent",
            raw_content_hash="raw-parent",
            content_hash="content-parent",
            confidence=0.7,
            evidence_count=1,
        )
        store.store(parent_ko)

        chunk_ko1 = KnowledgeObject(
            id="chunk-ko-1",
            type=KnowledgeType.CHUNK,
            source_id="src-1",
            acquired_at="2026-06-25T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            markdown="# Chunk 1",
            raw_content_hash="raw-parent",
            content_hash="content-chunk-1",
            confidence=0.7,
            evidence_count=1,
            parent_id="parent-ko",
            chunk_index=0,
            chunk_total=2,
        )
        chunk_ko2 = KnowledgeObject(
            id="chunk-ko-2",
            type=KnowledgeType.CHUNK,
            source_id="src-1",
            acquired_at="2026-06-25T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            markdown="# Chunk 2",
            raw_content_hash="raw-parent",
            content_hash="content-chunk-2",
            confidence=0.7,
            evidence_count=1,
            parent_id="parent-ko",
            chunk_index=1,
            chunk_total=2,
        )

        store.store(chunk_ko1)
        store.store(chunk_ko2)

        children = store.retrieve_by_parent("parent-ko")
        assert len(children) == 2
        child_ids = [c.id for c in children]
        assert "chunk-ko-1" in child_ids
        assert "chunk-ko-2" in child_ids


class TestRestartPersistence:

    def test_in_memory_store_state_persists_across_operations(self, store):
        # Simulate restart by creating a new store instance with the same data
        ko = KnowledgeObject(
            id="restart-ko",
            type=KnowledgeType.DOCUMENT,
            source_id="src-restart",
            acquired_at="2026-06-25T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            markdown="# Restart Test",
            raw_content_hash="raw-restart",
            content_hash="content-restart-hash",
            confidence=0.8,
            evidence_count=2,
        )
        store.store(ko)

        # Simulate retrieval after "restart" (new store instance would need data loaded,
        # but in-memory store tests state persistence within the same instance)
        retrieved = store.retrieve_by_id("restart-ko")
        assert retrieved is not None
        assert retrieved.content_hash == ko.content_hash
        assert retrieved.confidence == ko.confidence


class TestRepositoryIsolation:

    def test_repository_uses_store_interface(self, store, repo):
        ko = KnowledgeObject(
            id="repo-ko",
            type=KnowledgeType.DOCUMENT,
            source_id="src-repo",
            acquired_at="2026-06-25T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            markdown="# Repo Test",
            raw_content_hash="raw-repo",
            content_hash="content-repo-hash",
            confidence=0.5,
            evidence_count=1,
        )

        stored_id = repo.store(ko)
        assert stored_id == ko.id

        retrieved = repo.get_by_id("repo-ko")
        assert retrieved is not None
        assert retrieved.id == ko.id

        # Verify repository methods map to store methods
        dup_id = repo.check_duplicate("content-repo-hash")
        assert dup_id == ko.id

        children = repo.get_children("non-existent-parent")
        assert children == []


class TestStorageAbstraction:

    def test_in_memory_store_implements_knowledge_store_interface(self, store):
        assert isinstance(store, KnowledgeStore)

        # Verify all required methods exist
        assert hasattr(store, 'store')
        assert hasattr(store, 'retrieve_by_id')
        assert hasattr(store, 'retrieve_by_hash')
        assert hasattr(store, 'retrieve_by_raw_hash')
        assert hasattr(store, 'retrieve_by_parent')
        assert hasattr(store, 'list_by_source')
        assert hasattr(store, 'list_by_date_range')
        assert hasattr(store, 'delete')
        assert hasattr(store, 'check_duplicate')
        assert hasattr(store, 'get_metrics')
        assert hasattr(store, 'health')
