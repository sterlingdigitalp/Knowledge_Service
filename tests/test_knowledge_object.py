"""Tests for Knowledge Object data model"""

import pytest
import hashlib
from src.knowledge_service.knowledge_object import (
    KnowledgeObject, KnowledgeType, SourceType, CitationType,
    AcquisitionRecord, ProviderType, AcquisitionStatus,
    Citation, RelationshipType, IndexStatus,
)


class TestKnowledgeObjectCreation:

    def test_default_creation(self):
        ko = KnowledgeObject()
        assert ko.id is not None
        assert ko.version == 1
        assert ko.type == KnowledgeType.DOCUMENT
        assert 0.0 <= ko.confidence <= 1.0
        assert ko.storage_backend == "primary-store-01"
        assert ko.index_status == IndexStatus.PENDING

    def test_uuid_v7_generated(self):
        ko1 = KnowledgeObject()
        ko2 = KnowledgeObject()
        assert ko1.id != ko2.id
        assert len(ko1.id) == 36

    def test_type_enum(self):
        for t in KnowledgeType:
            ko = KnowledgeObject(type=t)
            assert ko.type == t

    def test_citation_creation(self):
        c = Citation(
            target_id="abc-123",
            target_url="https://example.com",
            context="supports claim about X",
            citation_type=CitationType.SUPPORTING_EVIDENCE,
        )
        assert c.target_id == "abc-123"
        assert c.citation_type == CitationType.SUPPORTING_EVIDENCE


class TestKnowledgeObjectHashes:

    def test_raw_content_hash_deterministic(self):
        content1 = b"Hello World"
        content2 = b"Hello World"
        hash1 = KnowledgeObject.compute_raw_content_hash(content1)
        hash2 = KnowledgeObject.compute_raw_content_hash(content2)
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_raw_content_hash_different(self):
        hash1 = KnowledgeObject.compute_raw_content_hash(b"Hello")
        hash2 = KnowledgeObject.compute_raw_content_hash(b"World")
        assert hash1 != hash2

    def test_content_hash_deterministic(self):
        md1 = "# Title\n\nSome content."
        md2 = "# Title\n\nSome content."
        h1 = KnowledgeObject.compute_content_hash(md1)
        h2 = KnowledgeObject.compute_content_hash(md2)
        assert h1 == h2

    def test_content_hash_unique_per_content(self):
        h1 = KnowledgeObject.compute_content_hash("Content A")
        h2 = KnowledgeObject.compute_content_hash("Content B")
        assert h1 != h2


class TestKnowledgeObjectSerialization:

    def test_to_dict_minimal(self):
        ko = KnowledgeObject(id="test-id-001")
        d = ko.to_dict()
        assert d["id"] == "test-id-001"
        assert d["version"] == 1
        assert d["type"] == "document"
        assert d["confidence"] == 0.0
        assert d["evidence_count"] == 0

    def test_to_dict_with_all_fields(self):
        ko = KnowledgeObject(
            id="test-full",
            version=1,
            type=KnowledgeType.DOCUMENT,
            source_id="test-source",
            source_url="https://example.com",
            source_type=SourceType.WEB_PAGE,
            acquired_at="2026-06-25T12:00:00Z",
            published_at="2026-06-24T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            markdown="# Hello\n\nWorld",
            raw_content_hash="abc123",
            content_hash="def456",
            title="Hello",
            authors=["Alice", "Bob"],
            language="en",
            topics=["programming"],
            word_count=50,
            confidence=0.85,
            evidence_count=3,
            citations=[Citation(target_url="https://ref.com", citation_type=CitationType.REFERENCE)],
            acquisition_chain=[
                AcquisitionRecord(
                    provider_name="crawl4ai",
                    provider_type=ProviderType.CRAWLER,
                    request_id="req-001",
                    timestamp="2026-06-25T12:00:00Z",
                    status=AcquisitionStatus.SUCCESS,
                    latency_ms=1200,
                )
            ],
            storage_backend="test-store",
            index_status=IndexStatus.INDEXED,
        )
        d = ko.to_dict()
        assert d["id"] == "test-full"
        assert d["title"] == "Hello"
        assert d["authors"] == ["Alice", "Bob"]
        assert d["language"] == "en"
        assert d["confidence"] == 0.85
        assert len(d["acquisition_chain"]) == 1
        assert d["acquisition_chain"][0]["provider_name"] == "crawl4ai"
        assert d["index_status"] == "indexed"

    def test_from_dict_roundtrip(self):
        original = KnowledgeObject(
            id="roundtrip-test",
            type=KnowledgeType.DOCUMENT,
            source_id="src-001",
            source_url="https://example.com",
            markdown="# Title\n\nBody",
            raw_content_hash="raw-hash",
            content_hash="content-hash",
            title="Test Document",
            language="en",
            confidence=0.75,
            evidence_count=2,
        )
        d = original.to_dict()
        restored = KnowledgeObject.from_dict(d)
        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.confidence == original.confidence
        assert restored.raw_content_hash == original.raw_content_hash
        assert restored.content_hash == original.content_hash

    def test_from_dict_preserves_unknown_fields(self):
        d = {
            "id": "test-001",
            "type": "document",
            "source_id": "source-1",
            "source_type": "web_page",
            "acquired_at": "2026-06-25T12:00:00Z",
            "updated_at": "2026-06-25T12:00:00Z",
            "raw_content_hash": "abc",
            "content_hash": "def",
            "confidence": 0.5,
            "evidence_count": 1,
            "storage_backend": "store",
            "index_status": "pending",
            "unknown_field": "should_be_preserved",
        }
        ko = KnowledgeObject.from_dict(d)
        assert ko.source_id == "source-1"
        assert ko.confidence == 0.5
