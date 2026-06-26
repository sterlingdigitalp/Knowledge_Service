"""Processing Pipeline — orchestrates all 7 stages

AcquisitionBundle -> Pipeline -> List[KnowledgeObject]
"""

from typing import Dict, Any, List, Optional
from ..acquisition.acquisition_bundle import AcquisitionBundle
from ..knowledge_object import (
    KnowledgeObject, KnowledgeType, SourceType, AcquisitionRecord,
    ProviderType, AcquisitionStatus, CitationType,
)
from .context import ProcessingContext
from .clean import CleanStage
from .normalize import NormalizeStage
from .extract import ExtractStage
from .markdown import MarkdownStage
from .chunk import ChunkStage
from .enrich import EnrichStage
from .validate import ValidateStage


class Pipeline:

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.stages = [
            ("clean", CleanStage()),
            ("normalize", NormalizeStage()),
            ("extract", ExtractStage()),
            ("markdown", MarkdownStage()),
            ("chunk", ChunkStage()),
            ("enrich", EnrichStage()),
            ("validate", ValidateStage()),
        ]

    def process(self, bundle: AcquisitionBundle) -> List[KnowledgeObject]:
        kobjects: List[KnowledgeObject] = []
        for doc in bundle.acquired_documents:
            ctx = ProcessingContext(
                bundle=bundle,
                document=doc,
                raw_content=doc.raw_content,
            )

            for stage_name, stage in self.stages:
                try:
                    stage_config = self.config.get(stage_name, {})
                    ctx = stage.execute(ctx, stage_config)
                except Exception as e:
                    impact = self._stage_confidence_impact(stage_name)
                    ctx.confidence_adjustments.append(impact)
                    ctx.errors.append(f"{stage_name} stage failed: {str(e)}")
                    ctx.stage_results[stage_name] = type("sr", (), {
                        "stage_name": stage_name, "success": False,
                        "confidence_impact": impact, "warnings": [], "error": str(e)
                    })()

            kos = self._build_knowledge_objects(ctx)
            kobjects.extend(kos)

        return kobjects

    def _build_knowledge_objects(self, ctx: ProcessingContext) -> List[KnowledgeObject]:
        kobjects: List[KnowledgeObject] = []
        bundle = ctx.bundle
        doc = ctx.document

        if not doc:
            return kobjects

        source_id = doc.provider_name if doc.provider_name else (bundle.request_id if bundle else "unknown")
        source_url = doc.url
        acquired_at = doc.acquired_at

        acquisition_records: List[AcquisitionRecord] = []
        if bundle:
            for exec_rec in bundle.provider_executions:
                ar = AcquisitionRecord(
                    provider_name=exec_rec.provider_name,
                    provider_type=self._map_provider_type(exec_rec.provider_type),
                    request_id=bundle.request_id,
                    timestamp=acquired_at,
                    status=self._map_status(exec_rec.status),
                    response_size_bytes=doc.content_size_bytes,
                    latency_ms=exec_rec.latency_ms if exec_rec.latency_ms else None,
                    error_message=exec_rec.error_message,
                )
                acquisition_records.append(ar)

        doc_ko = KnowledgeObject(
            type=KnowledgeType.DOCUMENT,
            source_id=source_id,
            source_url=source_url,
            source_type=SourceType.WEB_PAGE,
            acquired_at=acquired_at,
            updated_at=acquired_at,
            markdown=ctx.markdown or None,
            raw_content_hash=ctx.raw_content_hash,
            content_hash=ctx.content_hash,
            title=ctx.title,
            authors=ctx.authors,
            language=ctx.language or "en",
            topics=ctx.topics,
            word_count=ctx.word_count,
            confidence=ctx.confidence,
            evidence_count=ctx.evidence_count,
            acquisition_chain=acquisition_records,
            storage_backend=self.config.get("storage_backend", "primary-store-01"),
        )
        kobjects.append(doc_ko)

        for chunk_data in ctx.chunks:
            chunk_ko = KnowledgeObject(
                type=KnowledgeType.CHUNK,
                source_id=source_id,
                source_url=source_url,
                source_type=SourceType.WEB_PAGE,
                acquired_at=acquired_at,
                updated_at=acquired_at,
                markdown=chunk_data["content"],
                raw_content_hash=ctx.raw_content_hash,
                content_hash=chunk_data["content_hash"],
                topics=ctx.topics,
                word_count=chunk_data.get("word_count", 0),
                confidence=ctx.confidence,
                evidence_count=ctx.evidence_count,
                acquisition_chain=acquisition_records,
                parent_id=chunk_data.get("parent_id"),
                chunk_index=chunk_data.get("chunk_index"),
                chunk_total=chunk_data.get("chunk_total"),
                storage_backend=self.config.get("storage_backend", "primary-store-01"),
            )
            kobjects.append(chunk_ko)

        return kobjects

    def _map_provider_type(self, pt: str) -> ProviderType:
        mapping = {
            "search": ProviderType.SEARCH,
            "crawl": ProviderType.CRAWLER,
            "api": ProviderType.API,
            "rss": ProviderType.RSS,
            "file_processor": ProviderType.FILE_PROCESSOR,
            "database": ProviderType.DATABASE,
        }
        return mapping.get(pt, ProviderType.CRAWLER)

    def _map_status(self, status: str) -> AcquisitionStatus:
        mapping = {
            "success": AcquisitionStatus.SUCCESS,
            "partial": AcquisitionStatus.PARTIAL,
            "failed": AcquisitionStatus.FAILED,
            "cached": AcquisitionStatus.CACHED,
        }
        return mapping.get(status, AcquisitionStatus.SUCCESS)

    def _stage_confidence_impact(self, stage_name: str) -> float:
        impacts = {
            "clean": -0.10,
            "normalize": -0.05,
            "extract": -0.10,
            "markdown": -0.15,
            "chunk": 0.0,
            "enrich": -0.05,
            "validate": -0.05,
        }
        return impacts.get(stage_name, -0.05)
