"""Tests for Enrich stage"""

import pytest
from src.knowledge_service.processing.enrich import EnrichStage
from src.knowledge_service.processing.context import ProcessingContext, StageResult
from src.knowledge_service.acquisition.acquisition_bundle import AcquisitionBundle


class TestEnrichStage:

    def test_computes_confidence_default(self):
        ctx = ProcessingContext()
        ctx.markdown = "Some content here for testing."
        ctx.word_count = 5
        ctx.title = "Test"
        ctx.language = "en"
        ctx.raw_content_hash = "abc123"
        ctx.citations = [{"target_url": "https://ref.com", "citation_type": "reference"}]
        ctx.stage_results = {
            "clean": StageResult("clean", True),
            "normalize": StageResult("normalize", True),
            "extract": StageResult("extract", True),
            "markdown": StageResult("markdown", True),
            "chunk": StageResult("chunk", True),
        }
        bundle = AcquisitionBundle(
            request_id="req-1", plan_id="plan-1", acquisition_timestamp="2026-06-25T12:00:00Z"
        )
        bundle.provider_executions = []
        bundle.acquired_documents = []
        ctx.bundle = bundle
        stage = EnrichStage()
        ctx = stage.execute(ctx, {"compute_confidence": True})
        assert 0.0 <= ctx.confidence <= 1.0
        assert ctx.confidence > 0.0

    def test_confidence_never_exceeds_bounds(self):
        ctx = ProcessingContext()
        ctx.markdown = "Content"
        ctx.word_count = 1
        ctx.title = "T"
        ctx.language = "en"
        ctx.raw_content_hash = "hash"
        ctx.citations = [{"target_url": "https://x.com"}] * 100
        ctx.stage_results = {
            "clean": StageResult("clean", True),
            "normalize": StageResult("normalize", True),
            "extract": StageResult("extract", True),
            "markdown": StageResult("markdown", True),
            "chunk": StageResult("chunk", True),
        }
        ctx.bundle = AcquisitionBundle(
            request_id="r", plan_id="p", acquisition_timestamp="2026-06-25T12:00:00Z"
        )
        ctx.bundle.provider_executions = []
        ctx.bundle.acquired_documents = []
        stage = EnrichStage()
        ctx = stage.execute(ctx, {"compute_confidence": True})
        assert ctx.confidence <= 1.0
        assert ctx.confidence >= 0.0

    def test_classifies_topics(self):
        ctx = ProcessingContext()
        ctx.markdown = "This is about Python programming and software development. API and framework."
        stage = EnrichStage()
        ctx = stage.execute(ctx, {"classify_topics": True})
        assert len(ctx.topics) > 0
        assert "programming" in ctx.topics or "web_development" in ctx.topics

    def test_count_evidence(self):
        ctx = ProcessingContext()
        ctx.markdown = "Some content."
        ctx.citations = [{"target_url": "https://x.com"}] * 3
        ctx.bundle = AcquisitionBundle(
            request_id="r", plan_id="p", acquisition_timestamp="2026-06-25T12:00:00Z"
        )
        ctx.bundle.provider_executions = []
        ctx.bundle.acquired_documents = []
        stage = EnrichStage()
        ctx = stage.execute(ctx, {})
        assert ctx.evidence_count >= 3
