"""Performance Tests — Baseline timing measurements

Measures average processing time per stage and total pipeline throughput.
Outputs results in milliseconds for documentation baseline.
"""

import os, sys, time, statistics
_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

import pytest
from src.knowledge_service.acquisition.acquisition_bundle import (
    AcquisitionBundle, DocumentRecord, ExecutionRecord,
)
from src.knowledge_service.processing.clean import CleanStage
from src.knowledge_service.processing.normalize import NormalizeStage
from src.knowledge_service.processing.extract import ExtractStage
from src.knowledge_service.processing.markdown import MarkdownStage
from src.knowledge_service.processing.chunk import ChunkStage
from src.knowledge_service.processing.enrich import EnrichStage
from src.knowledge_service.processing.validate import ValidateStage
from src.knowledge_service.processing.pipeline import Pipeline
from src.knowledge_service.processing.context import ProcessingContext
from src.knowledge_service.knowledge_object import (
    KnowledgeObject, KnowledgeType, AcquisitionRecord,
    ProviderType, AcquisitionStatus,
)


SAMPLE_HTML = """<!DOCTYPE html>
<html><head><title>Test Performance</title></head>
<body>
  <h1>Performance Test Document</h1>
  <p>This is a test document used to measure pipeline performance.</p>
  <h2>Section 1</h2>
  <p>Content for section one with some additional text to make it longer.</p>
  <h3>Subsection 1.1</h3>
  <p>More detailed content that goes into specifics about the topic.</p>
  <pre><code>def hello():\\n    print("world")\\n</code></pre>
  <h2>Section 2</h2>
  <p>Second section with different content patterns.</p>
  <table><tr><td>A</td><td>B</td></tr><tr><td>1</td><td>2</td></tr></table>
</body></html>"""

SAMPLE_MD = """# Performance Test Document

This is a test document used to measure pipeline performance.

## Section 1

Content for section one with some additional text to make it longer.

### Subsection 1.1

More detailed content that goes into specifics about the topic.

```python
def hello():
    print("world")
```

## Section 2

Second section with different content patterns."""


def make_bundle(content=SAMPLE_HTML):
    bundle = AcquisitionBundle(
        request_id="perf-test",
        plan_id="perf-plan",
        acquisition_timestamp="2026-06-25T12:00:00Z",
    )
    bundle.add_execution_record(ExecutionRecord(
        step_id="step-0", provider_name="crawl4ai-primary",
        provider_type="crawl", target="https://example.com",
        status="success", latency_ms=100,
    ))
    bundle.add_document(DocumentRecord(
        document_id="doc-1", url="https://example.com",
        provider_name="crawl4ai-primary", content_type="text/html",
        raw_content=content,
        content_size_bytes=len(content.encode("utf-8")),
        acquired_at="2026-06-25T12:00:00Z",
    ))
    return bundle


def make_valid_ko():
    raw = "raw content"
    raw_hash = KnowledgeObject.compute_raw_content_hash(raw.encode("utf-8"))
    md = "# Test"
    content_hash = KnowledgeObject.compute_content_hash(md)
    return KnowledgeObject(
        id="perf-ko",
        type=KnowledgeType.DOCUMENT,
        source_id="perf-source",
        source_url="https://example.com",
        acquired_at="2026-06-25T12:00:00Z",
        updated_at="2026-06-25T12:00:00Z",
        markdown=md,
        raw_content_hash=raw_hash,
        content_hash=content_hash,
        confidence=0.5,
        evidence_count=1,
        acquisition_chain=[
            AcquisitionRecord(
                provider_name="crawl4ai", provider_type=ProviderType.CRAWLER,
                request_id="perf-req", timestamp="2026-06-25T12:00:00Z",
                status=AcquisitionStatus.SUCCESS,
            )
        ],
    )


class TestPerStageTiming:

    SAMPLES = 100

    def test_clean_stage_timing(self):
        ctx = ProcessingContext()
        ctx.raw_content = SAMPLE_HTML
        stage = CleanStage()
        times = []
        for _ in range(self.SAMPLES):
            ctx2 = ProcessingContext()
            ctx2.raw_content = SAMPLE_HTML
            t0 = time.perf_counter()
            stage.execute(ctx2, {})
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)
        avg = statistics.mean(times)
        assert avg < 5.0, f"Clean stage too slow: {avg:.3f}ms"
        print(f"\n  Clean stage: {avg:.3f}ms avg ({min(times):.3f}ms min, {max(times):.3f}ms max)")

    def test_normalize_stage_timing(self):
        ctx = ProcessingContext()
        ctx.cleaned_content = "Cleaned content for testing purposes.\n\nWith multiple paragraphs."
        stage = NormalizeStage()
        times = []
        for _ in range(self.SAMPLES):
            ctx2 = ProcessingContext()
            ctx2.cleaned_content = "Cleaned content for testing purposes.\n\nWith multiple paragraphs."
            t0 = time.perf_counter()
            stage.execute(ctx2, {})
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)
        avg = statistics.mean(times)
        assert avg < 5.0
        print(f"  Normalize stage: {avg:.3f}ms avg ({min(times):.3f}ms min, {max(times):.3f}ms max)")

    def test_extract_stage_timing(self):
        stage = ExtractStage()
        times = []
        for _ in range(self.SAMPLES):
            ctx2 = ProcessingContext()
            ctx2.normalized_content = SAMPLE_MD
            ctx2.normalized_metadata = {}
            t0 = time.perf_counter()
            stage.execute(ctx2, {})
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)
        avg = statistics.mean(times)
        assert avg < 5.0
        print(f"  Extract stage: {avg:.3f}ms avg ({min(times):.3f}ms min, {max(times):.3f}ms max)")

    def test_markdown_stage_timing(self):
        stage = MarkdownStage()
        times = []
        for _ in range(self.SAMPLES):
            ctx2 = ProcessingContext()
            ctx2.raw_content = "raw"
            ctx2.cleaned_content = SAMPLE_HTML
            ctx2.normalized_content = SAMPLE_HTML
            t0 = time.perf_counter()
            stage.execute(ctx2, {})
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)
        avg = statistics.mean(times)
        assert avg < 5.0
        print(f"  Markdown stage: {avg:.3f}ms avg ({min(times):.3f}ms min, {max(times):.3f}ms max)")

    def test_chunk_stage_timing(self):
        stage = ChunkStage()
        times = []
        for _ in range(self.SAMPLES):
            ctx2 = ProcessingContext()
            ctx2.markdown = SAMPLE_MD
            ctx2.word_count = len(SAMPLE_MD.split())
            ctx2.knowledge_objects = [KnowledgeObject(id="parent-1")]
            t0 = time.perf_counter()
            stage.execute(ctx2, {"strategy": "semantic"})
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)
        avg = statistics.mean(times)
        assert avg < 5.0
        print(f"  Chunk stage: {avg:.3f}ms avg ({min(times):.3f}ms min, {max(times):.3f}ms max)")

    def test_enrich_stage_timing(self):
        stage = EnrichStage()
        times = []
        for _ in range(self.SAMPLES):
            ctx2 = ProcessingContext()
            ctx2.markdown = SAMPLE_MD
            ctx2.word_count = len(SAMPLE_MD.split())
            ctx2.title = "Test"
            ctx2.language = "en"
            ctx2.raw_content_hash = "abc123"
            ctx2.stage_results = {
                "clean": type("sr", (), {"stage_name": "clean", "success": True, "confidence_impact": 0.0})(),
                "normalize": type("sr", (), {"stage_name": "normalize", "success": True, "confidence_impact": 0.0})(),
                "extract": type("sr", (), {"stage_name": "extract", "success": True, "confidence_impact": 0.0})(),
                "markdown": type("sr", (), {"stage_name": "markdown", "success": True, "confidence_impact": 0.0})(),
                "chunk": type("sr", (), {"stage_name": "chunk", "success": True, "confidence_impact": 0.0})(),
            }
            ctx2.bundle = make_bundle()
            t0 = time.perf_counter()
            stage.execute(ctx2, {})
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)
        avg = statistics.mean(times)
        assert avg < 5.0
        print(f"  Enrich stage: {avg:.3f}ms avg ({min(times):.3f}ms min, {max(times):.3f}ms max)")

    def test_validate_stage_timing(self):
        stage = ValidateStage()
        kos = [make_valid_ko()]
        times = []
        for _ in range(self.SAMPLES):
            ctx2 = ProcessingContext()
            ctx2.raw_content = "raw content"
            ctx2.raw_content_hash = KnowledgeObject.compute_raw_content_hash(b"raw content")
            ctx2.knowledge_objects = [make_valid_ko()]
            ctx2.bundle = make_bundle()
            t0 = time.perf_counter()
            stage.execute(ctx2, {})
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)
        avg = statistics.mean(times)
        assert avg < 5.0
        print(f"  Validate stage: {avg:.3f}ms avg ({min(times):.3f}ms min, {max(times):.3f}ms max)")


class TestPipelineTiming:

    SAMPLES = 50

    def test_total_pipeline_timing(self):
        bundle = make_bundle()
        pipeline = Pipeline()
        times = []
        for _ in range(self.SAMPLES):
            b2 = make_bundle()
            t0 = time.perf_counter()
            pipeline.process(b2)
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)
        avg = statistics.mean(times)
        assert avg < 50.0, f"Pipeline too slow: {avg:.3f}ms"
        print(f"\n  Total pipeline: {avg:.3f}ms avg ({min(times):.3f}ms min, {max(times):.3f}ms max)")
