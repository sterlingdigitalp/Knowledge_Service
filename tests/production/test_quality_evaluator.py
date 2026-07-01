from knowledge_service.analyst.synthesis.items.engine import IntelligenceItemEngine
from knowledge_service.analyst.synthesis.themes.discovery import ThemeDiscoveryEngine
from knowledge_service.analyst.synthesis.themes.evolution import ThemeEvolutionEngine
from knowledge_service.intelligence.state import FileStateStore
from knowledge_service.production.briefing.quality import BriefQualityEvaluator
from knowledge_service.production.briefing.morning_brief_v3 import MorningBriefV3Generator
from knowledge_service.production.personalization.feedback import UserFeedbackEngine
from knowledge_service.production.personalization.store import PersonalizationStore

from tests.analyst.synthesis.conftest import build_scored_claims_and_clusters


def _build_brief(state_dir):
    scored, clusters = build_scored_claims_and_clusters(state_dir)
    themes = ThemeDiscoveryEngine().discover(scored)
    evolutions = ThemeEvolutionEngine().evaluate(themes, [])
    items = IntelligenceItemEngine().synthesize(scored, themes, clusters, evolutions)
    brief = MorningBriefV3Generator().generate(items, claims_synthesized=len(scored))
    return brief, items


def test_quality_evaluator_scores_brief_dimensions(phase32_state_dir):
    brief, items = _build_brief(phase32_state_dir)
    quality = BriefQualityEvaluator().evaluate(brief, items, len(items) * 4)

    assert 5 <= quality["items_selected"] <= 10
    assert quality["item_count_ok"] is True
    assert 45 <= quality["reading_time_seconds"] <= 60
    assert quality["reading_time_ok"] is True
    assert quality["duplicate_titles"] == 0
    assert 0.0 <= quality["overall_score"] <= 1.0
    assert quality["signal_to_noise"] > 0
    assert quality["evidence_quality"] > 0
    assert quality["compression"] == brief.compression_ratio


def test_quality_evaluator_counts_personal_relevance_hits(phase32_state_dir):
    brief, items = _build_brief(phase32_state_dir)
    store = PersonalizationStore(FileStateStore(phase32_state_dir))
    feedback = UserFeedbackEngine(store)

    lead = brief.items[0]
    feedback.tell_me_more(lead.intelligence_item_id)

    quality = BriefQualityEvaluator().evaluate(
        brief,
        items,
        len(items) * 4,
        store,
    )

    assert quality["personal_relevance_hits"] >= 1
    brief.quality_score = quality["overall_score"]
    assert brief.quality_score > 0