"""Failure Injection End-to-End Tests

Verifies graceful handling of malformed input through the complete lifecycle.
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


def create_bundle_with_content(html):
    bundle = AcquisitionBundle(
        request_id="fail-test", plan_id="fail-plan", acquisition_timestamp="2026-06-25T12:00:00Z",
    )
    bundle.add_execution_record(ExecutionRecord(step_id="s0", provider_name="crawl4ai",
        provider_type="crawl", target="https://example.com", status="success", latency_ms=100))
    bundle.add_document(DocumentRecord(document_id="d-fail", url="https://example.com",
        provider_name="crawl4ai", content_type="text/html", raw_content=html,
        content_size_bytes=len(html.encode("utf-8")), acquired_at="2026-06-25T12:00:00Z"))
    return bundle


class TestFailureInjectionE2E:

    def test_malformed_html_processed_gracefully(self):
        html = "<html><body><h1>Title<p>Unclosed paragraph<div>Nested"
        bundle = create_bundle_with_content(html)
        pipeline = Pipeline()
        kos = pipeline.process(bundle)
        assert len(kos) > 0

    def test_empty_document_handled_gracefully(self):
        bundle = create_bundle_with_content("")
        pipeline = Pipeline()
        kos = pipeline.process(bundle)
        assert len(kos) == 1

    def test_large_document_handled_gracefully(self):
        html = "<html><body>" + "x" * 5_000_000 + "</body></html>"
        bundle = create_bundle_with_content(html)
        pipeline = Pipeline({"clean": {"max_content_length": 1024 * 1024}})
        kos = pipeline.process(bundle)
        assert len(kos) > 0
