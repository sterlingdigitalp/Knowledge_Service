"""Claim Extraction Engine — atomic claims from transcript segments."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ...intelligence.models import IntelligenceProfile
from ...processing.transcript import format_timestamp, timestamped_source_url
from ...retrieval.embedding import embed_text
from ..models import Claim


SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'])")
FILLER_RE = re.compile(
    r"^(?:um+|uh+|yeah|yes|no|okay|ok|right|so|well|like|you know|i mean|sort of|kind of)[\s.,!]*$",
    re.IGNORECASE,
)
ENTITY_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b")
MIN_CLAIM_CHARS = 35


class ClaimExtractor:
    """Extract atomic claims from processed transcript knowledge objects."""

    def extract_from_episode(
        self,
        document: Dict[str, Any],
        episode_meta: Dict[str, Any],
        profiles: Sequence[IntelligenceProfile],
    ) -> List[Claim]:
        structured = document.get("structured_data") or {}
        segments = structured.get("transcript_segments") or []
        if not segments:
            return []

        metadata = structured.get("metadata") or {}
        source_url = document.get("source_url") or metadata.get("source_url") or ""
        profile_id = metadata.get("profile_id") or episode_meta.get("profile_id") or ""
        episode_id = metadata.get("episode_id") or episode_meta.get("episode_id") or ""
        participants = list(metadata.get("participants") or episode_meta.get("matched_watch_entries") or [])
        route_confidence = metadata.get("route_confidence") or episode_meta.get("route_confidence")
        podcast_name = metadata.get("podcast_name") or episode_meta.get("podcast_name") or structured.get("show") or ""
        published_at = document.get("published_at") or structured.get("episode_date") or ""

        all_interests = _collect_interests(profiles)
        all_watch_names = _collect_watch_names(profiles)

        claims: List[Claim] = []
        for index, segment in enumerate(segments):
            context = _surrounding_context(segments, index)
            for sentence in _atomic_sentences(segment.get("text") or ""):
                if len(sentence) < MIN_CLAIM_CHARS or FILLER_RE.match(sentence.strip()):
                    continue
                speaker = str(segment.get("speaker") or "unknown")
                start = segment.get("start_seconds")
                end = segment.get("end_seconds")
                label = format_timestamp(start) if start is not None else ""
                entities = _extract_entities(sentence, all_watch_names)
                topic = _infer_topic(sentence, all_interests, entities)
                confidence = _claim_confidence(segment, sentence)
                timestamp_url = timestamped_source_url(source_url, start) or source_url

                claims.append(Claim(
                    claim_text=sentence.strip(),
                    speaker=speaker,
                    timestamp_start=start,
                    timestamp_end=end,
                    timestamp_label=label,
                    transcript_reference=timestamp_url,
                    evidence=sentence.strip(),
                    confidence=confidence,
                    topic=topic,
                    entities=entities,
                    supporting_context=context,
                    episode_id=episode_id,
                    event_id=episode_id,
                    profile_id=profile_id,
                    source_id=metadata.get("source_id") or episode_meta.get("source_id") or "",
                    source_url=source_url,
                    podcast_name=podcast_name,
                    participants=participants,
                    route_confidence=route_confidence,
                    segment_id=str(segment.get("segment_id") or f"seg-{index}"),
                    knowledge_object_id=document.get("id") or "",
                    published_at=published_at,
                    embedding=embed_text(sentence),
                ))
        return claims

    def extract_from_corpus(
        self,
        knowledge_objects: List[Dict[str, Any]],
        episodes: List[Dict[str, Any]],
        profiles: Sequence[IntelligenceProfile],
    ) -> List[Claim]:
        episode_index = {episode.get("episode_id"): episode for episode in episodes}
        documents = [obj for obj in knowledge_objects if obj.get("type") == "document"]
        claims: List[Claim] = []
        for document in documents:
            metadata = (document.get("structured_data") or {}).get("metadata") or {}
            episode_id = metadata.get("episode_id")
            episode_meta = episode_index.get(episode_id, {})
            claims.extend(self.extract_from_episode(document, episode_meta, profiles))
        return claims


def _atomic_sentences(text: str) -> List[str]:
    text = " ".join((text or "").split())
    if not text:
        return []
    parts = SENTENCE_SPLIT_RE.split(text)
    return [part.strip() for part in parts if part.strip()]


def _surrounding_context(segments: List[Dict[str, Any]], index: int, window: int = 1) -> str:
    start = max(0, index - window)
    end = min(len(segments), index + window + 1)
    lines = []
    for segment in segments[start:end]:
        speaker = segment.get("speaker") or "unknown"
        snippet = (segment.get("text") or "").strip()
        if snippet:
            lines.append(f"{speaker}: {snippet}")
    return "\n".join(lines)


def _collect_interests(profiles: Sequence[IntelligenceProfile]) -> List[str]:
    interests: List[str] = []
    for profile in profiles:
        interests.extend(profile.interests)
    return list(dict.fromkeys(interests))


def _collect_watch_names(profiles: Sequence[IntelligenceProfile]) -> List[str]:
    names: List[str] = []
    for profile in profiles:
        for entry in profile.watch_list:
            names.extend(entry.names())
    return list(dict.fromkeys(names))


def _extract_entities(text: str, watch_names: Sequence[str]) -> List[str]:
    entities: List[str] = []
    lower = text.lower()
    for name in watch_names:
        if name.lower() in lower:
            entities.append(name)
    for match in ENTITY_RE.findall(text):
        if match not in entities and len(match) > 3:
            entities.append(match)
    return entities[:8]


def _infer_topic(text: str, interests: Sequence[str], entities: Sequence[str]) -> str:
    lower = text.lower()
    for interest in interests:
        if interest.lower() in lower:
            return interest
    if entities:
        return entities[0]
    return "general"


def _claim_confidence(segment: Dict[str, Any], sentence: str) -> float:
    speaker_conf = float(segment.get("speaker_confidence") or 0.7)
    transcript_conf = float(segment.get("transcript_confidence") or 0.75)
    length_factor = min(1.0, len(sentence) / 120.0)
    return round(min(0.99, 0.45 + 0.25 * speaker_conf + 0.2 * transcript_conf + 0.1 * length_factor), 3)