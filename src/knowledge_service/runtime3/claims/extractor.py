"""Agent B — improved claim extraction with segment-aware filtering."""

from __future__ import annotations

import re
from typing import List, Sequence

from ...processing.transcript import format_timestamp, timestamped_source_url
from ...retrieval.embedding import embed_text
from ..config import Runtime3Config
from ..models import (
    NON_NEWS_SEGMENT_TYPES,
    ClaimType,
    SegmentType,
    SemanticClaim,
    TranscriptSegment,
)
from ..segmentation.patterns import (
    META_REQUEST_PATTERNS,
    OUTRO_PATTERNS,
    SPONSOR_PATTERNS,
)

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")
FILLER_RE = re.compile(
    r"^(?:um+|uh+|yeah|yes|no|okay|ok|right|so|well|like|you know|i mean|sort of|kind of)[\s.,!]*$",
    re.IGNORECASE,
)
PODCAST_METADATA_RE = re.compile(
    r"^(?:follow|subscribe|rate|review|share|check out|visit|go to)\b",
    re.IGNORECASE,
)


class SemanticClaimExtractor:
    """Extract substantive claims from classified transcript segments."""

    def __init__(self, config: Runtime3Config | None = None):
        self.config = config or Runtime3Config()

    def extract_from_segments(self, segments: Sequence[TranscriptSegment]) -> List[SemanticClaim]:
        claims: List[SemanticClaim] = []
        segment_list = list(segments)
        for index, segment in enumerate(segment_list):
            if self._should_skip_segment(segment):
                continue
            context = self._surrounding_context(segment_list, index)
            for sentence in self._atomic_sentences(segment.text):
                if not self._is_valid_claim_sentence(sentence, segment.segment_type):
                    continue
                claim_type = self._infer_claim_type(sentence, segment.segment_type)
                confidence = self._claim_confidence(segment, sentence, claim_type)
                timestamp_url = timestamped_source_url(segment.source_url, segment.start_seconds) or segment.source_url
                claims.append(SemanticClaim(
                    claim_id="",
                    claim_text=sentence.strip(),
                    claim_type=claim_type,
                    confidence=confidence,
                    segment_type=segment.segment_type,
                    speaker=segment.speaker,
                    entities=[],
                    resolved_entity_ids=[],
                    event_references=[],
                    supporting_sentences=[sentence.strip()],
                    episode_id=segment.episode_id,
                    podcast_name=segment.podcast_name,
                    source_url=timestamp_url,
                    timestamp_start=segment.start_seconds,
                    timestamp_label=format_timestamp(segment.start_seconds) if segment.start_seconds is not None else "",
                    segment_id=segment.segment_id,
                    embedding=embed_text(sentence),
                ))
                if context and len(context) > len(sentence):
                    claims[-1].supporting_sentences = [context]
        return claims

    def _should_skip_segment(self, segment: TranscriptSegment) -> bool:
        if self.config.reject_non_news_segments and segment.segment_type in NON_NEWS_SEGMENT_TYPES:
            return True
        if segment.segment_type in {SegmentType.SPONSOR, SegmentType.ADVERTISEMENT}:
            return True
        return False

    def _is_valid_claim_sentence(self, sentence: str, segment_type: SegmentType) -> bool:
        text = sentence.strip()
        if len(text) < self.config.min_claim_chars:
            return False
        if FILLER_RE.match(text):
            return False
        if PODCAST_METADATA_RE.match(text):
            return False
        if any(pattern.search(text) for pattern in SPONSOR_PATTERNS):
            return False
        if any(pattern.search(text) for pattern in META_REQUEST_PATTERNS):
            return False
        if segment_type == SegmentType.OUTRO and any(pattern.search(text) for pattern in OUTRO_PATTERNS):
            return False
        if re.search(r"\b(?:follow|subscribe)\s+(?:us|me)\s+on\b", text, re.I):
            return False
        return True

    def _infer_claim_type(self, sentence: str, segment_type: SegmentType) -> ClaimType:
        lower = sentence.lower()
        if segment_type in {SegmentType.SPONSOR, SegmentType.ADVERTISEMENT}:
            return ClaimType.SPONSOR
        if segment_type == SegmentType.META_REQUEST:
            return ClaimType.META
        if any(word in lower for word in ("will ", "going to ", "expect ", "predict ", "forecast ")):
            return ClaimType.PREDICTION
        if any(word in lower for word in ("i think", "i believe", "in my view", "arguably", "seems like")):
            return ClaimType.OPINION
        if any(word in lower for word in ("because", "therefore", "suggests", "implies", "indicates")):
            return ClaimType.ANALYSIS
        if sentence.startswith('"') or " said " in lower or " says " in lower:
            return ClaimType.QUOTE
        return ClaimType.FACTUAL

    def _claim_confidence(
        self,
        segment: TranscriptSegment,
        sentence: str,
        claim_type: ClaimType,
    ) -> float:
        base = segment.confidence * 0.4 + 0.35
        length_factor = min(0.15, len(sentence) / 400.0)
        type_bonus = {
            ClaimType.FACTUAL: 0.12,
            ClaimType.ANALYSIS: 0.10,
            ClaimType.QUOTE: 0.08,
            ClaimType.PREDICTION: 0.06,
            ClaimType.OPINION: 0.04,
            ClaimType.META: 0.0,
            ClaimType.SPONSOR: 0.0,
        }.get(claim_type, 0.05)
        if segment.segment_type in {SegmentType.NEWS, SegmentType.INTERVIEW, SegmentType.DISCUSSION}:
            base += 0.08
        return round(min(0.99, base + length_factor + type_bonus), 3)

    @staticmethod
    def _atomic_sentences(text: str) -> List[str]:
        text = " ".join((text or "").split())
        if not text:
            return []
        parts = SENTENCE_SPLIT_RE.split(text)
        return [part.strip() for part in parts if part.strip()]

    @staticmethod
    def _surrounding_context(segments: List[TranscriptSegment], index: int, window: int = 1) -> str:
        start = max(0, index - window)
        end = min(len(segments), index + window + 1)
        lines = []
        for segment in segments[start:end]:
            snippet = segment.text.strip()
            if snippet:
                lines.append(f"{segment.speaker}: {snippet}")
        return "\n".join(lines)