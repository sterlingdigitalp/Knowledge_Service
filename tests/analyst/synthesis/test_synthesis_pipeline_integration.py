from knowledge_service.analyst.pipeline import IntelligenceAnalystPipeline
from knowledge_service.analyst.synthesis.store import SynthesisStore
from knowledge_service.intelligence.state import FileStateStore


def test_full_synthesis_pipeline_on_phase32_state_copy(phase32_state_dir):
    pipeline = IntelligenceAnalystPipeline(str(phase32_state_dir))

    result = pipeline.run()

    assert result.status == "completed"
    assert result.claims_extracted > 0
    assert result.synthesis is not None
    assert result.synthesis.themes_discovered > 0
    assert result.synthesis.intelligence_items > 0
    assert result.intelligence_brief is not None
    assert 5 <= result.intelligence_brief.total_items <= 15
    assert result.intelligence_brief.reading_time_seconds <= 60
    assert result.synthesis.compression_ratio >= 10
    assert result.latency_seconds["synthesis"] > 0

    store = SynthesisStore(FileStateStore(phase32_state_dir))
    summary = store.summary(claims_count=result.claims_scored)

    assert summary["themes"] > 0
    assert summary["intelligence_items"] > 0
    assert summary["briefs"] == 1
    assert summary["latest_brief_items"] == result.intelligence_brief.total_items
    assert summary["reading_time_seconds"] <= 60
    assert summary["runs"] == 1
    assert store.load_items()
    assert store.load_themes()
    assert store.load_theme_history()


def test_synthesis_pipeline_deep_dive_after_run(phase32_state_dir):
    pipeline = IntelligenceAnalystPipeline(str(phase32_state_dir))
    result = pipeline.run()
    item_id = result.intelligence_brief.items[0].intelligence_item_id

    dive = pipeline.intelligence_deep_dive(item_id)

    assert dive is not None
    assert dive.intelligence_item_id == item_id
    assert dive.timestamped_sources
    assert dive.timeline