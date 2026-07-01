from knowledge_service.analyst.synthesis.items.engine import IntelligenceItemEngine
from knowledge_service.analyst.synthesis.themes.discovery import ThemeDiscoveryEngine
from knowledge_service.analyst.synthesis.themes.evolution import ThemeEvolutionEngine
from knowledge_service.production.briefing.morning_brief_v3 import (
    MAX_ITEMS,
    MIN_ITEMS,
    MorningBriefV3Generator,
)

from tests.analyst.synthesis.conftest import build_scored_claims_and_clusters


def _build_items(state_dir):
    scored, clusters = build_scored_claims_and_clusters(state_dir)
    themes = ThemeDiscoveryEngine().discover(scored)
    evolutions = ThemeEvolutionEngine().evaluate(themes, [])
    return IntelligenceItemEngine().synthesize(scored, themes, clusters, evolutions), len(scored)


def test_morning_brief_v3_item_count_reading_time_and_version(phase32_state_dir):
    items, claims_count = _build_items(phase32_state_dir)
    assert len(items) >= MIN_ITEMS

    brief = MorningBriefV3Generator().generate(
        items,
        pipeline_run_id="phase5-test",
        claims_synthesized=claims_count,
    )

    assert MIN_ITEMS <= brief.total_items <= MAX_ITEMS
    assert brief.reading_time_seconds <= 60
    assert brief.version == "3.0"
    assert brief.pipeline_run_id == "phase5-test"
    assert brief.compression_ratio >= 10


def test_morning_brief_v3_deduplicates_titles(phase32_state_dir):
    items, claims_count = _build_items(phase32_state_dir)
    duplicate_title = "Inference Economics Update"
    for index, item in enumerate(items[:3]):
        item.title = duplicate_title
        item.importance_score = 0.9 - (index * 0.01)
        item.star_rating = 5

    brief = MorningBriefV3Generator().generate(items, claims_synthesized=claims_count)
    titles = [entry.title.lower() for entry in brief.items]

    assert titles.count(duplicate_title.lower()) == 1
    assert len(titles) == len(set(titles))


def test_morning_brief_v3_entries_reference_intelligence_items(phase32_state_dir):
    items, claims_count = _build_items(phase32_state_dir)
    brief = MorningBriefV3Generator().generate(items, claims_synthesized=claims_count)
    item_ids = {item.item_id for item in items}

    assert brief.items
    assert brief.narrative_flow
    for entry in brief.items:
        assert entry.intelligence_item_id in item_ids
        assert entry.title
        assert entry.what_changed
        assert entry.why_you_care
        assert entry.why_surfaced
        assert entry.evidence_summary
        assert entry.explainability.get("claim_count", 0) >= 2