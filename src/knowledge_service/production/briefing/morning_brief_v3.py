"""Morning Intelligence Brief v3 — publication-quality, personalized."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Sequence

from ...analyst.synthesis.models import IntelligenceBriefEntry
from ...intelligence.models import now_iso, stable_id

if TYPE_CHECKING:
    from ..llm.provider import LLMProvider


MIN_ITEMS = 5
MAX_ITEMS = 10
TARGET_SECONDS = 60
WORDS_PER_SECOND = 3.3
MAX_WORDS = int(TARGET_SECONDS * WORDS_PER_SECOND)


@dataclass
class IntelligenceBriefV3:
    brief_id: str
    generated_at: str
    reading_time_seconds: int
    total_items: int
    items: List[IntelligenceBriefEntry]
    compression_ratio: float
    claims_synthesized: int
    quality_score: float = 0.0
    version: str = "3.0"
    pipeline_run_id: str = ""
    narrative_flow: List[str] = field(default_factory=list)
    brief_polish_applied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brief_id": self.brief_id,
            "generated_at": self.generated_at,
            "reading_time_seconds": self.reading_time_seconds,
            "total_items": self.total_items,
            "items": [item.to_dict() for item in self.items],
            "compression_ratio": self.compression_ratio,
            "claims_synthesized": self.claims_synthesized,
            "quality_score": self.quality_score,
            "version": self.version,
            "pipeline_run_id": self.pipeline_run_id,
            "narrative_flow": list(self.narrative_flow),
            "brief_polish_applied": self.brief_polish_applied,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntelligenceBriefV3":
        return cls(
            brief_id=str(data.get("brief_id") or ""),
            generated_at=str(data.get("generated_at") or ""),
            reading_time_seconds=int(data.get("reading_time_seconds") or 60),
            total_items=int(data.get("total_items") or 0),
            items=[IntelligenceBriefEntry.from_dict(item) for item in data.get("items") or []],
            compression_ratio=float(data.get("compression_ratio") or 0.0),
            claims_synthesized=int(data.get("claims_synthesized") or 0),
            quality_score=float(data.get("quality_score") or 0.0),
            version=str(data.get("version") or "3.0"),
            pipeline_run_id=str(data.get("pipeline_run_id") or ""),
            narrative_flow=list(data.get("narrative_flow") or []),
            brief_polish_applied=bool(data.get("brief_polish_applied")),
        )


class MorningBriefV3Generator:
    """Select 5-10 high-signal intelligence items with narrative flow."""

    def select_items(self, items: Sequence) -> List:
        """Deterministic selection before any live LLM enhancement."""
        ranked = list(items)
        selected: List = []
        seen_titles: set[str] = set()

        for item in ranked:
            if len(selected) >= MAX_ITEMS:
                break
            title_key = item.title.lower().strip()
            if title_key in seen_titles:
                continue
            if item.importance_score < 0.62:
                continue
            if item.star_rating < 3:
                continue
            selected.append(item)
            seen_titles.add(title_key)

        if len(selected) < MIN_ITEMS:
            for item in ranked:
                if len(selected) >= MIN_ITEMS:
                    break
                title_key = item.title.lower().strip()
                if title_key in seen_titles:
                    continue
                selected.append(item)
                seen_titles.add(title_key)
        return selected

    def generate(
        self,
        items: Sequence,
        *,
        pipeline_run_id: str = "",
        claims_synthesized: int = 0,
        quality_score: float = 0.0,
        llm_enhanced: bool = False,
    ) -> IntelligenceBriefV3:
        selected_items = list(items)
        selected: List[IntelligenceBriefEntry] = []
        seen_titles: set[str] = set()
        word_budget = 0

        for item in selected_items:
            if len(selected) >= MAX_ITEMS:
                break
            title_key = item.title.lower().strip()
            if title_key in seen_titles:
                continue
            entry = _to_entry(item)
            words = _word_count(entry)
            if word_budget + words > MAX_WORDS and len(selected) >= MIN_ITEMS:
                continue
            selected.append(entry)
            seen_titles.add(title_key)
            word_budget += words

        if len(selected) < MIN_ITEMS:
            for item in selected_items:
                if len(selected) >= MIN_ITEMS:
                    break
                title_key = item.title.lower().strip()
                if title_key in seen_titles:
                    continue
                selected.append(_to_entry(item))
                seen_titles.add(title_key)
                word_budget += _word_count(selected[-1])

        reading_time = max(45, min(60, int(word_budget / WORDS_PER_SECOND) + 3))
        compression = round(claims_synthesized / max(len(selected), 1), 1)
        flow = _narrative_flow(selected)

        return IntelligenceBriefV3(
            brief_id=stable_id("brief-v3", now_iso()),
            generated_at=now_iso(),
            reading_time_seconds=reading_time,
            total_items=len(selected),
            items=selected,
            compression_ratio=compression,
            claims_synthesized=claims_synthesized,
            quality_score=quality_score,
            pipeline_run_id=pipeline_run_id,
            narrative_flow=flow,
            brief_polish_applied=llm_enhanced,
        )


def _to_entry(item) -> IntelligenceBriefEntry:
    profile_name = item.profile_names[0] if item.profile_names else "General"
    profile_id = item.profile_ids[0] if item.profile_ids else "general"
    evidence_speakers = ", ".join(item.speakers[:4]) if item.speakers else "multiple speakers"
    evidence_sources = ", ".join(item.sources[:3]) if item.sources else "multiple sources"

    return IntelligenceBriefEntry(
        entry_id=stable_id("brief-v3-entry", item.item_id),
        intelligence_item_id=item.item_id,
        profile_id=profile_id,
        profile_name=profile_name,
        title=item.title,
        what_changed=item.executive_summary,
        why_you_care=item.why_it_matters,
        why_surfaced=item.why_surfaced,
        evidence_summary=f"Evidence: {evidence_speakers} ({evidence_sources})",
        star_rating=item.star_rating,
        importance_band=item.importance_band,
        corroborated_by=item.corroboration_count,
        explainability={
            "matched": item.theme_label,
            "novelty": item.novelty_classification,
            "novelty_score": item.novelty_score,
            "importance": item.importance_band,
            "importance_score": item.importance_score,
            "corroborated_by": item.corroboration_count,
            "confidence": item.confidence,
            "claim_count": item.claim_count,
            "historical_context": item.historical_developments,
            "evidence_type": "timestamped_transcript_citations",
        },
    )


def _word_count(entry: IntelligenceBriefEntry) -> int:
    return len(f"{entry.title} {entry.what_changed} {entry.why_you_care}".split())


def _narrative_flow(entries: List[IntelligenceBriefEntry]) -> List[str]:
    if not entries:
        return []
    lead = entries[0].title
    if len(entries) == 1:
        return [f"Lead development: {lead}"]
    middle = ", ".join(entry.title for entry in entries[1:-1]) if len(entries) > 2 else entries[1].title
    if len(entries) >= 3:
        return [
            f"Lead: {lead}",
            f"Supporting: {middle}",
            f"Also watch: {entries[-1].title}",
        ]
    return [f"Lead: {lead}", f"Also watch: {entries[-1].title}"]