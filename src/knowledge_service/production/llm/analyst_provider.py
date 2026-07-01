"""Analyst-quality generation without external API — pattern-based research prose."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .provider import ConversationRequest, ConversationResult, LLMProvider, SummaryRequest, ThemeNamingRequest


ANALYST_PATTERNS: List[Tuple[Tuple[str, ...], str]] = [
    (("inference", "cost", "gpu", "compute", "datacenter"), "Inference Economics"),
    (("agent", "autonomous", "tool", "workflow"), "Enterprise AI Agents"),
    (("glp", "ozempic", "wegovy", "metabolic", "longevity"), "GLP-1 Competitive Landscape"),
    (("founder", "startup", "building", "operator"), "Founder Operating Lessons"),
    (("market", "valuation", "capital", "invest"), "Capital Allocation Debate"),
    (("model", "scaling", "frontier", "training"), "Frontier Model Scaling"),
    (("cuda", "chip", "semiconductor", "nvidia"), "AI Infrastructure Supply"),
    (("health", "protein", "clinical", "medicine"), "Translational Medicine Signals"),
    (("openai", "anthropic", "altman"), "Frontier Lab Strategy"),
    (("energy", "power", "electricity"), "AI Power Demand"),
]


class AnalystLLMProvider(LLMProvider):
    """Produces analyst-report style naming and summaries locally."""

    name = "analyst_heuristic"

    def name_theme(self, request: ThemeNamingRequest) -> str:
        haystack = " ".join([
            *request.keywords,
            *request.entities,
            *request.sample_claims[:3],
        ]).lower()

        for triggers, title in ANALYST_PATTERNS:
            if any(trigger in haystack for trigger in triggers):
                return title

        concepts = _substantive_concepts(request.keywords, request.entities)
        if len(concepts) >= 2:
            return f"{concepts[0]} {concepts[1]}"
        if concepts:
            return f"{concepts[0]} Developments"

        for claim in request.sample_claims:
            titled = _title_from_claim(claim)
            if titled:
                return titled
        return "Emerging Intelligence Signal"

    def executive_summary(self, request: SummaryRequest) -> str:
        source_count = len(request.sources) or 1
        speaker_line = ", ".join(request.speakers[:4]) if request.speakers else "multiple monitored voices"
        lead = request.claim_excerpts[0][:200] if request.claim_excerpts else request.theme_label
        what_changed = (
            f"{source_count} independent source{'s' if source_count != 1 else ''} "
            f"({speaker_line}) are converging on {request.title}."
        )
        why_matters = _why_matters(request)
        why_now = _why_now(request)
        watch_next = _watch_next(request)
        return (
            f"{what_changed} The core signal: {lead} "
            f"Why it matters: {why_matters} "
            f"Why now: {why_now} "
            f"What to watch next: {watch_next}"
        )

    def converse(self, request: ConversationRequest) -> ConversationResult:
        message = (request.user_message or "").strip().lower()
        if not message or message in {"tell me more", "more", "continue"}:
            return ConversationResult(text=_opening_briefing(request), provider=self.name)
        if "contradict" in message or "conflict" in message:
            return ConversationResult(
                text=(
                    f"On {request.title}, conflicting positions exist in the evidence base. "
                    f"I would compare primary sources before updating your view. "
                    f"Key tension: {request.executive_summary[:280]}"
                ),
                provider=self.name,
            )
        if "timeline" in message or "history" in message or "when" in message:
            lines = [f"Timeline for {request.title}:"]
            for item in request.evidence[:6]:
                lines.append(f"- {item.get('timestamp_label', 'n/a')} | {item.get('speaker', 'unknown')} ({item.get('source', 'source')}): {str(item.get('excerpt', ''))[:120]}")
            return ConversationResult(text="\n".join(lines), provider=self.name)
        if "evidence" in message or "source" in message:
            lines = [f"Evidence map for {request.title}:"]
            for item in request.evidence[:5]:
                lines.append(f"- {item.get('speaker', 'unknown')} @ {item.get('timestamp_label', 'n/a')} ({item.get('source', 'source')})")
            return ConversationResult(text="\n".join(lines), provider=self.name)
        if "?" in request.user_message:
            return ConversationResult(
                text=(
                    f"Analyst view on {request.title}: {request.executive_summary[:320]} "
                    f"Follow-up angles: corroboration strength, who changed position, and what would falsify the thesis."
                ),
                provider=self.name,
            )
        return ConversationResult(
            text=(
                f"Continuing on {request.title}: {request.executive_summary[:260]} "
                f"You can ask about timeline, contradictions, evidence, or competing viewpoints."
            ),
            provider=self.name,
        )

    def suggested_followups(
        self,
        *,
        title: str,
        executive_summary: str,
        contradiction_count: int = 0,
        corroboration_count: int = 0,
    ) -> List[str]:
        prompts = [
            "Show me the timeline",
            "What evidence supports this?",
            "Are there competing viewpoints?",
            "What should I watch next?",
        ]
        if contradiction_count:
            prompts.insert(0, "Explain the contradictions")
        if corroboration_count:
            prompts.insert(1, "Who corroborated this independently?")
        return prompts[:5]


def _substantive_concepts(keywords: List[str], entities: List[str]) -> List[str]:
    concepts: List[str] = []
    for entity in entities:
        cleaned = entity.strip()
        if cleaned and cleaned.lower() != "unknown" and cleaned not in concepts:
            concepts.append(_title_case(cleaned))
    for keyword in keywords:
        if len(keyword) < 4 or keyword.lower() in FRAGMENT_STARTERS:
            continue
        title = _title_case(keyword)
        if title not in concepts and not _is_fragment_label(title):
            concepts.append(title)
    return concepts[:3]


FRAGMENT_STARTERS = {"i", "and", "but", "so", "well", "yeah", "okay", "the", "a", "we", "you", "ones", "this", "that"}


def _title_from_claim(claim: str) -> str:
    lower = claim.lower()
    for triggers, title in ANALYST_PATTERNS:
        if any(trigger in lower for trigger in triggers):
            return title
    for marker in ("ai ", "inference", "founder", "market", "longevity", "openai", "spacex", "obama", "biden"):
        if marker in lower:
            return _title_case(marker.strip()) + " Developments"
    return ""


def _is_fragment_label(label: str) -> bool:
    words = label.split()
    if not words:
        return True
    if words[0].lower() in FRAGMENT_STARTERS:
        return True
    return len(words) == 1 and len(words[0]) < 5


def _title_case(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).title()


def _why_matters(request: SummaryRequest) -> str:
    if request.corroboration_count >= 2:
        return f"Independent corroboration ({request.corroboration_count} sources) raises confidence this is a real shift, not noise."
    if request.importance_band in {"very_high", "high"}:
        return "High importance scoring indicates potential portfolio or strategic relevance."
    return "This development may influence near-term decisions in your monitored domains."


def _why_now(request: SummaryRequest) -> str:
    if request.novelty_classification in {"new", "update", "contradiction"}:
        return f"Novelty is {request.novelty_classification}, suggesting this is not stale repetition."
    if request.theme_evolution:
        return request.theme_evolution
    return "Fresh transcript activity landed in the last collection window."


def _watch_next(request: SummaryRequest) -> str:
    if request.contradictions:
        return "Watch whether leading voices reconcile or harden opposing positions."
    if request.corroboration_count:
        return "Watch for a third independent source to confirm consensus formation."
    return "Watch for follow-on commentary from primary decision-makers."


def _opening_briefing(request: ConversationRequest) -> str:
    evidence_count = len(request.evidence)
    return (
        f"Analyst briefing — {request.title}\n\n"
        f"{request.executive_summary}\n\n"
        f"I have {evidence_count} timestamped citations, historical context, and contradiction checks ready. "
        f"Ask about timeline, evidence, competing viewpoints, or what would change the thesis."
    )