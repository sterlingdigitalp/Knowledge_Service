"""Transcript parsing, timestamp links, and timestamp-aware chunking."""

from html import unescape
from html.parser import HTMLParser
import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from ..retrieval.embedding import embed_text


TRANSCRIPT_SOURCE_TYPE = "video_transcript"
TRANSCRIPT_CONTENT_TYPES = {
    "text/vtt",
    "text/srt",
    "application/x-subrip",
    "text/transcript",
    "application/transcript+json",
}
TIME_RE = re.compile(r"^(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:[\.,](\d{1,3}))?$")
TIME_RANGE_RE = re.compile(
    r"(?P<start>(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[\.,]\d{1,3})?)\s*-->\s*"
    r"(?P<end>(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[\.,]\d{1,3})?)"
)
LINE_TIMESTAMP_RE = re.compile(
    r"^\s*[\[(]?(?P<start>(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[\.,]\d{1,3})?)[\])]?[ \t-]+"
    r"(?:(?P<speaker>[A-Za-z][A-Za-z0-9 ._\-'’]{1,80}):\s*)?(?P<text>.+?)\s*$"
)
SPEAKER_TIMESTAMP_RE = re.compile(
    r"^\s*(?:(?P<speaker>[A-Za-z][A-Za-z0-9 ._\-'’]{1,80})\s+)?[\[(]{1,2}"
    r"(?P<start>(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[\.,]\d{1,3})?)[\])]{1,2}[ \t-]*"
    r"(?P<text>.+?)\s*$"
)
STARTING_POINT_RE = re.compile(
    r"^\s*Starting point is\s+(?P<start>(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[\.,]\d{1,3})?)\s+"
    r"(?P<text>.+?)\s*$",
    re.IGNORECASE,
)
STANDALONE_TIMESTAMP_RE = re.compile(
    r"^\s*[\[(]?(?P<start>(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[\.,]\d{1,3})?)[\])]?[\s]*$"
)
SPEAKER_RE = re.compile(r"^\s*(?P<speaker>[A-Za-z][A-Za-z0-9 ._\-'’]{1,80}):\s+(?P<text>.+?)\s*$")


class _VisibleTextHTMLParser(HTMLParser):
    """Extract visible text while preserving transcript line boundaries."""

    BLOCK_TAGS = {
        "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt",
        "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6",
        "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section", "table", "tbody",
        "td", "tfoot", "th", "thead", "tr", "ul",
    }
    SKIP_TAGS = {"script", "style", "noscript", "svg", "canvas"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: List[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in self.BLOCK_TAGS:
            self._append_newline()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag in self.BLOCK_TAGS:
            self._append_newline()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        if self._parts and not self._parts[-1].endswith(("\n", " ")):
            self._parts.append(" ")
        self._parts.append(text)

    def get_text(self) -> str:
        text = "".join(self._parts)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    def _append_newline(self) -> None:
        if not self._parts or self._parts[-1] == "\n":
            return
        self._parts.append("\n")


def is_transcript_document(document: Any) -> bool:
    if document is None:
        return False
    metadata = getattr(document, "metadata", {}) or {}
    content_type = (getattr(document, "content_type", "") or "").lower()
    return (
        getattr(document, "source_type", "") == TRANSCRIPT_SOURCE_TYPE
        or metadata.get("source_type") == TRANSCRIPT_SOURCE_TYPE
        or metadata.get("transcript_source") is not None
        or metadata.get("transcript_segments") is not None
        or metadata.get("segments") is not None
        or content_type in TRANSCRIPT_CONTENT_TYPES
    )


def extract_transcript_text(content: str) -> str:
    """Return parseable transcript text from plain text or published transcript HTML."""
    raw = content or ""
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    if not _looks_like_html(normalized):
        return unescape(normalized)

    parser = _VisibleTextHTMLParser()
    parser.feed(normalized)
    parser.close()
    return parser.get_text()


def _looks_like_html(content: str) -> bool:
    sample = content[:4096].lower()
    return (
        "<html" in sample
        or "<!doctype html" in sample
        or "</p>" in sample
        or "</div>" in sample
        or "<script" in sample
    )


def parse_timestamp(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)

    raw = str(value).strip().replace(",", ".")
    if raw.isdigit():
        return float(raw)

    match = TIME_RE.match(raw)
    if not match:
        return None

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    millis = match.group(4) or "0"
    fraction = int(millis.ljust(3, "0")[:3]) / 1000.0
    return hours * 3600 + minutes * 60 + seconds + fraction


def format_timestamp(seconds: Optional[float]) -> str:
    if seconds is None:
        return "unknown"
    total = int(seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def timestamped_source_url(source_url: Optional[str], start_seconds: Optional[float]) -> Optional[str]:
    if not source_url:
        return None
    if start_seconds is None:
        return source_url

    start = max(0, int(start_seconds))
    parsed = urlparse(source_url)
    host = parsed.netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["t"] = f"{start}s"
        return urlunparse(parsed._replace(query=urlencode(query), fragment=""))

    fragment = f"t={start}"
    return urlunparse(parsed._replace(fragment=fragment))


def parse_transcript(content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    metadata = metadata or {}
    structured_segments = metadata.get("transcript_segments") or metadata.get("segments")
    if isinstance(structured_segments, list):
        return _normalize_segments(structured_segments, metadata)

    raw = extract_transcript_text(content or "")
    parsed_json = _parse_json_segments(raw, metadata)
    if parsed_json:
        return parsed_json

    timed_segments = _parse_timed_blocks(raw, metadata)
    if timed_segments:
        return timed_segments

    standalone_timestamp_segments = _parse_standalone_timestamp_blocks(raw, metadata)
    if standalone_timestamp_segments:
        return standalone_timestamp_segments

    line_segments = _parse_timestamped_lines(raw, metadata)
    if line_segments:
        return line_segments

    speaker_segments = _parse_speaker_lines(raw, metadata)
    if speaker_segments:
        return speaker_segments


    stripped = raw.strip()
    if not stripped:
        return []
    return _normalize_segments([{
        "segment_id": "segment-0",
        "start_seconds": None,
        "end_seconds": None,
        "speaker": "unknown",
        "speaker_confidence": 0.0,
        "text": stripped,
        "raw_text": raw,
    }], metadata)


def build_transcript_chunks(
    segments: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    metadata = metadata or {}
    config = config or {}
    max_words = int(config.get("transcript_chunk_size_words", config.get("chunk_size_tokens", 140)))
    max_duration = float(config.get("transcript_chunk_max_duration_seconds", 90.0))
    transcript_id = metadata.get("transcript_id") or metadata.get("episode_id") or metadata.get("video_id") or "transcript"
    source_url = metadata.get("source_url") or metadata.get("url")
    transcript_confidence = float(metadata.get("transcript_confidence", _default_transcript_confidence(metadata)))

    chunks: List[Dict[str, Any]] = []
    current: List[Dict[str, Any]] = []

    def should_flush(next_segment: Dict[str, Any]) -> bool:
        if not current:
            return False
        current_speaker = _speaker_for_group(current)
        next_speaker = next_segment.get("speaker") or "unknown"
        if current_speaker != next_speaker:
            return True
        words = sum(len((seg.get("text") or "").split()) for seg in current)
        words += len((next_segment.get("text") or "").split())
        if words > max_words:
            return True
        start = current[0].get("start_seconds")
        end = next_segment.get("end_seconds") or next_segment.get("start_seconds")
        if start is not None and end is not None and end - start > max_duration:
            return True
        return False

    def flush() -> None:
        if not current:
            return
        chunk_index = len(chunks)
        text = " ".join((seg.get("text") or "").strip() for seg in current if seg.get("text")).strip()
        start = _first_timestamp(current, "start_seconds")
        end = _last_timestamp(current, "end_seconds") or _last_timestamp(current, "start_seconds")
        speaker = _speaker_for_group(current)
        speaker_confidence = min(float(seg.get("speaker_confidence", 0.0)) for seg in current) if current else 0.0
        segment_ids = [seg.get("segment_id") for seg in current if seg.get("segment_id")]
        context = _chunk_context(segments, current)
        deep_link = timestamped_source_url(source_url, start)
        confidence = min(float(seg.get("confidence", transcript_confidence)) for seg in current) if current else transcript_confidence

        chunks.append({
            "transcript_chunk_id": f"{transcript_id}:chunk-{chunk_index}",
            "transcript_id": transcript_id,
            "content": text,
            "speaker": speaker,
            "speaker_confidence": speaker_confidence,
            "transcript_confidence": transcript_confidence,
            "confidence": min(confidence, transcript_confidence),
            "timestamp_start": start,
            "timestamp_end": end,
            "timestamp_start_label": format_timestamp(start),
            "timestamp_end_label": format_timestamp(end),
            "timestamped_source_url": deep_link,
            "surrounding_context": context,
            "segments": current.copy(),
            "segment_ids": segment_ids,
            "embedding": embed_text(text),
            "citations": [{
                "target_id": transcript_id,
                "target_url": deep_link,
                "context": context,
                "citation_type": "supporting_evidence",
                "start_seconds": start,
                "end_seconds": end,
                "segment_id": ",".join(segment_ids) if segment_ids else None,
                "quote": text,
                "speaker": speaker,
                "speaker_confidence": speaker_confidence,
                "transcript_confidence": transcript_confidence,
                "surrounding_context": context,
                "metadata": _result_metadata(metadata),
            }],
        })

    for segment in segments:
        if should_flush(segment):
            flush()
            current = []
        current.append(segment)
    flush()

    return chunks


def _parse_json_segments(content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    stripped = content.strip()
    if not stripped or stripped[0] not in "[{":
        return []
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        segments = payload.get("segments") or payload.get("transcript_segments") or payload.get("transcript")
    else:
        segments = payload
    return _normalize_segments(segments, metadata) if isinstance(segments, list) else []


def _parse_timed_blocks(content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    lines = content.splitlines()
    raw_segments: List[Dict[str, Any]] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        match = TIME_RANGE_RE.search(line)
        if not match:
            index += 1
            continue
        start = parse_timestamp(match.group("start"))
        end = parse_timestamp(match.group("end"))
        index += 1
        text_lines: List[str] = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index])
            index += 1
        raw_text = "\n".join(text_lines)
        speaker, text = _split_speaker(raw_text)
        raw_segments.append({
            "segment_id": f"segment-{len(raw_segments)}",
            "start_seconds": start,
            "end_seconds": end,
            "speaker": speaker,
            "text": text,
            "raw_text": raw_text,
        })
        index += 1
    return _normalize_segments(raw_segments, metadata)


def _parse_timestamped_lines(content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_segments: List[Dict[str, Any]] = []
    for line in content.splitlines():
        match = LINE_TIMESTAMP_RE.match(line)
        if match:
            speaker = (match.group("speaker") or "unknown").strip()
            text = match.group("text")
            if _skip_chapter_index_line(speaker, text):
                continue
            raw_segments.append({
                "segment_id": f"segment-{len(raw_segments)}",
                "start_seconds": parse_timestamp(match.group("start")),
                "speaker": speaker,
                "text": text,
                "raw_text": line,
            })
            continue

        match = SPEAKER_TIMESTAMP_RE.match(line)
        if match:
            speaker = (match.group("speaker") or "unknown").strip()
            text = match.group("text")
            if _skip_chapter_index_line(speaker, text):
                continue
            raw_segments.append({
                "segment_id": f"segment-{len(raw_segments)}",
                "start_seconds": parse_timestamp(match.group("start")),
                "speaker": speaker,
                "text": text,
                "raw_text": line,
            })
            continue

        match = STARTING_POINT_RE.match(line)
        if not match:
            continue
        raw_segments.append({
            "segment_id": f"segment-{len(raw_segments)}",
            "start_seconds": parse_timestamp(match.group("start")),
            "speaker": "unknown",
            "text": match.group("text"),
            "raw_text": line,
        })
    return _normalize_segments(raw_segments, metadata, infer_end=True)


def _skip_chapter_index_line(speaker: str, text: str) -> bool:
    stripped = text.strip()
    if speaker != "unknown" or not stripped.startswith(("-", "–", "—")):
        return False
    title = stripped.lstrip("-–— ").strip()
    return bool(title) and len(title.split()) <= 12 and not re.search(r"[.?!]\s*$", title)


def _parse_standalone_timestamp_blocks(content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    lines = content.splitlines()
    raw_segments: List[Dict[str, Any]] = []
    index = 0
    while index < len(lines):
        match = STANDALONE_TIMESTAMP_RE.match(lines[index])
        if not match:
            index += 1
            continue

        start = parse_timestamp(match.group("start"))
        index += 1
        text_lines: List[str] = []
        while index < len(lines):
            next_line = lines[index]
            if STANDALONE_TIMESTAMP_RE.match(next_line):
                break
            stripped = next_line.strip()
            if stripped:
                text_lines.append(stripped)
            index += 1

        raw_text = " ".join(text_lines).strip()
        if not raw_text:
            continue
        speaker, text = _split_speaker(raw_text)
        raw_segments.append({
            "segment_id": f"segment-{len(raw_segments)}",
            "start_seconds": start,
            "speaker": speaker,
            "text": text,
            "raw_text": raw_text,
        })
    return _normalize_segments(raw_segments, metadata, infer_end=True)


def _parse_speaker_lines(content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_segments: List[Dict[str, Any]] = []
    for line in content.splitlines():
        match = SPEAKER_RE.match(line)
        if not match:
            continue
        raw_segments.append({
            "segment_id": f"segment-{len(raw_segments)}",
            "start_seconds": None,
            "end_seconds": None,
            "speaker": match.group("speaker").strip(),
            "text": match.group("text"),
            "raw_text": line,
        })
    return _normalize_segments(raw_segments, metadata)


def _normalize_segments(
    segments: Any,
    metadata: Dict[str, Any],
    infer_end: bool = False,
) -> List[Dict[str, Any]]:
    if not isinstance(segments, list):
        return []

    normalized: List[Dict[str, Any]] = []
    transcript_confidence = float(metadata.get("transcript_confidence", _default_transcript_confidence(metadata)))
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            continue
        text = segment.get("text") or segment.get("content") or segment.get("transcript") or ""
        text = str(text).strip()
        if not text:
            continue
        speaker = segment.get("speaker") or segment.get("speaker_name") or "unknown"
        speaker = str(speaker).strip() if speaker else "unknown"
        speaker_confidence = segment.get("speaker_confidence")
        if speaker_confidence is None:
            speaker_confidence = 0.0 if speaker == "unknown" else 1.0
        start = parse_timestamp(segment.get("start_seconds", segment.get("start", segment.get("timestamp_start"))))
        end = parse_timestamp(segment.get("end_seconds", segment.get("end", segment.get("timestamp_end"))))
        duration = segment.get("duration")
        if end is None and start is not None and duration is not None:
            parsed_duration = parse_timestamp(duration)
            if parsed_duration is not None:
                end = start + parsed_duration
        normalized.append({
            "segment_id": str(segment.get("segment_id") or segment.get("id") or f"segment-{index}"),
            "start_seconds": start,
            "end_seconds": end,
            "speaker": speaker,
            "speaker_confidence": float(speaker_confidence),
            "text": text,
            "raw_text": str(segment.get("raw_text") or text),
            "confidence": float(segment.get("confidence", transcript_confidence)),
        })

    if infer_end:
        for index, segment in enumerate(normalized):
            if segment.get("end_seconds") is None:
                next_start = normalized[index + 1].get("start_seconds") if index + 1 < len(normalized) else None
                segment["end_seconds"] = next_start if next_start is not None else segment.get("start_seconds")

    return normalized


def _split_speaker(raw_text: str) -> tuple[str, str]:
    match = SPEAKER_RE.match(raw_text.replace("\n", " ").strip())
    if not match:
        return "unknown", raw_text.strip()
    return match.group("speaker").strip(), match.group("text").strip()


def _speaker_for_group(segments: List[Dict[str, Any]]) -> str:
    speakers = [(seg.get("speaker") or "unknown") for seg in segments]
    unique = {speaker for speaker in speakers if speaker != "unknown"}
    if len(unique) == 1:
        return next(iter(unique))
    if not unique:
        return "unknown"
    return "multiple"


def _first_timestamp(segments: List[Dict[str, Any]], key: str) -> Optional[float]:
    for segment in segments:
        value = segment.get(key)
        if value is not None:
            return value
    return None


def _last_timestamp(segments: List[Dict[str, Any]], key: str) -> Optional[float]:
    for segment in reversed(segments):
        value = segment.get(key)
        if value is not None:
            return value
    return None


def _chunk_context(all_segments: List[Dict[str, Any]], chunk_segments: List[Dict[str, Any]]) -> str:
    if not chunk_segments:
        return ""
    first_id = chunk_segments[0].get("segment_id")
    last_id = chunk_segments[-1].get("segment_id")
    indexes = [index for index, segment in enumerate(all_segments) if segment.get("segment_id") in {first_id, last_id}]
    if not indexes:
        return " ".join(seg.get("text", "") for seg in chunk_segments).strip()
    start = max(0, min(indexes) - 1)
    end = min(len(all_segments), max(indexes) + 2)
    return " ".join(seg.get("text", "") for seg in all_segments[start:end] if seg.get("text")).strip()


def _default_transcript_confidence(metadata: Dict[str, Any]) -> float:
    source = metadata.get("transcript_source") or metadata.get("source") or "published"
    if source == "published_transcript":
        return 0.95
    if source == "youtube_captions":
        return 0.85
    if source == "whisper_fallback":
        return 0.65
    return 0.8


def _result_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    keys = [
        "show", "episode", "episode_id", "episode_date", "video_id",
        "transcript_source", "provider", "acquisition_status",
    ]
    return {key: metadata[key] for key in keys if key in metadata}
