"""Knowledge Object — Canonical Knowledge Representation (Phase 0 Specification)

Matches KNOWN_OBJECT.md exactly. Core identity, source info, temporal info,
content with hashes, metadata, evidence/confidence, acquisition history,
chunking info, relationships, and system fields.

All fields optional at construction time; validation enforces required fields.
"""

import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime, timezone


class KnowledgeType(Enum):
    DOCUMENT = "document"
    CHUNK = "chunk"
    SUMMARY = "summary"
    CITATION = "citation"
    RELATIONSHIP = "relationship"


class SourceType(Enum):
    WEB_PAGE = "web_page"
    API_RESPONSE = "api_response"
    RSS_FEED = "rss_feed"
    GITHUB_REPOSITORY = "github_repository"
    PDF_DOCUMENT = "pdf_document"
    VIDEO_TRANSCRIPT = "video_transcript"
    DATABASE_RECORD = "database_record"
    EMAIL = "email"
    OTHER = "other"


class CitationType(Enum):
    REFERENCE = "reference"
    SUPPORTING_EVIDENCE = "supporting_evidence"
    CONTRADICTORY_EVIDENCE = "contradictory_evidence"
    SUPPLEMENTARY = "supplementary"
    DERIVED_FROM = "derived_from"


class ProviderType(Enum):
    CRAWLER = "crawler"
    SEARCH = "search"
    API = "api"
    RSS = "rss"
    FILE_PROCESSOR = "file_processor"
    DATABASE = "database"


class AcquisitionStatus(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    CACHED = "cached"


class IndexStatus(Enum):
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"


class RelationshipType(Enum):
    REFERENCES = "references"
    CITES = "cites"
    CONTRADICTS = "contradicts"
    SUPPLEMENTS = "supplements"
    DERIVES_FROM = "derives_from"
    PART_OF = "part_of"
    RELATED_TO = "related_to"


@dataclass
class Citation:
    target_id: Optional[str] = None
    target_url: Optional[str] = None
    context: Optional[str] = None
    citation_type: CitationType = CitationType.REFERENCE
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    segment_id: Optional[str] = None
    quote: Optional[str] = None
    speaker: Optional[str] = None
    speaker_confidence: Optional[float] = None
    transcript_confidence: Optional[float] = None
    surrounding_context: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AcquisitionRecord:
    provider_name: str = ""
    provider_type: ProviderType = ProviderType.CRAWLER
    request_id: str = ""
    timestamp: str = ""
    status: AcquisitionStatus = AcquisitionStatus.SUCCESS
    response_size_bytes: Optional[int] = None
    latency_ms: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class KnowledgeObject:
    id: str = ""
    version: int = 1
    type: KnowledgeType = KnowledgeType.DOCUMENT

    source_id: str = ""
    source_url: Optional[str] = None
    source_type: SourceType = SourceType.WEB_PAGE

    acquired_at: str = ""
    published_at: Optional[str] = None
    updated_at: str = ""

    markdown: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    raw_content_hash: str = ""
    content_hash: str = ""

    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    language: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    word_count: int = 0

    confidence: float = 0.0
    evidence_count: int = 0
    citations: List[Citation] = field(default_factory=list)

    acquisition_chain: List[AcquisitionRecord] = field(default_factory=list)

    parent_id: Optional[str] = None
    chunk_index: Optional[int] = None
    chunk_total: Optional[int] = None
    overlap_with_next_id: Optional[str] = None

    related_to: List[str] = field(default_factory=list)
    relationship_types: List[RelationshipType] = field(default_factory=list)

    storage_backend: str = "primary-store-01"
    index_status: IndexStatus = IndexStatus.PENDING
    retention_policy_id: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid7())
        if not self.acquired_at:
            self.acquired_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if not self.updated_at:
            self.updated_at = self.acquired_at

    @staticmethod
    def compute_raw_content_hash(raw_bytes: bytes) -> str:
        return hashlib.sha256(raw_bytes).hexdigest()

    @staticmethod
    def compute_content_hash(markdown: str) -> str:
        return hashlib.sha256(markdown.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        d["id"] = self.id
        d["version"] = self.version
        d["type"] = self.type.value

        d["source_id"] = self.source_id
        if self.source_url is not None:
            d["source_url"] = self.source_url
        d["source_type"] = self.source_type.value

        d["acquired_at"] = self.acquired_at
        if self.published_at is not None:
            d["published_at"] = self.published_at
        d["updated_at"] = self.updated_at

        if self.markdown is not None:
            d["markdown"] = self.markdown
        if self.structured_data is not None:
            d["structured_data"] = self.structured_data
        d["raw_content_hash"] = self.raw_content_hash
        d["content_hash"] = self.content_hash

        if self.title is not None:
            d["title"] = self.title
        if self.authors:
            d["authors"] = self.authors
        if self.language is not None:
            d["language"] = self.language
        if self.topics:
            d["topics"] = self.topics
        if self.word_count:
            d["word_count"] = self.word_count

        d["confidence"] = self.confidence
        d["evidence_count"] = self.evidence_count
        if self.citations:
            citation_dicts = []
            for c in self.citations:
                citation_dict: Dict[str, Any] = {
                    "target_id": c.target_id,
                    "target_url": c.target_url,
                    "context": c.context,
                    "citation_type": c.citation_type.value,
                }
                optional_fields = {
                    "start_seconds": c.start_seconds,
                    "end_seconds": c.end_seconds,
                    "segment_id": c.segment_id,
                    "quote": c.quote,
                    "speaker": c.speaker,
                    "speaker_confidence": c.speaker_confidence,
                    "transcript_confidence": c.transcript_confidence,
                    "surrounding_context": c.surrounding_context,
                }
                for key, value in optional_fields.items():
                    if value is not None:
                        citation_dict[key] = value
                if c.metadata:
                    citation_dict["metadata"] = c.metadata
                citation_dicts.append(citation_dict)
            d["citations"] = citation_dicts

        if self.acquisition_chain:
            d["acquisition_chain"] = [
                {
                    "provider_name": a.provider_name,
                    "provider_type": a.provider_type.value,
                    "request_id": a.request_id,
                    "timestamp": a.timestamp,
                    "status": a.status.value,
                    "response_size_bytes": a.response_size_bytes,
                    "latency_ms": a.latency_ms,
                    "error_message": a.error_message,
                }
                for a in self.acquisition_chain
            ]

        if self.parent_id is not None:
            d["parent_id"] = self.parent_id
        if self.chunk_index is not None:
            d["chunk_index"] = self.chunk_index
        if self.chunk_total is not None:
            d["chunk_total"] = self.chunk_total
        if self.overlap_with_next_id is not None:
            d["overlap_with_next_id"] = self.overlap_with_next_id

        if self.related_to:
            d["related_to"] = self.related_to
        if self.relationship_types:
            d["relationship_types"] = [r.value for r in self.relationship_types]

        d["storage_backend"] = self.storage_backend
        d["index_status"] = self.index_status.value
        if self.retention_policy_id is not None:
            d["retention_policy_id"] = self.retention_policy_id

        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "KnowledgeObject":
        obj = cls()
        obj.id = d.get("id", str(uuid.uuid7()))
        obj.version = d.get("version", 1)
        obj.type = KnowledgeType(d.get("type", "document"))

        obj.source_id = d.get("source_id", "")
        obj.source_url = d.get("source_url")
        obj.source_type = SourceType(d.get("source_type", "web_page"))

        obj.acquired_at = d.get("acquired_at", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        obj.published_at = d.get("published_at")
        obj.updated_at = d.get("updated_at", obj.acquired_at)

        obj.markdown = d.get("markdown")
        obj.structured_data = d.get("structured_data")
        obj.raw_content_hash = d.get("raw_content_hash", "")
        obj.content_hash = d.get("content_hash", "")

        obj.title = d.get("title")
        obj.authors = d.get("authors", [])
        obj.language = d.get("language")
        obj.topics = d.get("topics", [])
        obj.word_count = d.get("word_count", 0)

        obj.confidence = d.get("confidence", 0.0)
        obj.evidence_count = d.get("evidence_count", 0)

        raw_citations = d.get("citations", [])
        if raw_citations:
            citations = []
            for c in raw_citations:
                citation_type = c.get("citation_type", "reference")
                if not isinstance(citation_type, CitationType):
                    citation_type = CitationType(citation_type)
                citations.append(Citation(
                    target_id=c.get("target_id"),
                    target_url=c.get("target_url"),
                    context=c.get("context"),
                    citation_type=citation_type,
                    start_seconds=c.get("start_seconds"),
                    end_seconds=c.get("end_seconds"),
                    segment_id=c.get("segment_id"),
                    quote=c.get("quote"),
                    speaker=c.get("speaker"),
                    speaker_confidence=c.get("speaker_confidence"),
                    transcript_confidence=c.get("transcript_confidence"),
                    surrounding_context=c.get("surrounding_context"),
                    metadata=c.get("metadata", {}),
                ))
            obj.citations = citations

        raw_chain = d.get("acquisition_chain", [])
        if raw_chain:
            obj.acquisition_chain = [
                AcquisitionRecord(
                    provider_name=a.get("provider_name", ""),
                    provider_type=ProviderType(a.get("provider_type", "crawler")),
                    request_id=a.get("request_id", ""),
                    timestamp=a.get("timestamp", ""),
                    status=AcquisitionStatus(a.get("status", "success")),
                    response_size_bytes=a.get("response_size_bytes"),
                    latency_ms=a.get("latency_ms"),
                    error_message=a.get("error_message"),
                )
                for a in raw_chain
            ]

        obj.parent_id = d.get("parent_id")
        obj.chunk_index = d.get("chunk_index")
        obj.chunk_total = d.get("chunk_total")
        obj.overlap_with_next_id = d.get("overlap_with_next_id")

        obj.related_to = d.get("related_to", [])
        raw_rel_types = d.get("relationship_types", [])
        if raw_rel_types:
            obj.relationship_types = [RelationshipType(r) for r in raw_rel_types]

        obj.storage_backend = d.get("storage_backend", "primary-store-01")
        obj.index_status = IndexStatus(d.get("index_status", "pending"))
        obj.retention_policy_id = d.get("retention_policy_id")

        return obj
