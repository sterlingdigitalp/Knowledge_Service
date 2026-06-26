"""Stage 2: Normalize — content type, metadata extraction, language detection, heading hierarchy

Input: cleaned content
Output: normalized content with metadata, language detection, heading normalization
"""

import re
from typing import Dict, Any
from .context import ProcessingContext, StageResult


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
LANG_COMMON_WORDS = {
    "en": {"the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out"},
    "es": {"el", "la", "los", "las", "que", "por", "con", "para", "una", "son", "del", "como", "más", "pero", "sus"},
    "fr": {"le", "la", "les", "des", "que", "dans", "pour", "avec", "une", "sur", "pas", "plus", "sont", "leur", "nous"},
    "de": {"der", "die", "das", "den", "mit", "auf", "für", "ist", "nicht", "sich", "ein", "eine", "bei", "aus", "nach"},
    "zh": {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也"},
    "ja": {"の", "に", "を", "は", "が", "で", "ます", "た", "です", "と", "し", "て", "いる", "ある", "ない"},
}
CONTENT_TYPE_PATTERNS = [
    ("code", re.compile(r"```[\s\S]*?```")),
    ("code", re.compile(r"(?:function|def |class |import |export |return |var |let |const )")),
    ("code", re.compile(r"(?:\/\*[\s\S]*?\*\/|\/\/.*)")),
    ("table", re.compile(r"\|[^\n]+\|[ \t]*\n\|[-\s|]+\|")),
    ("list", re.compile(r"^[\s]*[-*+][\s]+", re.MULTILINE)),
    ("list", re.compile(r"^[\s]*\d+\.[\s]+", re.MULTILINE)),
]
SHORT_CODE_LANG_RE = re.compile(r"```(\w+)")


class NormalizeStage:

    def execute(self, context: ProcessingContext, config: Dict[str, Any]) -> ProcessingContext:
        content = context.cleaned_content
        if not content:
            context.stage_results["normalize"] = StageResult("normalize", True, confidence_impact=-0.05, warnings=["No content to normalize"])
            return context

        detect_language = config.get("detect_language", True)
        normalize_headings = config.get("normalize_headings", True)

        metadata: Dict[str, Any] = {}

        content_type = self._detect_content_type(content)
        metadata["content_type"] = content_type

        if detect_language:
            lang = self._detect_language(content)
            context.language = lang
            metadata["detected_language"] = lang

        if normalize_headings:
            content = self._normalize_headings(content)

        metadata["total_lines"] = len(content.split("\n"))
        metadata["char_count"] = len(content)

        context.normalized_content = content
        context.normalized_metadata = metadata
        context.stage_results["normalize"] = StageResult("normalize", True, confidence_impact=0.0)
        return context

    def _detect_content_type(self, content: str) -> str:
        score = 0
        has_code = False
        for ctype, pattern in CONTENT_TYPE_PATTERNS:
            if pattern.search(content):
                if ctype == "code":
                    has_code = True
                score += 1
        code_blocks = SHORT_CODE_LANG_RE.findall(content)
        if code_blocks:
            has_code = True
            score += len(code_blocks)
        if has_code and score > 3:
            return "code"
        if score > 2:
            if re.search(r"\|[^\n]+\|[ \t]*\n\|[-\s|]+\|", content):
                return "data"
            return "article"
        return "article"

    def _detect_language(self, content: str) -> str:
        words = re.findall(r"[a-zA-ZÀ-ÿ]+", content.lower())
        if not words:
            return "unknown"
        unique_words = set(words)
        scores: Dict[str, int] = {}
        for lang, common in LANG_COMMON_WORDS.items():
            scores[lang] = len(unique_words & common)
        if not scores:
            return "en"
        return max(scores, key=scores.get) if max(scores.values()) > 0 else "en"

    def _normalize_headings(self, content: str) -> str:
        LOTS_HASH_RE = re.compile(r"^#{7,}\s+(.+)$", re.MULTILINE)
        content = LOTS_HASH_RE.sub(r"# \1", content)
        def _relevel(m: re.Match) -> str:
            level = len(m.group(1))
            if level > 6:
                level = 6
            return "#" * level + " " + m.group(2)
        return HEADING_RE.sub(_relevel, content)
