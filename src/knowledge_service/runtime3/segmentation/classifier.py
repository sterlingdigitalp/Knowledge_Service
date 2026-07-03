"""Agent A — semantic transcript segmentation."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from ...processing.transcript import format_timestamp
from ..models import TranscriptSegment
from .patterns import classify_segment_text


class SegmentClassifier:
    """Classify raw transcript segments into semantic segment types."""

    def classify_episode(
        self,
        document: Dict[str, Any],
        episode_meta: Dict[str, Any],
    ) -> List[TranscriptSegment]:
        structured = document.get("structured_data") or {}
        raw_segments = structured.get("transcript_segments") or []
        if not raw_segments:
            return []

        metadata = structured.get("metadata") or {}
        episode_id = metadata.get("episode_id") or episode_meta.get("episode_id") or ""
        podcast_name = (
            metadata.get("podcast_name")
            or episode_meta.get("podcast_name")
            or structured.get("show")
            or ""
        )
        source_url = document.get("source_url") or metadata.get("source_url") or ""
        knowledge_object_id = document.get("id") or ""
        total = len(raw_segments)

        classified: List[TranscriptSegment] = []
        for index, segment in enumerate(raw_segments):
            text = segment.get("text") or segment.get("raw_text") or ""
            position_ratio = index / max(total - 1, 1)
            segment_type, confidence = classify_segment_text(text, position_ratio=position_ratio)
            start = segment.get("start_seconds")
            classified.append(TranscriptSegment(
                segment_id=str(segment.get("segment_id") or f"seg-{index}"),
                text=text.strip(),
                speaker=str(segment.get("speaker") or "unknown"),
                start_seconds=start,
                end_seconds=segment.get("end_seconds"),
                segment_type=segment_type,
                confidence=confidence,
                episode_id=episode_id,
                podcast_name=podcast_name,
                source_url=source_url,
                knowledge_object_id=knowledge_object_id,
            ))
        return classified

    def classify_corpus(
        self,
        knowledge_objects: Sequence[Dict[str, Any]],
        episodes: Sequence[Dict[str, Any]],
        *,
        episode_ids: Sequence[str] | None = None,
    ) -> List[TranscriptSegment]:
        episode_index = {episode.get("episode_id"): episode for episode in episodes}
        allowed = set(episode_ids) if episode_ids else None
        segments: List[TranscriptSegment] = []
        for document in knowledge_objects:
            if document.get("type") != "document":
                continue
            metadata = (document.get("structured_data") or {}).get("metadata") or {}
            episode_id = metadata.get("episode_id")
            if allowed and episode_id not in allowed:
                continue
            episode_meta = episode_index.get(episode_id, {})
            segments.extend(self.classify_episode(document, episode_meta))
        return segments

    @staticmethod
    def timestamp_label(segment: TranscriptSegment) -> str:
        if segment.start_seconds is not None:
            return format_timestamp(segment.start_seconds)
        return ""