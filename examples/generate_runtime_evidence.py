#!/usr/bin/env python3
"""Generate a non-overwriting runtime evidence package.

The generated artifacts are intended for engineering audit. The script preserves
raw HTTP responses, provider outputs, parsed segments, chunk data, KnowledgeObjects,
retrieval outputs, logs, timings, diagnostics, and reproduction instructions.
"""

import csv
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from knowledge_service.acquisition.acquisition_bundle import AcquisitionBundle, DocumentRecord, ExecutionRecord
from knowledge_service.interfaces.provider import ProviderRequest, ProviderType
from knowledge_service.knowledge_object import KnowledgeObject
from knowledge_service.processing.pipeline import Pipeline
from knowledge_service.processing.transcript import build_transcript_chunks, parse_transcript
from knowledge_service.providers.crawl4ai_provider import Crawl4AIProvider
from knowledge_service.providers.searxng_search_provider import SearXNGSearchProvider
from knowledge_service.providers.transcript_provider import TranscriptProvider
from knowledge_service.retrieval.quotes import search_quotes
from knowledge_service.retrieval.retriever import KnowledgeRetrieverImpl
from knowledge_service.storage.postgres.in_memory_store import InMemoryKnowledgeStore
from knowledge_service.storage.repositories.knowledge_repository import KnowledgeRepository


SOURCES: List[Dict[str, Any]] = [
    {
        "id": "lex-sam-altman-2",
        "title": "Sam Altman: OpenAI, GPT-5, Sora, Board Saga, Elon Musk, Ilya, Power and AGI",
        "show": "Lex Fridman Podcast",
        "guests": ["Sam Altman"],
        "hosts": ["Lex Fridman"],
        "url": "https://lexfridman.com/sam-altman-2-transcript/",
        "transcript_source": "published_transcript",
        "min_segments": 400,
        "source_evidence": {
            "guest": "Title contains 'Sam Altman'.",
            "host": "Page title/show identifies Lex Fridman Podcast; parsed speaker labels include Lex Fridman.",
        },
    },
    {
        "id": "dwarkesh-satya-nadella-podscripts",
        "title": "Satya Nadella: How Microsoft is preparing for AGI",
        "show": "Dwarkesh Podcast",
        "guests": ["Satya Nadella"],
        "hosts": ["Dwarkesh Patel", "Dylan Patel"],
        "url": "https://podscripts.co/podcasts/dwarkesh-podcast/satya-nadella-how-microsoft-is-preparing-for-agi",
        "transcript_source": "published_transcript",
        "min_segments": 100,
        "source_evidence": {
            "guest": "Title contains 'Satya Nadella'.",
            "host": "Transcript text begins 'we being me and Dylan Patel'; show/source identifies Dwarkesh Podcast.",
        },
    },
    {
        "id": "happyscribe-lex-sam-altman-419",
        "title": "#419 Sam Altman: OpenAI, GPT-5, Sora, Board Saga, Elon Musk, Ilya, Power and AGI",
        "show": "Lex Fridman Podcast",
        "guests": ["Sam Altman"],
        "hosts": ["Lex Fridman"],
        "url": "https://podcasts.happyscribe.com/lex-fridman-podcast-artificial-intelligence-ai/419-sam-altman-openai-gpt-5-sora-board-saga-elon-musk-ilya-power-agi",
        "transcript_source": "published_transcript",
        "min_segments": 500,
        "source_evidence": {
            "guest": "Title contains 'Sam Altman'.",
            "host": "Source page identifies Lex Fridman Podcast.",
        },
    },
    {
        "id": "happyscribe-all-in-bill-ackman",
        "title": "Bill Ackman: Investment strategy, what the market is missing, how AI breaks businesses",
        "show": "All-In Podcast",
        "guests": ["Bill Ackman"],
        "hosts": ["Chamath Palihapitiya", "Jason Calacanis", "David Sacks", "David Friedberg"],
        "url": "https://podcasts.happyscribe.com/all-in-with-chamath-jason-sacks-friedberg/bill-ackman-investment-strategy-what-the-market-is-missing-how-ai-breaks-businesses",
        "transcript_source": "published_transcript",
        "min_segments": 50,
        "source_evidence": {
            "guest": "Title contains 'Bill Ackman'.",
            "host": "Source URL slug identifies all-in-with-chamath-jason-sacks-friedberg.",
        },
    },
]

SEARCHES: List[Dict[str, Any]] = [
    {"name": "sam_altman_power_struggle", "query": "power struggle", "speaker": "Sam Altman", "show": "Lex Fridman Podcast", "limit": 3, "expect": "success"},
    {"name": "lex_fridman_board_structure", "query": "board structure", "speaker": "Lex Fridman", "show": "Lex Fridman Podcast", "limit": 3, "expect": "success"},
    {"name": "sam_altman_compute_currency", "query": "compute currency future", "speaker": "Sam Altman", "show": "Lex Fridman Podcast", "limit": 3, "expect": "success"},
    {"name": "sam_altman_ilya_agi", "query": "Ilya has not seen AGI", "speaker": "Sam Altman", "show": "Lex Fridman Podcast", "limit": 3, "expect": "success"},
    {"name": "lex_fridman_agi_power", "query": "Whoever builds AGI first gets power", "speaker": "Lex Fridman", "show": "Lex Fridman Podcast", "limit": 3, "expect": "success"},
    {"name": "all_in_unknown_investment_strategy", "query": "investment strategy market AI businesses", "show": "All-In Podcast", "limit": 3, "expect": "success"},
    {"name": "all_in_bill_ackman_hard_filter", "query": "investment strategy", "speaker": "Bill Ackman", "show": "All-In Podcast", "limit": 3, "expect": "failure_zero_results"},
    {"name": "dwarkesh_fairwater_training_capacity", "query": "Fairwater data center training capacity", "show": "Dwarkesh Podcast", "limit": 3, "expect": "success"},
    {"name": "dwarkesh_github_coding_agents", "query": "GitHub coding agents Agent HQ", "show": "Dwarkesh Podcast", "limit": 3, "expect": "success"},
    {"name": "lex_sora_misinformation", "query": "Sora deepfakes misinformation", "show": "Lex Fridman Podcast", "limit": 3, "expect": "success"},
    {"name": "nonexistent_speaker_filter", "query": "AGI", "speaker": "Nonexistent Person", "limit": 3, "expect": "failure_zero_results"},
    {"name": "unknown_speaker_dwarkesh", "query": "Microsoft OpenAI partnership", "speaker": "unknown", "show": "Dwarkesh Podcast", "limit": 3, "expect": "success"},
]


def main() -> int:
    evidence_dir = _new_evidence_dir(ROOT / "runtime_evidence")
    _mkdirs(evidence_dir)

    state: Dict[str, Any] = {
        "evidence_dir": str(evidence_dir),
        "generated_at": _now_iso(),
        "acquisition_attempts": [],
        "corpus": [],
        "failures": [],
        "warnings": [],
        "performance": {},
        "provider_status": [],
        "blockers": [],
    }

    _write_json(evidence_dir / "SOURCE_URLS.json", SOURCES)
    bundle, acquired = _acquire_sources(evidence_dir, state)
    provider_blocker_attempts = _run_blocker_acquisition_attempts(evidence_dir, state)
    state["blocker_acquisition_attempts"] = provider_blocker_attempts

    knowledge_objects, pipeline_timings = _process_bundle(bundle)
    state["performance"]["pipeline_instrumentation"] = pipeline_timings

    store, repo, storage_records, storage_timings = _store_knowledge_objects(knowledge_objects)
    state["performance"]["storage"] = storage_timings
    retriever = KnowledgeRetrieverImpl(repo)

    source_index = _index_runtime_objects(acquired, knowledge_objects, storage_records)
    _write_transcript_artifacts(evidence_dir, acquired, source_index)
    _write_raw_runtime_files(evidence_dir, bundle, knowledge_objects, storage_records, source_index)

    retrieval_records, retrieval_timings = _run_searches(evidence_dir, retriever)
    state["retrieval_records"] = retrieval_records
    state["performance"]["retrieval"] = retrieval_timings

    storage_verification = _verify_storage(repo, store, knowledge_objects, retrieval_records)
    provider_status = _inspect_providers(state, acquired)
    state["provider_status"] = provider_status
    blockers = _build_blockers(evidence_dir, state, provider_status)
    state["blockers"] = blockers

    inspector = _build_inspector_dump(state, acquired, source_index, retrieval_records, storage_records, storage_verification)
    _write_json(evidence_dir / "runtime_inspector_dump.json", inspector)

    _write_corpus_inventory(evidence_dir, acquired, source_index)
    _write_acquisition_log(evidence_dir, state["acquisition_attempts"])
    _write_runtime_inspector_md(evidence_dir, inspector)
    _write_chunk_inventory(evidence_dir, source_index)
    _write_knowledge_objects_md(evidence_dir, knowledge_objects, storage_records)
    _write_storage_verification(evidence_dir, storage_verification)
    _write_retrieval_verification(evidence_dir, retrieval_records)
    _write_performance(evidence_dir, state["performance"], acquired, retrieval_records)
    _write_provider_report(evidence_dir, provider_status)
    _write_blockers(evidence_dir, blockers)
    _write_reproduce_runtime(evidence_dir)
    _write_manifest(evidence_dir, inspector)
    _write_tree(evidence_dir)

    print(str(evidence_dir))
    return 0


def _new_evidence_dir(parent: Path) -> Path:
    parent.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = parent / f"runtime_{stamp}"
    if not base.exists():
        return base
    index = 1
    while True:
        candidate = parent / f"runtime_{stamp}_{index}"
        if not candidate.exists():
            return candidate
        index += 1


def _mkdirs(evidence_dir: Path) -> None:
    for relative in [
        "logs",
        "transcripts",
        "search_results",
        "intermediate",
        "raw_runtime",
        "inputs",
    ]:
        (evidence_dir / relative).mkdir(parents=True, exist_ok=True)


def _acquire_sources(evidence_dir: Path, state: Dict[str, Any]) -> Tuple[AcquisitionBundle, List[Dict[str, Any]]]:
    provider = TranscriptProvider("runtime-evidence-transcript-provider")
    provider.initialize({"timeout_ms": 30000})
    bundle = AcquisitionBundle(
        request_id="runtime-evidence-real-podcasts",
        plan_id="runtime-evidence",
        acquisition_timestamp=_now_iso(),
    )
    acquired: List[Dict[str, Any]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    }

    for source in SOURCES:
        transcript_dir = evidence_dir / "transcripts" / source["id"]
        transcript_dir.mkdir(parents=True, exist_ok=True)

        raw_attempt: Dict[str, Any] = {}
        for raw_attempt_index in range(1, 4):
            raw_started = time.perf_counter()
            raw_attempt = {
                "attempt_id": f"raw-http-{source['id']}-attempt-{raw_attempt_index}",
                "timestamp": _now_iso(),
                "provider": "httpx.get raw snapshot",
                "url": source["url"],
                "method": "GET",
                "attempt_number": raw_attempt_index,
            }
            try:
                raw_response = httpx.get(source["url"], timeout=30.0, follow_redirects=True, headers=headers)
                raw_elapsed = time.perf_counter() - raw_started
                attempt_raw_file = transcript_dir / f"ORIGINAL_HTTP_RESPONSE_ATTEMPT_{raw_attempt_index}.html"
                attempt_raw_file.write_text(raw_response.text, encoding="utf-8")
                if raw_response.is_success:
                    (transcript_dir / "ORIGINAL_HTTP_RESPONSE.html").write_text(raw_response.text, encoding="utf-8")
                raw_attempt.update({
                    "success": raw_response.is_success,
                    "reason": f"HTTP {raw_response.status_code}",
                    "elapsed_seconds": round(raw_elapsed, 6),
                    "output": str(attempt_raw_file.relative_to(evidence_dir)),
                    "final_output": str((transcript_dir / "ORIGINAL_HTTP_RESPONSE.html").relative_to(evidence_dir)) if raw_response.is_success else None,
                    "status_code": raw_response.status_code,
                    "content_type": raw_response.headers.get("content-type"),
                    "bytes": len(raw_response.text.encode("utf-8")),
                })
            except Exception as exc:
                raw_elapsed = time.perf_counter() - raw_started
                raw_attempt.update({
                    "success": False,
                    "reason": type(exc).__name__,
                    "elapsed_seconds": round(raw_elapsed, 6),
                    "output": str(exc),
                })
            state["acquisition_attempts"].append(raw_attempt)
            if raw_attempt.get("success"):
                break
            time.sleep(1.0)

        metadata = {
            "transcript_id": source["id"],
            "source_url": source["url"],
            "show": source["show"],
            "episode": source["title"],
        }
        accepted: Optional[Dict[str, Any]] = None
        provider_attempt: Dict[str, Any] = {}
        for provider_attempt_index in range(1, 4):
            provider_started = time.perf_counter()
            response = provider.execute(ProviderRequest(
                target=source["url"],
                provider_type=ProviderType.API,
                options={
                    "source": "published",
                    "allow_fallback": False,
                    "timeout_ms": 30000,
                    "metadata": metadata,
                },
            ))
            provider_elapsed = time.perf_counter() - provider_started

            provider_attempt = {
                "attempt_id": f"provider-published-{source['id']}-attempt-{provider_attempt_index}",
                "timestamp": _now_iso(),
                "provider": provider.name,
                "url": source["url"],
                "method": "TranscriptProvider.execute source=published allow_fallback=False",
                "elapsed_seconds": round(provider_elapsed, 6),
                "attempt_number": provider_attempt_index,
            }

            if response.error:
                provider_attempt.update({
                    "success": False,
                    "reason": response.error.code,
                    "output": response.error.message,
                })
                state["acquisition_attempts"].append(provider_attempt)
                time.sleep(1.0)
                continue

            content = response.content or ""
            attempt_transcript = transcript_dir / f"ORIGINAL_TRANSCRIPT_ATTEMPT_{provider_attempt_index}.txt"
            attempt_transcript.write_text(content, encoding="utf-8")

            parse_started = time.perf_counter()
            segments = parse_transcript(content, response.metadata)
            parse_elapsed = time.perf_counter() - parse_started

            chunk_started = time.perf_counter()
            chunks = build_transcript_chunks(segments, response.metadata)
            chunk_elapsed = time.perf_counter() - chunk_started

            min_segments = int(source.get("min_segments", 1))
            valid_segment_count = len(segments) >= min_segments
            provider_attempt.update({
                "success": valid_segment_count,
                "reason": "success" if valid_segment_count else "validation_failed_min_segments",
                "output": str(attempt_transcript.relative_to(evidence_dir)),
                "content_type": response.content_type,
                "bytes": len(content.encode("utf-8")),
                "segment_count": len(segments),
                "minimum_required_segments": min_segments,
                "chunk_count_direct_measurement": len(chunks),
            })
            state["acquisition_attempts"].append(provider_attempt)
            if valid_segment_count:
                original_transcript = transcript_dir / "ORIGINAL_TRANSCRIPT.txt"
                original_transcript.write_text(content, encoding="utf-8")
                parsed_file = transcript_dir / "PARSED_TRANSCRIPT.jsonl"
                _write_jsonl(parsed_file, segments)
                provider_metadata_file = transcript_dir / "PROVIDER_RESPONSE_METADATA.json"
                _write_json(provider_metadata_file, response.metadata)
                accepted = {
                    "response": response,
                    "content": content,
                    "segments": segments,
                    "chunks": chunks,
                    "parse_elapsed": parse_elapsed,
                    "chunk_elapsed": chunk_elapsed,
                    "provider_elapsed": provider_elapsed,
                    "original_transcript": original_transcript,
                    "parsed_file": parsed_file,
                    "provider_metadata_file": provider_metadata_file,
                }
                break
            time.sleep(1.0)

        if accepted is None:
            state["failures"].append(provider_attempt)
            bundle.add_execution_record(ExecutionRecord(
                step_id=source["id"],
                provider_name=provider.name,
                provider_type="api",
                target=source["url"],
                status="failed",
                latency_ms=int(float(provider_attempt.get("elapsed_seconds", 0.0)) * 1000),
                error_code=provider_attempt.get("reason"),
                error_message=str(provider_attempt.get("output")),
            ))
            continue

        response = accepted["response"]
        content = accepted["content"]
        segments = accepted["segments"]
        chunks = accepted["chunks"]
        provider_elapsed = accepted["provider_elapsed"]
        parse_elapsed = accepted["parse_elapsed"]
        chunk_elapsed = accepted["chunk_elapsed"]
        original_transcript = accepted["original_transcript"]
        parsed_file = accepted["parsed_file"]
        provider_metadata_file = accepted["provider_metadata_file"]

        bundle.add_execution_record(ExecutionRecord(
            step_id=source["id"],
            provider_name=provider.name,
            provider_type="api",
            target=source["url"],
            status="success",
            latency_ms=int(provider_elapsed * 1000),
            response_metadata=response.metadata,
        ))
        bundle.add_document(DocumentRecord(
            document_id=source["id"],
            url=source["url"],
            provider_name=provider.name,
            content_type=response.content_type,
            raw_content=content,
            content_size_bytes=len(content.encode("utf-8")),
            acquired_at=response.metadata.get("acquisition_timestamp") or _now_iso(),
            metadata=response.metadata,
            source_type="video_transcript",
        ))
        item = {
            "source": source,
            "response_metadata": response.metadata,
            "content": content,
            "segments": segments,
            "direct_chunks": chunks,
            "paths": {
                "transcript_dir": str(transcript_dir.relative_to(evidence_dir)),
                "original_transcript": str(original_transcript.relative_to(evidence_dir)),
                "parsed_transcript": str(parsed_file.relative_to(evidence_dir)),
                "provider_metadata": str(provider_metadata_file.relative_to(evidence_dir)),
            },
            "timings": {
                "raw_http_seconds": raw_attempt.get("elapsed_seconds"),
                "provider_acquisition_seconds": round(provider_elapsed, 6),
                "parse_seconds_direct_measurement": round(parse_elapsed, 6),
                "chunk_seconds_direct_measurement": round(chunk_elapsed, 6),
            },
        }
        acquired.append(item)
        state["corpus"].append(_corpus_state_item(item))

    _write_jsonl(evidence_dir / "logs" / "acquisition_attempts.jsonl", state["acquisition_attempts"])
    return bundle, acquired


def _run_blocker_acquisition_attempts(evidence_dir: Path, state: Dict[str, Any]) -> List[Dict[str, Any]]:
    provider = TranscriptProvider("runtime-evidence-transcript-provider")
    provider.initialize({"timeout_ms": 30000})
    attempts: List[Dict[str, Any]] = []

    youtube_started = time.perf_counter()
    youtube_response = provider.execute(ProviderRequest(
        target="https://youtube.com/watch?v=jvqFAi7vkBc",
        provider_type=ProviderType.API,
        options={"source": "youtube_captions", "allow_fallback": False},
    ))
    youtube_attempt = {
        "attempt_id": "provider-youtube-captions-lex-sam-altman",
        "timestamp": _now_iso(),
        "provider": provider.name,
        "url": "https://youtube.com/watch?v=jvqFAi7vkBc",
        "method": "TranscriptProvider.execute source=youtube_captions allow_fallback=False",
        "success": youtube_response.error is None,
        "reason": youtube_response.error.code if youtube_response.error else "success",
        "elapsed_seconds": round(time.perf_counter() - youtube_started, 6),
        "output": youtube_response.error.message if youtube_response.error else "captions acquired",
    }
    attempts.append(youtube_attempt)
    state["acquisition_attempts"].append(youtube_attempt)

    placeholder_audio = evidence_dir / "inputs" / "empty_audio_for_dependency_check.wav"
    placeholder_audio.write_bytes(b"")
    whisper_started = time.perf_counter()
    whisper_response = provider.execute(ProviderRequest(
        target=str(placeholder_audio),
        provider_type=ProviderType.API,
        options={"source": "whisper_fallback", "audio_path": str(placeholder_audio), "allow_fallback": False},
    ))
    whisper_attempt = {
        "attempt_id": "provider-whisper-fallback-placeholder-audio",
        "timestamp": _now_iso(),
        "provider": provider.name,
        "url": str(placeholder_audio),
        "method": "TranscriptProvider.execute source=whisper_fallback audio_path=<evidence placeholder>",
        "success": whisper_response.error is None,
        "reason": whisper_response.error.code if whisper_response.error else "success",
        "elapsed_seconds": round(time.perf_counter() - whisper_started, 6),
        "output": whisper_response.error.message if whisper_response.error else "audio transcribed",
    }
    attempts.append(whisper_attempt)
    state["acquisition_attempts"].append(whisper_attempt)
    _write_jsonl(evidence_dir / "logs" / "blocker_acquisition_attempts.jsonl", attempts)
    _write_jsonl(evidence_dir / "logs" / "acquisition_attempts.jsonl", state["acquisition_attempts"])
    return attempts


def _process_bundle(bundle: AcquisitionBundle) -> Tuple[List[KnowledgeObject], Dict[str, Any]]:
    timings: Dict[str, Any] = {
        "parse_calls": [],
        "chunk_calls": [],
        "embedding_calls": [],
    }

    import knowledge_service.processing.extract as extract_module
    import knowledge_service.processing.chunk as chunk_module
    import knowledge_service.processing.transcript as transcript_module

    original_parse = extract_module.parse_transcript
    original_build_chunks = chunk_module.build_transcript_chunks
    original_embed_text = transcript_module.embed_text

    def timed_parse(content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        started = time.perf_counter()
        result = original_parse(content, metadata)
        timings["parse_calls"].append({
            "seconds": round(time.perf_counter() - started, 6),
            "content_bytes": len((content or "").encode("utf-8")),
            "segment_count": len(result),
            "transcript_id": (metadata or {}).get("transcript_id"),
        })
        return result

    def timed_build_chunks(segments: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        started = time.perf_counter()
        result = original_build_chunks(segments, metadata, config)
        timings["chunk_calls"].append({
            "seconds": round(time.perf_counter() - started, 6),
            "segment_count": len(segments),
            "chunk_count": len(result),
            "transcript_id": (metadata or {}).get("transcript_id"),
        })
        return result

    def timed_embed_text(text: str, dimensions: int = 64) -> List[float]:
        started = time.perf_counter()
        result = original_embed_text(text, dimensions)
        timings["embedding_calls"].append({
            "seconds": round(time.perf_counter() - started, 6),
            "text_bytes": len((text or "").encode("utf-8")),
            "dimensions": len(result),
            "embedding_id": _embedding_id(result),
        })
        return result

    extract_module.parse_transcript = timed_parse
    chunk_module.build_transcript_chunks = timed_build_chunks
    transcript_module.embed_text = timed_embed_text
    started_total = time.perf_counter()
    try:
        knowledge_objects = Pipeline().process(bundle)
    finally:
        extract_module.parse_transcript = original_parse
        chunk_module.build_transcript_chunks = original_build_chunks
        transcript_module.embed_text = original_embed_text

    timings["total_pipeline_seconds"] = round(time.perf_counter() - started_total, 6)
    timings["parse_total_seconds"] = round(sum(call["seconds"] for call in timings["parse_calls"]), 6)
    timings["chunk_total_seconds"] = round(sum(call["seconds"] for call in timings["chunk_calls"]), 6)
    timings["embedding_total_seconds"] = round(sum(call["seconds"] for call in timings["embedding_calls"]), 6)
    timings["embedding_count"] = len(timings["embedding_calls"])
    timings["knowledge_object_count"] = len(knowledge_objects)
    return knowledge_objects, timings


def _store_knowledge_objects(knowledge_objects: List[KnowledgeObject]) -> Tuple[InMemoryKnowledgeStore, KnowledgeRepository, List[Dict[str, Any]], Dict[str, Any]]:
    store = InMemoryKnowledgeStore()
    repo = KnowledgeRepository(store)
    records: List[Dict[str, Any]] = []
    total_started = time.perf_counter()
    for ko in knowledge_objects:
        started = time.perf_counter()
        stored_id = repo.store(ko)
        elapsed = time.perf_counter() - started
        records.append({
            "object_id": ko.id,
            "stored_id": stored_id,
            "source_id": ko.source_id,
            "type": ko.type.value,
            "content_hash": ko.content_hash,
            "raw_content_hash": ko.raw_content_hash,
            "persisted_in_store_under_own_id": stored_id == ko.id and repo.get_by_id(ko.id) is not None,
            "duplicate_prevented": stored_id != ko.id,
            "storage_backend": "InMemoryKnowledgeStore",
            "storage_location": "Python process memory: InMemoryKnowledgeStore._objects",
            "elapsed_seconds": round(elapsed, 6),
        })
    total_elapsed = time.perf_counter() - total_started
    timings = {
        "total_storage_seconds": round(total_elapsed, 6),
        "store_call_count": len(records),
        "stored_unique_objects": len(store.list_all(limit=100000)),
        "duplicates_prevented": sum(1 for record in records if record["duplicate_prevented"]),
        "store_metrics": store.get_metrics(),
        "per_object_storage_records": records,
    }
    return store, repo, records, timings


def _index_runtime_objects(acquired: List[Dict[str, Any]], knowledge_objects: List[KnowledgeObject], storage_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    storage_by_id = {record["object_id"]: record for record in storage_records}
    source_index: Dict[str, Dict[str, Any]] = {}
    for item in acquired:
        source_id = item["source"]["id"]
        source_index[source_id] = {
            "source": item["source"],
            "response_metadata": item["response_metadata"],
            "segments": item["segments"],
            "direct_chunks": item["direct_chunks"],
            "paths": item["paths"],
            "timings": item["timings"],
            "knowledge_objects": [],
            "document_objects": [],
            "chunk_objects": [],
        }

    for ko in knowledge_objects:
        if ko.source_id not in source_index:
            continue
        ko_record = {
            "object": ko,
            "dict": ko.to_dict(),
            "storage": storage_by_id.get(ko.id),
        }
        source_index[ko.source_id]["knowledge_objects"].append(ko_record)
        if ko.type.value == "document":
            source_index[ko.source_id]["document_objects"].append(ko_record)
        if ko.type.value == "chunk":
            source_index[ko.source_id]["chunk_objects"].append(ko_record)
    return source_index


def _write_transcript_artifacts(evidence_dir: Path, acquired: List[Dict[str, Any]], source_index: Dict[str, Dict[str, Any]]) -> None:
    for item in acquired:
        source_id = item["source"]["id"]
        transcript_dir = evidence_dir / "transcripts" / source_id
        transcript_dir.mkdir(parents=True, exist_ok=True)
        index_entry = source_index[source_id]
        segments = item["segments"]
        chunks = index_entry["chunk_objects"]

        with (transcript_dir / "SPEAKER_ASSIGNMENTS.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["segment_id", "speaker", "speaker_confidence", "text"])
            writer.writeheader()
            for segment in segments:
                writer.writerow({
                    "segment_id": segment.get("segment_id"),
                    "speaker": segment.get("speaker"),
                    "speaker_confidence": segment.get("speaker_confidence"),
                    "text": segment.get("text"),
                })

        with (transcript_dir / "TIMESTAMP_ASSIGNMENTS.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["segment_id", "start_seconds", "end_seconds", "start_label", "end_label", "text"])
            writer.writeheader()
            for segment in segments:
                writer.writerow({
                    "segment_id": segment.get("segment_id"),
                    "start_seconds": segment.get("start_seconds"),
                    "end_seconds": segment.get("end_seconds"),
                    "start_label": _format_seconds(segment.get("start_seconds")),
                    "end_label": _format_seconds(segment.get("end_seconds")),
                    "text": segment.get("text"),
                })

        chunk_rows = []
        context_rows = []
        for chunk_record in chunks:
            ko = chunk_record["object"]
            data = ko.structured_data or {}
            embedding = data.get("embedding") or []
            citation_id = _citation_id(ko.id, 0) if ko.citations else None
            chunk_rows.append({
                "knowledge_object_id": ko.id,
                "chunk_id": data.get("transcript_chunk_id"),
                "transcript_id": data.get("transcript_id"),
                "speaker": data.get("speaker"),
                "timestamp_start": data.get("timestamp_start"),
                "timestamp_end": data.get("timestamp_end"),
                "word_count": ko.word_count,
                "embedding_id": _embedding_id(embedding),
                "citation_id": citation_id,
                "segment_ids": data.get("segment_ids"),
                "content": ko.markdown,
                "segments": data.get("segments"),
                "storage": chunk_record.get("storage"),
            })
            context_rows.append({
                "knowledge_object_id": ko.id,
                "chunk_id": data.get("transcript_chunk_id"),
                "timestamp_start": data.get("timestamp_start"),
                "timestamp_end": data.get("timestamp_end"),
                "context_window": data.get("surrounding_context"),
                "quote": ko.citations[0].quote if ko.citations else ko.markdown,
            })
        _write_jsonl(transcript_dir / "CHUNK_BOUNDARIES.jsonl", chunk_rows)
        _write_jsonl(transcript_dir / "CONTEXT_WINDOWS.jsonl", context_rows)
        _write_jsonl(transcript_dir / "KNOWLEDGE_OBJECTS.jsonl", [record["dict"] for record in index_entry["knowledge_objects"]])
        _write_text(transcript_dir / "README.md", _transcript_readme(item, index_entry))


def _write_raw_runtime_files(evidence_dir: Path, bundle: AcquisitionBundle, knowledge_objects: List[KnowledgeObject], storage_records: List[Dict[str, Any]], source_index: Dict[str, Dict[str, Any]]) -> None:
    _write_json(evidence_dir / "raw_runtime" / "acquisition_bundle.json", _to_plain(bundle))
    _write_jsonl(evidence_dir / "raw_runtime" / "knowledge_objects_created.jsonl", [ko.to_dict() for ko in knowledge_objects])
    _write_jsonl(evidence_dir / "raw_runtime" / "storage_records.jsonl", storage_records)
    chunk_rows = []
    direct_chunk_rows = []
    parsed_segment_rows = []
    source_timing_rows = []
    for source_id, item in source_index.items():
        source_timing_rows.append({
            "transcript_id": source_id,
            "timings": item["timings"],
            "paths": item["paths"],
        })
        for segment in item["segments"]:
            parsed_segment_rows.append({"transcript_id": source_id, **segment})
        for chunk in item["direct_chunks"]:
            direct_chunk_rows.append({"transcript_id": source_id, **chunk})
        for chunk in item["chunk_objects"]:
            chunk_rows.append(_chunk_inventory_record(source_id, chunk))
    _write_jsonl(evidence_dir / "raw_runtime" / "chunks.jsonl", chunk_rows)
    _write_jsonl(evidence_dir / "intermediate" / "parsed_segments_all_transcripts.jsonl", parsed_segment_rows)
    _write_jsonl(evidence_dir / "intermediate" / "direct_chunks_all_transcripts.jsonl", direct_chunk_rows)
    _write_json(evidence_dir / "intermediate" / "source_timings_and_paths.json", source_timing_rows)


def _run_searches(evidence_dir: Path, retriever: KnowledgeRetrieverImpl) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    search_dir = evidence_dir / "search_results"
    records: List[Dict[str, Any]] = []
    total_started = time.perf_counter()
    for index, search in enumerate(SEARCHES, start=1):
        started = time.perf_counter()
        results = search_quotes(
            retriever,
            query=search["query"],
            speaker=search.get("speaker"),
            show=search.get("show"),
            limit=search.get("limit", 10),
        )
        elapsed = time.perf_counter() - started
        raw_results = [result.to_dict() for result in results]
        filename = f"{index:02d}_{search['name']}.json"
        _write_json(search_dir / filename, raw_results)
        record = {
            "index": index,
            "name": search["name"],
            "input": search,
            "elapsed_seconds": round(elapsed, 6),
            "result_count": len(raw_results),
            "raw_output_file": str((search_dir / filename).relative_to(evidence_dir)),
            "results": raw_results,
            "expectation": search.get("expect"),
            "expectation_observed": _search_expectation(search, raw_results),
        }
        records.append(record)
    timings = {
        "total_retrieval_seconds": round(time.perf_counter() - total_started, 6),
        "search_count": len(records),
        "per_search": [{"name": record["name"], "elapsed_seconds": record["elapsed_seconds"], "result_count": record["result_count"]} for record in records],
    }
    _write_jsonl(evidence_dir / "logs" / "retrieval_searches.jsonl", records)
    return records, timings


def _verify_storage(repo: KnowledgeRepository, store: InMemoryKnowledgeStore, knowledge_objects: List[KnowledgeObject], retrieval_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    sample_ids = [ko.id for ko in knowledge_objects[:10]]
    before_restart = []
    for obj_id in sample_ids:
        result = repo.get_by_id(obj_id)
        before_restart.append({"object_id": obj_id, "retrieved": result is not None})

    restarted_store = InMemoryKnowledgeStore()
    restarted_repo = KnowledgeRepository(restarted_store)
    after_restart = []
    for obj_id in sample_ids:
        result = restarted_repo.get_by_id(obj_id)
        after_restart.append({"object_id": obj_id, "retrieved": result is not None})

    restarted_retriever = KnowledgeRetrieverImpl(restarted_repo)
    restart_search_started = time.perf_counter()
    restart_search = search_quotes(restarted_retriever, query="power struggle", speaker="Sam Altman", limit=3)
    return {
        "runtime_store_type": "InMemoryKnowledgeStore",
        "runtime_store_module": "knowledge_service.storage.postgres.in_memory_store",
        "postgres_used": False,
        "json_store_used": False,
        "filesystem_store_used_for_runtime": False,
        "cache_used": False,
        "memory_used": True,
        "evidence_filesystem_exports_created": True,
        "store_metrics": store.get_metrics(),
        "unique_objects_in_memory_before_restart": len(store.list_all(limit=100000)),
        "sample_retrieve_before_restart": before_restart,
        "sample_retrieve_after_new_store_restart_simulation": after_restart,
        "search_after_new_store_restart_simulation": {
            "query": "power struggle",
            "speaker": "Sam Altman",
            "elapsed_seconds": round(time.perf_counter() - restart_search_started, 6),
            "result_count": len(restart_search),
            "results": [result.to_dict() for result in restart_search],
        },
        "retrievable_after_restart": False,
        "reason_not_retrievable_after_restart": "This evidence run stores KnowledgeObjects in InMemoryKnowledgeStore only. A new store instance starts with empty dictionaries.",
    }


def _inspect_providers(state: Dict[str, Any], acquired: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    reports: List[Dict[str, Any]] = []

    transcript = TranscriptProvider("provider-report-transcript")
    transcript_init = transcript.initialize({"timeout_ms": 30000})
    reports.append({
        "provider_class": "TranscriptProvider",
        "name": transcript.name,
        "available": True,
        "unavailable_reason": None,
        "configuration": {"timeout_ms": 30000},
        "dependencies": {
            "httpx": _module_available("httpx"),
            "youtube_transcript_api": _module_available("youtube_transcript_api"),
            "whisper": _module_available("whisper"),
        },
        "capabilities": transcript_init.capabilities,
        "health": _to_plain(transcript.health()),
        "last_runtime_result": {
            "successful_published_transcripts": len(acquired),
            "youtube_caption_attempt": _attempt_by_id(state["acquisition_attempts"], "provider-youtube-captions-lex-sam-altman"),
            "whisper_attempt": _attempt_by_id(state["acquisition_attempts"], "provider-whisper-fallback-placeholder-audio"),
        },
    })

    searxng = SearXNGSearchProvider("provider-report-searxng")
    searxng_config = {"endpoint": "http://localhost:8080", "timeout_ms": 15000}
    searxng._config = searxng_config
    searxng_health = searxng.health()
    searxng_init_error = None
    searxng_last_result: Any = "health check only; provider was not healthy enough to execute search"
    if searxng_health.status.value == "healthy":
        try:
            searxng.initialize(searxng_config)
            search_started = time.perf_counter()
            search_response = searxng.execute(ProviderRequest(
                target="podcast transcript runtime evidence",
                provider_type=ProviderType.SEARCH,
                options={},
            ))
            searxng_last_result = {
                "operation": "SearXNGSearchProvider.execute",
                "query": "podcast transcript runtime evidence",
                "elapsed_seconds": round(time.perf_counter() - search_started, 6),
                "success": search_response.error is None,
                "error": _to_plain(search_response.error) if search_response.error else None,
                "status_code": search_response.status_code,
                "content_type": search_response.content_type,
                "result_count": len((search_response.metadata or {}).get("results", [])),
                "metadata_keys": sorted((search_response.metadata or {}).keys()),
            }
        except Exception as exc:
            searxng_init_error = f"{type(exc).__name__}: {exc}"
    reports.append({
        "provider_class": "SearXNGSearchProvider",
        "name": searxng.name,
        "available": searxng_health.status.value == "healthy" and searxng_init_error is None,
        "unavailable_reason": searxng_init_error or searxng_health.degradation_reason,
        "configuration": searxng_config,
        "dependencies": {"httpx": _module_available("httpx"), "service_endpoint": "http://localhost:8080"},
        "capabilities": searxng.capabilities,
        "health": _to_plain(searxng_health),
        "last_runtime_result": searxng_last_result,
    })

    crawl = Crawl4AIProvider("provider-report-crawl4ai")
    crawl_config = {
        "endpoint": "http://localhost:11235",
        "timeout_ms": 60000,
        "auth_token_present": bool(os.environ.get("CRAWL4AI_API_TOKEN")),
    }
    crawl._config = {"endpoint": crawl_config["endpoint"], "timeout_ms": crawl_config["timeout_ms"], "auth_token": os.environ.get("CRAWL4AI_API_TOKEN")}
    crawl_health = crawl.health()
    crawl_init_error = None
    if os.environ.get("CRAWL4AI_API_TOKEN"):
        try:
            crawl.initialize({"endpoint": crawl_config["endpoint"], "timeout_ms": crawl_config["timeout_ms"], "auth_token": os.environ["CRAWL4AI_API_TOKEN"]})
        except Exception as exc:
            crawl_init_error = f"{type(exc).__name__}: {exc}"
    else:
        crawl_init_error = "CRAWL4AI_API_TOKEN is not set"
    reports.append({
        "provider_class": "Crawl4AIProvider",
        "name": crawl.name,
        "available": crawl_health.status.value == "healthy" and crawl_init_error is None,
        "unavailable_reason": crawl_init_error or crawl_health.degradation_reason,
        "configuration": crawl_config,
        "dependencies": {"httpx": _module_available("httpx"), "service_endpoint": "http://localhost:11235", "CRAWL4AI_API_TOKEN": bool(os.environ.get("CRAWL4AI_API_TOKEN"))},
        "capabilities": crawl.capabilities,
        "health": _to_plain(crawl_health),
        "last_runtime_result": "health/configuration check only; crawl not executed for transcript certification",
    })
    return reports


def _build_blockers(evidence_dir: Path, state: Dict[str, Any], provider_status: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    command_checks = {
        "agent-reach": shutil.which("agent-reach"),
        "yt-dlp": shutil.which("yt-dlp"),
        "mcporter": shutil.which("mcporter"),
        "curl": shutil.which("curl"),
    }
    commands = [
        ("agent-reach doctor --json", ["agent-reach", "doctor", "--json"]),
        ("yt-dlp --version", ["yt-dlp", "--version"]),
        ("mcporter exa web_search_exa", ["mcporter", "call", "exa.web_search_exa(query: \"podcast transcript\", numResults: 1)"]),
    ]
    command_results = []
    for label, command in commands:
        command_results.append(_run_command(label, command, timeout_seconds=20))
    _write_json(evidence_dir / "logs" / "command_blocker_checks.json", {"which": command_checks, "commands": command_results})

    blockers: List[Dict[str, Any]] = []
    if command_checks["agent-reach"] is None:
        blockers.append({
            "description": "agent-reach CLI unavailable",
            "why_builder_a_cannot_solve_it": "The command is not installed on PATH in the audited runtime. Installing it would change the runtime under audit.",
            "evidence": {"which": command_checks["agent-reach"], "command_result": _command_result(command_results, "agent-reach doctor --json")},
            "required_external_input": "Install/configure agent-reach or provide an approved alternative web/search backend for certification.",
        })
    if command_checks["yt-dlp"] is None:
        blockers.append({
            "description": "yt-dlp CLI unavailable",
            "why_builder_a_cannot_solve_it": "The command is not installed on PATH in the audited runtime. Installing it would change the runtime under audit.",
            "evidence": {"which": command_checks["yt-dlp"], "command_result": _command_result(command_results, "yt-dlp --version")},
            "required_external_input": "Install yt-dlp or provide an approved YouTube caption acquisition mechanism.",
        })
    if not _module_available("youtube_transcript_api"):
        blockers.append({
            "description": "youtube_transcript_api module unavailable",
            "why_builder_a_cannot_solve_it": "The module is not installed in the audited virtual environment. Installing it would change the runtime under audit.",
            "evidence": {
                "module_available": False,
                "provider_attempt": _attempt_by_id(state["acquisition_attempts"], "provider-youtube-captions-lex-sam-altman"),
            },
            "required_external_input": "Install youtube_transcript_api into the runtime environment and rerun certification.",
        })
    if not _module_available("whisper"):
        blockers.append({
            "description": "whisper module unavailable",
            "why_builder_a_cannot_solve_it": "The module is not installed in the audited virtual environment. Installing it would change the runtime under audit.",
            "evidence": {
                "module_available": False,
                "provider_attempt": _attempt_by_id(state["acquisition_attempts"], "provider-whisper-fallback-placeholder-audio"),
            },
            "required_external_input": "Install/configure whisper and provide real audio input for fallback certification.",
        })
    exa_result = _command_result(command_results, "mcporter exa web_search_exa")
    if exa_result and exa_result.get("returncode") != 0:
        blockers.append({
            "description": "Exa MCP route unavailable through mcporter",
            "why_builder_a_cannot_solve_it": "mcporter is present, but the audited runtime does not expose an MCP server named exa.",
            "evidence": exa_result,
            "required_external_input": "Configure an exa MCP server in mcporter or provide another approved web search provider.",
        })

    for provider in provider_status:
        if not provider["available"] and provider["provider_class"] in {"SearXNGSearchProvider", "Crawl4AIProvider"}:
            blockers.append({
                "description": f"{provider['provider_class']} unavailable",
                "why_builder_a_cannot_solve_it": "The required local service/configuration is not available in the audited runtime. Starting services or adding credentials would change the runtime under audit.",
                "evidence": provider,
                "required_external_input": "Start/configure the provider service and credentials, then rerun certification if this provider is in scope.",
            })
    return blockers


def _build_inspector_dump(
    state: Dict[str, Any],
    acquired: List[Dict[str, Any]],
    source_index: Dict[str, Dict[str, Any]],
    retrieval_records: List[Dict[str, Any]],
    storage_records: List[Dict[str, Any]],
    storage_verification: Dict[str, Any],
) -> Dict[str, Any]:
    transcript_summary = []
    chunk_summary = []
    embedding_summary = []
    citation_summary = []
    speaker_counter = Counter()
    total_segments = 0
    total_chunks = 0
    total_embeddings = 0
    total_citations = 0

    for item in acquired:
        source_id = item["source"]["id"]
        index_entry = source_index[source_id]
        speakers = Counter(segment.get("speaker", "unknown") for segment in item["segments"])
        speaker_counter.update(speakers)
        chunks = index_entry["chunk_objects"]
        embeddings = [chunk["object"].structured_data.get("embedding") for chunk in chunks if chunk["object"].structured_data and chunk["object"].structured_data.get("embedding")]
        citations = sum(len(record["object"].citations) for record in index_entry["knowledge_objects"])
        total_segments += len(item["segments"])
        total_chunks += len(chunks)
        total_embeddings += len(embeddings)
        total_citations += citations
        transcript_summary.append({
            "transcript_id": source_id,
            "title": item["source"]["title"],
            "show": item["source"]["show"],
            "url": item["source"]["url"],
            "content_bytes": len(item["content"].encode("utf-8")),
            "segment_count": len(item["segments"]),
            "speaker_counts": dict(sorted(speakers.items())),
            "paths": item["paths"],
            "timings": item["timings"],
        })
        chunk_summary.append({
            "transcript_id": source_id,
            "chunk_count": len(chunks),
            "chunk_ids": [chunk["object"].structured_data.get("transcript_chunk_id") for chunk in chunks if chunk["object"].structured_data],
        })
        embedding_summary.append({
            "transcript_id": source_id,
            "embedding_count": len(embeddings),
            "embedding_ids": [_embedding_id(embedding) for embedding in embeddings],
        })
        citation_summary.append({
            "transcript_id": source_id,
            "citation_count": citations,
        })

    warnings = list(state.get("warnings", []))
    warnings.append({
        "description": "Per-stage ProcessingContext warnings are not exported by Pipeline.process.",
        "evidence": "Pipeline.process returns List[KnowledgeObject] and does not expose ProcessingContext objects after each document.",
        "requested_artifact_status": "cannot produce per-document stage warning dump from this runtime without changing Pipeline API or adding instrumentation before the run",
    })

    return {
        "system_summary": {
            "generated_at": state["generated_at"],
            "evidence_dir": state["evidence_dir"],
            "source_count": len(SOURCES),
            "successful_transcripts": len(acquired),
            "failed_transcripts": len(state.get("failures", [])),
            "segment_count": total_segments,
            "chunk_count": total_chunks,
            "embedding_count": total_embeddings,
            "citation_count": total_citations,
            "knowledge_objects_created": len(storage_records),
            "knowledge_objects_unique_in_memory": state["performance"]["storage"]["stored_unique_objects"],
            "retrieval_searches": len(retrieval_records),
            "speaker_counts": dict(sorted(speaker_counter.items())),
        },
        "corpus_summary": state["corpus"],
        "transcript_summary": transcript_summary,
        "chunk_summary": chunk_summary,
        "embedding_summary": embedding_summary,
        "citation_summary": citation_summary,
        "retrieval_summary": retrieval_records,
        "diagnostics": {
            "commands": {command: shutil.which(command) for command in ["agent-reach", "yt-dlp", "mcporter", "curl"]},
            "modules": {module: _module_available(module) for module in ["httpx", "youtube_transcript_api", "whisper", "psycopg2"]},
            "storage_verification": storage_verification,
        },
        "performance": state["performance"],
        "provider_status": state["provider_status"],
        "failures": state.get("failures", []),
        "warnings": warnings,
        "blockers": state["blockers"],
        "acquisition_attempts": state["acquisition_attempts"],
    }


def _write_corpus_inventory(evidence_dir: Path, acquired: List[Dict[str, Any]], source_index: Dict[str, Dict[str, Any]]) -> None:
    lines = ["# Corpus Inventory", ""]
    for item in acquired:
        source = item["source"]
        index_entry = source_index[source["id"]]
        kos = index_entry["knowledge_objects"]
        chunks = index_entry["chunk_objects"]
        embeddings = [chunk for chunk in chunks if chunk["object"].structured_data and chunk["object"].structured_data.get("embedding")]
        citation_count = sum(len(record["object"].citations) for record in kos)
        lines.extend([
            f"## {source['id']}",
            f"- title: {source['title']}",
            f"- podcast/show: {source['show']}",
            f"- guest(s): {', '.join(source['guests'])}",
            f"- guest evidence: {source['source_evidence']['guest']}",
            f"- host(s): {', '.join(source['hosts'])}",
            f"- host evidence: {source['source_evidence']['host']}",
            f"- original source URL: {source['url']}",
            f"- transcript source: {source['transcript_source']}",
            "- acquisition method: TranscriptProvider.execute(source=published, allow_fallback=False) plus raw httpx snapshot",
            f"- acquisition timestamp: {item['response_metadata'].get('acquisition_timestamp')}",
            f"- transcript length: {len(item['content'].encode('utf-8'))} bytes; {len(item['content'].split())} whitespace-delimited words",
            f"- segment count: {len(item['segments'])}",
            f"- chunk count: {len(chunks)}",
            f"- storage location: InMemoryKnowledgeStore during runtime; evidence export under {item['paths']['transcript_dir']}",
            f"- embedding count: {len(embeddings)}",
            f"- citation count: {citation_count}",
            "- KnowledgeObject ID(s):",
        ])
        for record in kos:
            storage = record.get("storage") or {}
            lines.append(f"  - {record['object'].id} ({record['object'].type.value}; stored_id={storage.get('stored_id')}; duplicate_prevented={storage.get('duplicate_prevented')})")
        lines.append("")
    _write_text(evidence_dir / "CORPUS_INVENTORY.md", "\n".join(lines))


def _write_acquisition_log(evidence_dir: Path, attempts: List[Dict[str, Any]]) -> None:
    lines = ["# Acquisition Log", ""]
    for index, attempt in enumerate(attempts, start=1):
        lines.extend([
            f"## Attempt {index}: {attempt.get('attempt_id')}",
            f"- Attempt: {attempt.get('method')}",
            f"- Provider: {attempt.get('provider')}",
            f"- URL: {attempt.get('url')}",
            f"- Success/Failure: {'Success' if attempt.get('success') else 'Failure'}",
            f"- Reason: {attempt.get('reason')}",
            f"- Elapsed time: {attempt.get('elapsed_seconds')} seconds",
            f"- Output: {attempt.get('output')}",
            "",
            "Raw attempt record:",
            "```json",
            json.dumps(attempt, indent=2, sort_keys=True),
            "```",
            "",
        ])
    _write_text(evidence_dir / "ACQUISITION_LOG.md", "\n".join(lines))


def _write_runtime_inspector_md(evidence_dir: Path, inspector: Dict[str, Any]) -> None:
    lines = ["# Runtime Inspector Dump", ""]
    sections = [
        ("System Summary", "system_summary"),
        ("Corpus Summary", "corpus_summary"),
        ("Transcript Summary", "transcript_summary"),
        ("Chunk Summary", "chunk_summary"),
        ("Embedding Summary", "embedding_summary"),
        ("Retrieval Summary", "retrieval_summary"),
        ("Diagnostics", "diagnostics"),
        ("Performance", "performance"),
        ("Provider Status", "provider_status"),
        ("Failures", "failures"),
        ("Warnings", "warnings"),
        ("Blockers", "blockers"),
        ("Acquisition Attempts", "acquisition_attempts"),
        ("Full Inspector JSON", None),
    ]
    for title, key in sections:
        lines.extend([f"## {title}", "", "```json"])
        payload = inspector if key is None else inspector[key]
        lines.append(json.dumps(payload, indent=2, sort_keys=True))
        lines.extend(["```", ""])
    _write_text(evidence_dir / "RUNTIME_INSPECTOR.md", "\n".join(lines))


def _write_chunk_inventory(evidence_dir: Path, source_index: Dict[str, Dict[str, Any]]) -> None:
    rows = []
    for source_id, item in source_index.items():
        for chunk in item["chunk_objects"]:
            rows.append(_chunk_inventory_record(source_id, chunk))
    fieldnames = [
        "chunk id",
        "transcript id",
        "speaker",
        "start timestamp",
        "end timestamp",
        "token count",
        "embedding id",
        "citation id",
        "KnowledgeObject id",
        "stored id",
        "storage status",
    ]
    with (evidence_dir / "CHUNK_INVENTORY.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_knowledge_objects_md(evidence_dir: Path, knowledge_objects: List[KnowledgeObject], storage_records: List[Dict[str, Any]]) -> None:
    storage_by_id = {record["object_id"]: record for record in storage_records}
    lines = ["# KnowledgeObject Inventory", ""]
    for ko in knowledge_objects:
        storage = storage_by_id.get(ko.id, {})
        status = "in-memory persisted under own id" if storage.get("persisted_in_store_under_own_id") else "temporary pipeline object; duplicate-prevented or not inserted under own id"
        lines.extend([
            f"## {ko.id}",
            f"- object id: {ko.id}",
            f"- type: {ko.type.value}",
            f"- parent: {ko.parent_id}",
            f"- raw_content_hash: {ko.raw_content_hash}",
            f"- content_hash: {ko.content_hash}",
            f"- storage location: {storage.get('storage_location')}",
            f"- persisted: {storage.get('persisted_in_store_under_own_id')}",
            "- cached: false",
            "- temporary: true for pipeline-created object lifetime; false only while stored under own id in current in-memory store",
            "- in-memory only: true",
            f"- status explanation: {status}",
            "- acquisition chain:",
            "```json",
            json.dumps(_to_plain(ko.acquisition_chain), indent=2, sort_keys=True),
            "```",
            "- citations:",
            "```json",
            json.dumps(_to_plain(ko.citations), indent=2, sort_keys=True),
            "```",
            "- full object:",
            "```json",
            json.dumps(ko.to_dict(), indent=2, sort_keys=True),
            "```",
            "",
        ])
    _write_text(evidence_dir / "KNOWLEDGE_OBJECTS.md", "\n".join(lines))


def _write_storage_verification(evidence_dir: Path, verification: Dict[str, Any]) -> None:
    lines = [
        "# Storage Verification",
        "",
        "## Explicit Answers",
        "- Where are the transcripts now? In this runtime, raw transcript content is held in KnowledgeObject markdown/structured_data in InMemoryKnowledgeStore and exported to transcripts/*/ORIGINAL_TRANSCRIPT.txt in the evidence package.",
        "- Where are the chunks? In this runtime, chunks are KnowledgeObject(type=chunk) instances in InMemoryKnowledgeStore and exported to CHUNK_INVENTORY.csv plus transcripts/*/CHUNK_BOUNDARIES.jsonl.",
        "- Where are the embeddings? In this runtime, embeddings are stored in each chunk KnowledgeObject structured_data.embedding field in InMemoryKnowledgeStore and exported to raw_runtime/chunks.jsonl and transcript chunk files.",
        "- Where are the citations? In this runtime, citations are stored on KnowledgeObject.citations in InMemoryKnowledgeStore and exported to KNOWLEDGE_OBJECTS.md/raw_runtime/knowledge_objects_created.jsonl.",
        "- PostgreSQL: false for this evidence run.",
        "- JSON: true for exported evidence artifacts only; false as Knowledge_Service runtime storage backend.",
        "- filesystem: true for exported evidence artifacts only; false as Knowledge_Service runtime storage backend.",
        "- memory: true for Knowledge_Service runtime storage backend.",
        "- cache: false.",
        "- Can they be retrieved after restarting Knowledge_Service? No for this evidence run.",
        "",
        "## Demonstration",
        "```json",
        json.dumps(verification, indent=2, sort_keys=True),
        "```",
    ]
    _write_text(evidence_dir / "STORAGE_VERIFICATION.md", "\n".join(lines))


def _write_retrieval_verification(evidence_dir: Path, retrieval_records: List[Dict[str, Any]]) -> None:
    lines = ["# Retrieval Verification", ""]
    for record in retrieval_records:
        lines.extend([
            f"## Search {record['index']}: {record['name']}",
            "### Input",
            "```json",
            json.dumps(record["input"], indent=2, sort_keys=True),
            "```",
            f"- Raw returned objects file: {record['raw_output_file']}",
            f"- Result count: {record['result_count']}",
            f"- Retrieval elapsed seconds: {record['elapsed_seconds']}",
            f"- Verification notes: expectation={record['expectation']}; observed={record['expectation_observed']}",
        ])
        if not record["results"]:
            lines.extend(["- Returned quote: <none>", "- KnowledgeObject ID: <none>", "- Speaker: <none>", "- Timestamp: <none>", "- Source URL: <none>", "- Context: <none>", "- Retrieval score: <none>", ""])
            continue
        for result_index, result in enumerate(record["results"], start=1):
            lines.extend([
                f"### Result {result_index}",
                f"- Returned quote: {result.get('quote')}",
                f"- KnowledgeObject ID: {result.get('chunk_id')}",
                f"- Speaker: {result.get('speaker')}",
                f"- Timestamp: {result.get('timestamp_start')} - {result.get('timestamp_end')}",
                f"- Source URL: {result.get('timestamped_source_url')}",
                f"- Context: {result.get('surrounding_context')}",
                f"- Retrieval score: {result.get('relevance_score')}",
                "- Full returned object:",
                "```json",
                json.dumps(result, indent=2, sort_keys=True),
                "```",
            ])
        lines.append("")
    _write_text(evidence_dir / "RETRIEVAL_VERIFICATION.md", "\n".join(lines))


def _write_performance(evidence_dir: Path, performance: Dict[str, Any], acquired: List[Dict[str, Any]], retrieval_records: List[Dict[str, Any]]) -> None:
    acquisition_total = sum(item["timings"]["provider_acquisition_seconds"] for item in acquired)
    direct_parse_total = sum(item["timings"]["parse_seconds_direct_measurement"] for item in acquired)
    direct_chunk_total = sum(item["timings"]["chunk_seconds_direct_measurement"] for item in acquired)
    lines = [
        "# Performance",
        "",
        "## Aggregate Measured Timings",
        f"- acquisition: {round(acquisition_total, 6)} seconds (sum of TranscriptProvider published acquisition attempts)",
        f"- parsing: {performance['pipeline_instrumentation']['parse_total_seconds']} seconds (instrumented Pipeline ExtractStage parse calls)",
        f"- parsing_direct_replay: {round(direct_parse_total, 6)} seconds (direct parse used for transcript artifacts)",
        f"- chunking: {performance['pipeline_instrumentation']['chunk_total_seconds']} seconds (instrumented Pipeline ChunkStage build_transcript_chunks calls; includes embedding calls)",
        f"- chunking_direct_replay: {round(direct_chunk_total, 6)} seconds (direct chunking used for transcript artifacts)",
        f"- embeddings: {performance['pipeline_instrumentation']['embedding_total_seconds']} seconds ({performance['pipeline_instrumentation']['embedding_count']} instrumented embedding calls inside pipeline chunking)",
        f"- storage: {performance['storage']['total_storage_seconds']} seconds ({performance['storage']['store_call_count']} store calls)",
        f"- retrieval: {performance['retrieval']['total_retrieval_seconds']} seconds ({performance['retrieval']['search_count']} searches)",
        "",
        "## Full Performance JSON",
        "```json",
        json.dumps({"performance": performance, "per_source_timings": [{"id": item["source"]["id"], "timings": item["timings"]} for item in acquired], "retrieval_timings": retrieval_records}, indent=2, sort_keys=True),
        "```",
    ]
    _write_text(evidence_dir / "PERFORMANCE.md", "\n".join(lines))


def _write_provider_report(evidence_dir: Path, provider_status: List[Dict[str, Any]]) -> None:
    lines = ["# Provider Report", ""]
    for provider in provider_status:
        lines.extend([
            f"## {provider['provider_class']}",
            f"- Available: {provider['available']}",
            f"- Unavailable reason: {provider['unavailable_reason']}",
            "- Configuration:",
            "```json",
            json.dumps(provider["configuration"], indent=2, sort_keys=True),
            "```",
            "- Dependencies:",
            "```json",
            json.dumps(provider["dependencies"], indent=2, sort_keys=True),
            "```",
            "- Capabilities:",
            "```json",
            json.dumps(provider["capabilities"], indent=2, sort_keys=True),
            "```",
            "- Last runtime result:",
            "```json",
            json.dumps(provider["last_runtime_result"], indent=2, sort_keys=True),
            "```",
            "- Health:",
            "```json",
            json.dumps(provider["health"], indent=2, sort_keys=True),
            "```",
            "",
        ])
    _write_text(evidence_dir / "PROVIDER_REPORT.md", "\n".join(lines))


def _write_blockers(evidence_dir: Path, blockers: List[Dict[str, Any]]) -> None:
    lines = ["# External Blockers", ""]
    for index, blocker in enumerate(blockers, start=1):
        lines.extend([
            f"## Blocker {index}",
            f"- Description: {blocker['description']}",
            f"- Why Builder A cannot solve it: {blocker['why_builder_a_cannot_solve_it']}",
            "- Evidence:",
            "```json",
            json.dumps(blocker["evidence"], indent=2, sort_keys=True),
            "```",
            f"- Required external input: {blocker['required_external_input']}",
            "",
        ])
    _write_text(evidence_dir / "BLOCKERS.md", "\n".join(lines))


def _write_reproduce_runtime(evidence_dir: Path) -> None:
    lines = [
        "# Reproduce Runtime",
        "",
        "## Working Directory",
        f"`{ROOT}`",
        "",
        "## Dependencies Observed During Evidence Generation",
        "- Python virtualenv: `./.venv/bin/python`",
        "- Import path: `PYTHONPATH=src`",
        "- Required for published transcript path: `httpx`",
        "- Optional and unavailable in this run: `youtube_transcript_api`, `whisper`, `agent-reach`, `yt-dlp`, Exa MCP route via `mcporter`",
        "",
        "## URLs Used",
        "```json",
        json.dumps([{source["id"]: source["url"]} for source in SOURCES], indent=2, sort_keys=True),
        "```",
        "",
        "## Generate Evidence Package",
        "```bash",
        "PYTHONPATH=src ./.venv/bin/python examples/generate_runtime_evidence.py",
        "```",
        "",
        "Expected output: a single path like `runtime_evidence/runtime_YYYYMMDDTHHMMSSZ`.",
        "",
        "## Runtime Inspector Only",
        "```bash",
        "PYTHONPATH=src ./.venv/bin/python examples/runtime_inspector.py --format json --timeout-ms 30000",
        "```",
        "",
        "Expected output from the current certified published-transcript path: JSON with `system_summary.status` equal to `pass` when live URLs are reachable.",
        "",
        "## Test Commands Used During Certification",
        "```bash",
        "PYTHONPATH=src ./.venv/bin/python -m pytest tests/processing/test_transcript.py tests/providers/test_transcript_provider.py -q",
        "PYTHONPATH=src ./.venv/bin/python -m pytest tests/retrieval/test_quote_search.py tests/end_to_end/test_transcript_citation_lifecycle.py -q",
        "PYTHONPATH=src ./.venv/bin/python -m pytest -q",
        "```",
        "",
        "Expected output observed before evidence package generation: `504 passed, 1 warning` for the full suite.",
        "",
        "## Configuration",
        "- `TranscriptProvider` timeout: `30000` ms.",
        "- Published transcript acquisition: `source=published`, `allow_fallback=False`.",
        "- Runtime storage: `InMemoryKnowledgeStore`.",
        "- No cleanup step is executed by the evidence generator.",
    ]
    _write_text(evidence_dir / "REPRODUCE_RUNTIME.md", "\n".join(lines))


def _write_manifest(evidence_dir: Path, inspector: Dict[str, Any]) -> None:
    _write_json(evidence_dir / "EVIDENCE_MANIFEST.json", {
        "generated_at": _now_iso(),
        "evidence_dir": str(evidence_dir),
        "preservation": "No cleanup performed. Raw responses, transcripts, intermediate files, chunk data, runtime inspector output, and logs are retained in this directory.",
        "required_files": [
            "CORPUS_INVENTORY.md",
            "ACQUISITION_LOG.md",
            "RUNTIME_INSPECTOR.md",
            "transcripts/",
            "CHUNK_INVENTORY.csv",
            "KNOWLEDGE_OBJECTS.md",
            "STORAGE_VERIFICATION.md",
            "RETRIEVAL_VERIFICATION.md",
            "search_results/",
            "PERFORMANCE.md",
            "PROVIDER_REPORT.md",
            "BLOCKERS.md",
            "REPRODUCE_RUNTIME.md",
            "RUNTIME_TREE.txt",
        ],
        "system_summary": inspector["system_summary"],
    })


def _write_tree(evidence_dir: Path) -> None:
    lines = [str(evidence_dir.name) + "/"]
    runtime_tree_listed = False
    for root, dirs, files in os.walk(evidence_dir):
        dirs.sort()
        files.sort()
        relative_root = Path(root).relative_to(evidence_dir)
        depth = 0 if str(relative_root) == "." else len(relative_root.parts)
        prefix = "  " * depth
        if str(relative_root) != ".":
            lines.append(f"{prefix}{relative_root.name}/")
        file_prefix = "  " * (depth + 1)
        for filename in files:
            if filename == "RUNTIME_TREE.txt":
                runtime_tree_listed = True
            lines.append(f"{file_prefix}{filename}")
    if not runtime_tree_listed:
        lines.insert(1, "  RUNTIME_TREE.txt")
    _write_text(evidence_dir / "RUNTIME_TREE.txt", "\n".join(lines) + "\n")


def _chunk_inventory_record(source_id: str, chunk: Dict[str, Any]) -> Dict[str, Any]:
    ko = chunk["object"]
    data = ko.structured_data or {}
    embedding = data.get("embedding") or []
    storage = chunk.get("storage") or {}
    return {
        "chunk id": data.get("transcript_chunk_id"),
        "transcript id": data.get("transcript_id") or source_id,
        "speaker": data.get("speaker"),
        "start timestamp": data.get("timestamp_start"),
        "end timestamp": data.get("timestamp_end"),
        "token count": ko.word_count,
        "embedding id": _embedding_id(embedding),
        "citation id": _citation_id(ko.id, 0) if ko.citations else None,
        "KnowledgeObject id": ko.id,
        "stored id": storage.get("stored_id"),
        "storage status": "stored_in_memory" if storage.get("persisted_in_store_under_own_id") else "duplicate_prevented_or_temporary",
    }


def _transcript_readme(item: Dict[str, Any], index_entry: Dict[str, Any]) -> str:
    source = item["source"]
    return "\n".join([
        f"# {source['id']}",
        "",
        f"- title: {source['title']}",
        f"- show: {source['show']}",
        f"- url: {source['url']}",
        f"- original transcript: {item['paths']['original_transcript']}",
        f"- parsed transcript: {item['paths']['parsed_transcript']}",
        "- speaker assignments: SPEAKER_ASSIGNMENTS.csv",
        "- timestamp assignments: TIMESTAMP_ASSIGNMENTS.csv",
        "- chunk boundaries: CHUNK_BOUNDARIES.jsonl",
        "- context windows: CONTEXT_WINDOWS.jsonl",
        "- raw KnowledgeObjects for this transcript: KNOWLEDGE_OBJECTS.jsonl",
        f"- segment count: {len(item['segments'])}",
        f"- chunk KnowledgeObject count: {len(index_entry['chunk_objects'])}",
    ])


def _corpus_state_item(item: Dict[str, Any]) -> Dict[str, Any]:
    source = item["source"]
    speakers = Counter(segment.get("speaker", "unknown") for segment in item["segments"])
    return {
        "id": source["id"],
        "title": source["title"],
        "show": source["show"],
        "guests": source["guests"],
        "hosts": source["hosts"],
        "url": source["url"],
        "transcript_source": source["transcript_source"],
        "acquisition_timestamp": item["response_metadata"].get("acquisition_timestamp"),
        "content_bytes": len(item["content"].encode("utf-8")),
        "word_count": len(item["content"].split()),
        "segment_count": len(item["segments"]),
        "direct_chunk_count": len(item["direct_chunks"]),
        "speaker_counts": dict(sorted(speakers.items())),
        "paths": item["paths"],
    }


def _search_expectation(search: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
    expectation = search.get("expect")
    if expectation == "success":
        return "met" if results else "not met: zero results"
    if expectation == "failure_zero_results":
        return "met" if not results else f"not met: {len(results)} results"
    return "no expectation configured"


def _attempt_by_id(attempts: Iterable[Dict[str, Any]], attempt_id: str) -> Optional[Dict[str, Any]]:
    for attempt in attempts:
        if attempt.get("attempt_id") == attempt_id:
            return attempt
    return None


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _run_command(label: str, command: List[str], timeout_seconds: int) -> Dict[str, Any]:
    started = time.perf_counter()
    if shutil.which(command[0]) is None:
        return {
            "label": label,
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": f"command not found: {command[0]}",
            "elapsed_seconds": round(time.perf_counter() - started, 6),
        }
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds, check=False)
        return {
            "label": label,
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
        }
    except Exception as exc:
        return {
            "label": label,
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": round(time.perf_counter() - started, 6),
        }


def _command_result(results: List[Dict[str, Any]], label: str) -> Optional[Dict[str, Any]]:
    for result in results:
        if result.get("label") == label:
            return result
    return None


def _embedding_id(embedding: Any) -> Optional[str]:
    if not embedding:
        return None
    payload = json.dumps(embedding, separators=(",", ":"), sort_keys=True)
    return "embedding:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _citation_id(knowledge_object_id: str, index: int) -> str:
    return f"citation:{knowledge_object_id}:{index}"


def _format_seconds(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    total = int(value)
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _to_plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, tuple):
        return [_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_plain(item) for key, item in value.items()}
    if is_dataclass(value):
        return _to_plain(asdict(value))
    return value


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_to_plain(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(_to_plain(row), sort_keys=True, ensure_ascii=False) + "\n")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    raise SystemExit(main())
