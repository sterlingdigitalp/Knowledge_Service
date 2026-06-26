"""Failure Injection Tests — Deliberately feed bad input

Tests graceful degradation against:
- Malformed HTML
- Missing metadata
- Empty content
- Huge documents
- Invalid UTF-8
- Duplicate content
- Broken acquisition metadata
- Corrupted timestamps
- Missing URLs
- Partial provider failures
"""

import os, sys
_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

import pytest
from src.knowledge_service.acquisition.acquisition_bundle import (
    AcquisitionBundle, DocumentRecord, ExecutionRecord,
)
from src.knowledge_service.processing.pipeline import Pipeline
from src.knowledge_service.knowledge_object import KnowledgeObject


def make_bundle(doc_content, content_type="text/html", url="https://example.com",
                exec_status="success", doc_id="doc-001", provider="crawl4ai-primary"):
    bundle = AcquisitionBundle(
        request_id="failure-test",
        plan_id="failure-plan",
        acquisition_timestamp="2026-06-25T12:00:00Z",
    )
    bundle.add_execution_record(ExecutionRecord(
        step_id="step-0",
        provider_name=provider,
        provider_type="crawl",
        target=url,
        status=exec_status,
        latency_ms=100,
    ))
    bundle.add_document(DocumentRecord(
        document_id=doc_id,
        url=url,
        provider_name=provider,
        content_type=content_type,
        raw_content=doc_content,
        content_size_bytes=len(doc_content.encode("utf-8")),
        acquired_at="2026-06-25T12:00:00Z",
    ))
    return bundle


class TestFailureInjection:

    def test_malformed_html_unclosed_tags(self):
        content = "<html><body><h1>Title<p>Paragraph without closing tags<div>Another"
        bundle = make_bundle(content)
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert len(kobjects) > 0
        assert kobjects[0].type.value == "document"

    def test_malformed_html_nested_scripts(self):
        content = "<html><script>if (a < b) { document.write('<script>nested</script>') }</script><body>Content"
        bundle = make_bundle(content)
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert len(kobjects) > 0

    def test_empty_content(self):
        bundle = make_bundle("")
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert len(kobjects) == 1
        assert kobjects[0].markdown is None or kobjects[0].markdown == ""

    def test_content_with_only_whitespace(self):
        bundle = make_bundle("   \n\n   \t   \n\n  ")
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert len(kobjects) == 1

    def test_huge_document(self):
        content = "<html><body>" + "x" * 5_000_000 + "</body></html>"
        bundle = make_bundle(content)
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert len(kobjects) > 0

    def test_invalid_utf8_replacement_char(self):
        content = "Normal text with \ufffd replacement and \x00 null bytes"
        bundle = make_bundle(content)
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert len(kobjects) > 0

    def test_duplicate_content_same_bundle(self):
        content = "<html><body><h1>Title</h1><p>Body</p></body></html>"
        bundle = AcquisitionBundle(
            request_id="dup-test",
            plan_id="dup-plan",
            acquisition_timestamp="2026-06-25T12:00:00Z",
        )
        bundle.add_execution_record(ExecutionRecord(
            step_id="step-0", provider_name="crawl4ai-primary",
            provider_type="crawl", target="https://example.com",
            status="success", latency_ms=100,
        ))
        bundle.add_document(DocumentRecord(
            document_id="doc-1", url="https://example.com/1",
            provider_name="crawl4ai-primary", content_type="text/html",
            raw_content=content,
            content_size_bytes=len(content.encode("utf-8")),
            acquired_at="2026-06-25T12:00:00Z",
        ))
        bundle.add_document(DocumentRecord(
            document_id="doc-2", url="https://example.com/2",
            provider_name="crawl4ai-primary", content_type="text/html",
            raw_content=content,
            content_size_bytes=len(content.encode("utf-8")),
            acquired_at="2026-06-25T12:00:00Z",
        ))
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert len(kobjects) == 2
        assert kobjects[0].raw_content_hash == kobjects[1].raw_content_hash
        assert kobjects[0].content_hash == kobjects[1].content_hash

    def test_no_execution_records(self):
        content = "<html><body><p>Content without execution records</p></body></html>"
        bundle = AcquisitionBundle(
            request_id="no-exec",
            plan_id="no-exec-plan",
            acquisition_timestamp="2026-06-25T12:00:00Z",
        )
        bundle.add_document(DocumentRecord(
            document_id="doc-1", url="https://example.com",
            provider_name="crawl4ai-primary", content_type="text/html",
            raw_content=content,
            content_size_bytes=len(content.encode("utf-8")),
            acquired_at="2026-06-25T12:00:00Z",
        ))
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert len(kobjects) == 1

    def test_corrupted_timestamps(self):
        content = "<html><body><p>Content</p></body></html>"
        bundle = make_bundle(content)
        bundle.acquisition_timestamp = "not-a-timestamp"
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert len(kobjects) > 0

    def test_missing_url(self):
        content = "<html><body><p>Content</p></body></html>"
        bundle = make_bundle(content, url="")
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert len(kobjects) > 0

    def test_partial_provider_failure(self):
        bundle = AcquisitionBundle(
            request_id="partial-fail",
            plan_id="partial-plan",
            acquisition_timestamp="2026-06-25T12:00:00Z",
        )
        bundle.add_execution_record(ExecutionRecord(
            step_id="step-0", provider_name="searxng-main",
            provider_type="search", target="test query",
            status="failed", latency_ms=500,
            error_code="NETWORK_ERROR", error_message="Connection timeout",
        ))
        content = "<html><body><p>Got some content despite search failure</p></body></html>"
        bundle.add_document(DocumentRecord(
            document_id="doc-1", url="https://example.com",
            provider_name="crawl4ai-primary", content_type="text/html",
            raw_content=content,
            content_size_bytes=len(content.encode("utf-8")),
            acquired_at="2026-06-25T12:00:00Z",
        ))
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert len(kobjects) > 0

    def test_mixed_content_types(self):
        bundle = AcquisitionBundle(
            request_id="mixed-types",
            plan_id="mixed-plan",
            acquisition_timestamp="2026-06-25T12:00:00Z",
        )
        bundle.add_execution_record(ExecutionRecord(
            step_id="step-0", provider_name="crawl4ai-primary",
            provider_type="crawl", target="https://example.com",
            status="success", latency_ms=100,
        ))
        bundle.add_document(DocumentRecord(
            document_id="doc-1", url="https://example.com/html",
            provider_name="crawl4ai-primary", content_type="text/html",
            raw_content="<html><body><h1>HTML Doc</h1><p>Content</p></body></html>",
            content_size_bytes=100, acquired_at="2026-06-25T12:00:00Z",
        ))
        bundle.add_document(DocumentRecord(
            document_id="doc-2", url="https://example.com/json",
            provider_name="api-provider", content_type="application/json",
            raw_content='{"key": "value", "nested": {"a": 1}}',
            content_size_bytes=50, acquired_at="2026-06-25T12:00:00Z",
        ))
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert len(kobjects) == 2

    def test_extremely_nested_html(self):
        nested = "<div>" * 1000 + "deep content" + "</div>" * 1000
        content = f"<html><body>{nested}</body></html>"
        bundle = make_bundle(content)
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert len(kobjects) > 0

    def test_content_with_only_special_chars(self):
        content = "<html><body>!@#$%^&*()_+{}|:\"<>?`~</body></html>"
        bundle = make_bundle(content)
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert len(kobjects) > 0

    def test_zero_length_content(self):
        bundle = make_bundle("", doc_id="zero-len")
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert len(kobjects) == 1

    def test_negative_content_size(self):
        bundle = make_bundle("Some content")
        bundle.acquired_documents[0].content_size_bytes = -1
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert len(kobjects) > 0
