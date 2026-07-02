"""Phase 1.2 Demonstration — AcquisitionBundle -> Knowledge Objects

Shows the complete processing pipeline transforming raw HTML content
through all 7 stages into canonical Knowledge Objects.

Usage: PYTHONPATH=src python3 tests/demo.py
"""

import os, sys
_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

from src.knowledge_service.acquisition.acquisition_bundle import (
    AcquisitionBundle, DocumentRecord, ExecutionRecord,
)
from src.knowledge_service.processing.pipeline import Pipeline


SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Knowledge Service Architecture Overview</title>
  <meta name="description" content="Architecture of the Knowledge Service platform">
</head>
<body>
  <nav>Navigation: Home | Docs | About</nav>
  <article>
    <h1>Knowledge Service Architecture</h1>
    <p>This document describes the six-layer architecture of the Knowledge Service platform.
    Written by Alice Chen. Published on 2026-06-20.</p>

    <h2>Layer Overview</h2>
    <p>The platform consists of six layers: API, Planning, Acquisition, Processing, Knowledge, and Provider.
    Each layer has a single responsibility and communicates through defined interfaces.</p>

    <h3>API Layer</h3>
    <p>Handles authentication, rate limiting, request validation, and response formatting.
    See https://docs.example.com/api for reference.</p>

    <h3>Processing Layer</h3>
    <p>Transforms raw acquisition into canonical Knowledge Objects through a seven-stage pipeline:
    Clean, Normalize, Extract, Markdown, Chunk, Enrich, and Validate.</p>

    <pre><code class="language-python">
from knowledge_service.processing.pipeline import Pipeline

pipeline = Pipeline(config)
objects = pipeline.process(bundle)
    </code></pre>

    <h2>Confidence Framework</h2>
    <p>Confidence is computed as a weighted combination of source trust,
    content completeness, processing quality, and evidence strength.</p>

    <table>
      <tr><th>Factor</th><th>Weight</th><th>Source</th></tr>
      <tr><td>Source Trust</td><td>0.35</td><td>Source Registry</td></tr>
      <tr><td>Content Completeness</td><td>0.25</td><td>Processing analysis</td></tr>
      <tr><td>Processing Quality</td><td>0.25</td><td>Pipeline stage metrics</td></tr>
      <tr><td>Evidence Strength</td><td>0.15</td><td>Citations and records</td></tr>
    </table>

    <h2>Future Work</h2>
    <p>The next phase will implement storage backends and the Knowledge Layer.
    See https://roadmap.example.com for details.</p>
  </article>
  <footer>Copyright 2026 Knowledge Service</footer>
</body>
</html>"""


def demonstrate():
    bundle = AcquisitionBundle(
        request_id="demo-req-001",
        plan_id="demo-plan-001",
        acquisition_timestamp="2026-06-25T12:00:00Z",
    )
    bundle.add_execution_record(ExecutionRecord(
        step_id="step-crawl-001",
        provider_name="crawl4ai-primary",
        provider_type="crawl",
        target="https://docs.example.com/architecture",
        status="success",
        latency_ms=850,
    ))
    bundle.add_document(DocumentRecord(
        document_id="doc-arch-001",
        url="https://docs.example.com/architecture",
        provider_name="crawl4ai-primary",
        content_type="text/html",
        raw_content=SAMPLE_HTML,
        content_size_bytes=len(SAMPLE_HTML.encode("utf-8")),
        acquired_at="2026-06-25T12:00:00Z",
    ))

    pipeline = Pipeline({
        "clean": {"strip_scripts": True, "strip_navigation": True},
        "normalize": {"detect_language": True, "normalize_headings": True},
        "extract": {"extract_citations": True, "extract_tables": True, "extract_authors": True},
        "markdown": {"preserve_code_formatting": True},
        "chunk": {"strategy": "semantic", "min_chunk_size_tokens": 10},
        "enrich": {
            "compute_confidence": True, "classify_topics": True,
            "default_source_trust": 0.85,
        },
    })

    kobjects = pipeline.process(bundle)

    print("=" * 70)
    print("PHASE 1.2 DEMONSTRATION")
    print("AcquisitionBundle -> Processing Pipeline -> Knowledge Objects")
    print("=" * 70)

    print(f"\nInput: {bundle.request_id}")
    print(f"Documents: {len(bundle.acquired_documents)}")
    print(f"Provider executions: {len(bundle.provider_executions)}")

    print(f"\nOutput: {len(kobjects)} Knowledge Objects")
    print(f"  Documents: {len([ko for ko in kobjects if ko.type.value == 'document'])}")
    print(f"  Chunks:    {len([ko for ko in kobjects if ko.type.value == 'chunk'])}")

    for ko in kobjects:
        print(f"\n  --- {'DOCUMENT' if ko.type.value == 'document' else 'CHUNK'} ---")
        print(f"  ID:            {ko.id}")
        print(f"  Type:          {ko.type.value}")
        print(f"  Source:        {ko.source_url}")
        print(f"  Title:         {ko.title or '(none)'}")
        print(f"  Language:      {ko.language}")
        print(f"  Topics:        {', '.join(ko.topics) if ko.topics else '(none)'}")
        print(f"  Authors:       {', '.join(ko.authors) if ko.authors else '(none)'}")
        print(f"  Word Count:    {ko.word_count}")
        print(f"  Confidence:    {ko.confidence:.3f}")
        print(f"  Evidence:      {ko.evidence_count}")
        print(f"  Raw Hash:      {ko.raw_content_hash[:16]}...")
        print(f"  Content Hash:  {ko.content_hash[:16]}...")
        if ko.parent_id:
            print(f"  Parent:        {ko.parent_id}")
            print(f"  Chunk:         {ko.chunk_index + 1}/{ko.chunk_total}")

    print(f"\n{'=' * 70}")
    print("DEMONSTRATION COMPLETE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    demonstrate()
