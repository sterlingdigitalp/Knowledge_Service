"""Production enhancement layer — neural embeddings, brief-first LLM, personalization."""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from ..analyst.pipeline import PipelineResult
from ..analyst.store import AnalystStore
from ..analyst.synthesis.models import IntelligenceItem
from ..analyst.synthesis.store import SynthesisStore
from ..intelligence.models import now_iso
from ..intelligence.state import FileStateStore
from .briefing.morning_brief_v3 import IntelligenceBriefV3, MorningBriefV3Generator
from .briefing.quality import BriefQualityEvaluator
from .embeddings.registry import configure_embeddings
from .llm.brief_enhancer import BriefItemEnhancer
from .llm.budget import LLMRuntimeBudget
from .llm.registry import get_llm_provider
from .personalization.feedback import UserFeedbackEngine
from .personalization.ranking import PersonalizedRankingEngine
from .personalization.store import PersonalizationStore
from .store import ProductionStore
from .trends.acceleration import TrendAccelerationEngine

try:
    from ..intelligence_v2 import apply_intelligence_layer_v2, is_il2_enabled
except ImportError:  # pragma: no cover
    def is_il2_enabled() -> bool:
        return False

    def apply_intelligence_layer_v2(items, **kwargs):
        return list(items), type("IL2Result", (), {"to_dict": lambda self: {"enabled": False}})()

try:
    from ..runtime3 import apply_runtime3_layer, is_runtime3_enabled
except ImportError:  # pragma: no cover
    def is_runtime3_enabled() -> bool:
        return False

    def apply_runtime3_layer(**kwargs):
        return type("R3Result", (), {"to_dict": lambda self: {"enabled": False}, "stories": []})(), None, []


@dataclass
class ProductionResult:
    intelligence_brief_v3: Optional[IntelligenceBriefV3] = None
    items_enhanced: int = 0
    themes_renamed: int = 0
    trends: List[Dict[str, Any]] = field(default_factory=list)
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    embedding_provider: str = "local_neural"
    llm_provider: str = "analyst_heuristic"
    llm_budget: Dict[str, Any] = field(default_factory=dict)
    latency_seconds: Dict[str, float] = field(default_factory=dict)
    intelligence_v2: Dict[str, Any] = field(default_factory=dict)
    runtime3: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intelligence_brief_v3": self.intelligence_brief_v3.to_dict() if self.intelligence_brief_v3 else None,
            "items_enhanced": self.items_enhanced,
            "themes_renamed": self.themes_renamed,
            "trends": list(self.trends),
            "quality_metrics": dict(self.quality_metrics),
            "embedding_provider": self.embedding_provider,
            "llm_provider": self.llm_provider,
            "llm_budget": dict(self.llm_budget),
            "latency_seconds": dict(self.latency_seconds),
            "intelligence_v2": dict(self.intelligence_v2),
            "runtime3": dict(self.runtime3),
        }


class ProductionEnhancementLayer:
    """Phase 5.1.2 — deterministic intelligence first, Grok edits the final brief only."""

    def __init__(self, state_dir: str):
        self.state = FileStateStore(state_dir)
        self.analyst_store = AnalystStore(self.state)
        self.synthesis_store = SynthesisStore(self.state)
        self.production_store = ProductionStore(self.state)
        self.personalization_store = PersonalizationStore(self.state)
        self.feedback = UserFeedbackEngine(self.personalization_store)
        self.ranking = PersonalizedRankingEngine(self.personalization_store)
        self.trends = TrendAccelerationEngine()
        self.brief_generator = MorningBriefV3Generator()
        self.quality = BriefQualityEvaluator()
        self.llm = get_llm_provider(state_dir=state_dir)

    def enhance(
        self,
        pipeline_result: PipelineResult,
        *,
        ranked_items: Optional[Sequence[IntelligenceItem]] = None,
        brief_override: Optional[IntelligenceBriefV3] = None,
    ) -> ProductionResult:
        started = time.perf_counter()
        result = ProductionResult(
            embedding_provider=configure_embeddings("local_neural").name,
            llm_provider=self.llm.name,
        )

        embed_started = time.perf_counter()
        self._reembed_corpus()
        result.latency_seconds["neural_reembedding"] = round(time.perf_counter() - embed_started, 3)

        rank_started = time.perf_counter()
        items = self.synthesis_store.load_items()
        self.ranking.learn_from_feedback(items)
        if ranked_items is None:
            ranked_items = self.ranking.rank(items)
            self.synthesis_store.save_items(list(ranked_items))
        else:
            ranked_items = list(ranked_items)
        result.latency_seconds["personalized_ranking"] = round(time.perf_counter() - rank_started, 3)

        if is_il2_enabled():
            il2_started = time.perf_counter()
            ranked_items, il2_result = apply_intelligence_layer_v2(ranked_items)
            result.intelligence_v2 = il2_result.to_dict() if hasattr(il2_result, "to_dict") else dict(il2_result)
            self.synthesis_store.save_items(list(ranked_items))
            result.latency_seconds["intelligence_v2"] = round(time.perf_counter() - il2_started, 3)

        if is_runtime3_enabled():
            r3_started = time.perf_counter()
            r3_result, r3_brief, _r3_items = apply_runtime3_layer(state_dir=str(self.state.root))
            result.runtime3 = r3_result.to_dict() if hasattr(r3_result, "to_dict") else {}
            if r3_brief is not None:
                result.runtime3["brief"] = r3_brief.to_dict()
            result.latency_seconds["runtime3"] = round(time.perf_counter() - r3_started, 3)

        themes = self.synthesis_store.load_themes()
        result.themes_renamed = len(themes)

        trend_started = time.perf_counter()
        evolutions = pipeline_result.synthesis.theme_evolutions if pipeline_result.synthesis else []
        history = self.production_store.load_trend_history()
        trends = self.trends.analyze(themes, evolutions, history)
        self.production_store.append_trend_snapshot(self.trends.snapshot(themes, trends))
        result.trends = trends[:10]
        result.latency_seconds["trend_acceleration"] = round(time.perf_counter() - trend_started, 3)

        brief_started = time.perf_counter()
        if brief_override is not None:
            brief = brief_override
            result.items_enhanced = 0
            result.llm_budget = {"calls_used": 0, "items_enhanced": 0, "cache_hits": 0}
            result.quality_metrics = {"overall_score": brief.quality_score, "freshness_gate": "empty_signal"}
            self.production_store.save_brief(brief)
            result.intelligence_brief_v3 = brief
            result.latency_seconds["brief_v3"] = round(time.perf_counter() - brief_started, 3)
        else:
            selected_items = self.brief_generator.select_items(ranked_items)
            enhancer = BriefItemEnhancer(self.llm, self.state)
            llm_cap = enhancer.budget.config.max_live_llm_items
            llm_candidates = selected_items[:llm_cap]

            llm_started = time.perf_counter()
            enhanced_subset, budget = enhancer.enhance_selected(llm_candidates)
            enhanced_index = {item.item_id: item for item in enhanced_subset}
            brief_items = [enhanced_index.get(item.item_id, item) for item in selected_items]
            result.items_enhanced = budget.items_enhanced
            result.llm_budget = budget.summary()
            self.production_store.save_llm_budget(budget.summary())
            result.latency_seconds["brief_llm_enhancement"] = round(time.perf_counter() - llm_started, 3)

            self._persist_enhanced_items(list(items), enhanced_subset)

            claims_count = pipeline_result.claims_scored or len(self.analyst_store.load_claims())
            brief = self.brief_generator.generate(
                brief_items,
                pipeline_run_id=pipeline_result.run_id,
                claims_synthesized=claims_count,
                llm_enhanced=budget.items_enhanced > 0,
            )
            quality = self.quality.evaluate(brief, list(ranked_items), claims_count, self.personalization_store)
            brief.quality_score = quality.get("overall_score", 0.0)
            self.production_store.save_brief(brief)
            result.intelligence_brief_v3 = brief
            result.quality_metrics = quality
            result.latency_seconds["brief_v3"] = round(time.perf_counter() - brief_started, 3)
        result.latency_seconds["total"] = round(time.perf_counter() - started, 3)

        self.production_store.record_run({
            "started_at": now_iso(),
            "result": result.to_dict(),
        })
        return result

    def _persist_enhanced_items(
        self,
        ranked_items: List[IntelligenceItem],
        enhanced_items: List[IntelligenceItem],
    ) -> None:
        """Write LLM-enhanced copies back only for brief-selected items."""
        enhanced_index = {item.item_id: item for item in enhanced_items}
        merged = []
        for item in ranked_items:
            if item.item_id in enhanced_index:
                merged.append(enhanced_index[item.item_id])
            else:
                merged.append(item)
        self.synthesis_store.save_items(merged)

    def enhance_intelligence_items(self, items: List[IntelligenceItem]) -> List[IntelligenceItem]:
        """Legacy bulk path for benchmarks — still budget-limited."""
        enhancer = BriefItemEnhancer(self.llm, self.state)
        enhanced, _ = enhancer.enhance_selected(copy.deepcopy(items))
        return enhanced

    def _reembed_corpus(self) -> None:
        claims = self.analyst_store.load_claims()
        corpus = [claim.claim_text for claim in claims]
        provider = configure_embeddings("local_neural", corpus)
        for claim in claims:
            claim.embedding = provider.embed(claim.claim_text)
        self.analyst_store.save_claims(claims)

        scored = self.analyst_store.load_scored_claims()
        for item in scored:
            item.claim.embedding = provider.embed(item.claim.claim_text)
        self.analyst_store.save_scored_claims(scored)

        themes = self.synthesis_store.load_themes()
        claim_index = {claim.claim_id: claim for claim in claims}
        for theme in themes:
            texts = []
            for claim_id in theme.claim_ids[:20]:
                claim = claim_index.get(claim_id)
                if claim:
                    texts.append(claim.claim_text)
            if texts:
                vectors = [provider.embed(text) for text in texts]
                theme.centroid_embedding = _average_vector(vectors)
        self.synthesis_store.save_themes(themes)


def _average_vector(vectors: List[List[float]]) -> List[float]:
    if not vectors:
        return []
    size = len(vectors[0])
    total = [0.0] * size
    for vector in vectors:
        for index, value in enumerate(vector[:size]):
            total[index] += value
    count = float(len(vectors))
    return [value / count for value in total]