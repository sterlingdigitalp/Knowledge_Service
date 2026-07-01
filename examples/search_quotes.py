#!/usr/bin/env python3
"""Minimal transcript quote-search demonstration.

Example:
    python examples/search_quotes.py --speaker "Bill Ackman" --query "tariffs"
"""

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from knowledge_service.acquisition.acquisition_bundle import AcquisitionBundle, DocumentRecord, ExecutionRecord
from knowledge_service.processing.pipeline import Pipeline
from knowledge_service.processing.transcript import format_timestamp
from knowledge_service.retrieval.quotes import search_quotes
from knowledge_service.retrieval.retriever import KnowledgeRetrieverImpl
from knowledge_service.storage.postgres.in_memory_store import InMemoryKnowledgeStore
from knowledge_service.storage.repositories.knowledge_repository import KnowledgeRepository


SAMPLE_TRANSCRIPT = (
    "[00:00:05] Host: What did you recently say about tariffs?\n"
    "[00:00:12] Bill Ackman: Tariffs are a tax on consumers and companies.\n"
    "[00:00:20] Bill Ackman: They raise prices and create uncertainty for capital allocation.\n"
    "[00:00:34] Host: How should investors respond?"
)


def build_demo_retriever(transcript: str) -> KnowledgeRetrieverImpl:
    source_url = "https://www.youtube.com/watch?v=ackman-tariffs"
    bundle = AcquisitionBundle(
        request_id="demo-search-quotes",
        plan_id="demo-plan",
        acquisition_timestamp="2026-06-25T12:00:00Z",
    )
    bundle.add_execution_record(ExecutionRecord(
        step_id="transcript-1",
        provider_name="transcript-provider",
        provider_type="api",
        target=source_url,
        status="success",
    ))
    bundle.add_document(DocumentRecord(
        document_id="demo-transcript",
        url=source_url,
        provider_name="transcript-provider",
        content_type="text/transcript",
        raw_content=transcript,
        content_size_bytes=len(transcript.encode("utf-8")),
        acquired_at="2026-06-25T12:00:00Z",
        metadata={
            "source_type": "video_transcript",
            "transcript_id": "ackman-tariffs",
            "transcript_source": "published_transcript",
            "provider": "transcript-provider",
            "acquisition_status": "success",
            "source_url": source_url,
            "show": "Capital Allocators",
            "episode": "Bill Ackman on Tariffs",
            "episode_date": "2026-06-20T00:00:00Z",
        },
        source_type="video_transcript",
    ))

    repo = KnowledgeRepository(InMemoryKnowledgeStore())
    for ko in Pipeline().process(bundle):
        repo.store(ko)
    return KnowledgeRetrieverImpl(repo)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search timestamped transcript quotes")
    parser.add_argument("--speaker", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--transcript-file")
    args = parser.parse_args()

    transcript = SAMPLE_TRANSCRIPT
    if args.transcript_file:
        transcript = Path(args.transcript_file).read_text(encoding="utf-8")

    retriever = build_demo_retriever(transcript)
    results = search_quotes(retriever, query=args.query, speaker=args.speaker, limit=args.limit)
    if not results:
        print("No matching quotes found.")
        return 1

    for index, result in enumerate(results, start=1):
        print(f"Result {index}")
        print(f"Quote: {result.quote}")
        print(f"Speaker: {result.speaker} (confidence {result.speaker_confidence:.2f})")
        print(f"Timestamp: {format_timestamp(result.timestamp_start)} - {format_timestamp(result.timestamp_end)}")
        print(f"Episode: {result.show} / {result.episode} ({result.episode_date})")
        print(f"Context: {result.surrounding_context}")
        print(f"Source URL: {result.timestamped_source_url}")
        print(f"Relevance: {result.relevance_score:.3f}")
        if index < len(results):
            print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
