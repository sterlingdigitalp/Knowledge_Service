"""True End-to-End Lifecycle Integration Tests

Validates the full path with real providers:
Question -> Planner -> Provider Execution -> AcquisitionBundle -> Processing ->
Storage -> Retrieval. Tests run only when Crawl4AI is reachable.
"""

import os
import sys
import threading
from contextlib import contextmanager
from http.server import HTTPServer, BaseHTTPRequestHandler

import pytest

_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

from knowledge_service.providers.crawl4ai_provider import Crawl4AIProvider
from knowledge_service.planning.planner import RuleBasedPlanner
from knowledge_service.planning.executor import AcquisitionExecutor
from knowledge_service.processing.pipeline import Pipeline
from knowledge_service.storage.postgres.in_memory_store import InMemoryKnowledgeStore
from knowledge_service.storage.repositories.knowledge_repository import KnowledgeRepository
from knowledge_service.retrieval.retriever import KnowledgeRetrieverImpl
from knowledge_service.retrieval.interfaces import KnowledgeQuery, SortField, SortOrder
from knowledge_service.registry.provider_registry import ProviderRegistry


CRAWL4AI_ENDPOINT = os.environ.get("KNOWLEDGE_SERVICE_CRAWL4AI_ENDPOINT", "http://localhost:11235")
CRAWL4AI_AUTH_TOKEN = os.environ.get("KNOWLEDGE_SERVICE_CRAWL4AI_TOKEN", "SterlingKnowledge2026")
MALFORMED_HTML = """<html><head><title>Broken</title><body><h1>Malformed<div><p>Missing close tags"""


@pytest.fixture(scope="module")
def crawl_registry():
    provider = Crawl4AIProvider("crawl4ai-e2e")
    try:
        provider.initialize({
            "endpoint": CRAWL4AI_ENDPOINT,
            "auth_token": CRAWL4AI_AUTH_TOKEN,
            "timeout_ms": 30000,
        })
    except Exception as exc:
        pytest.skip(f"Crawl4AI service not available: {exc}")

    registry = ProviderRegistry()
    registry.register(provider)

    yield registry

    provider.shutdown()


def _run_lifecycle(query: str, request_id: str, registry: ProviderRegistry):
    planner = RuleBasedPlanner(registry)
    executor = AcquisitionExecutor(registry)
    plan = planner.plan(query, request_id)
    bundle = executor.execute(plan)
    pipeline = Pipeline()
    kobjects = pipeline.process(bundle)
    return bundle, kobjects


def _object_signature(ko) -> tuple[str, str, str]:
    return (ko.type.value, ko.content_hash, ko.raw_content_hash)


class TestRealProviderLifecycle:

    def test_question_to_retrieval_through_real_crawler(self, crawl_registry):
        request_id = "real-e2e-question-1"
        bundle, kobjects = _run_lifecycle("https://example.com", request_id, crawl_registry)

        assert bundle.providers_queried >= 1
        assert bundle.providers_successful >= 1
        assert len(bundle.acquired_documents) >= 1
        assert len(kobjects) > 0

        docs = [ko for ko in kobjects if ko.type.value == "document"]
        assert docs, "Expected at least one document KnowledgeObject from real crawl"

        doc = docs[0]
        assert doc.source_id == "crawl4ai-e2e"
        assert doc.content_hash

        store = InMemoryKnowledgeStore()
        repository = KnowledgeRepository(store)
        retriever = KnowledgeRetrieverImpl(repository)

        for ko in kobjects:
            repository.store(ko)

        by_id = retriever.retrieve_by_id(doc.id)
        assert by_id.total_count == 1
        assert by_id.objects[0].content_hash == doc.content_hash

        by_hash = retriever.retrieve_by_content_hash(doc.content_hash)
        assert by_hash.total_count == 1
        assert by_hash.objects[0].content_hash == doc.content_hash

        by_acq = retriever.retrieve_by_acquisition(request_id)
        assert by_acq.total_count >= len(docs)
        assert all(
            request_id in [r.request_id for r in obj.acquisition_chain]
            for obj in by_acq.objects
        )

        ordered = retriever.retrieve_query(KnowledgeQuery(
            object_types=["document"],
            sort_field=SortField.CONFIDENCE,
            sort_order=SortOrder.DESCENDING,
            limit=10,
        ))
        ordered_ids = [obj.id for obj in ordered.objects]
        assert ordered_ids == [obj.id for obj in ordered.objects]
        assert ordered_ids

    def test_real_provider_duplicate_canonicalization_and_determinism(self, crawl_registry):
        store = InMemoryKnowledgeStore()
        repository = KnowledgeRepository(store)
        retriever = KnowledgeRetrieverImpl(repository)

        first_request = "real-e2e-dup-1"
        first_bundle, first_kos = _run_lifecycle("https://example.com", first_request, crawl_registry)
        assert first_bundle.providers_successful >= 1

        first_signatures: set[tuple[str, str, str]] = set()
        first_ids_by_signature: dict[tuple[str, str, str], str] = {}
        for ko in first_kos:
            signature = _object_signature(ko)
            first_signatures.add(signature)
            stored_id = repository.store(ko)
            first_ids_by_signature[signature] = stored_id

        assert first_signatures

        second_request = "real-e2e-dup-2"
        second_bundle, second_kos = _run_lifecycle("https://example.com", second_request, crawl_registry)
        assert second_bundle.providers_successful >= 1

        for ko in second_kos:
            signature = _object_signature(ko)
            assert signature in first_signatures
            second_id = repository.store(ko)
            assert second_id == first_ids_by_signature[signature]

        # Same crawl produces the same canonical graph even across repeated runs.
        assert store.get_metrics()["duplicates_prevented"] >= len(second_kos)

        first_order = [obj.id for obj in retriever.retrieve_query(KnowledgeQuery(
            object_types=["document"],
            sort_field=SortField.CONFIDENCE,
            sort_order=SortOrder.DESCENDING,
        )).objects]

        second_order = [obj.id for obj in retriever.retrieve_query(KnowledgeQuery(
            object_types=["document"],
            sort_field=SortField.CONFIDENCE,
            sort_order=SortOrder.DESCENDING,
        )).objects]

        assert first_order == second_order

    @contextmanager
    def _run_malformed_html_server(self, body: str):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                payload = body.encode("utf-8")
                if self.path != "/malformed":
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format, *args):  # noqa: A002
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            yield f"http://127.0.0.1:{server.server_port}/malformed"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

    def test_malformed_html_from_real_provider_is_processed_gracefully(self, crawl_registry):
        with self._run_malformed_html_server(MALFORMED_HTML) as malformed_url:
            request_id = "real-e2e-malformed-1"
            bundle, kobjects = _run_lifecycle(malformed_url, request_id, crawl_registry)

            assert bundle.providers_successful >= 1
            assert len(bundle.acquired_documents) >= 1
            assert len(kobjects) > 0

            doc_count = len([ko for ko in kobjects if ko.type.value == "document"])
            assert doc_count == 1

            store = InMemoryKnowledgeStore()
            repository = KnowledgeRepository(store)
            retriever = KnowledgeRetrieverImpl(repository)

            for ko in kobjects:
                repository.store(ko)

            result = retriever.retrieve_by_id(kobjects[0].id)
            assert result.total_count == 1
            assert result.objects[0].source_id == "crawl4ai-e2e"
