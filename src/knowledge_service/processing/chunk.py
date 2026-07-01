"""Stage 5: Chunk — semantic chunking with overlap, parent references

Input: markdown content
Output: list of chunk dicts with parent refs, indexes, overlap support
"""

import re
import hashlib
from typing import Dict, Any, List
from .context import ProcessingContext, StageResult
from .transcript import build_transcript_chunks, is_transcript_document


SECTION_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
PARAGRAPH_SPLIT_RE = re.compile(r"\n\n+")


class ChunkStage:

    def execute(self, context: ProcessingContext, config: Dict[str, Any]) -> ProcessingContext:
        md = context.markdown
        if not md:
            context.stage_results["chunk"] = StageResult("chunk", True, confidence_impact=0.0, warnings=["No content to chunk"])
            return context

        if is_transcript_document(context.document):
            segments = context.extracted_data.get("transcript_segments", [])
            metadata = dict(getattr(context.document, "metadata", {}) or {})
            chunks = build_transcript_chunks(segments, metadata, config)
            self._append_chunks(context, chunks, config.get("overlap_tokens", 0))
            warnings = [] if chunks else ["No transcript chunks created"]
            context.stage_results["chunk"] = StageResult("chunk", True, confidence_impact=0.0, warnings=warnings)
            return context

        strategy = config.get("strategy", "semantic")
        overlap_tokens = config.get("overlap_tokens", 50)
        min_chunk = config.get("min_chunk_size_tokens", 50)

        word_count = context.word_count

        if word_count <= min_chunk:
            context.stage_results["chunk"] = StageResult("chunk", True, confidence_impact=0.0, warnings=["Content too small to chunk"])
            return context

        if strategy == "semantic":
            chunks = self._semantic_chunk(md, overlap_tokens, min_chunk)
        elif strategy == "fixed_size":
            chunk_size = config.get("chunk_size_tokens", 512)
            chunks = self._fixed_size_chunk(md, chunk_size, overlap_tokens, min_chunk)
        else:
            chunks = self._semantic_chunk(md, overlap_tokens, min_chunk)

        self._append_chunks(context, chunks, overlap_tokens)

        context.stage_results["chunk"] = StageResult("chunk", True, confidence_impact=0.0)
        return context

    def _append_chunks(self, context: ProcessingContext, chunks: List[Dict[str, Any]], overlap_tokens: int) -> None:
        chunk_total = len(chunks)
        parent_id = context.knowledge_objects[0].id if context.knowledge_objects else ""

        for i, chunk_data in enumerate(chunks):
            chunk_hash = hashlib.sha256(chunk_data["content"].encode("utf-8")).hexdigest()
            cw = len(chunk_data["content"].split())
            chunk_entry = dict(chunk_data)
            chunk_entry.update({
                "parent_id": chunk_data.get("parent_id") or parent_id,
                "chunk_index": i,
                "chunk_total": chunk_total,
                "content": chunk_data["content"],
                "content_hash": chunk_hash,
                "word_count": cw,
                "heading_context": chunk_data.get("heading_context", ""),
            })
            if i < chunk_total - 1 and overlap_tokens > 0:
                chunk_entry["overlap_with_next"] = chunk_data.get("next_overlap", "")
            context.chunks.append(chunk_entry)

    def _semantic_chunk(self, md: str, overlap_tokens: int, min_chunk: int) -> List[Dict[str, Any]]:
        sections = SECTION_HEADING_RE.split(md)
        chunks: List[Dict[str, Any]] = []
        current = ""
        current_headings: list[str] = []

        if not SECTION_HEADING_RE.search(md):
            return self._fixed_size_chunk(md, 512, overlap_tokens, min_chunk)

        parts = SECTION_HEADING_RE.split(md)
        if parts and parts[0].strip():
            current = parts[0].strip()
            chunks.append({"content": current, "heading_context": "", "next_overlap": ""})

        i = 1
        while i < len(parts) - 1:
            level = len(parts[i])
            heading = parts[i + 1].strip()
            heading_context = "#" * level + " " + heading

            if level <= len(current_headings):
                current_headings = current_headings[:level - 1]
            current_headings.append(heading)

            content_parts = []
            j = i + 2
            while j < len(parts) - 1 and len(parts[j]) >= level:
                break
            remaining = ""
            if j < len(parts):
                remaining = parts[j] if j > i + 2 else (parts[j] if j == i + 2 else "")
            else:
                remaining = ""

            if remaining and remaining.strip():
                content_parts.append(heading_context)
                content_parts.append(remaining.strip())

            if content_parts:
                chunk_content = "\n\n".join(content_parts)
                context_str = " > ".join(current_headings)
                chunk_entry = {
                    "content": chunk_content,
                    "heading_context": context_str,
                    "next_overlap": "",
                }

                if chunks and overlap_tokens > 0:
                    prev_words = chunks[-1]["content"].split()
                    overlap_words = prev_words[-min(overlap_tokens, len(prev_words)):]
                    chunk_entry["next_overlap"] = " ".join(overlap_words)

                chunks.append(chunk_entry)

            i += 2

        if not chunks:
            return self._fixed_size_chunk(md, 512, overlap_tokens, min_chunk)

        return chunks

    def _fixed_size_chunk(self, md: str, chunk_size: int, overlap_tokens: int, min_chunk: int) -> List[Dict[str, Any]]:
        words = md.split()
        if len(words) <= min_chunk:
            return [{"content": md, "heading_context": "", "next_overlap": ""}]

        chunks: List[Dict[str, Any]] = []
        i = 0
        while i < len(words):
            end = min(i + chunk_size, len(words))
            chunk_words = words[i:end]
            chunk_content = " ".join(chunk_words)
            overlap_text = ""
            if end < len(words) and overlap_tokens > 0:
                overlap_end = min(end + overlap_tokens, len(words))
                overlap_text = " ".join(words[end:overlap_end])

            chunks.append({
                "content": chunk_content,
                "heading_context": "",
                "next_overlap": overlap_text,
            })
            step = chunk_size - overlap_tokens if overlap_tokens > 0 else chunk_size
            if step < 1:
                step = 1
            i += step

        return chunks
