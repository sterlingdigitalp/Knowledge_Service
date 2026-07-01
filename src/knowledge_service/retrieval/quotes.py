"""Timestamped transcript quote retrieval API."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..knowledge_object import KnowledgeObject, SourceType
from .embedding import cosine_similarity, embed_text, tokenize
from .interfaces import KnowledgeQuery
from .retriever import KnowledgeRetrieverImpl


@dataclass
class CitationResult:
    quote: str
    speaker: str
    speaker_confidence: float
    transcript_confidence: float
    show: Optional[str]
    episode: Optional[str]
    episode_date: Optional[str]
    timestamp_start: Optional[float]
    timestamp_end: Optional[float]
    timestamped_source_url: Optional[str]
    surrounding_context: str
    relevance_score: float
    source_url: Optional[str] = None
    transcript_id: Optional[str] = None
    chunk_id: Optional[str] = None
    confidence_metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quote": self.quote,
            "speaker": self.speaker,
            "speaker_confidence": self.speaker_confidence,
            "transcript_confidence": self.transcript_confidence,
            "show": self.show,
            "episode": self.episode,
            "episode_date": self.episode_date,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "timestamped_source_url": self.timestamped_source_url,
            "surrounding_context": self.surrounding_context,
            "relevance_score": self.relevance_score,
            "source_url": self.source_url,
            "transcript_id": self.transcript_id,
            "chunk_id": self.chunk_id,
            "confidence_metadata": self.confidence_metadata or {},
        }


def search_quotes(
    retriever: KnowledgeRetrieverImpl,
    query: str,
    speaker: Optional[str] = None,
    date_range: Optional[Tuple[str, str]] = None,
    show: Optional[str] = None,
    limit: int = 10,
) -> List[CitationResult]:
    """Search transcript chunks for verbatim timestamped quotes.

    Speaker filtering is a hard filter. Ranking combines deterministic semantic
    relevance, recency, and transcript/speaker confidence.
    """
    kquery = KnowledgeQuery(
        object_types=["chunk"],
        limit=100000,
        include_timing=False,
    )
    if date_range:
        kquery.acquired_after = date_range[0]
        kquery.acquired_before = date_range[1]

    retrieved = retriever.retrieve_query(kquery)
    candidates = [obj for obj in retrieved.objects if isinstance(obj, KnowledgeObject)]
    query_embedding = embed_text(query)
    normalized_speaker = _normalize(speaker)
    normalized_show = _normalize(show)

    results: List[CitationResult] = []
    for chunk in candidates:
        if chunk.source_type != SourceType.VIDEO_TRANSCRIPT:
            continue
        data = chunk.structured_data or {}
        metadata = data.get("metadata", {}) or {}
        chunk_speaker = data.get("speaker") or _first_citation_value(chunk, "speaker") or "unknown"
        if normalized_speaker and _normalize(chunk_speaker) != normalized_speaker:
            continue
        chunk_show = metadata.get("show")
        if normalized_show and _normalize(chunk_show) != normalized_show:
            continue
        episode_date = metadata.get("episode_date") or chunk.published_at
        if date_range and not _date_in_range(episode_date or chunk.acquired_at, date_range):
            continue

        quote = _quote_text(chunk)
        if not quote:
            continue
        embedding = data.get("embedding") or embed_text(quote)
        semantic_score = max(0.0, cosine_similarity(query_embedding, embedding))
        lexical_score = _lexical_score(query, quote)
        confidence_score = _confidence_score(chunk, data)
        recency_score = _recency_score(episode_date or chunk.acquired_at)
        relevance = round(
            (semantic_score * 0.45)
            + (lexical_score * 0.35)
            + (recency_score * 0.10)
            + (confidence_score * 0.10),
            6,
        )

        results.append(CitationResult(
            quote=quote,
            speaker=chunk_speaker,
            speaker_confidence=float(data.get("speaker_confidence", _first_citation_value(chunk, "speaker_confidence") or 0.0)),
            transcript_confidence=float(data.get("transcript_confidence", _first_citation_value(chunk, "transcript_confidence") or chunk.confidence)),
            show=chunk_show,
            episode=metadata.get("episode"),
            episode_date=episode_date,
            timestamp_start=data.get("timestamp_start"),
            timestamp_end=data.get("timestamp_end"),
            timestamped_source_url=data.get("timestamped_source_url") or _first_citation_value(chunk, "target_url"),
            surrounding_context=data.get("surrounding_context") or _first_citation_value(chunk, "surrounding_context") or quote,
            relevance_score=relevance,
            source_url=chunk.source_url,
            transcript_id=data.get("transcript_id") or metadata.get("transcript_id"),
            chunk_id=chunk.id,
            confidence_metadata={
                "semantic_score": round(semantic_score, 6),
                "lexical_score": round(lexical_score, 6),
                "recency_score": round(recency_score, 6),
                "confidence_score": round(confidence_score, 6),
                "chunk_confidence": chunk.confidence,
                "speaker_confidence": data.get("speaker_confidence"),
                "transcript_confidence": data.get("transcript_confidence"),
            },
        ))

    results.sort(key=lambda result: result.relevance_score, reverse=True)
    return results[:limit]


def _quote_text(chunk: KnowledgeObject) -> str:
    if chunk.citations and chunk.citations[0].quote:
        return chunk.citations[0].quote
    return chunk.markdown or ""


def _first_citation_value(chunk: KnowledgeObject, field: str) -> Any:
    if not chunk.citations:
        return None
    return getattr(chunk.citations[0], field, None)


def _confidence_score(chunk: KnowledgeObject, data: Dict[str, Any]) -> float:
    speaker_confidence = float(data.get("speaker_confidence", 0.0) or 0.0)
    transcript_confidence = float(data.get("transcript_confidence", chunk.confidence) or chunk.confidence)
    return max(0.0, min(1.0, (speaker_confidence + transcript_confidence + chunk.confidence) / 3.0))


def _lexical_score(query: str, quote: str) -> float:
    query_tokens = set(tokenize(query))
    if not query_tokens:
        return 0.0
    quote_tokens = set(tokenize(quote))
    if not quote_tokens:
        return 0.0
    overlap = len(query_tokens & quote_tokens) / len(query_tokens)
    normalized_query = " ".join(tokenize(query))
    normalized_quote = " ".join(tokenize(quote))
    phrase_bonus = 0.25 if normalized_query and normalized_query in normalized_quote else 0.0
    return max(0.0, min(1.0, overlap + phrase_bonus))


def _recency_score(date_value: Optional[str]) -> float:
    if not date_value:
        return 0.0
    try:
        normalized = date_value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return 0.0
    age_days = max(0, (datetime.now(timezone.utc) - dt).days)
    return 1.0 / (1.0 + (age_days / 365.0))


def _date_in_range(date_value: str, date_range: Tuple[str, str]) -> bool:
    return date_range[0] <= date_value <= date_range[1]


def _normalize(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return " ".join(value.lower().split())
