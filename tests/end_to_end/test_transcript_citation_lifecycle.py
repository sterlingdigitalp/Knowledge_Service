"""End-to-end transcript citation lifecycle test."""

from src.knowledge_service.interfaces.provider import ProviderType
from src.knowledge_service.planning.executor import AcquisitionExecutor
from src.knowledge_service.planning.interfaces import AcquisitionPlan, PlanStep
from src.knowledge_service.processing.pipeline import Pipeline
from src.knowledge_service.providers.transcript_provider import TranscriptProvider
from src.knowledge_service.registry.provider_registry import ProviderRegistry
from src.knowledge_service.retrieval.quotes import search_quotes
from src.knowledge_service.retrieval.retriever import KnowledgeRetrieverImpl
from src.knowledge_service.storage.postgres.in_memory_store import InMemoryKnowledgeStore
from src.knowledge_service.storage.repositories.knowledge_repository import KnowledgeRepository


def test_podcast_transcript_to_timestamped_quote_result():
    transcript = (
        "[00:00:05] Host: What did you recently say about tariffs?\n"
        "[00:00:12] Bill Ackman: Tariffs are a tax on consumers and companies.\n"
        "[00:00:20] Bill Ackman: They raise prices and create uncertainty for capital allocation."
    )
    registry = ProviderRegistry()
    provider = TranscriptProvider("transcript-provider")
    provider.initialize({})
    registry.register(provider)

    plan = AcquisitionPlan(
        plan_id="plan-podcast-citation",
        request_id="req-podcast-citation",
        query="What did Bill Ackman recently say about tariffs?",
        steps=[PlanStep(
            step_id="transcript-1",
            provider_type=ProviderType.API,
            target="https://www.youtube.com/watch?v=ackman-tariffs",
            options={
                "transcript_text": transcript,
                "metadata": {
                    "transcript_id": "ackman-tariffs",
                    "source_url": "https://www.youtube.com/watch?v=ackman-tariffs",
                    "show": "Capital Allocators",
                    "episode": "Bill Ackman on Tariffs",
                    "episode_date": "2026-06-20T00:00:00Z",
                },
            },
        )],
    )

    bundle = AcquisitionExecutor(registry).execute(plan)
    assert len(bundle.acquired_documents) == 1
    assert bundle.acquired_documents[0].metadata["transcript_source"] == "published_transcript"

    kos = Pipeline().process(bundle)
    store = InMemoryKnowledgeStore()
    repo = KnowledgeRepository(store)
    for ko in kos:
        repo.store(ko)

    results = search_quotes(KnowledgeRetrieverImpl(repo), query="tariffs", speaker="Bill Ackman", limit=1)

    assert len(results) == 1
    result = results[0].to_dict()
    assert result["quote"] == "Tariffs are a tax on consumers and companies. They raise prices and create uncertainty for capital allocation."
    assert result["speaker"] == "Bill Ackman"
    assert result["speaker_confidence"] == 1.0
    assert result["transcript_confidence"] == 0.95
    assert result["timestamp_start"] == 12.0
    assert result["timestamped_source_url"] == "https://www.youtube.com/watch?v=ackman-tariffs&t=12s"
    assert result["show"] == "Capital Allocators"
    assert result["episode"] == "Bill Ackman on Tariffs"
    assert "recently say about tariffs" in result["surrounding_context"]
    assert result["confidence_metadata"]["semantic_score"] > 0
