"""Detect where stories begin and end in transcripts."""

from __future__ import annotations

import re
from typing import List, Sequence

from ...intelligence.models import stable_id
from ..models import SegmentType, TranscriptSegment
from ..thinking.models import StoryBoundary
from .patterns import classify_segment_text

TOPIC_SHIFT_PATTERNS = [
    re.compile(r"^(?:moving on|let's talk about|switching gears|another topic|before we go)", re.I),
    re.compile(r"^(?:so|now),?\s+(?:let's|i want to)", re.I),
    re.compile(r"^the (?:next|other|bigger) (?:question|topic|thing)", re.I),
]

STORY_START_PATTERNS = [
    re.compile(r"\bannounced\b", re.I),
    re.compile(r"\bbreaking\b", re.I),
    re.compile(r"\bjust (?:released|launched|published)\b", re.I),
    re.compile(r"\baccording to\b", re.I),
    re.compile(r"\bnew (?:report|study|paper)\b", re.I),
]


class StoryBoundaryDetector:
    """Identify narrative boundaries within classified segments."""

    def detect(self, segments: Sequence[TranscriptSegment]) -> List[StoryBoundary]:
        if not segments:
            return []

        substantive = [
            segment for segment in segments
            if segment.segment_type not in {
                SegmentType.SPONSOR, SegmentType.ADVERTISEMENT,
                SegmentType.INTRO, SegmentType.OUTRO,
                SegmentType.HOUSEKEEPING, SegmentType.META_REQUEST,
            }
        ]
        if not substantive:
            return []

        boundaries: List[StoryBoundary] = []
        current_start = substantive[0]
        current_segments = [current_start.segment_id]

        for index in range(1, len(substantive)):
            segment = substantive[index]
            prior = substantive[index - 1]
            if self._is_topic_shift(prior, segment):
                boundaries.append(self._make_boundary(
                    current_start, prior, current_segments, "story_arc",
                ))
                boundaries.append(self._make_boundary(
                    segment, segment, [segment.segment_id], "story_start",
                ))
                current_start = segment
                current_segments = [segment.segment_id]
            else:
                current_segments.append(segment.segment_id)

        boundaries.append(self._make_boundary(
            current_start, substantive[-1], current_segments, "story_arc",
        ))
        return boundaries

    def _is_topic_shift(self, prior: TranscriptSegment, current: TranscriptSegment) -> bool:
        text = current.text.strip()
        if any(pattern.search(text[:120]) for pattern in TOPIC_SHIFT_PATTERNS):
            return True
        if any(pattern.search(text) for pattern in STORY_START_PATTERNS):
            if prior.podcast_name == current.podcast_name:
                gap = (current.start_seconds or 0) - (prior.end_seconds or prior.start_seconds or 0)
                if gap > 120:
                    return True
        return False

    def _make_boundary(
        self,
        start: TranscriptSegment,
        end: TranscriptSegment,
        segment_ids: List[str],
        boundary_type: str,
    ) -> StoryBoundary:
        label = start.text[:80] + ("…" if len(start.text) > 80 else "")
        return StoryBoundary(
            boundary_id=stable_id("boundary", start.episode_id, start.segment_id, boundary_type),
            episode_id=start.episode_id,
            start_seconds=float(start.start_seconds or 0),
            end_seconds=float(end.end_seconds or end.start_seconds or 0),
            boundary_type=boundary_type,
            segment_ids=list(segment_ids),
            confidence=0.72,
            label=label,
        )


def enrich_segments(segments: Sequence[TranscriptSegment]) -> list:
    """Add rich segment classification."""
    from ..thinking.models import EnrichedSegment, NON_SUBSTANTIVE_SEGMENTS, RichSegmentType

    RICH_MAP = {
        SegmentType.SPONSOR: RichSegmentType.SPONSOR,
        SegmentType.ADVERTISEMENT: RichSegmentType.ADVERTISEMENT,
        SegmentType.INTRO: RichSegmentType.INTRO,
        SegmentType.OUTRO: RichSegmentType.OUTRO,
        SegmentType.HOUSEKEEPING: RichSegmentType.HOUSEKEEPING,
        SegmentType.META_REQUEST: RichSegmentType.META_DISCUSSION,
        SegmentType.HOST_BANTER: RichSegmentType.META_DISCUSSION,
        SegmentType.INTERVIEW: RichSegmentType.INTERVIEW,
        SegmentType.QA: RichSegmentType.QA,
        SegmentType.NEWS: RichSegmentType.NEWS,
        SegmentType.DISCUSSION: RichSegmentType.DISCUSSION,
        SegmentType.UNKNOWN: RichSegmentType.UNKNOWN,
    }

    total = len(segments)
    enriched = []
    for index, segment in enumerate(segments):
        position_ratio = index / max(total - 1, 1)
        rich_type, confidence = _classify_rich(segment.text, position_ratio)
        if segment.segment_type in {SegmentType.SPONSOR, SegmentType.ADVERTISEMENT}:
            rich_type = RichSegmentType.SPONSOR if segment.segment_type == SegmentType.SPONSOR else RichSegmentType.ADVERTISEMENT

        enriched.append(EnrichedSegment(
            segment_id=segment.segment_id,
            text=segment.text,
            speaker=segment.speaker,
            start_seconds=segment.start_seconds,
            end_seconds=segment.end_seconds,
            segment_type=segment.segment_type,
            confidence=max(segment.confidence, confidence),
            episode_id=segment.episode_id,
            podcast_name=segment.podcast_name,
            source_url=segment.source_url,
            knowledge_object_id=segment.knowledge_object_id,
            rich_type=rich_type.value,
            is_substantive=rich_type not in NON_SUBSTANTIVE_SEGMENTS,
            topic_label=_topic_label(segment.text),
        ))
    return enriched


def _classify_rich(text: str, position_ratio: float) -> tuple:
    from ..thinking.models import RichSegmentType

    lower = text.lower()
    if re.search(r"\b(?:i think|in my view|arguably|seems to me)\b", lower):
        return RichSegmentType.OPINION, 0.75
    if re.search(r"\b(?:will |going to |expect |predict |forecast )\b", lower):
        return RichSegmentType.PREDICTION, 0.78
    if re.search(r"\b(?:might |could |maybe |perhaps |speculat)\b", lower):
        return RichSegmentType.SPECULATION, 0.70
    if re.search(r"\b(?:research|study|paper|peer.review|scientists? found)\b", lower):
        return RichSegmentType.RESEARCH, 0.80
    if re.search(r"\b(?:historically|in \d{3,4}|back in|century|empire|ancient)\b", lower):
        return RichSegmentType.HISTORICAL_CONTEXT, 0.75
    if re.search(r"\b(?:background|context|for those who don't know)\b", lower):
        return RichSegmentType.BACKGROUND, 0.72
    if re.search(r"\b(?:debate|argued|disagree|controversy|on the other hand)\b", lower):
        return RichSegmentType.DEBATE, 0.76
    base_type, conf = classify_segment_text(text, position_ratio=position_ratio)
    mapping = {
        "news": RichSegmentType.NEWS,
        "discussion": RichSegmentType.DISCUSSION,
        "interview": RichSegmentType.INTERVIEW,
        "qa": RichSegmentType.QA,
        "sponsor": RichSegmentType.SPONSOR,
        "advertisement": RichSegmentType.ADVERTISEMENT,
        "intro": RichSegmentType.INTRO,
        "outro": RichSegmentType.OUTRO,
        "housekeeping": RichSegmentType.HOUSEKEEPING,
        "meta_request": RichSegmentType.META_DISCUSSION,
        "host_banter": RichSegmentType.META_DISCUSSION,
    }
    return mapping.get(base_type.value, RichSegmentType.UNKNOWN), conf


def _topic_label(text: str) -> str:
    words = [word for word in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", text)]
    return words[0] if words else ""