from knowledge_service.analyst.pipeline import IntelligenceAnalystPipeline
from knowledge_service.analyst.store import AnalystStore
from knowledge_service.intelligence.state import FileStateStore


def test_pipeline_end_to_end_on_phase32_minimal_state(phase32_state_dir):
    pipeline = IntelligenceAnalystPipeline(str(phase32_state_dir))

    result = pipeline.run()

    assert result.status == "completed"
    assert result.claims_extracted > 0
    assert result.claims_scored == result.claims_extracted
    assert result.clusters_found > 0
    assert result.brief is not None
    assert set(result.brief.sections.keys()) == {"AI", "Investing", "Founders", "Longevity"}
    assert result.latency_seconds["total"] > 0

    store = AnalystStore(FileStateStore(phase32_state_dir))
    summary = store.summary()
    assert summary["claims"] > 0
    assert summary["claims"] <= result.claims_extracted
    assert summary["scored_claims"] == result.claims_scored
    assert summary["clusters"] == result.clusters_found
    assert summary["briefs"] == 1
    assert summary["runs"] == 1


def test_pipeline_deep_dive_after_run(phase32_state_dir):
    pipeline = IntelligenceAnalystPipeline(str(phase32_state_dir))
    pipeline.run()
    claim_id = pipeline.store.load_scored_claims()[0].claim.claim_id

    response = pipeline.deep_dive(claim_id)

    assert response is not None
    assert response.claim_id == claim_id
    assert response.transcript_excerpt
    assert response.explainability


def test_pipeline_idempotent_rerun_skips_rescoring(phase32_single_episode_state):
    pipeline = IntelligenceAnalystPipeline(str(phase32_single_episode_state))

    first = pipeline.run()
    second = pipeline.run()

    assert first.claims_extracted > 0
    assert first.claims_scored == first.claims_extracted
    assert second.claims_extracted == 0
    assert second.claims_scored == 0