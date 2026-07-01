# Runtime Certification Report

Generated: 2026-06-30

## 1. Executive Summary

The podcast transcript citation engine is certified for the published-transcript runtime path using real podcast transcript pages. The live inspector acquired four real transcript sources, produced 1,689 parsed segments and 854 transcript chunks, and passed 5 of 5 retrieval checks.

YouTube-caption and Whisper fallback paths are not certified in this run because their required tools/dependencies are unavailable in the environment.

## 2. Scope

Certified path:

- Published transcript URL acquisition through `TranscriptProvider`.
- HTML transcript cleanup into parseable visible text.
- Timestamp parsing for official transcript pages, Podscripts rows, and HappyScribe timestamp blocks.
- Transcript chunk creation with timestamped citation metadata.
- `search_quotes()` retrieval with hard speaker filters.

Not certified in this run:

- YouTube captions through `youtube_transcript_api`.
- Local Whisper audio transcription.
- Search/discovery through unavailable `agent-reach` CLI or Exa MCP routing.

## 3. Real Corpus

Runtime inspector command:

```bash
PYTHONPATH=src ./.venv/bin/python examples/runtime_inspector.py --format json --timeout-ms 30000
```

Corpus acquired successfully:

- `lex-sam-altman-2`: official Lex Fridman transcript, 499 segments, speakers: Lex Fridman 237, Sam Altman 240, unknown 22.
- `dwarkesh-satya-nadella-podscripts`: Podscripts transcript, 167 segments, unknown speaker 167.
- `happyscribe-lex-sam-altman-419`: HappyScribe transcript, 932 segments, unknown speaker 932.
- `happyscribe-all-in-bill-ackman`: HappyScribe transcript, 91 segments, unknown speaker 91.

No synthetic fixture was used for certification evidence.

## 4. Runtime Inspector

Added `examples/runtime_inspector.py`.

The inspector exposes:

- System summary: pass/fail, source counts, document/chunk/segment counts, speaker counts.
- Corpus: per-source URL, status, content type, segment counts, first parsed segments, speaker distribution.
- Retrieval: named checks, filters, result counts, top quotes, timestamp URLs, confidence metadata.
- Diagnostics: environment tools/modules and acquisition failures.
- Performance: acquisition, pipeline, indexing, retrieval, and total timings.

## 5. Acquisition Evidence

Observed initial runtime failures:

- Lex official HTML parsed into bogus JavaScript-like segments such as `helpers {}` instead of transcript speech.
- Podscripts HTML parsed into bogus page/script fragments instead of transcript rows.
- HappyScribe returned HTTP 403 to default `httpx` fetches.

Repairs:

- Added browser-like default `User-Agent` and `follow_redirects=True` for published transcript fetches.
- Added HTML visible-text extraction with `HTMLParser`, skipping `script`, `style`, `noscript`, `svg`, and `canvas` content.
- Published HTML responses now return `text/transcript` content after visible-text extraction.

Verification:

- All four live URLs acquired successfully through `TranscriptProvider`.
- HappyScribe changed from 403 to successful acquisition with the provider headers.

## 6. Parsing And Chunking Evidence

Repairs added support for live formats:

- `Sam Altman [(00:03:08)] text` speaker-before-timestamp format.
- `Starting point is 00:00:00 text` Podscripts format.
- Standalone timestamp block format used by HappyScribe.
- Chapter index rows from Lex table-of-contents are filtered from timestamped transcript segments.

Speaker safety repair:

- Tightened timestamp-line speaker detection so chapter text containing timestamps, such as `Bill Ackman joins the show! (0:30)`, is not fabricated into a speaker label.

Runtime output:

- Lex official transcript produced speaker-attributed segments for `Sam Altman` and `Lex Fridman`.
- Podscripts and HappyScribe sources without speaker labels correctly remained `unknown` with `speaker_confidence=0.0`.

## 7. Retrieval And Citation Evidence

Observed runtime quality failure:

- Query `power struggle` with speaker `Sam Altman` initially ranked short filler quote `Yeah.` above the topical quote.

Repair:

- Added lexical overlap and exact phrase bonus into `search_quotes()` relevance scoring.
- Kept semantic similarity, recency, and confidence in the score.
- Added `lexical_score` to `confidence_metadata`.

Post-repair live retrieval checks:

- `speaker_hard_filter_sam_altman`: passed. Top quote: `The road to AGI should be a giant power struggle...`, speaker `Sam Altman`, timestamp 188s.
- `speaker_hard_filter_lex_fridman`: passed. Top quote references `board structure`, speaker `Lex Fridman`, timestamp 1315s.
- `unknown_speaker_transcript_does_not_match_bill_ackman_filter`: passed. `Bill Ackman` hard filter returned 0 results against an unknown-speaker All-In transcript.
- `unknown_speaker_retrieval_allowed_without_speaker_filter`: passed. All-In transcript returned timestamped unknown-speaker results without speaker filtering.
- `cross_corpus_podscripts_retrieval`: passed. Dwarkesh/Podscripts returned timestamped results for `Fairwater data center training capacity`.

## 8. Failure And Repair Log

| Failure | Root Cause | Repair | Verification |
| --- | --- | --- | --- |
| Raw HTML created bogus transcript segments | Parser processed scripts/styles and page chrome as transcript text | HTML visible-text extraction and script/style skipping | Live Lex and Podscripts parse real transcript rows |
| HappyScribe direct fetch returned 403 | Default `httpx` request lacked browser-like headers | Default provider User-Agent and redirects | HappyScribe Lex and All-In pages acquired successfully |
| Live speaker-before timestamp format was unsupported | Parser only handled leading timestamp or VTT ranges | Added `SPEAKER_TIMESTAMP_RE` | Lex official transcript parses Sam Altman and Lex Fridman speakers |
| Podscripts rows were unsupported | Parser did not recognize `Starting point is` | Added `STARTING_POINT_RE` | Dwarkesh Podscripts source produced 167 segments |
| HappyScribe timestamp blocks were unsupported | Parser did not combine standalone timestamp lines with following text | Added standalone timestamp block parser | HappyScribe Lex source produced 932 segments |
| Chapter text could fabricate speakers | Timestamp speaker group was too permissive | Restricted speaker group to valid speaker-name characters | All-In Podscripts no longer fabricates `Bill Ackman joins...` as a speaker |
| Filler quote outranked topical quote | Deterministic semantic score dominated lexical relevance | Added lexical score into ranking | `power struggle` now returns the topical Sam Altman quote first |

## 9. Verification Matrix

Targeted tests:

```bash
PYTHONPATH=src ./.venv/bin/python -m pytest tests/processing/test_transcript.py tests/providers/test_transcript_provider.py -q
```

Result: `16 passed`.

Retrieval/E2E tests:

```bash
PYTHONPATH=src ./.venv/bin/python -m pytest tests/retrieval/test_quote_search.py tests/end_to_end/test_transcript_citation_lifecycle.py -q
```

Result: `5 passed`.

Runtime inspector:

```bash
PYTHONPATH=src ./.venv/bin/python examples/runtime_inspector.py --format json --timeout-ms 30000
```

Result: status `pass`, 4 successful sources, 1,689 segments, 854 chunks, 5/5 retrieval checks passed.

## 10. Performance

Latest live inspector run:

- Acquisition: 0.852s.
- Pipeline: 0.095s.
- Indexing: 0.000s.
- Retrieval checks: 0.018s.
- Total: 0.965s.
- Pipeline throughput: 17,788.739 segments/sec and 8,994.425 chunks/sec.

Performance is acceptable for the current in-memory runtime inspector corpus.

## 11. Certification Decision

Decision: pass with scoped external blockers.

The engine is production-ready for real published transcript pages that expose transcript text in HTML or plain transcript formats. It preserves hard speaker filters and does not fabricate speakers for transcripts that omit labels.

External blockers remain:

- `agent-reach` command unavailable.
- `yt-dlp` command unavailable.
- `youtube_transcript_api` unavailable.
- `whisper` unavailable.

Those blockers prevent certification of search/discovery, YouTube-caption, and local audio transcription fallback paths in this environment.
