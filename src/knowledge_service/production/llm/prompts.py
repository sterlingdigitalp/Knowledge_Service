"""Dedicated analyst prompts for production LLM generation."""

from __future__ import annotations

from .provider import ConversationRequest, SummaryRequest, ThemeNamingRequest

ANALYST_SYSTEM = (
    "You are a senior personal intelligence analyst. Write crisp, evidence-backed prose. "
    "Never mention transcripts, claims, clustering, embeddings, or LLM mechanics. "
    "Avoid marketing language, filler, and clichés like 'delve', 'landscape shift', or 'game-changer'. "
    "Sound like a research desk briefing a principal."
)


def theme_naming_instructions() -> str:
    return (
        f"{ANALYST_SYSTEM}\n"
        "Name this intelligence theme like an equity research section title.\n"
        "Return only the title: 2-5 words, title case, no quotes, no punctuation at end.\n"
        "Examples: 'Inference Economics', 'GLP-1 Competitive Landscape', 'Enterprise AI Agents'."
    )


def theme_naming_input(request: ThemeNamingRequest) -> str:
    return (
        f"Keywords: {', '.join(request.keywords[:12])}\n"
        f"Entities: {', '.join(request.entities[:8])}\n"
        f"Sources: {', '.join(request.sources[:6])}\n"
        f"Speakers: {', '.join(request.speakers[:6])}\n"
        f"Sample signals: {' | '.join(request.sample_claims[:4])}"
    )


def executive_summary_instructions() -> str:
    return (
        f"{ANALYST_SYSTEM}\n"
        "Write a concise executive summary in four parts as flowing analyst prose:\n"
        "1) What changed\n"
        "2) Why it matters\n"
        "3) Why now\n"
        "4) What to watch next\n"
        "Use complete sentences. No bullet lists. No transcript quotes. 80-140 words."
    )


def executive_summary_input(request: SummaryRequest) -> str:
    return (
        f"Theme: {request.title}\n"
        f"Prior label: {request.theme_label}\n"
        f"Sources ({len(request.sources)}): {', '.join(request.sources[:8])}\n"
        f"Speakers: {', '.join(request.speakers[:8])}\n"
        f"Novelty: {request.novelty_classification}\n"
        f"Importance: {request.importance_band}\n"
        f"Corroboration count: {request.corroboration_count}\n"
        f"Contradictions: {request.contradictions}\n"
        f"Theme evolution: {request.theme_evolution or 'n/a'}\n"
        f"Evidence excerpts: {' | '.join(request.claim_excerpts[:5])}"
    )


def deep_dive_instructions() -> str:
    return (
        f"{ANALYST_SYSTEM}\n"
        "Deliver a research analyst briefing. Include historical context, competing views, "
        "corroboration, contradictions, and future watch points when relevant. "
        "Cite speakers and sources naturally. 120-220 words unless the user asks a narrow question."
    )


def deep_dive_input(request: ConversationRequest) -> str:
    history = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in request.conversation_history[-8:]
    )
    evidence_lines = []
    for item in request.evidence[:8]:
        evidence_lines.append(
            f"- {item.get('speaker', 'unknown')} @ {item.get('timestamp_label', 'n/a')} "
            f"({item.get('source', 'source')}): {str(item.get('excerpt', ''))[:160]}"
        )
    evidence_block = "\n".join(evidence_lines) if evidence_lines else "- No timestamped evidence attached."
    return (
        f"Intelligence item: {request.title}\n"
        f"Executive summary: {request.executive_summary}\n"
        f"Evidence:\n{evidence_block}\n"
        f"Conversation history:\n{history or '(opening turn)'}\n"
        f"User: {request.user_message}"
    )


def followup_instructions() -> str:
    return (
        f"{ANALYST_SYSTEM}\n"
        "Suggest exactly 4 follow-up questions a principal would ask next.\n"
        "Return one question per line. No numbering, bullets, or quotes."
    )


def followup_input(title: str, executive_summary: str, *, contradiction_count: int, corroboration_count: int) -> str:
    return (
        f"Item: {title}\n"
        f"Summary: {executive_summary[:400]}\n"
        f"Contradictions: {contradiction_count}\n"
        f"Corroboration: {corroboration_count}"
    )


def morning_brief_wording_instructions() -> str:
    return (
        f"{ANALYST_SYSTEM}\n"
        "Polish this morning brief item for 45-60 second total reading time across all items.\n"
        "Keep facts intact. Improve readability and narrative flow. One tight paragraph."
    )


def brief_item_enhancement_instructions() -> str:
    return (
        f"{ANALYST_SYSTEM}\n"
        "Polish one Morning Brief intelligence item. Return exactly three labeled lines:\n"
        "TITLE: 2-5 word analyst section title\n"
        "SUMMARY: 80-140 words covering what changed, why it matters, why now, what to watch\n"
        "WHY_IT_MATTERS: one crisp sentence on strategic relevance\n"
        "No bullets. No transcript quotes. No meta commentary."
    )


def brief_item_enhancement_input(request) -> str:
    return (
        f"Current title: {request.title}\n"
        f"Theme: {request.theme_label}\n"
        f"Current summary: {request.executive_summary[:500]}\n"
        f"Why it matters: {request.why_it_matters}\n"
        f"Sources: {', '.join(request.sources[:6])}\n"
        f"Speakers: {', '.join(request.speakers[:6])}\n"
        f"Novelty: {request.novelty_classification}\n"
        f"Importance: {request.importance_band}\n"
        f"Corroboration: {request.corroboration_count}\n"
        f"Evidence: {' | '.join(request.claim_excerpts[:4])}"
    )


def morning_brief_wording_input(request) -> str:
    return (
        f"Title: {request.title}\n"
        f"What changed: {request.what_changed}\n"
        f"Why you should care: {request.why_you_care}\n"
        f"Evidence: {request.evidence_summary}\n"
        "Return only the polished 'what changed' paragraph."
    )