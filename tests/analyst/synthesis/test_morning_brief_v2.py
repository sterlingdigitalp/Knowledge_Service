from knowledge_service.analyst.synthesis.briefing.morning_brief_v2 import (
    MAX_ITEMS,
    MIN_ITEMS,
    IntelligenceBriefGenerator,
)
from knowledge_service.analyst.synthesis.items.engine import IntelligenceItemEngine
from knowledge_service.analyst.synthesis.themes.discovery import ThemeDiscoveryEngine
from knowledge_service.analyst.synthesis.themes.evolution import ThemeEvolutionEngine

from .conftest import build_scored_claims_and_clusters


def _build_items(state_dir):
    scored, clusters = build_scored_claims_and_clusters(state_dir)
    themes = ThemeDiscoveryEngine().discover(scored)
    evolutions = ThemeEvolutionEngine().evaluate(themes, [])
    return IntelligenceItemEngine().synthesize(scored, themes, clusters, evolutions), len(scored)


def test_morning_brief_v2_item_count_and_reading_time(phase32_state_dir):
    items, claims_count = _build_items(phase32_state_dir)
    assert len(items) >= MIN_ITEMS

    brief = IntelligenceBriefGenerator().generate(
        items,
        pipeline_run_id="test-run",
        claims_synthesized=claims_count,
    )

    assert MIN_ITEMS <= brief.total_items <= MAX_ITEMS
    assert brief.reading_time_seconds <= 60
    assert brief.version == "2.0"
    assert brief.compression_ratio >= 10
    assert brief.pipeline_run_id == "test-run"


def test_morning_brief_v2_entries_reference_intelligence_items(phase32_state_dir):
    items, claims_count = _build_items(phase32_state_dir)
    brief = IntelligenceBriefGenerator().generate(items, claims_synthesized=claims_count)
    item_ids = {item.item_id for item in items}

    assert brief.items
    for entry in brief.items:
        assert entry.intelligence_item_id in item_ids
        assert entry.title
        assert entry.what_changed
        assert entry.why_you_care
        assert entry.why_surfaced
        assert entry.evidence_summary
        assert entry.explainability.get("claim_count", 0) >= 2