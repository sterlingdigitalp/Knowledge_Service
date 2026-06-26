"""End-to-End Lifecycle Integration Tests — Phase 1.6C

Verifies one continuous lifecycle:
Question -> Planning -> Search Provider -> Crawl Provider -> Real AcquisitionBundle
-> Processing Pipeline -> Knowledge Objects -> Storage -> Retrieval -> Verification

No simulated AcquisitionBundle. No handcrafted HTML. No mock provider output.
The AcquisitionBundle entering Processing must be produced by the real AcquisitionExecutor.
"""

import hashlib
import os
import sys
from datetime import datetime, timezone

# Add src to path
_SRC_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

import pytest

from src.knowledge_service.acquisition.acquisition_bundle import (
    AcquisitionBundle,
    DocumentRecord,
    ExecutionRecord,
)
from src.knowledge_service.interfaces.provider import ProviderType
from src.knowledge_service.knowledge_object import KnowledgeObject
from src.knowledge_service.planning.executor import AcquisitionExecutor
from src.knowledge_service.planning.interfaces import AcquisitionPlan
from src.knowledge_service.planning.planner import RuleBasedPlanner
from src.knowledge_service.processing.pipeline import Pipeline
from src.knowledge_service.providers.crawl4ai_provider import Crawl4AIProvider
from src.knowledge_service.providers.searxng_search_provider import (
    SearXNGSearchProvider,
)
from src.knowledge_service.registry.provider_registry import ProviderRegistry
from src.knowledge_service.retrieval.retriever import (
    KnowledgeRetrieverImpl,
    RetrievalResult,
)
from src.knowledge_service.storage.postgres.in_memory_store import (
    InMemoryKnowledgeStore,
    InMemorySourceStore,
)
from src.knowledge_service.storage.repositories.knowledge_repository import (
    KnowledgeRepository,
)
from src.knowledge_service.storage.repositories.source_repository import (
    SourceRepository,
)

CRAWL4AI_AUTH_TOKEN = "SterlingKnowledge2026"


def get_timestamp() -> str:
    """Get current timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_storage_components():
    """Create in-memory storage and repository components"""
    store = InMemoryKnowledgeStore()
    source_store = InMemorySourceStore()

    knowledge_repo = KnowledgeRepository(store)
    source_repo = SourceRepository(source_store)

    return store, knowledge_repo, source_repo


class TestEndToEndLifecycle:
    """Test the complete end-to-end lifecycle from Question to Retrieval"""

    @pytest.fixture(scope="class")
    def registry(self):
        """Create and initialize the provider registry"""
        registry = ProviderRegistry()

        # Initialize SearXNG Search Provider
        searxng_provider = SearXNGSearchProvider("searxng-main")
        try:
            searxng_provider.initialize(
                {
                    "endpoint": "http://localhost:8080",
                    "timeout_ms": 15000,
                }
            )
        except Exception as exc:
            pytest.skip(f"SearXNG service not available: {exc}")
        registry.register(searxng_provider)

        # Initialize Crawl4AI Provider
        crawl4ai_provider = Crawl4AIProvider("crawl4ai-primary")
        try:
            crawl4ai_provider.initialize(
                {
                    "endpoint": "http://localhost:11235",
                    "auth_token": CRAWL4AI_AUTH_TOKEN,
                    "timeout_ms": 60000,
                }
            )
        except Exception as exc:
            pytest.skip(f"Crawl4AI service not available: {exc}")
        registry.register(crawl4ai_provider)

        return registry

    def test_full_lifecycle_quest_to_verification(self, registry):
        """Execute complete lifecycle: Question -> Planning -> Providers -> Bundle -> Pipeline -> Storage -> Retrieval -> Verification"""
        store, knowledge_repo, source_repo = create_storage_components()

        # Stage 1: Question & Planning
        question = "What is Crawl4AI?"
        request_id = f"req-{get_timestamp()}"

        planner = RuleBasedPlanner(registry)
        plan: AcquisitionPlan = planner.plan(question, request_id)

        assert plan is not None
        assert plan.request_id == request_id
        assert plan.query == question
        assert len(plan.steps) >= 2

        # Verify search step exists
        search_step = None
        crawl_step = None
        for step in plan.steps:
            if step.provider_type == ProviderType.SEARCH:
                search_step = step
            elif step.provider_type == ProviderType.CRAWL:
                crawl_step = step

        assert search_step is not None, "Search step should exist in plan"
        assert crawl_step is not None, "Crawl step should exist in plan"

        # Stage 2: Execute Providers via AcquisitionExecutor (REAL AcquisitionBundle)
        executor = AcquisitionExecutor(registry, source_repo)
        bundle: AcquisitionBundle = executor.execute(plan)

        # Verify real AcquisitionBundle was produced (not simulated)
        assert bundle is not None
        assert bundle.request_id == request_id
        assert bundle.plan_id == plan.plan_id
        assert len(bundle.provider_executions) > 0

        # Verify search and crawl executions exist
        search_exec = None
        crawl_execs = []
        for exec_rec in bundle.provider_executions:
            if exec_rec.provider_type == "search":
                search_exec = exec_rec
            elif exec_rec.provider_type == "crawl":
                crawl_execs.append(exec_rec)

        assert search_exec is not None, "Search execution should exist"
        assert len(crawl_execs) > 0, "At least one crawl execution should exist"

        # Verify documents were acquired
        assert len(bundle.acquired_documents) > 0, (
            "At least one document should be acquired"
        )

        # Verify discovered URLs were captured
        assert len(bundle.discovered_urls) > 0, "Discovered URLs should be present"

        # Stage 3: Processing Pipeline
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)

        # Verify Knowledge Objects were created
        assert len(kobjects) > 0, "Knowledge objects should be created from bundle"

        # Verify document KnowledgeObject exists
        doc_kos = [ko for ko in kobjects if ko.type.value == "document"]
        assert len(doc_kos) > 0, "Document KnowledgeObject should exist"

        # Verify chunk KnowledgeObjects exist
        chunk_kos = [ko for ko in kobjects if ko.type.value == "chunk"]
        assert len(chunk_kos) > 0, "Chunk KnowledgeObjects should exist"

        # Verify byte-for-byte provider output -> processing input (no transformation outside Processing Layer)
        first_doc = bundle.acquired_documents[0]
        first_ko = doc_kos[0]

        # The markdown in the KnowledgeObject should match or be derived from the raw_content
        assert first_ko.raw_content_hash == KnowledgeObject.compute_raw_content_hash(
            first_doc.raw_content.encode("utf-8")
        )

        # Stage 4: Storage
        stored_ids = []
        actually_stored = []  # Track objects that were actually stored (not deduplicated)
        for ko in kobjects:
            stored_id = knowledge_repo.store(ko)
            # store() may return an older object's ID if content_hash matches
            # an existing object (canonical deduplication by design).
            # Verify the stored_id is valid.
            assert stored_id is not None
            retrieved = knowledge_repo.get_by_id(stored_id)
            assert retrieved is not None, f"Object {stored_id} should be retrievable"
            assert retrieved.content_hash == ko.content_hash
            stored_ids.append(stored_id)
            # Track objects that were actually stored (ID matches)
            if stored_id == ko.id:
                actually_stored.append(ko)

        # Verify duplicates would be detected
        if actually_stored:
            verify_ko = actually_stored[0]  # Use an object that was actually stored
        else:
            verify_ko = first_ko  # Fallback if all were deduplicated (shouldn't happen)

        duplicate_check = knowledge_repo.check_duplicate(verify_ko.content_hash)
        assert duplicate_check == verify_ko.id, (
            "Duplicate check should return the object ID"
        )

        # Stage 5: Retrieval - use an actually stored object to avoid deduplication issues
        retriever = KnowledgeRetrieverImpl(knowledge_repo)

        # Retrieve by ID (use verify_ko which was actually stored)
        result_by_id: RetrievalResult = retriever.retrieve_by_id(verify_ko.id)
        assert result_by_id is not None, f"Object {verify_ko.id} should be retrievable"
        assert len(result_by_id.objects) == 1
        retrieved_ko = result_by_id.objects[0]
        assert retrieved_ko.id == verify_ko.id
        assert retrieved_ko.content_hash == verify_ko.content_hash

        # Retrieve by content hash
        result_by_hash: RetrievalResult = retriever.retrieve_by_content_hash(
            verify_ko.content_hash
        )
        assert result_by_hash is not None
        assert len(result_by_hash.objects) == 1
        assert result_by_hash.objects[0].id == verify_ko.id

        # Stage 6: Verification - Hashes verified, Confidence verified, Acquisition history verified
        assert retrieved_ko.content_hash == verify_ko.content_hash, (
            "Content hash should be preserved"
        )
        assert retrieved_ko.raw_content_hash == verify_ko.raw_content_hash, (
            "Raw content hash should be preserved"
        )

        # Confidence verified
        assert retrieved_ko.confidence > 0, "Confidence should be greater than 0"

        # Acquisition history verified
        assert len(retrieved_ko.acquisition_chain) > 0, "Acquisition chain should exist"
        acquisition_providers = [
            rec.provider_name for rec in retrieved_ko.acquisition_chain
        ]
        assert "searxng-main" in acquisition_providers or any(
            "searxng" in p for p in acquisition_providers
        )
        assert "crawl4ai-primary" in acquisition_providers or any(
            "crawl4ai" in p for p in acquisition_providers
        )

    def test_determinism_identical_hashes_and_objects(self, registry):
        """Verify determinism: same input → same output (within a single run).

        Since SearXNG returns different URLs each time, we verify:
        1. Duplicate detection works correctly (same content → same hash)
        2. Processing pipeline is deterministic for the same bundle
        3. Storage and retrieval are consistent
        """
        store, knowledge_repo, source_repo = create_storage_components()

        question = "What is Crawl4AI?"
        request_id = f"req-determinism-{get_timestamp()}"

        planner = RuleBasedPlanner(registry)
        plan: AcquisitionPlan = planner.plan(question, request_id)

        executor = AcquisitionExecutor(registry, source_repo)
        bundle: AcquisitionBundle = executor.execute(plan)

        # Verify we have documents to work with
        assert len(bundle.acquired_documents) > 0, "Should have acquired documents"

        # Process through pipeline twice and verify identical results
        pipeline1 = Pipeline()
        kobjects1 = pipeline1.process(bundle)

        pipeline2 = Pipeline()
        kobjects2 = pipeline2.process(bundle)

        assert len(kobjects1) == len(kobjects2), "Same number of KOs from same bundle"

        # Verify each corresponding KO has identical hashes
        for i, (ko1, ko2) in enumerate(zip(kobjects1, kobjects2)):
            assert ko1.content_hash == ko2.content_hash, (
                f"KO[{i}] content_hash should be deterministic: {ko1.content_hash[:16]}... vs {ko2.content_hash[:16]}..."
            )
            assert ko1.raw_content_hash == ko2.raw_content_hash, (
                f"KO[{i}] raw_content_hash should be deterministic"
            )
            assert ko1.type == ko2.type
            assert ko1.confidence == ko2.confidence

        # Store all KOs and verify duplicate detection works
        stored_ids = []
        for ko in kobjects1:
            stored_id = knowledge_repo.store(ko)
            stored_ids.append(stored_id)

        metrics = store.get_metrics()
        assert metrics["objects_stored"] > 0, "Should have stored objects"

        # Verify retrieval is consistent
        retriever = KnowledgeRetrieverImpl(knowledge_repo)

        # Find a document KO that was actually stored
        doc_kos1 = [ko for ko in kobjects1 if ko.type.value == "document"]
        assert len(doc_kos1) > 0, "Should have document KOs"

        first_doc = doc_kos1[0]
        result_by_id = retriever.retrieve_by_id(first_doc.id)
        assert result_by_id is not None
        assert len(result_by_id.objects) == 1
        retrieved = result_by_id.objects[0]
        assert retrieved.content_hash == first_doc.content_hash


class TestFailureInjection:
    """Test failure injection scenarios"""

    def test_provider_failure_graceful_stop(self):
        """Test that provider failure is handled gracefully"""
        _, knowledge_repo, _ = create_storage_components()

        # Create a bundle with failed provider execution
        bundle = AcquisitionBundle(
            request_id="fail-test",
            plan_id="fail-plan",
            acquisition_timestamp=get_timestamp(),
        )
        bundle.add_execution_record(
            ExecutionRecord(
                step_id="step-0",
                provider_name="searxng-main",
                provider_type="search",
                target="test query",
                status="failed",
                latency_ms=500,
                error_code="NETWORK_ERROR",
                error_message="Connection timeout",
            )
        )

        content = "<html><body><p>Content despite search failure</p></body></html>"
        bundle.add_document(
            DocumentRecord(
                document_id="doc-1",
                url="https://example.com",
                provider_name="crawl4ai-primary",
                content_type="text/html",
                raw_content=content,
                content_size_bytes=len(content.encode("utf-8")),
                acquired_at=get_timestamp(),
            )
        )

        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)

        # Should still process successfully despite search failure
        assert len(kobjects) > 0

    def test_malformed_html_graceful_processing(self):
        """Test that malformed HTML is processed gracefully"""
        _, knowledge_repo, _ = create_storage_components()

        content = "<html><body><h1>Title<p>Paragraph without closing tags<div>Another"
        bundle = AcquisitionBundle(
            request_id="malformed-test",
            plan_id="malformed-plan",
            acquisition_timestamp=get_timestamp(),
        )
        bundle.add_execution_record(
            ExecutionRecord(
                step_id="step-0",
                provider_name="crawl4ai-primary",
                provider_type="crawl",
                target="https://example.com",
                status="success",
                latency_ms=100,
            )
        )
        bundle.add_document(
            DocumentRecord(
                document_id="doc-1",
                url="https://example.com",
                provider_name="crawl4ai-primary",
                content_type="text/html",
                raw_content=content,
                content_size_bytes=len(content.encode("utf-8")),
                acquired_at=get_timestamp(),
            )
        )

        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)

        # Should process successfully despite malformed HTML
        assert len(kobjects) > 0

    def test_duplicate_acquisition_detection(self):
        """Test that duplicate acquisitions are detected"""
        _, knowledge_repo, _ = create_storage_components()

        content = (
            "<html><body><h1>Duplicate Title</h1><p>Body Content</p></body></html>"
        )

        # Create bundle with duplicate content
        bundle = AcquisitionBundle(
            request_id="dup-test",
            plan_id="dup-plan",
            acquisition_timestamp=get_timestamp(),
        )
        bundle.add_execution_record(
            ExecutionRecord(
                step_id="step-0",
                provider_name="crawl4ai-primary",
                provider_type="crawl",
                target="https://example.com/1",
                status="success",
                latency_ms=100,
            )
        )
        bundle.add_document(
            DocumentRecord(
                document_id="doc-1",
                url="https://example.com/1",
                provider_name="crawl4ai-primary",
                content_type="text/html",
                raw_content=content,
                content_size_bytes=len(content.encode("utf-8")),
                acquired_at=get_timestamp(),
            )
        )

        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)

        # Store first document
        doc_kos = [ko for ko in kobjects if ko.type.value == "document"]
        assert len(doc_kos) > 0

        first_ko = doc_kos[0]
        stored_id1 = knowledge_repo.store(first_ko)

        # Create a second document with identical content (simulating duplicate acquisition)
        bundle2 = AcquisitionBundle(
            request_id="dup-test-2",
            plan_id="dup-plan-2",
            acquisition_timestamp=get_timestamp(),
        )
        bundle2.add_execution_record(
            ExecutionRecord(
                step_id="step-0",
                provider_name="crawl4ai-primary",
                provider_type="crawl",
                target="https://example.com/2",
                status="success",
                latency_ms=100,
            )
        )
        bundle2.add_document(
            DocumentRecord(
                document_id="doc-2",
                url="https://example.com/2",
                provider_name="crawl4ai-primary",
                content_type="text/html",
                raw_content=content,
                content_size_bytes=len(content.encode("utf-8")),
                acquired_at=get_timestamp(),
            )
        )

        kobjects2 = pipeline.process(bundle2)
        doc_kos2 = [ko for ko in kobjects2 if ko.type.value == "document"]
        assert len(doc_kos2) > 0

        second_ko = doc_kos2[0]

        # Verify duplicate detection
        assert first_ko.content_hash == second_ko.content_hash

        # Store should return existing ID for duplicate
        stored_id2 = knowledge_repo.store(second_ko)
        assert stored_id1 == stored_id2, "Duplicate should return the existing ID"
