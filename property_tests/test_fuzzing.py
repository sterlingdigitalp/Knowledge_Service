"""Property-Based Tests — Randomized AcquisitionBundle fuzzing

Randomly generates AcquisitionBundles with varying content sizes,
HTML structures, metadata presence, and provider execution records.
Verifies the pipeline never crashes and always produces valid KOs.
"""

import os, sys, random, string, hashlib
_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

import pytest
from src.knowledge_service.acquisition.acquisition_bundle import (
    AcquisitionBundle, DocumentRecord, ExecutionRecord,
)
from src.knowledge_service.processing.pipeline import Pipeline
from src.knowledge_service.knowledge_object import KnowledgeObject


LOWERCASE = string.ascii_lowercase
UPPERCASE = string.ascii_uppercase
DIGITS = string.digits


def random_string(min_len=10, max_len=200):
    return ''.join(random.choice(LOWERCASE + UPPERCASE + DIGITS + ' ') for _ in range(random.randint(min_len, max_len)))


def random_url():
    return f"https://{random_string(5, 15).strip().replace(' ', '')}.com/{random_string(3, 10).strip().replace(' ', '')}"


def random_html(min_paras=1, max_paras=10):
    paras = []
    for _ in range(random.randint(min_paras, max_paras)):
        tag = random.choice(["p", "div", "span"])
        content = random_string(20, 200)
        paras.append(f"<{tag}>{content}</{tag}>")
    
    has_heading = random.random() > 0.3
    has_title = random.random() > 0.4
    has_author = random.random() > 0.6
    has_code = random.random() > 0.7
    has_table = random.random() > 0.8
    has_nav = random.random() > 0.5
    has_script = random.random() > 0.6
    has_comment = random.random() > 0.5
    
    parts = []
    
    if has_nav:
        parts.append(f"<nav>{random_string(10, 50)}</nav>")
    
    if has_title:
        parts.append(f"<h1>{random_string(10, 60)}</h1>")
    
    if has_author:
        names = [random_string(5, 15).strip() for _ in range(random.randint(1, 3))]
        author_str = ", ".join(names)
        parts.append(f"<p>By {author_str}</p>")
    
    parts.extend(paras)
    
    if has_script:
        parts.append(f"<script>{random_string(10, 50)}</script>")
    
    if has_comment:
        parts.append(f"<!-- {random_string(10, 30)} -->")
    
    if has_code:
        lang = random.choice(["python", "javascript", "go", "rust", ""])
        code = random_string(20, 100)
        parts.append(f"<pre><code class=\"language-{lang}\">{code}</code></pre>")
    
    if has_table:
        rows = random.randint(2, 5)
        table = "<table>"
        for i in range(rows):
            cells = "".join(f"<td>{random_string(3, 10)}</td>" for _ in range(random.randint(2, 4)))
            table += f"<tr>{cells}</tr>"
        table += "</table>"
        parts.append(table)
    
    header = "<!DOCTYPE html><html><head>"
    if has_title:
        header += f"<title>{random_string(10, 60)}</title>"
    header += "</head><body>"
    
    footer = "</body></html>"
    
    return header + "\n".join(parts) + footer


def random_bundle():
    bundle = AcquisitionBundle(
        request_id=random_string(8, 20),
        plan_id=random_string(8, 20),
        acquisition_timestamp="2026-06-25T12:00:00Z",
    )
    
    num_execs = random.randint(0, 5)
    for i in range(num_execs):
        bundle.add_execution_record(ExecutionRecord(
            step_id=f"step-{i}",
            provider_name=random.choice(["crawl4ai-primary", "searxng-main", "github-api"]),
            provider_type=random.choice(["crawl", "search", "api"]),
            target=random_url(),
            status=random.choice(["success", "partial", "failed", "cached"]),
            latency_ms=random.randint(100, 5000),
        ))
    
    num_docs = random.randint(1, 5)
    for i in range(num_docs):
        html = random_html()
        bundle.add_document(DocumentRecord(
            document_id=f"doc-{i}-{random_string(5, 10)}",
            url=random_url(),
            provider_name=random.choice(["crawl4ai-primary", "searxng-main"]),
            content_type=random.choice(["text/html", "text/markdown", "application/json"]),
            raw_content=html,
            content_size_bytes=len(html.encode("utf-8")),
            acquired_at="2026-06-25T12:00:00Z",
        ))
    
    return bundle


class TestPropertyBasedFuzzing:

    @pytest.mark.parametrize("seed", range(50))
    def test_random_bundles_never_crash(self, seed):
        random.seed(seed)
        bundle = random_bundle()
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert isinstance(kobjects, list)
        for ko in kobjects:
            assert isinstance(ko, KnowledgeObject)

    @pytest.mark.parametrize("seed", range(50))
    def test_random_bundle_hashes_always_valid(self, seed):
        random.seed(seed)
        bundle = random_bundle()
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        for ko in kobjects:
            assert len(ko.raw_content_hash) == 64, f"raw_content_hash invalid length: {len(ko.raw_content_hash)}"
            assert len(ko.content_hash) == 64, f"content_hash invalid length: {len(ko.content_hash)}"
            assert all(c in "0123456789abcdef" for c in ko.raw_content_hash), "raw_content_hash not hex"
            assert all(c in "0123456789abcdef" for c in ko.content_hash), "content_hash not hex"

    @pytest.mark.parametrize("seed", range(50))
    def test_random_bundle_confidence_bounded(self, seed):
        random.seed(seed)
        bundle = random_bundle()
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        for ko in kobjects:
            assert 0.0 <= ko.confidence <= 1.0, f"Confidence out of bounds: {ko.confidence}"

    @pytest.mark.parametrize("seed", range(30))
    def test_random_bundle_chunk_refs_valid(self, seed):
        random.seed(seed)
        bundle = random_bundle()
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        parents = {ko.id for ko in kobjects if ko.type.value == "document"}
        for ko in kobjects:
            if ko.type.value == "chunk":
                assert ko.parent_id in parents, f"Chunk {ko.id} parent {ko.parent_id} not found in documents"
                assert ko.chunk_index is not None
                assert ko.chunk_total is not None
                assert 0 <= ko.chunk_index < ko.chunk_total

    @pytest.mark.parametrize("seed", range(30))
    def test_random_bundle_reproducible(self, seed):
        random.seed(seed)
        bundle1 = random_bundle()
        bundle2 = AcquisitionBundle(
            request_id=bundle1.request_id,
            plan_id=bundle1.plan_id,
            acquisition_timestamp=bundle1.acquisition_timestamp,
        )
        for doc in bundle1.acquired_documents:
            bundle2.add_document(doc)
        for ex in bundle1.provider_executions:
            bundle2.add_execution_record(ex)

        pipeline = Pipeline()
        k1 = pipeline.process(bundle1)
        k2 = pipeline.process(bundle2)

        assert len(k1) == len(k2)
        for ko1, ko2 in zip(k1, k2):
            assert ko1.content_hash == ko2.content_hash, f"Content hash mismatch for {ko1.id}"
            assert ko1.raw_content_hash == ko2.raw_content_hash

    def test_empty_bundle(self):
        bundle = AcquisitionBundle(
            request_id="empty-test",
            plan_id="empty-plan",
            acquisition_timestamp="2026-06-25T12:00:00Z",
        )
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert kobjects == []

    def test_bundle_with_only_executions(self):
        bundle = AcquisitionBundle(
            request_id="exec-only",
            plan_id="exec-plan",
            acquisition_timestamp="2026-06-25T12:00:00Z",
        )
        bundle.add_execution_record(ExecutionRecord(
            step_id="step-0",
            provider_name="crawl4ai-primary",
            provider_type="crawl",
            target="https://example.com",
            status="success",
            latency_ms=100,
        ))
        pipeline = Pipeline()
        kobjects = pipeline.process(bundle)
        assert kobjects == []

    def test_repeated_same_seed_same_bundle(self):
        random.seed(42)
        b1 = random_bundle()
        random.seed(42)
        b2 = random_bundle()
        assert len(b1.acquired_documents) == len(b2.acquired_documents)
        for d1, d2 in zip(b1.acquired_documents, b2.acquired_documents):
            assert d1.raw_content == d2.raw_content
