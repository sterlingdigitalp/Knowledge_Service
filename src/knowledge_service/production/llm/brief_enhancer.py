"""Enhance only final Morning Brief items — cache-first, budget-aware."""

from __future__ import annotations

import copy
from typing import List, Tuple

from ...analyst.synthesis.models import IntelligenceItem
from ...intelligence.models import now_iso
from ...intelligence.state import FileStateStore
from .budget import LLMRuntimeBudget
from .cache import PROMPT_VERSION, CachedBriefEnhancement, LLMEnhancementCache, claim_fingerprint
from .config import load_llm_config
from .provider import BriefItemEnhancementRequest, LLMProvider


LIVE_PROVIDERS = frozenset({"xai_responses", "openai_compatible"})


class BriefItemEnhancer:
    """Grok edits only the handful of items selected for the Morning Brief."""

    def __init__(
        self,
        llm: LLMProvider,
        state: FileStateStore,
        *,
        budget: LLMRuntimeBudget | None = None,
    ):
        self.llm = llm
        self.cache = LLMEnhancementCache(state)
        self.budget = budget or LLMRuntimeBudget()
        self.model = load_llm_config().model
        self.prompt_version = PROMPT_VERSION

    def enhance_selected(self, items: List[IntelligenceItem]) -> Tuple[List[IntelligenceItem], LLMRuntimeBudget]:
        enhanced: List[IntelligenceItem] = []
        live = self.llm.name in LIVE_PROVIDERS

        for item in items:
            if self.budget.runtime_exceeded():
                self.budget.mark_timed_out()

            cached = self.cache.get(
                item_id=item.item_id,
                theme_id=item.theme_id,
                supporting_claim_ids=item.supporting_claim_ids,
                prompt_version=self.prompt_version,
                model=self.model,
            )
            if cached is not None:
                self.budget.record_cache_hit()
                enhanced.append(self._apply(item, cached.title, cached.executive_summary, cached.why_it_matters))
                continue

            self.budget.record_cache_miss()

            if live and not self.budget.can_enhance_live_item():
                self.budget.record_skipped()
                enhanced.append(copy.deepcopy(item))
                continue

            request = self._to_request(item)
            if live:
                result = self.llm.enhance_brief_item(request)
                self.budget.record_live_call()
                self.budget.record_live_item()
            else:
                result = self.llm.enhance_brief_item(request)
                self.budget.record_local_item()

            self.cache.put(CachedBriefEnhancement(
                item_id=item.item_id,
                theme_id=item.theme_id,
                claim_fingerprint=claim_fingerprint(item.supporting_claim_ids),
                prompt_version=self.prompt_version,
                model=self.model,
                title=result.title,
                executive_summary=result.executive_summary,
                why_it_matters=result.why_it_matters,
                provider=result.provider or self.llm.name,
                cached_at=now_iso(),
            ))
            enhanced.append(self._apply(item, result.title, result.executive_summary, result.why_it_matters))

        self.budget.finalize()
        return enhanced, self.budget

    def _to_request(self, item: IntelligenceItem) -> BriefItemEnhancementRequest:
        theme_keywords = [word for word in item.theme_label.split() if len(word) > 3]
        return BriefItemEnhancementRequest(
            theme_label=item.theme_label,
            title=item.title,
            executive_summary=item.executive_summary,
            why_it_matters=item.why_it_matters,
            keywords=theme_keywords or item.theme_label.split(),
            entities=[speaker for speaker in item.speakers if speaker and speaker.lower() != "unknown"],
            sources=item.sources,
            speakers=item.speakers,
            claim_excerpts=[ev.get("excerpt", "") for ev in item.supporting_evidence[:5]],
            novelty_classification=item.novelty_classification,
            importance_band=item.importance_band,
            corroboration_count=item.corroboration_count,
            contradictions=item.contradiction_count,
            theme_evolution=item.theme_evolution.explanation if item.theme_evolution else "",
        )

    def _apply(
        self,
        item: IntelligenceItem,
        title: str,
        summary: str,
        why_it_matters: str,
    ) -> IntelligenceItem:
        updated = copy.deepcopy(item)
        updated.title = title
        updated.executive_summary = summary
        updated.why_it_matters = why_it_matters
        updated.why_surfaced = f"Matched: {title}. {item.why_surfaced}"
        return updated