"""End-to-End Integration Tests — Complete Knowledge Lifecycle

Demonstrates the full pipeline:
AcquisitionBundle → Processing Pipeline → Knowledge Objects → Storage → Retrieval → Verification
"""

import os, sys
_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

import pytest
from src.knowledge_service.acquisition.acquisition_bundle import (
    AcquisitionBundle, DocumentRecord, ExecutionRecord,
)
from src.knowledge_service.processing.pipeline import Pipeline
from src.knowledge_service.storage.postgres.in_memory_store import InMemoryKnowledgeStore
from src.knowledge_service.storage.repositories.knowledge_repository import KnowledgeRepository
from src.knowledge_service.knowledge_object import (
    KnowledgeObject, KnowledgeType, AcquisitionRecord, ProviderType, AcquisitionStatus, IndexStatus,
)


SAMPLE_HTML = """<!DOCTYPE html>
<html><head><title>E2E Test Doc</title></head>
<body>
  <h1>End-to-End Test Document</h1>
  <p>This is a test document for the complete lifecycle validation.</p>
</body></html>"""


def create_test_bundle():
    bundle = AcquisitionBundle(
        request_id="e2e-test-req",
        plan_id="e2e-test-plan",
        acquisition_timestamp="2026-06-25T12:00:00Z",
    )
    bundle.add_execution_record(ExecutionRecord(
        step_id="step-0", provider_name="crawl4ai-primary",
        provider_type="crawl", target="https://example.com/e2e",
        status="success", latency_ms=100,
    ))
    bundle.add_document(DocumentRecord(
        document_id="doc-e2e-1", url="https://example.com/e2e",
        provider_name="crawl4ai-primary", content_type="text/html",
        raw_content=SAMPLE_HTML,
        content_size_bytes=len(SAMPLE_HTML.encode("utf-8")),
        acquired_at="2026-06-25T12:00:00Z",
    ))
    return bundle


class TestEndToEndLifecycle:

    def test_complete_lifecycle_from_bundle_to_retrieval(self):
        # 1. Create AcquisitionBundle
        bundle = create_test_bundle()

        # 2. Process through Pipeline → KnowledgeObjects
        pipeline = Pipeline({
            "clean": {"strip_scripts": True, "strip_navigation": True},
            "normalize": {"detect_language": True, "normalize_headings": True},
            "extract": {"extract_citations": True, "extract_tables": True, "extract_authors": True},
            "markdown": {"preserve_code_formatting": True},
            "chunk": {"strategy": "semantic", "min_chunk_size_tokens": 10},
            "enrich": {"compute_confidence": True, "classify_topics": True},
        })
        kos = pipeline.process(bundle)

        assert len(kos) > 0
        doc_ko = [ko for ko in kos if ko.type.value == "document"][0]

        # 3. Store via KnowledgeRepository
        store = InMemoryKnowledgeStore()
        repo = KnowledgeRepository(store)

        stored_id = repo.store(doc_ko)
        assert stored_id == doc_ko.id

        # 4. Retrieve by ID
        retrieved_by_id = repo.get_by_id(doc_ko.id)
        assert retrieved_by_id is not None
        assert retrieved_by_id.content_hash == doc_ko.content_hash

        # 5. Verify identical fields
        assert retrieved_by_id.id == doc_ko.id
        assert retrieved_by_id.markdown == doc_ko.markdown
        assert retrieved_by_id.confidence == doc_ko.confidence
        assert retrieved_by_id.evidence_count == doc_ko.evidence_count
        assert len(retrieved_by_id.acquisition_chain) == len(doc_ko.acquisition_chain)

    def test_hash_integrity_preserved_through_storage(self):
        bundle = create_test_bundle()
        pipeline = Pipeline()
        kos = pipeline.process(bundle)
        doc_ko = [ko for ko in kos if ko.type.value == "document"][0]

        store = InMemoryKnowledgeStore()
        repo = KnowledgeRepository(store)
        repo.store(doc_ko)

        # Retrieve by content_hash
        retrieved_by_hash = repo.get_by_content_hash(doc_ko.content_hash)
        assert retrieved_by_hash is not None
        assert retrieved_by_hash.raw_content_hash == doc_ko.raw_content_hash
        assert retrieved_by_hash.content_hash == doc_ko.content_hash

    def test_confidence_preserved_through_storage(self):
        bundle = create_test_bundle()
        pipeline = Pipeline({"enrich": {"compute_confidence": True}})
        kos = pipeline.process(bundle)
        doc_ko = [ko for ko in kos if ko.type.value == "document"][0]

        store = InMemoryKnowledgeStore()
        repo = KnowledgeRepository(store)
        repo.store(doc_ko)

        retrieved = repo.get_by_id(doc_ko.id)
        assert retrieved is not None
        assert 0.0 <= retrieved.confidence <= 1.0


class TestDuplicateDetectionEndToEnd:

    def test_duplicate_document_prevented_in_lifecycle(self):
        # Create two identical bundles
        bundle1 = create_test_bundle()
        pipeline = Pipeline()
        kos1 = pipeline.process(bundle1)

        bundle2 = create_test_bundle()  # Same content
        kos2 = pipeline.process(bundle2)

        # Both should have same content_hash
        doc_ko1 = [ko for ko in kos1 if ko.type.value == "document"][0]
        doc_ko2 = [ko for ko in kos2 if ko.type.value == "document"][0]
        assert doc_ko1.content_hash == doc_ko2.content_hash

        # Store first
        store = InMemoryKnowledgeStore()
        repo = KnowledgeRepository(store)
        id1 = repo.store(doc_ko1)

        # Store second (duplicate)
        id2 = repo.store(doc_ko2)

        # Should return same ID
        assert id1 == id2
        assert store.get_metrics()["duplicates_prevented"] == 1
