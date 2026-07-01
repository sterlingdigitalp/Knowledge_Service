"""Stage 1: Clean — encoding, HTML stripping, whitespace normalization

Input: raw content string from AcquisitionBundle DocumentRecord
Output: cleaned content with markup removed, encoding normalized, artifacts stripped
"""

import re
from typing import Dict, Any
from .context import ProcessingContext, StageResult
from .transcript import is_transcript_document


HTML_TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
SCRIPT_STYLE_SHORT_RE = re.compile(r"<(script|style)[^>]*/>", re.IGNORECASE)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
WHITESPACE_RE = re.compile(r"[ \t]+")
MULTILINE_BREAK_RE = re.compile(r"\n{3,}")
DOCTYPE_RE = re.compile(r"<!DOCTYPE[^>]*>", re.IGNORECASE)
CSS_RE = re.compile(r"<style[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
NAV_RE = re.compile(
    r"<(nav|header|footer|aside|menu|sidebar)[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL
)
BINARY_PATTERNS = [
    re.compile(rb"^%PDF"), re.compile(rb"^\x89PNG"), re.compile(rb"^\xff\xd8"),
    re.compile(rb"^PK\x03\x04"), re.compile(rb"^\x1f\x8b"), re.compile(rb"^\x00\x00"),
]


class CleanStage:

    def execute(self, context: ProcessingContext, config: Dict[str, Any]) -> ProcessingContext:
        raw = context.raw_content
        if not raw:
            context.stage_results["clean"] = StageResult("clean", True, warnings=["Empty content"])
            return context

        if is_transcript_document(context.document):
            context.cleaned_content = raw
            context.stage_results["clean"] = StageResult("clean", True, confidence_impact=0.0)
            return context

        strip_scripts = config.get("strip_scripts", True)
        strip_navigation = config.get("strip_navigation", True)
        normalize_whitespace = config.get("normalize_whitespace", True)
        max_length = config.get("max_content_length", 10 * 1024 * 1024)

        content = raw

        if len(content.encode("utf-8")) > max_length:
            context.warnings.append("Content exceeds max_content_length; truncating")
            content = content[:max_length]

        if strip_scripts:
            content = SCRIPT_STYLE_RE.sub("", content)
            content = SCRIPT_STYLE_SHORT_RE.sub("", content)

        content = COMMENT_RE.sub("", content)
        content = DOCTYPE_RE.sub("", content)
        content = CSS_RE.sub("", content)

        if strip_navigation:
            content = NAV_RE.sub("", content)

        content = HTML_TAG_RE.sub("", content)
        content = content.replace("&amp;", "&")
        content = content.replace("&lt;", "<")
        content = content.replace("&gt;", ">")
        content = content.replace("&quot;", "\"")
        content = content.replace("&#39;", "'")
        content = content.replace("&nbsp;", " ")

        if normalize_whitespace:
            content = WHITESPACE_RE.sub(" ", content)
            content = content.replace("\r\n", "\n")
            content = content.replace("\r", "\n")
            content = MULTILINE_BREAK_RE.sub("\n\n", content)

        content = content.strip()

        context.cleaned_content = content
        context.stage_results["clean"] = StageResult("clean", True, confidence_impact=0.0)
        return context
