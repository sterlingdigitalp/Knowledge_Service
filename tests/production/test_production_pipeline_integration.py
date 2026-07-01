from knowledge_service.intelligence.state import FileStateStore
from knowledge_service.production.inspector import inspect_production_runtime
from knowledge_service.production.pipeline import ProductionIntelligencePipeline
from knowledge_service.production.store import ProductionStore


def test_full_production_pipeline_on_phase32_state_copy(phase32_state_dir):
    pipeline = ProductionIntelligencePipeline(str(phase32_state_dir))

    result = pipeline.run(manual=True)

    assert result.analyst.status == "completed"
    assert result.analyst.claims_extracted > 0
    assert result.analyst.synthesis is not None
    assert result.analyst.synthesis.intelligence_items > 0

    production = result.production
    brief = production.intelligence_brief_v3

    assert brief is not None
    assert 5 <= brief.total_items <= 10
    assert brief.reading_time_seconds <= 60
    assert brief.version == "3.0"
    assert production.embedding_provider == "local_neural_tfidf"
    assert production.llm_provider == "analyst_heuristic"
    assert 0 < production.items_enhanced <= 5
    assert production.llm_budget.get("items_enhanced", production.items_enhanced) <= 5
    assert production.quality_metrics.get("overall_score", 0) >= 0.4
    assert production.latency_seconds["total"] > 0
    assert result.benchmark.get("improvement_delta") is not None

    store = ProductionStore(FileStateStore(phase32_state_dir))
    summary = store.summary()

    assert summary["briefs"] == 1
    assert summary["latest_items"] == brief.total_items
    assert summary["reading_time_seconds"] <= 60
    assert summary["quality_score"] > 0
    assert summary["trend_snapshots"] >= 1
    assert summary["benchmark_available"] is True


def test_production_pipeline_learning_loop_and_conversation(phase32_state_dir):
    pipeline = ProductionIntelligencePipeline(str(phase32_state_dir))
    first = pipeline.run(manual=True)
    brief = first.production.intelligence_brief_v3
    assert brief and len(brief.items) >= 2

    lead_id = brief.items[0].intelligence_item_id
    runner_id = brief.items[1].intelligence_item_id
    dismiss_id = brief.items[2].intelligence_item_id if len(brief.items) > 2 else None

    pipeline.record_tell_me_more(lead_id, duration_seconds=180)
    pipeline.feedback.save(runner_id)
    if dismiss_id:
        pipeline.feedback.dismiss(dismiss_id)

    session = pipeline.start_conversation(lead_id)
    assert session is not None
    assert session["intelligence_item_id"] == lead_id

    follow_up = pipeline.continue_conversation(session["session_id"], "Are there competing viewpoints?")
    assert follow_up is not None
    assert len(follow_up["messages"]) >= 3

    second = pipeline.rerun_with_learning()
    second_brief = second.production.intelligence_brief_v3
    assert second_brief is not None

    prefs = pipeline.personalization.load_preferences()
    assert lead_id in prefs["tell_me_more_items"]
    assert runner_id in prefs["saved_items"]
    if dismiss_id:
        second_ids = [entry.intelligence_item_id for entry in second_brief.items]
        assert dismiss_id not in second_ids
        assert dismiss_id in prefs["dismissed_items"]

    inspector = inspect_production_runtime(phase32_state_dir)
    assert inspector["production"]["latest_items"] == second_brief.total_items
    assert inspector["personalization"]["event_count"] >= 3
    assert inspector["scheduler"]["history_count"] >= 2