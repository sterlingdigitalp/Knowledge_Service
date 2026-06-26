"""End-to-end pipeline test — AcquisitionBundle -> Knowledge Objects"""

import pytest
import os
import sys
_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

from src.knowledge_service.acquisition.acquisition_bundle import (
    AcquisitionBundle, DocumentRecord, ExecutionRecord,
)
from src.knowledge_service.processing.pipeline import Pipeline


class TestPipelineEndToEnd:

    SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Test Document</title>
  <meta name="description" content="A test document for pipeline">
</head>
<body>
  <nav>Navigation links here</nav>
  <article>
    <h1>Test Document Title</h1>
    <p>This is the first paragraph of a test document. It contains
    some text that should be cleaned and normalized.</p>
    <p>By John Smith and Jane Doe. Published on 2026-06-25.</p>
    <h2>Section One</h2>
    <p>This section discusses important concepts. You can see
    more details at https://example.com/reference.</p>
    <pre><code class="language-python">
def hello():
    print("Hello, World!")
    </code></pre>
    <h3>Subsection</h3>
    <p>More detailed content here.</p>
    <table>
      <tr><th>Name</th><th>Value</th></tr>
      <tr><td>Item</td><td>42</td></tr>
    </table>
    <h2>Section Two</h2>
    <p>Final section of the document.</p>
  </article>
  <footer>Footer content</footer>
</body>
</html>"""

    @pytest.fixture
    def bundle(self):
        b = AcquisitionBundle(
            request_id="test-req-001",
            plan_id="test-plan-001",
            acquisition_timestamp="2026-06-25T12:00:00Z",
        )
        b.add_execution_record(ExecutionRecord(
            step_id="step-1",
            provider_name="crawl4ai-primary",
            provider_type="crawl",
            target="https://example.com",
            status="success",
            latency_ms=1200,
        ))
        b.add_document(DocumentRecord(
            document_id="doc-001",
            url="https://example.com",
            provider_name="crawl4ai-primary",
            content_type="text/html",
            raw_content=self.SAMPLE_HTML,
            content_size_bytes=len(self.SAMPLE_HTML.encode("utf-8")),
            acquired_at="2026-06-25T12:00:00Z",
        ))
        return b

    def test_pipeline_produces_knowledge_objects(self, bundle):
        pipeline = Pipeline({
            "clean": {"strip_scripts": True, "strip_navigation": True},
            "normalize": {"detect_language": True, "normalize_headings": True},
            "extract": {"extract_citations": True, "extract_tables": True, "extract_authors": True},
            "markdown": {"preserve_code_formatting": True},
            "chunk": {"strategy": "semantic", "min_chunk_size_tokens": 10},
            "enrich": {"compute_confidence": True, "classify_topics": True},
        })
        kobjects = pipeline.process(bundle)
        assert len(kobjects) > 0

        doc_kos = [ko for ko in kobjects if ko.type.value == "document"]
        chunk_kos = [ko for ko in kobjects if ko.type.value == "chunk"]
        assert len(doc_kos) == 1
        assert len(chunk_kos) >= 1

        doc = doc_kos[0]
        assert doc.markdown is not None
        assert len(doc.markdown) > 0
        assert doc.raw_content_hash is not None
        assert doc.content_hash is not None
        assert 0.0 <= doc.confidence <= 1.0
        assert doc.confidence > 0.0
        assert doc.evidence_count > 0
        assert doc.acquisition_chain is not None

    def test_pipeline_metadata_extraction(self, bundle):
        pipeline = Pipeline({
            "extract": {"extract_citations": True, "extract_tables": True, "extract_authors": True},
            "enrich": {"compute_confidence": False, "classify_topics": False},
        })
        kobjects = pipeline.process(bundle)
        doc = kobjects[0]
        assert doc.title is not None
        assert doc.markdown is not None

    def test_pipeline_hashing_determinism(self):
        pipeline = Pipeline()
        b1 = AcquisitionBundle(
            request_id="r1", plan_id="p1", acquisition_timestamp="2026-06-25T12:00:00Z"
        )
        b1.add_document(DocumentRecord(
            document_id="d1", url="https://example.com",
            provider_name="crawl4ai", content_type="text/html",
            raw_content=self.SAMPLE_HTML,
            content_size_bytes=len(self.SAMPLE_HTML.encode()),
            acquired_at="2026-06-25T12:00:00Z",
        ))
        b2 = AcquisitionBundle(
            request_id="r2", plan_id="p2", acquisition_timestamp="2026-06-25T12:00:00Z"
        )
        b2.add_document(DocumentRecord(
            document_id="d2", url="https://example.com",
            provider_name="crawl4ai", content_type="text/html",
            raw_content=self.SAMPLE_HTML,
            content_size_bytes=len(self.SAMPLE_HTML.encode()),
            acquired_at="2026-06-25T12:00:00Z",
        ))

        k1 = pipeline.process(b1)
        k2 = pipeline.process(b2)
        assert k1[0].content_hash == k2[0].content_hash

    def test_pipeline_provider_info_does_not_leak(self, bundle):
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        for ko in kobjects:
            assert ko is not None
            assert ko.type.value in ("document", "chunk")
        doc_json = kobjects[0].to_dict()
        assert "provider" not in doc_json or doc_json.get("provider") is None
        assert "crawl4ai" not in str(doc_json.get("markdown", ""))

    def test_pipeline_confidence_has_all_factors(self, bundle):
        pipeline = Pipeline({
            "enrich": {
                "compute_confidence": True,
                "weight_source_trust": 0.35,
                "weight_content_completeness": 0.25,
                "weight_processing_quality": 0.25,
                "weight_evidence_strength": 0.15,
            }
        })
        kobjects = pipeline.process(bundle)
        doc = kobjects[0]
        assert 0.0 <= doc.confidence <= 1.0
