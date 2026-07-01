from knowledge_service.analyst.synthesis.items.engine import IntelligenceItemEngine
from knowledge_service.analyst.synthesis.themes.discovery import ThemeDiscoveryEngine
from knowledge_service.analyst.synthesis.themes.evolution import ThemeEvolutionEngine

from .conftest import build_scored_claims_and_clusters


def test_claims_merge_into_intelligence_items(phase32_state_dir):
    scored, clusters = build_scored_claims_and_clusters(phase32_state_dir)
    themes = ThemeDiscoveryEngine().discover(scored)
    evolutions = ThemeEvolutionEngine().evaluate(themes, [])

    items = IntelligenceItemEngine().synthesize(scored, themes, clusters, evolutions)

    assert themes
    assert items
    assert len(items) >= 5
    for item in items:
        assert item.item_id
        assert item.title
        assert item.executive_summary
        assert item.why_surfaced
        assert item.why_it_matters
        assert item.claim_count >= 2
        assert len(item.supporting_claim_ids) == item.claim_count
        assert item.supporting_evidence
        assert item.timestamped_citations
        assert item.importance_score >= 0.55


def test_items_reference_theme_and_cluster_context(phase32_state_dir):
    scored, clusters = build_scored_claims_and_clusters(phase32_state_dir)
    themes = ThemeDiscoveryEngine().discover(scored)
    evolutions = ThemeEvolutionEngine().evaluate(themes, [])
    items = IntelligenceItemEngine().synthesize(scored, themes, clusters, evolutions)

    themed = [item for item in items if item.theme_id]
    assert themed
    item = themed[0]
    assert item.theme_label
    assert item.supporting_claim_ids
    assert all(
        row.get("claim_id") in item.supporting_claim_ids
        for row in item.supporting_evidence
    )