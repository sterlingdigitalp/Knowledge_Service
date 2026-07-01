"""Parse structured LLM responses."""

from __future__ import annotations

import re

from .provider import BriefItemEnhancementRequest, BriefItemEnhancementResult


def parse_brief_item_response(text: str, fallback: BriefItemEnhancementRequest) -> BriefItemEnhancementResult:
    title = fallback.title
    summary = fallback.executive_summary
    why = fallback.why_it_matters
    for line in text.splitlines():
        cleaned = line.strip()
        upper = cleaned.upper()
        if upper.startswith("TITLE:"):
            title = cleaned.split(":", 1)[1].strip().strip("\"'")
        elif upper.startswith("SUMMARY:"):
            summary = cleaned.split(":", 1)[1].strip()
        elif upper.startswith("WHY_IT_MATTERS:") or upper.startswith("WHY IT MATTERS:"):
            why = re.split(r":", cleaned, maxsplit=1)[-1].strip()
    if not summary:
        summary = re.sub(r"\s+", " ", text.strip())
    return BriefItemEnhancementResult(title=title, executive_summary=summary, why_it_matters=why)