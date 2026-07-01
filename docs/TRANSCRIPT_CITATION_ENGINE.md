# Transcript Citation Engine — Sprint 1

## Purpose

Sprint 1 makes transcripts a first-class Knowledge_Service source for verbatim, timestamped, verifiable quote retrieval. The implementation extends the existing provider, acquisition bundle, processing pipeline, KnowledgeObject, storage, and retrieval layers.

## Architecture Summary

| Layer | Sprint 1 behavior |
|---|---|
| Provider | `TranscriptProvider` acquires published transcript text, structured segments, YouTube captions when `youtube_transcript_api` is installed, or local Whisper fallback when `whisper` is installed. |
| Acquisition | `DocumentRecord` now carries `metadata` and `source_type`, preserving transcript source, provider, acquisition timestamp, status, show, episode, episode date, and source URL. |
| Processing | Existing clean, normalize, markdown, extract, chunk, enrich, and validate stages now detect `video_transcript` documents and preserve transcript text without rewriting it. |
| Knowledge Object | `SourceType.VIDEO_TRANSCRIPT` is used for transcript documents and chunks. Transcript citations are embedded in the existing `citations` list. |
| Storage | Existing JSONB citation storage persists timestamped citation fields through `KnowledgeObject.to_dict()` and `from_dict()`. |
| Retrieval | `search_quotes()` searches transcript chunks through `KnowledgeRetrieverImpl`, ranks by semantic relevance, recency, and confidence, and returns citation-ready results. |
| CLI | `examples/search_quotes.py` demonstrates the vertical slice end to end with an in-memory store. |

## Acquisition Contract

Transcript provider responses use the standard `ProviderResponse` contract.

```python
ProviderResponse(
    content="[00:00:12] Bill Ackman: Tariffs are a tax.",
    content_type="text/transcript",
    metadata={
        "source_type": "video_transcript",
        "transcript_source": "published_transcript",
        "provider": "transcript-provider",
        "acquisition_status": "success",
        "acquisition_timestamp": "2026-06-25T12:00:00Z",
        "source_url": "https://www.youtube.com/watch?v=...",
        "show": "Capital Allocators",
        "episode": "Bill Ackman on Tariffs",
        "episode_date": "2026-06-20T00:00:00Z",
        "transcript_segments": [...]
    },
)
```

## Provider Additions

`knowledge_service.providers.transcript_provider.TranscriptProvider` supports three acquisition paths.

| Priority | Source | Behavior |
|---|---|---|
| 1 | Published transcript | Accepts `transcript_text`, structured `segments`, or fetches a published transcript URL. |
| 2 | YouTube captions | Uses optional `youtube_transcript_api` when installed. Missing dependency or unavailable captions return recoverable provider errors. |
| 3 | Whisper fallback | Uses optional local `whisper` when an `audio_path` is provided. Missing input or dependency returns recoverable provider errors. |

## Processing Rules

Transcript processing is timestamp-aware and verbatim-preserving.

| Stage | Transcript-specific behavior |
|---|---|
| Clean | Bypasses HTML stripping and whitespace rewriting for transcript documents. |
| Normalize | Preserves transcript content and records transcript metadata. |
| Extract | Parses VTT, SRT, timestamped lines, JSON/structured segments, and speaker-prefixed fallback lines. Unknown speakers remain `unknown`. |
| Markdown | Uses transcript text unchanged for hashable canonical content. |
| Chunk | Groups consecutive same-speaker segments by token and duration limits. Chunks include timestamps, context, speaker metadata, confidence, and embeddings. |
| Enrich | Existing confidence/evidence calculation applies to transcript objects. |
| Validate | Existing KnowledgeObject validation applies. |

Raw transcript text is stored on the document KnowledgeObject at `structured_data.raw_transcript`. Segment-level text is preserved in `structured_data.transcript_segments` and chunk `structured_data.segments`.

## KnowledgeObject Schema Changes

`Citation` now supports optional transcript anchor fields.

| Field | Description |
|---|---|
| `start_seconds` | Quote start time in seconds. |
| `end_seconds` | Quote end time in seconds. |
| `segment_id` | Segment id or comma-separated segment ids backing the quote. |
| `quote` | Verbatim quote text from stored transcript segments. |
| `speaker` | Explicit speaker name or `unknown`. |
| `speaker_confidence` | Speaker attribution confidence. |
| `transcript_confidence` | Transcript acquisition/quality confidence. |
| `surrounding_context` | Neighboring transcript text for verification. |
| `metadata` | Show, episode, source, provider, and acquisition metadata. |

No separate transcript object hierarchy was added.

## Storage Changes

No new tables are required for Sprint 1. Transcript documents and chunks are stored in the existing `knowledge_objects` table.

| Existing column | Transcript usage |
|---|---|
| `source_type` | `video_transcript` |
| `structured_data` | Raw transcript, parsed segments, chunk metadata, embeddings, show/episode metadata |
| `citations` | Timestamped transcript citation anchors |
| `published_at` | Episode date when available |

The PostgreSQL store serializes citations and acquisition chains through `KnowledgeObject.to_dict()` before writing JSONB.

## Retrieval API

`knowledge_service.retrieval.quotes.search_quotes()` is the Sprint 1 quote retrieval API.

```python
results = search_quotes(
    retriever,
    query="tariffs",
    speaker="Bill Ackman",
    date_range=("2026-01-01T00:00:00Z", "2026-12-31T23:59:59Z"),
    show="Capital Allocators",
    limit=5,
)
```

Speaker filtering is a hard filter. Ranking combines deterministic semantic similarity, recency, and confidence metadata.

Each result includes:

| Field | Meaning |
|---|---|
| `quote` | Verbatim transcript quote. |
| `speaker` | Speaker name or `unknown`. |
| `speaker_confidence` | Attribution confidence. |
| `transcript_confidence` | Transcript confidence. |
| `show` | Show metadata. |
| `episode` | Episode metadata. |
| `episode_date` | Episode publication date. |
| `timestamp_start` | Start seconds. |
| `timestamp_end` | End seconds. |
| `timestamped_source_url` | Deep link with timestamp when possible. |
| `surrounding_context` | Neighboring transcript context. |
| `relevance_score` | Combined ranking score. |
| `confidence_metadata` | Semantic, recency, and confidence components. |

## Timestamp Deep Links

YouTube URLs receive a `t=<seconds>s` query parameter. Other URLs receive a `#t=<seconds>` fragment. If no timestamp is available, the original source URL is returned.

## CLI Demonstration

```bash
python examples/search_quotes.py --speaker "Bill Ackman" --query "tariffs"
```

Expected output includes quote, speaker confidence, timestamp range, episode metadata, surrounding context, timestamped source URL, and relevance score.

## Testing

Sprint 1 adds deterministic tests for:

| Area | Test file |
|---|---|
| Transcript parsing, chunking, timestamp links, embeddings | `tests/processing/test_transcript.py` |
| Provider acquisition and graceful fallbacks | `tests/providers/test_transcript_provider.py` |
| Quote retrieval ranking and hard speaker filters | `tests/retrieval/test_quote_search.py` |
| Full provider to acquisition to pipeline to storage to retrieval lifecycle | `tests/end_to_end/test_transcript_citation_lifecycle.py` |
| Citation schema round-trip | `tests/test_knowledge_object.py` |

## Sprint 2 Extension Points

Sprint 2 can add automated watch-list ingestion without changing the citation result schema.

Planned extension points:

| Extension point | Sprint 2 use |
|---|---|
| Provider metadata | Add watch-list source ids and polling provenance. |
| Acquisition plans | Schedule repeated transcript acquisition steps. |
| Duplicate detection | Prevent duplicate transcript ingestion by content hash. |
| TranscriptProvider | Add platform-specific provider configuration and retries. |
| `search_quotes()` | Use existing show/date/speaker filters for watch-list scoped retrieval. |
