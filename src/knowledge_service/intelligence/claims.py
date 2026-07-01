"""Claim extraction for the Personal Intelligence Analyst."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from ..retrieval.embedding import embed_text, tokenize
from .models import content_hash, now_iso, stable_id
from .state import FileStateStore


CLAIMS_FILE = "claims.jsonl"

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")

CLAIM_VERBS = {
    "is", "are", "was", "were", "will", "would", "can", "could", "should", "must",
    "has", "have", "had", "gets", "becomes", "means", "suggests", "shows", "expects",
    "thinks", "believes", "says", "argues", "predicts", "matters", "changes", "improves",
    "struggles", "solves", "loses", "gains", "raises", "blocks", "reduces", "increases",
}

STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "have", "has", "had", "are",
    "was", "were", "will", "would", "could", "should", "you", "your", "they", "their",
    "about", "into", "there", "what", "when", "where", "which", "because", "while", "like",
    "just", "than", "then", "them", "these", "those", "been", "being", "also", "very",
}


@dataclass
class IntelligenceClaim:
    claim_id: str
    claim_text: str
    event_id: str
    profile_id: str
    source_id: str
    source_name: str
    speaker: str = "unknown"
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    timestamped_source_url: Optional[str] = None
    transcript_reference: Dict[str, Any] = field(default_factory=dict)
    evidence: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    topic: str = "general"
    entities: List[str] = field(default_factory=list)
    supporting_context: str = ""
    route_confidence: Optional[float] = None
    acquisition_route: Optional[str] = None
    extracted_at: str = field(default_factory=now_iso)
    embedding: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "event_id": self.event_id,
            "profile_id": self.profile_id,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "speaker": self.speaker,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "timestamped_source_url": self.timestamped_source_url,
            "transcript_reference": dict(self.transcript_reference),
            "evidence": dict(self.evidence),
            "confidence": self.confidence,
            "topic": self.topic,
            "entities": list(self.entities),
            "supporting_context": self.supporting_context,
            "route_confidence": self.route_confidence,
            "acquisition_route": self.acquisition_route,
            "extracted_at": self.extracted_at,
            "embedding": list(self.embedding),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntelligenceClaim":
        return cls(
            claim_id=str(data.get("claim_id") or ""),
            claim_text=str(data.get("claim_text") or ""),
            event_id=str(data.get("event_id") or ""),
            profile_id=str(data.get("profile_id") or ""),
            source_id=str(data.get("source_id") or ""),
            source_name=str(data.get("source_name") or ""),
            speaker=str(data.get("speaker") or "unknown"),
            timestamp_start=data.get("timestamp_start"),
            timestamp_end=data.get("timestamp_end"),
            timestamped_source_url=data.get("timestamped_source_url"),
            transcript_reference=dict(data.get("transcript_reference") or {}),
            evidence=dict(data.get("evidence") or {}),
            confidence=float(data.get("confidence", 0.0)),
            topic=str(data.get("topic") or "general"),
            entities=list(data.get("entities") or []),
            supporting_context=str(data.get("supporting_context") or ""),
            route_confidence=data.get("route_confidence"),
            acquisition_route=data.get("acquisition_route"),
            extracted_at=str(data.get("extracted_at") or now_iso()),
            embedding=list(data.get("embedding") or []),
        )


class ClaimExtractor:
    def __init__(self, state: FileStateStore):
        self.state = state

    def extract(self, knowledge_objects: Optional[List[Dict[str, Any]]] = None) -> List[IntelligenceClaim]:
        objects = knowledge_objects if knowledge_objects is not None else self.state.read_jsonl("knowledge_objects.jsonl")
        claims: List[IntelligenceClaim] = []
        seen: set[str] = set()
        for obj in objects:
            if obj.get("type") != "chunk":
                continue
            metadata = ((obj.get("structured_data") or {}).get("metadata") or {})
            event_id = metadata.get("event_id") or metadata.get("episode_id")
            if not event_id:
                continue
            for index, sentence in enumerate(_candidate_sentences(obj.get("markdown") or "")):
                if not _looks_like_claim(sentence):
                    continue
                claim_id = stable_id(event_id, obj.get("id"), index, _normalize_claim(sentence))
                if claim_id in seen:
                    continue
                seen.add(claim_id)
                citation = (obj.get("citations") or [{}])[0] if obj.get("citations") else {}
                structured = obj.get("structured_data") or {}
                claim = IntelligenceClaim(
                    claim_id=claim_id,
                    claim_text=sentence,
                    event_id=event_id,
                    profile_id=metadata.get("profile_id", ""),
                    source_id=metadata.get("source_id", ""),
                    source_name=metadata.get("venue") or metadata.get("podcast_name") or metadata.get("show") or "",
                    speaker=structured.get("speaker") or citation.get("speaker") or "unknown",
                    timestamp_start=structured.get("timestamp_start") or citation.get("start_seconds"),
                    timestamp_end=structured.get("timestamp_end") or citation.get("end_seconds"),
                    timestamped_source_url=structured.get("timestamped_source_url") or citation.get("target_url") or obj.get("source_url"),
                    transcript_reference={
                        "knowledge_object_id": obj.get("id"),
                        "chunk_id": obj.get("id"),
                        "source_url": obj.get("source_url"),
                        "content_hash": obj.get("content_hash"),
                    },
                    evidence={
                        "quote": sentence,
                        "citation_quote": citation.get("quote"),
                        "citation_context": citation.get("context"),
                        "timestamped_source_url": structured.get("timestamped_source_url") or citation.get("target_url") or obj.get("source_url"),
                    },
                    confidence=_claim_confidence(obj, citation, metadata),
                    topic=_topic_for(sentence),
                    entities=_entities_for(sentence, metadata),
                    supporting_context=structured.get("surrounding_context") or citation.get("surrounding_context") or citation.get("context") or "",
                    route_confidence=metadata.get("route_confidence"),
                    acquisition_route=metadata.get("acquisition_route"),
                    embedding=embed_text(sentence),
                )
                claims.append(claim)
        self.state.write_jsonl(CLAIMS_FILE, [claim.to_dict() for claim in claims])
        self.state.write_json("claim_index.json", _claim_index(claims))
        return claims

    def load(self) -> List[IntelligenceClaim]:
        return [IntelligenceClaim.from_dict(row) for row in self.state.read_jsonl(CLAIMS_FILE)]


def _candidate_sentences(text: str) -> Iterable[str]:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return []
    parts: List[str] = []
    for paragraph in cleaned.split("\n"):
        parts.extend(SENTENCE_RE.split(paragraph))
    output = []
    for part in parts:
        sentence = part.strip(" -\t\n")
        if 45 <= len(sentence) <= 420:
            output.append(sentence)
    return output


def _looks_like_claim(sentence: str) -> bool:
    tokens = tokenize(sentence)
    if len(tokens) < 8:
        return False
    if not any(token in CLAIM_VERBS for token in tokens):
        return False
    return len([token for token in tokens if token not in STOPWORDS]) >= 4


def _normalize_claim(text: str) -> str:
    return " ".join(token for token in tokenize(text) if token not in STOPWORDS)


def _topic_for(text: str) -> str:
    tokens = [token for token in tokenize(text) if token not in STOPWORDS]
    priority = [
        "ai", "agents", "inference", "datacenter", "datacenters", "compute", "math", "coding",
        "markets", "investing", "china", "founder", "business", "muscle", "glp", "longevity",
        "health", "weight", "model", "enterprise", "tariff", "geometry", "combinatorics",
    ]
    for token in priority:
        if token in tokens:
            return token
    return tokens[0] if tokens else "general"


def _entities_for(text: str, metadata: Dict[str, Any]) -> List[str]:
    entities = set(metadata.get("participants") or metadata.get("matched_watch_entries") or [])
    for match in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b", text):
        if match.lower() not in {"I", "The", "And", "But", "So"}:
            entities.add(match)
    return sorted(entities)[:12]


def _claim_confidence(obj: Dict[str, Any], citation: Dict[str, Any], metadata: Dict[str, Any]) -> float:
    base = float(obj.get("confidence", 0.75) or 0.75)
    transcript_confidence = citation.get("transcript_confidence") or metadata.get("transcript_confidence") or 0.8
    route_confidence = metadata.get("route_confidence") if metadata.get("route_confidence") is not None else 0.75
    evidence_bonus = 0.05 if citation else 0.0
    return round(min(1.0, (base * 0.4) + (float(transcript_confidence) * 0.3) + (float(route_confidence) * 0.3) + evidence_bonus), 4)


def _claim_index(claims: List[IntelligenceClaim]) -> Dict[str, Any]:
    by_event: Dict[str, int] = {}
    by_topic: Dict[str, int] = {}
    for claim in claims:
        by_event[claim.event_id] = by_event.get(claim.event_id, 0) + 1
        by_topic[claim.topic] = by_topic.get(claim.topic, 0) + 1
    return {
        "claim_count": len(claims),
        "by_event": by_event,
        "by_topic": by_topic,
        "content_hash": content_hash("\n".join(claim.claim_id for claim in claims)),
        "generated_at": now_iso(),
    }
