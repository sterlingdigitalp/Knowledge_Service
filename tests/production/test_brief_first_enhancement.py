import copy

from knowledge_service.analyst.synthesis.models import IntelligenceItem
from knowledge_service.intelligence.state import FileStateStore
from knowledge_service.production.briefing.morning_brief_v3 import MorningBriefV3Generator
from knowledge_service.production.llm.analyst_provider import AnalystLLMProvider
from knowledge_service.production.llm.brief_enhancer import BriefItemEnhancer
from knowledge_service.production.llm.budget import LLMBudgetConfig, LLMRuntimeBudget


def _item(item_id: str, title: str, importance: float = 0.9) -> IntelligenceItem:
    return IntelligenceItem(
        item_id=item_id,
        title=title,
        executive_summary=f"Summary for {title}",
        why_surfaced="Matched theme",
        why_it_matters="Strategic relevance",
        novelty_score=0.8,
        novelty_classification="new",
        importance_score=importance,
        importance_band="high",
        confidence=0.8,
        corroboration_count=2,
        contradiction_count=0,
        theme_id=f"theme-{item_id}",
        theme_label="inference economics",
        profile_ids=["p1"],
        profile_names=["General"],
        supporting_claim_ids=[f"claim-{item_id}"],
        supporting_evidence=[{"excerpt": "signal", "speaker": "A", "source": "Pod"}],
        timestamped_citations=[],
        speakers=["A"],
        sources=["Pod"],
        contradictions=[],
        historical_developments=[],
        star_rating=5,
        claim_count=1,
    )


def test_select_items_before_enhancement_limits_candidates():
    items = [_item(f"i{n}", f"Topic {n}", importance=0.9 - n * 0.01) for n in range(20)]
    selected = MorningBriefV3Generator().select_items(items)
    assert 5 <= len(selected) <= 10


def test_enhancer_only_touches_selected_items(tmp_path):
    state = FileStateStore(tmp_path)
    items = [_item(f"i{n}", f"Topic {n}") for n in range(8)]
    selected = MorningBriefV3Generator().select_items(items)[:5]
    budget = LLMRuntimeBudget(config=LLMBudgetConfig(max_live_llm_items=5, max_live_llm_calls_per_run=20))
    enhancer = BriefItemEnhancer(AnalystLLMProvider(), state, budget=budget)
    enhanced, result = enhancer.enhance_selected(copy.deepcopy(selected))
    assert len(enhanced) == 5
    assert result.items_enhanced <= 5


def test_second_run_uses_cache_without_live_calls(tmp_path):
    state = FileStateStore(tmp_path)
    items = [_item("i1", "Inference Economics")]
    enhancer = BriefItemEnhancer(AnalystLLMProvider(), state)
    enhancer.enhance_selected(copy.deepcopy(items))
    budget = LLMRuntimeBudget()
    enhancer2 = BriefItemEnhancer(AnalystLLMProvider(), state, budget=budget)
    _, result = enhancer2.enhance_selected(copy.deepcopy(items))
    assert result.cache_hits == 1
    assert result.items_enhanced_cached == 1