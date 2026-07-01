"""Stage 3: Extract — title, authors, dates, citations, tables, code blocks

Input: normalized content
Output: extracted metadata (title, authors, dates, citations, tables, code blocks)
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from .context import ProcessingContext, StageResult
from .transcript import is_transcript_document, parse_transcript, timestamped_source_url


TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE)
AUTHOR_META_RE = re.compile(
    r'(?:author|by)[:\s]+([A-Z][a-zA-Z\s,.]+?)(?:\n|$)',
    re.IGNORECASE | re.MULTILINE
)
DATE_PATTERNS = [
    re.compile(r"\b(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b"),
    re.compile(r"\b(0[1-9]|[12]\d|3[01])[-/](0[1-9]|1[0-2])[-/](20\d{2})\b"),
    re.compile(r"\b(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])T\d{2}:\d{2}:\d{2}"),
    re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(20\d{2})\b", re.IGNORECASE),
]
CITATION_RE = re.compile(r"\[(\d+)\]|\(https?://[^\s)]+\)|(?:see|ref|source)[:\s]+https?://\S+", re.IGNORECASE)
TABLE_RE = re.compile(r"\|[^\n]+\|[ \t]*\n\|[-\s|]+\|(?:\n\|[^\n]+\|)*")
CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
URL_RE = re.compile(r"https?://[^\s<>\"']+")


class ExtractStage:

    def execute(self, context: ProcessingContext, config: Dict[str, Any]) -> ProcessingContext:
        content = context.normalized_content
        if not content:
            context.stage_results["extract"] = StageResult("extract", True, confidence_impact=-0.10, warnings=["No content to extract"])
            return context

        extract_citations = config.get("extract_citations", True)
        extract_tables = config.get("extract_tables", True)
        extract_authors = config.get("extract_authors", True)

        extracted: Dict[str, Any] = {}

        if is_transcript_document(context.document):
            metadata = dict(getattr(context.document, "metadata", {}) or {})
            segments = parse_transcript(content, metadata)
            context.title = metadata.get("episode") or metadata.get("title") or context.title
            if metadata.get("authors"):
                context.authors = list(metadata.get("authors", []))
            if metadata.get("episode_date"):
                context.extracted_data["published_date"] = metadata["episode_date"]
                extracted["published_date"] = metadata["episode_date"]
            extracted["transcript_segments"] = segments
            extracted["transcript_segments_count"] = len(segments)
            extracted["transcript_metadata"] = metadata
            context.citations = self._extract_transcript_citations(segments, metadata)
            if context.citations:
                extracted["citations_count"] = len(context.citations)
            context.extracted_data.update(extracted)
            warnings = [] if segments else ["No transcript segments parsed"]
            context.stage_results["extract"] = StageResult("extract", True, confidence_impact=0.0, warnings=warnings)
            return context

        title = self._extract_title(content, context.normalized_metadata)
        if title:
            context.title = title
            extracted["title"] = title

        if extract_authors:
            authors = self._extract_authors(content)
            if authors:
                context.authors = authors
                extracted["authors"] = authors

        pub_date = self._extract_date(content)
        if pub_date:
            extracted["published_date"] = pub_date
            context.extracted_data["published_date"] = pub_date

        if extract_citations:
            citations = self._extract_citations(content)
            if citations:
                context.citations = citations
                extracted["citations_count"] = len(citations)

        if extract_tables:
            tables = TABLE_RE.findall(content)
            if tables:
                extracted["tables_count"] = len(tables)
                extracted["tables"] = tables

        code_blocks = CODE_BLOCK_RE.findall(content)
        if code_blocks:
            extracted["code_blocks_count"] = len(code_blocks)
            extracted["code_blocks_languages"] = [lang for lang, _ in code_blocks if lang]

        urls = URL_RE.findall(content)
        if urls:
            extracted["external_urls"] = urls

        context.extracted_data.update(extracted)
        context.stage_results["extract"] = StageResult("extract", True, confidence_impact=0.0)
        return context

    def _extract_title(self, content: str, metadata: Dict[str, Any]) -> Optional[str]:
        m = TITLE_RE.search(content)
        if m:
            return m.group(1).strip()
        m = H1_RE.search(content)
        if m:
            cleaned = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if cleaned:
                return cleaned
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        if lines and len(lines[0]) < 200:
            return lines[0]
        return None

    def _extract_authors(self, content: str) -> List[str]:
        authors: List[str] = []
        for m in AUTHOR_META_RE.finditer(content):
            raw = m.group(1).strip().rstrip(".,")
            parts = re.split(r"\s+(?:and|&)\s+", raw)
            for part in parts:
                for sub in re.split(r"\s*,\s*", part):
                    sub = sub.strip()
                    if sub and len(sub) < 100 and sub not in authors and re.search(r"[A-Za-z]", sub):
                        authors.append(sub)
        return authors[:5]

    def _extract_date(self, content: str) -> Optional[str]:
        for pattern in DATE_PATTERNS:
            m = pattern.search(content)
            if m:
                try:
                    groups = m.groups()
                    if len(groups) == 3:
                        if "T" in m.group(0):
                            return m.group(0)
                        if len(groups[0]) == 4:
                            return f"{groups[0]}-{groups[1]}-{groups[2]}"
                        else:
                            return f"{groups[2]}-{groups[0]}-{groups[1]}"
                except Exception:
                    continue
        return None

    def _extract_citations(self, content: str) -> List[Dict[str, Any]]:
        citations: List[Dict[str, Any]] = []
        for m in URL_RE.finditer(content):
            url = m.group(0)
            citations.append({"target_url": url, "citation_type": "reference"})
        return citations[:50]

    def _extract_transcript_citations(self, segments: List[Dict[str, Any]], metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        transcript_id = metadata.get("transcript_id") or metadata.get("episode_id") or metadata.get("video_id")
        source_url = metadata.get("source_url") or metadata.get("url")
        transcript_confidence = metadata.get("transcript_confidence", 0.8)
        citations: List[Dict[str, Any]] = []
        for segment in segments[:500]:
            start = segment.get("start_seconds")
            end = segment.get("end_seconds")
            text = segment.get("text")
            citations.append({
                "target_id": transcript_id,
                "target_url": timestamped_source_url(source_url, start),
                "context": text,
                "citation_type": "supporting_evidence",
                "start_seconds": start,
                "end_seconds": end,
                "segment_id": segment.get("segment_id"),
                "quote": text,
                "speaker": segment.get("speaker", "unknown"),
                "speaker_confidence": segment.get("speaker_confidence", 0.0),
                "transcript_confidence": transcript_confidence,
                "surrounding_context": text,
                "metadata": {
                    "show": metadata.get("show"),
                    "episode": metadata.get("episode"),
                    "episode_date": metadata.get("episode_date"),
                    "transcript_source": metadata.get("transcript_source"),
                    "provider": metadata.get("provider"),
                    "acquisition_status": metadata.get("acquisition_status"),
                },
            })
        return citations
