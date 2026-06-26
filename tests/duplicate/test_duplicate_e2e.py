"""Duplicate Detection End-to-End Tests

Verifies that duplicate acquisition produces only one canonical Knowledge Object.
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


SAMPLE_HTML = """<!DOCTYPE html><html><body><h1>Duplicate Test</h1><p>Content.</p></body></html>"""


def create_bundle(html):
    bundle = AcquisitionBundle(
        request_id="dup-test", plan_id="dup-plan", acquisition_timestamp="2026-06-25T12:00:00Z",
    )
    bundle.add_execution_record(ExecutionRecord(step_id="s0", provider_name="crawl4ai",
        provider_type="crawl", target="https://example.com", status="success", latency_ms=100))
    bundle.add_document(DocumentRecord(document_id="d1", url="https://example.com",
        provider_name="crawl4ai", content_type="text/html", raw_content=html,
        content_size_bytes=len(html.encode("utf-8")), acquired_at="2026-06-25T12:00:00Z"))
    return bundle


class TestDuplicatePreventionE2E:

    def test_acquire_identical_document_twice_only_one_stored(self):
        bundle1 = create_bundle(SAMPLE_HTML)
        pipeline = Pipeline()
        kos1 = pipeline.process(bundle1)

        bundle2 = create_bundle(SAMPLE_HTML)
        kos2 = pipeline.process(bundle2)

        ko1 = [ko for ko in kos1 if ko.type.value == "document"][0]
        ko2 = [ko for ko in kos2 if ko.type.value == "document"][0]

        assert ko1.content_hash == ko2.content_hash

        store = InMemoryKnowledgeStore()
        repo = KnowledgeRepository(store)

        id1 = repo.store(ko1)
        id2 = repo.store(ko2)

        assert id1 == id2
        metrics = store.get_metrics()
        assert metrics["duplicates_prevented"] == 1
        assert metrics["objects_stored"] == 1
