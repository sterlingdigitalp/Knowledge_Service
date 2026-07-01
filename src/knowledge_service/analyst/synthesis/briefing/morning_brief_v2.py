"""Morning Intelligence Brief v2 — intelligence items, not claims."""

from __future__ import annotations

from typing import List, Sequence

from ....intelligence.models import now_iso, stable_id
from ..models import IntelligenceBrief, IntelligenceBriefEntry, IntelligenceItem


MIN_ITEMS = 5
MAX_ITEMS = 15
TARGET_READING_SECONDS = 60
WORDS_PER_SECOND = 3.2
MAX_WORDS = int(TARGET_READING_SECONDS * WORDS_PER_SECOND)


class IntelligenceBriefGenerator:
    """Generate a concise development-oriented morning brief."""

    def generate(
        self,
        items: Sequence[IntelligenceItem],
        pipeline_run_id: str = "",
        claims_synthesized: int = 0,
    ) -> IntelligenceBrief:
        ranked = sorted(
            items,
            key=lambda row: (row.importance_score, row.corroboration_count, row.star_rating),
            reverse=True,
        )

        selected: List[IntelligenceBriefEntry] = []
        used_profiles: set[str] = set()
        word_budget = 0

        for item in ranked:
            if len(selected) >= MAX_ITEMS:
                break
            entry = _to_entry(item)
            entry_words = _word_count(entry)
            if word_budget + entry_words > MAX_WORDS and len(selected) >= MIN_ITEMS:
                continue
            selected.append(entry)
            word_budget += entry_words
            used_profiles.update(item.profile_names)

        if len(selected) < MIN_ITEMS:
            for item in ranked:
                if len(selected) >= MIN_ITEMS:
                    break
                if any(entry.intelligence_item_id == item.item_id for entry in selected):
                    continue
                selected.append(_to_entry(item))

        reading_time = max(45, min(60, int(word_budget / WORDS_PER_SECOND) + 5))
        compression = round(claims_synthesized / max(len(selected), 1), 1)

        return IntelligenceBrief(
            brief_id=stable_id("intel-brief", now_iso()),
            generated_at=now_iso(),
            reading_time_seconds=reading_time,
            total_items=len(selected),
            items=selected,
            compression_ratio=compression,
            claims_synthesized=claims_synthesized,
            pipeline_run_id=pipeline_run_id,
        )


def _to_entry(item: IntelligenceItem) -> IntelligenceBriefEntry:
    primary_profile = item.profile_names[0] if item.profile_names else "General"
    primary_profile_id = item.profile_ids[0] if item.profile_ids else "general"

    evidence_speakers = ", ".join(item.speakers[:4]) if item.speakers else "multiple speakers"
    evidence_sources = ", ".join(item.sources[:3]) if item.sources else "multiple sources"
    evidence_summary = f"Supporting evidence: {evidence_speakers} ({evidence_sources})"

    return IntelligenceBriefEntry(
        entry_id=stable_id("intel-brief-entry", item.item_id),
        intelligence_item_id=item.item_id,
        profile_id=primary_profile_id,
        profile_name=primary_profile,
        title=item.title,
        what_changed=item.executive_summary,
        why_you_care=item.why_it_matters,
        why_surfaced=item.why_surfaced,
        evidence_summary=evidence_summary,
        star_rating=item.star_rating,
        importance_band=item.importance_band,
        corroborated_by=item.corroboration_count,
        explainability={
            "matched": item.theme_label,
            "keywords": item.supporting_evidence[:3],
            "novelty": item.novelty_classification,
            "importance": item.importance_band,
            "corroborated_by": item.corroboration_count,
            "historical_context": item.historical_developments,
            "evidence_type": "timestamped_transcript_citations",
            "claim_count": item.claim_count,
            "confidence": item.confidence,
        },
    )


def _word_count(entry: IntelligenceBriefEntry) -> int:
    return len(
        f"{entry.title} {entry.what_changed} {entry.why_you_care} {entry.why_surfaced}".split()
    )