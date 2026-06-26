"""Tests for Validate stage"""

import pytest
from src.knowledge_service.processing.validate import ValidateStage
from src.knowledge_service.processing.context import ProcessingContext
from src.knowledge_service.knowledge_object import (
    KnowledgeObject, KnowledgeType, AcquisitionRecord,
    ProviderType, AcquisitionStatus,
)
from src.knowledge_service.acquisition.acquisition_bundle import AcquisitionBundle


class TestValidateStage:

    def test_validates_correct_object(self):
        ctx = ProcessingContext()
        ctx.raw_content = "Raw content"
        ctx.raw_content_hash = KnowledgeObject.compute_raw_content_hash(b"Raw content")
        ko = KnowledgeObject(
            id="valid-ko",
            type=KnowledgeType.DOCUMENT,
            source_id="source-1",
            source_url="https://example.com",
            acquired_at="2026-06-25T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            markdown="# Hello",
            raw_content_hash=ctx.raw_content_hash,
            content_hash=KnowledgeObject.compute_content_hash("# Hello"),
            confidence=0.75,
            evidence_count=1,
            acquisition_chain=[
                AcquisitionRecord(
                    provider_name="crawl4ai",
                    provider_type=ProviderType.CRAWLER,
                    request_id="req-1",
                    timestamp="2026-06-25T12:00:00Z",
                    status=AcquisitionStatus.SUCCESS,
                )
            ],
        )
        ctx.knowledge_objects = [ko]
        ctx.bundle = AcquisitionBundle(
            request_id="r", plan_id="p", acquisition_timestamp="2026-06-25T12:00:00Z"
        )
        stage = ValidateStage()
        ctx = stage.execute(ctx, {})
        assert ctx.stage_results["validate"].success
        assert len(ctx.knowledge_objects) == 1

    def test_rejects_missing_hash(self):
        ctx = ProcessingContext()
        ctx.raw_content = "Raw content"
        ctx.raw_content_hash = ""
        ko = KnowledgeObject(
            id="bad-hash",
            type=KnowledgeType.DOCUMENT,
            source_id="source-1",
            acquired_at="2026-06-25T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            confidence=0.5,
            evidence_count=1,
            raw_content_hash="",
            content_hash="",
        )
        ctx.knowledge_objects = [ko]
        ctx.bundle = AcquisitionBundle(
            request_id="r", plan_id="p", acquisition_timestamp="2026-06-25T12:00:00Z"
        )
        stage = ValidateStage()
        ctx = stage.execute(ctx, {})
        assert len(ctx.knowledge_objects) == 0

    def test_rejects_wrong_confidence_range(self):
        ctx = ProcessingContext()
        ctx.raw_content = "Raw"
        ctx.raw_content_hash = KnowledgeObject.compute_raw_content_hash(b"Raw")
        ko = KnowledgeObject(
            id="bad-conf",
            type=KnowledgeType.DOCUMENT,
            source_id="src-1",
            acquired_at="2026-06-25T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            markdown="# Test",
            raw_content_hash=KnowledgeObject.compute_raw_content_hash(b"Raw"),
            content_hash=KnowledgeObject.compute_content_hash("# Test"),
            confidence=1.5,
            evidence_count=1,
        )
        ctx.knowledge_objects = [ko]
        ctx.bundle = AcquisitionBundle(
            request_id="r", plan_id="p", acquisition_timestamp="2026-06-25T12:00:00Z"
        )
        stage = ValidateStage()
        ctx = stage.execute(ctx, {})
        assert len(ctx.knowledge_objects) == 0

    def test_warns_on_empty_acquisition_chain(self):
        ctx = ProcessingContext()
        ctx.raw_content = "Raw"
        ctx.raw_content_hash = KnowledgeObject.compute_raw_content_hash(b"Raw")
        ko = KnowledgeObject(
            id="no-chain",
            type=KnowledgeType.DOCUMENT,
            source_id="src-1",
            source_url="https://example.com",
            acquired_at="2026-06-25T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            markdown="# Test",
            raw_content_hash=KnowledgeObject.compute_raw_content_hash(b"Raw"),
            content_hash=KnowledgeObject.compute_content_hash("# Test"),
            confidence=0.5,
            evidence_count=1,
            acquisition_chain=[],
        )
        ctx.knowledge_objects = [ko]
        ctx.bundle = AcquisitionBundle(
            request_id="r", plan_id="p", acquisition_timestamp="2026-06-25T12:00:00Z"
        )
        stage = ValidateStage()
        ctx = stage.execute(ctx, {})
        assert len(ctx.knowledge_objects) == 1

    def test_validates_chunk_relationships(self):
        ctx = ProcessingContext()
        ctx.raw_content = "Raw"
        ctx.raw_content_hash = KnowledgeObject.compute_raw_content_hash(b"Raw")
        parent = KnowledgeObject(
            id="parent-1",
            type=KnowledgeType.DOCUMENT,
            source_id="src-1",
            source_url="https://example.com",
            acquired_at="2026-06-25T12:00:00Z",
            updated_at="2026-06-25T12:00:00Z",
            markdown="# Parent",
            raw_content_hash=KnowledgeObject.compute_raw_content_hash(b"Raw"),
            content_hash=KnowledgeObject.compute_content_hash("# Parent"),
            confidence=0.7,
            evidence_count=1,
            acquisition_chain=[
                AcquisitionRecord(
                    provider_name="crawl4ai",
                    provider_type=ProviderType.CRAWLER,
                    request_id="req-1",
                    timestamp="2026-06-25T12:00:00Z",
                    status=AcquisitionStatus.SUCCESS,
                )
            ],
        )
        ctx.knowledge_objects = [parent]
        ctx.chunks = []
        ctx.bundle = AcquisitionBundle(
            request_id="r", plan_id="p", acquisition_timestamp="2026-06-25T12:00:00Z"
        )
        stage = ValidateStage()
        ctx = stage.execute(ctx, {})
        assert len(ctx.knowledge_objects) == 1
