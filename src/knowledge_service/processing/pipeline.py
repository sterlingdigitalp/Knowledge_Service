"""Processing Pipeline — orchestrates all 7 stages

AcquisitionBundle -> Pipeline -> List[KnowledgeObject]
"""

from typing import Dict, Any, List, Optional
from ..acquisition.acquisition_bundle import AcquisitionBundle
from ..knowledge_object import (
    KnowledgeObject, KnowledgeType, SourceType, AcquisitionRecord,
    ProviderType, AcquisitionStatus, CitationType, Citation,
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

        doc_metadata = dict(getattr(doc, "metadata", {}) or {})
        source_type = self._map_source_type(getattr(doc, "source_type", "web_page"), doc_metadata, doc.content_type)
        source_id = self._source_id(doc, bundle, doc_metadata, source_type)
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

        doc_structured_data = self._document_structured_data(ctx, doc_metadata, source_type)
        doc_citations = self._build_citations(ctx.citations)

        doc_ko = KnowledgeObject(
            type=KnowledgeType.DOCUMENT,
            source_id=source_id,
            source_url=source_url,
            source_type=source_type,
            acquired_at=acquired_at,
            published_at=ctx.extracted_data.get("published_date"),
            updated_at=acquired_at,
            markdown=ctx.markdown or None,
            structured_data=doc_structured_data,
            raw_content_hash=ctx.raw_content_hash,
            content_hash=ctx.content_hash,
            title=ctx.title,
            authors=ctx.authors,
            language=ctx.language or "en",
            topics=ctx.topics,
            word_count=ctx.word_count,
            confidence=ctx.confidence,
            evidence_count=ctx.evidence_count,
            citations=doc_citations,
            acquisition_chain=acquisition_records,
            storage_backend=self.config.get("storage_backend", "primary-store-01"),
        )
        kobjects.append(doc_ko)

        for chunk_data in ctx.chunks:
            chunk_structured_data = self._chunk_structured_data(chunk_data, doc_metadata, source_type)
            chunk_citations = self._build_citations(chunk_data.get("citations", []))
            chunk_ko = KnowledgeObject(
                type=KnowledgeType.CHUNK,
                source_id=source_id,
                source_url=source_url,
                source_type=source_type,
                acquired_at=acquired_at,
                published_at=ctx.extracted_data.get("published_date"),
                updated_at=acquired_at,
                markdown=chunk_data["content"],
                structured_data=chunk_structured_data,
                raw_content_hash=ctx.raw_content_hash,
                content_hash=chunk_data["content_hash"],
                topics=ctx.topics,
                word_count=chunk_data.get("word_count", 0),
                confidence=chunk_data.get("confidence", ctx.confidence),
                evidence_count=max(1, len(chunk_citations) or ctx.evidence_count),
                citations=chunk_citations,
                acquisition_chain=acquisition_records,
                parent_id=chunk_data.get("parent_id") or doc_ko.id,
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

    def _source_id(self, doc: Any, bundle: Optional[AcquisitionBundle], metadata: Dict[str, Any], source_type: SourceType) -> str:
        if source_type == SourceType.VIDEO_TRANSCRIPT:
            return (
                metadata.get("transcript_id")
                or metadata.get("episode_id")
                or metadata.get("video_id")
                or doc.document_id
            )
        return doc.provider_name if doc.provider_name else (bundle.request_id if bundle else "unknown")

    def _map_source_type(self, source_type: str, metadata: Dict[str, Any], content_type: str) -> SourceType:
        raw = metadata.get("source_type") or source_type
        if raw == "video_transcript" or content_type in {"text/vtt", "text/srt", "application/x-subrip", "text/transcript"}:
            return SourceType.VIDEO_TRANSCRIPT
        try:
            return SourceType(raw)
        except Exception:
            return SourceType.WEB_PAGE

    def _build_citations(self, raw_citations: List[Dict[str, Any]]) -> List[Citation]:
        citations: List[Citation] = []
        for raw in raw_citations:
            citation_type = raw.get("citation_type", "reference")
            if not isinstance(citation_type, CitationType):
                citation_type = CitationType(citation_type)
            citations.append(Citation(
                target_id=raw.get("target_id"),
                target_url=raw.get("target_url"),
                context=raw.get("context"),
                citation_type=citation_type,
                start_seconds=raw.get("start_seconds"),
                end_seconds=raw.get("end_seconds"),
                segment_id=raw.get("segment_id"),
                quote=raw.get("quote"),
                speaker=raw.get("speaker"),
                speaker_confidence=raw.get("speaker_confidence"),
                transcript_confidence=raw.get("transcript_confidence"),
                surrounding_context=raw.get("surrounding_context"),
                metadata=raw.get("metadata", {}),
            ))
        return citations

    def _document_structured_data(self, ctx: ProcessingContext, metadata: Dict[str, Any], source_type: SourceType) -> Optional[Dict[str, Any]]:
        if source_type != SourceType.VIDEO_TRANSCRIPT and not metadata and not ctx.extracted_data:
            return None
        structured: Dict[str, Any] = {
            "metadata": metadata,
            "extracted_data": ctx.extracted_data,
        }
        if source_type == SourceType.VIDEO_TRANSCRIPT:
            structured.update({
                "raw_transcript": ctx.raw_content,
                "transcript_id": metadata.get("transcript_id") or metadata.get("episode_id") or metadata.get("video_id"),
                "transcript_source": metadata.get("transcript_source"),
                "acquisition_status": metadata.get("acquisition_status"),
                "provider": metadata.get("provider"),
                "show": metadata.get("show"),
                "episode": metadata.get("episode"),
                "episode_date": metadata.get("episode_date"),
                "transcript_segments": ctx.extracted_data.get("transcript_segments", []),
            })
        return structured

    def _chunk_structured_data(self, chunk_data: Dict[str, Any], metadata: Dict[str, Any], source_type: SourceType) -> Optional[Dict[str, Any]]:
        if source_type != SourceType.VIDEO_TRANSCRIPT:
            return {"heading_context": chunk_data.get("heading_context", "")} if chunk_data.get("heading_context") else None
        keys = {
            "transcript_chunk_id", "transcript_id", "speaker", "speaker_confidence",
            "transcript_confidence", "timestamp_start", "timestamp_end",
            "timestamp_start_label", "timestamp_end_label", "timestamped_source_url",
            "surrounding_context", "segments", "segment_ids", "embedding",
        }
        structured = {key: chunk_data.get(key) for key in keys if key in chunk_data}
        structured["metadata"] = metadata
        return structured

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
