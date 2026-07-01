from knowledge_service.analyst.briefing.deep_dive import DeepDiveGenerator
from knowledge_service.analyst.pipeline import IntelligenceAnalystPipeline


def test_deep_dive_returns_evidence_backed_response(phase32_single_episode_state):
    pipeline = IntelligenceAnalystPipeline(str(phase32_single_episode_state))
    result = pipeline.run()
    claim_id = pipeline.store.load_scored_claims()[0].claim.claim_id

    response = pipeline.deep_dive(claim_id)

    assert response is not None
    assert response.claim_id == claim_id
    assert response.transcript_excerpt
    assert response.surrounding_context
    assert response.timestamped_sources
    assert response.timestamped_sources[0]["url"]
    assert response.analyst_summary
    assert response.explainability.get("novelty")
    assert response.explainability.get("importance")
    assert response.explainability.get("relevance")
    assert result.brief is not None


def test_deep_dive_unknown_claim_returns_none(phase32_single_episode_state):
    pipeline = IntelligenceAnalystPipeline(str(phase32_single_episode_state))
    pipeline.run()

    response = pipeline.deep_dive("missing-claim-id")

    assert response is None


def test_deep_dive_minimal_response_for_unscored_claim(extracted_claims):
    claim = extracted_claims[0]

    response = DeepDiveGenerator().generate(claim.claim_id, [], [claim])

    assert response is not None
    assert response.claim_id == claim.claim_id
    assert response.transcript_excerpt == claim.evidence
    assert response.timestamped_sources
    assert response.explainability == {}