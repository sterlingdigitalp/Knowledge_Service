from knowledge_service.analyst.pipeline import IntelligenceAnalystPipeline
from knowledge_service.analyst.synthesis.briefing.deep_dive_v2 import IntelligenceDeepDiveGenerator
from knowledge_service.analyst.synthesis.items.engine import IntelligenceItemEngine
from knowledge_service.analyst.synthesis.themes.discovery import ThemeDiscoveryEngine
from knowledge_service.analyst.synthesis.themes.evolution import ThemeEvolutionEngine

from .conftest import build_scored_claims_and_clusters


def test_deep_dive_v2_expands_intelligence_item_not_claim(phase32_state_dir):
    scored, clusters = build_scored_claims_and_clusters(phase32_state_dir)
    claims = [item.claim for item in scored]
    themes = ThemeDiscoveryEngine().discover(scored)
    evolutions = ThemeEvolutionEngine().evaluate(themes, [])
    items = IntelligenceItemEngine().synthesize(scored, themes, clusters, evolutions)
    assert items

    item = items[0]
    dive = IntelligenceDeepDiveGenerator().generate(item.item_id, items, scored, claims)

    assert dive is not None
    assert dive.intelligence_item_id == item.item_id
    assert dive.title == item.title
    assert dive.executive_summary == item.executive_summary
    assert dive.supporting_claims
    assert all(row["claim_id"] in item.supporting_claim_ids for row in dive.supporting_claims)
    assert dive.analyst_briefing
    assert "Claims synthesized" in dive.analyst_briefing
    assert dive.explainability.get("claim_count") == item.claim_count
    assert not hasattr(dive, "claim_id")


def test_deep_dive_v2_unknown_item_returns_none(phase32_state_dir):
    scored, clusters = build_scored_claims_and_clusters(phase32_state_dir)
    claims = [item.claim for item in scored]
    themes = ThemeDiscoveryEngine().discover(scored)
    evolutions = ThemeEvolutionEngine().evaluate(themes, [])
    items = IntelligenceItemEngine().synthesize(scored, themes, clusters, evolutions)

    dive = IntelligenceDeepDiveGenerator().generate("missing-intel-item", items, scored, claims)

    assert dive is None


def test_pipeline_intelligence_deep_dive_uses_item_id(phase32_state_dir):
    pipeline = IntelligenceAnalystPipeline(str(phase32_state_dir))
    result = pipeline.run()
    assert result.intelligence_brief and result.intelligence_brief.items

    item_id = result.intelligence_brief.items[0].intelligence_item_id
    dive = pipeline.intelligence_deep_dive(item_id)

    assert dive is not None
    assert dive.intelligence_item_id == item_id
    assert dive.supporting_claims