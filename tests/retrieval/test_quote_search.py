"""Transcript citation retrieval tests."""

from src.knowledge_service.acquisition.acquisition_bundle import AcquisitionBundle, DocumentRecord, ExecutionRecord
from src.knowledge_service.processing.pipeline import Pipeline
from src.knowledge_service.retrieval.quotes import search_quotes
from src.knowledge_service.retrieval.retriever import KnowledgeRetrieverImpl
from src.knowledge_service.storage.postgres.in_memory_store import InMemoryKnowledgeStore
from src.knowledge_service.storage.repositories.knowledge_repository import KnowledgeRepository


TRANSCRIPT = (
    "[00:00:05] Host: What did tariffs do to markets?\n"
    "[00:00:12] Bill Ackman: Tariffs are a tax on consumers and companies.\n"
    "[00:00:20] Bill Ackman: They raise prices and create uncertainty.\n"
    "[00:00:34] Jane Doe: Monetary policy was also important."
)


def _build_retriever(transcript=TRANSCRIPT):
    bundle = AcquisitionBundle("req-transcript", "plan-transcript", "2026-06-25T12:00:00Z")
    bundle.add_execution_record(ExecutionRecord(
        step_id="transcript-1",
        provider_name="transcript-provider",
        provider_type="api",
        target="https://www.youtube.com/watch?v=ackman123",
        status="success",
    ))
    bundle.add_document(DocumentRecord(
        document_id="doc-transcript-1",
        url="https://www.youtube.com/watch?v=ackman123",
        provider_name="transcript-provider",
        content_type="text/transcript",
        raw_content=transcript,
        content_size_bytes=len(transcript.encode("utf-8")),
        acquired_at="2026-06-25T12:00:00Z",
        metadata={
            "source_type": "video_transcript",
            "transcript_id": "ackman123",
            "transcript_source": "published_transcript",
            "provider": "transcript-provider",
            "acquisition_status": "success",
            "source_url": "https://www.youtube.com/watch?v=ackman123",
            "show": "Investing Podcast",
            "episode": "Bill Ackman on Tariffs",
            "episode_date": "2026-06-20T00:00:00Z",
        },
        source_type="video_transcript",
    ))
    kos = Pipeline().process(bundle)
    store = InMemoryKnowledgeStore()
    repo = KnowledgeRepository(store)
    for ko in kos:
        repo.store(ko)
    return KnowledgeRetrieverImpl(repo), kos


def test_search_quotes_returns_verbatim_timestamped_citation():
    retriever, _ = _build_retriever()

    results = search_quotes(retriever, query="tariffs", speaker="Bill Ackman", limit=3)

    assert len(results) >= 1
    top = results[0]
    assert top.speaker == "Bill Ackman"
    assert top.quote == "Tariffs are a tax on consumers and companies. They raise prices and create uncertainty."
    assert top.timestamp_start == 12.0
    assert top.timestamped_source_url == "https://www.youtube.com/watch?v=ackman123&t=12s"
    assert "What did tariffs do" in top.surrounding_context
    assert top.show == "Investing Podcast"
    assert top.episode == "Bill Ackman on Tariffs"
    assert top.relevance_score > 0


def test_search_quotes_speaker_filter_is_hard_filter():
    retriever, _ = _build_retriever()

    results = search_quotes(retriever, query="tariffs", speaker="Jane Doe", limit=10)

    assert all(result.speaker == "Jane Doe" for result in results)
    assert all("Bill Ackman" != result.speaker for result in results)


def test_search_quotes_prefers_lexical_match_over_short_filler():
    transcript = (
        "[00:00:01] Bill Ackman: Yeah.\n"
        "[00:00:02] Host: Continue.\n"
        "[00:00:03] Bill Ackman: Tariffs are a tax on consumers."
    )
    retriever, _ = _build_retriever(transcript)

    results = search_quotes(retriever, query="tariffs", speaker="Bill Ackman", limit=2)

    assert results[0].quote == "Tariffs are a tax on consumers."
    assert results[0].confidence_metadata["lexical_score"] > 0


def test_pipeline_stores_raw_transcript_and_chunk_embeddings():
    _, kos = _build_retriever()

    doc = [ko for ko in kos if ko.type.value == "document"][0]
    chunks = [ko for ko in kos if ko.type.value == "chunk"]

    assert doc.source_type.value == "video_transcript"
    assert doc.structured_data["raw_transcript"] == TRANSCRIPT
    assert doc.citations[0].quote == "What did tariffs do to markets?"
    assert chunks
    assert chunks[0].structured_data["embedding"]
    assert chunks[0].citations[0].target_url is not None
