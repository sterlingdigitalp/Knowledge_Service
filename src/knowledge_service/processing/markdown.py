"""Stage 4: Markdown — canonical markdown conversion, content hashing

Input: extracted/normalized content
Output: canonical markdown string, raw_content_hash, content_hash, word_count
"""

import re
import hashlib
from typing import Dict, Any
from .context import ProcessingContext, StageResult


LIST_ITEM_RE = re.compile(r"^(\s*)[-*+]\s+(.*)", re.MULTILINE)
ORDERED_ITEM_RE = re.compile(r"^(\s*)\d+\.\s+(.*)", re.MULTILINE)
BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)", re.MULTILINE)
HEADING_MD_RE = re.compile(r"^(#{1,6})\s+(.*)", re.MULTILINE)
HORIZONTAL_RULE_RE = re.compile(r"^---+\s*$", re.MULTILINE)


class MarkdownStage:

    def execute(self, context: ProcessingContext, config: Dict[str, Any]) -> ProcessingContext:
        content = context.normalized_content or context.cleaned_content
        if not content:
            context.stage_results["markdown"] = StageResult("markdown", True, confidence_impact=-0.15, warnings=["No content for markdown conversion"])
            return context

        preserve_code = config.get("preserve_code_formatting", True)
        max_heading_depth = config.get("max_heading_depth", 6)

        md = self._to_markdown(content, preserve_code, max_heading_depth)

        wc = self._count_words(md)
        context.word_count = wc

        rch = hashlib.sha256(context.raw_content.encode("utf-8")).hexdigest()
        ch = hashlib.sha256(md.encode("utf-8")).hexdigest()

        context.markdown = md
        context.raw_content_hash = rch
        context.content_hash = ch
        context.stage_results["markdown"] = StageResult("markdown", True, confidence_impact=0.0)
        return context

    def _to_markdown(self, content: str, preserve_code: bool, max_depth: int) -> str:
        lines = content.split("\n")
        result: list[str] = []
        in_code_block = False
        code_lang = ""
        code_buffer: list[str] = []

        for line in lines:
            cb = CODE_BLOCK_DETECT_RE.match(line)
            if cb:
                if in_code_block:
                    code_buffer.append(line)
                    result.extend(self._flush_code(code_buffer, code_lang, preserve_code))
                    code_buffer = []
                    in_code_block = False
                    code_lang = ""
                else:
                    if code_buffer:
                        result.extend(self._flush_code(code_buffer, code_lang, preserve_code))
                        code_buffer = []
                    in_code_block = True
                    code_lang = cb.group(1) if cb.group(1) else ""
                    code_buffer.append(line)
                continue

            if in_code_block:
                code_buffer.append(line)
                continue

            processed = self._process_line(line, max_depth)
            result.append(processed)

        if in_code_block and code_buffer:
            result.extend(self._flush_code(code_buffer, code_lang, preserve_code))
        elif code_buffer:
            result.extend(self._flush_code(code_buffer, code_lang, preserve_code))

        md = "\n".join(result)
        md = re.sub(r"\n{4,}", "\n\n\n", md)
        return md.strip()

    def _process_line(self, line: str, max_depth: int) -> str:
        m = HEADING_MD_RE.match(line)
        if m:
            level = len(m.group(1))
            if level > max_depth:
                level = max_depth
            return "#" * level + " " + m.group(2)

        m = BLOCKQUOTE_RE.match(line)
        if m:
            return "> " + m.group(1)

        m = HORIZONTAL_RULE_RE.match(line)
        if m:
            return "---"

        return line

    def _flush_code(self, lines: list[str], lang: str, preserve: bool) -> list[str]:
        if not lines:
            return []
        fence = "```"
        if lines[0].startswith(fence):
            lines = lines[1:]
        while lines and lines[-1].strip() == "":
            lines = lines[:-1]
        while lines and lines[0].strip() == "":
            lines = lines[1:]
        result = [f"{fence}{lang}"]
        for line in lines:
            if line.startswith(fence):
                continue
            result.append(line.rstrip() if preserve else line.strip())
        result.append(fence)
        return result

    def _count_words(self, text: str) -> int:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if not cleaned:
            return 0
        return len(cleaned.split(" "))


CODE_BLOCK_DETECT_RE = re.compile(r"^```(\w*)$")
