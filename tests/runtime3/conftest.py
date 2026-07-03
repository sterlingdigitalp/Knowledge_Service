"""Fixtures for Runtime 3 tests."""

from __future__ import annotations

from knowledge_service.runtime3.models import SegmentType, TranscriptSegment


def make_segment(
    text: str,
    *,
    segment_type: SegmentType = SegmentType.DISCUSSION,
    podcast: str = "Test Podcast",
    episode_id: str = "ep-1",
) -> TranscriptSegment:
    return TranscriptSegment(
        segment_id="seg-1",
        text=text,
        speaker="Host",
        start_seconds=60.0,
        end_seconds=90.0,
        segment_type=segment_type,
        confidence=0.8,
        episode_id=episode_id,
        podcast_name=podcast,
        source_url="https://example.com/ep",
    )