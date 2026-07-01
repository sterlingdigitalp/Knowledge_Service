#!/usr/bin/env python3
"""Runtime inspector for the real podcast transcript citation engine.

This script intentionally uses live published transcript pages. It does not use
synthetic fixtures, mocks, or canned transcript text.
"""

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from knowledge_service.acquisition.acquisition_bundle import AcquisitionBundle, DocumentRecord, ExecutionRecord
from knowledge_service.interfaces.provider import ProviderRequest, ProviderType
from knowledge_service.processing.pipeline import Pipeline
from knowledge_service.providers.transcript_provider import TranscriptProvider
from knowledge_service.retrieval.quotes import search_quotes
from knowledge_service.retrieval.retriever import KnowledgeRetrieverImpl
from knowledge_service.storage.postgres.in_memory_store import InMemoryKnowledgeStore
from knowledge_service.storage.repositories.knowledge_repository import KnowledgeRepository
from knowledge_service.intelligence.inspector import inspect_intelligence_runtime


REAL_SOURCES: List[Dict[str, Any]] = [
    {
        "id": "lex-sam-altman-2",
        "url": "https://lexfridman.com/sam-altman-2-transcript/",
        "show": "Lex Fridman Podcast",
        "episode": "Sam Altman: OpenAI, GPT-5, Sora, Board Saga, Elon Musk, Ilya, Power and AGI",
        "episode_date": "2024-03-18T00:00:00Z",
        "source_note": "Official human-generated transcript with speaker labels and clickable timestamps.",
    },
    {
        "id": "dwarkesh-satya-nadella-podscripts",
        "url": "https://podscripts.co/podcasts/dwarkesh-podcast/satya-nadella-how-microsoft-is-preparing-for-agi",
        "show": "Dwarkesh Podcast",
        "episode": "Satya Nadella: How Microsoft is preparing for AGI",
        "episode_date": "2025-11-12T00:00:00Z",
        "source_note": "Podscripts transcript using 'Starting point is HH:MM:SS' rows without speaker labels.",
    },
    {
        "id": "happyscribe-lex-sam-altman-419",
        "url": "https://podcasts.happyscribe.com/lex-fridman-podcast-artificial-intelligence-ai/419-sam-altman-openai-gpt-5-sora-board-saga-elon-musk-ilya-power-agi",
        "show": "Lex Fridman Podcast",
        "episode": "#419 Sam Altman: OpenAI, GPT-5, Sora, Board Saga, Elon Musk, Ilya, Power and AGI",
        "episode_date": "2024-03-18T00:00:00Z",
        "source_note": "HappyScribe transcript using standalone timestamp blocks without speaker labels.",
    },
    {
        "id": "happyscribe-all-in-bill-ackman",
        "url": "https://podcasts.happyscribe.com/all-in-with-chamath-jason-sacks-friedberg/bill-ackman-investment-strategy-what-the-market-is-missing-how-ai-breaks-businesses",
        "show": "All-In Podcast",
        "episode": "Bill Ackman: Investment strategy, what the market is missing, how AI breaks businesses",
        "episode_date": "2025-01-01T00:00:00Z",
        "source_note": "HappyScribe transcript with timestamps but no speaker labels; speaker filters must remain hard filters.",
    },
]


RETRIEVAL_CHECKS: List[Dict[str, Any]] = [
    {
        "name": "speaker_hard_filter_sam_altman",
        "query": "power struggle",
        "speaker": "Sam Altman",
        "show": "Lex Fridman Podcast",
        "limit": 3,
        "expect_min": 1,
        "expect_all_speaker": "Sam Altman",
    },
    {
        "name": "speaker_hard_filter_lex_fridman",
        "query": "board structure",
        "speaker": "Lex Fridman",
        "show": "Lex Fridman Podcast",
        "limit": 3,
        "expect_min": 1,
        "expect_all_speaker": "Lex Fridman",
    },
    {
        "name": "unknown_speaker_transcript_does_not_match_bill_ackman_filter",
        "query": "investment strategy",
        "speaker": "Bill Ackman",
        "show": "All-In Podcast",
        "limit": 3,
        "expect_max": 0,
    },
    {
        "name": "unknown_speaker_retrieval_allowed_without_speaker_filter",
        "query": "investment strategy market AI businesses",
        "show": "All-In Podcast",
        "limit": 3,
        "expect_min": 1,
    },
    {
        "name": "cross_corpus_podscripts_retrieval",
        "query": "Fairwater data center training capacity",
        "show": "Dwarkesh Podcast",
        "limit": 3,
        "expect_min": 1,
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect real podcast transcript citation runtime")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--include-acquisition-ladder", action="store_true")
    parser.add_argument("--whisper-model", default="tiny")
    parser.add_argument("--whisper-clip-seconds", type=float, default=45.0)
    parser.add_argument("--audio-download-dir")
    parser.add_argument("--phase3-state-dir", help="Include Phase 3 intelligence collection runtime state")
    args = parser.parse_args()

    report = inspect_runtime(
        args.timeout_ms,
        include_acquisition_ladder=args.include_acquisition_ladder,
        whisper_model=args.whisper_model,
        whisper_clip_seconds=args.whisper_clip_seconds,
        audio_download_dir=args.audio_download_dir,
        phase3_state_dir=args.phase3_state_dir,
    )
    if args.format == "markdown":
        print(_to_markdown(report))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["system_summary"]["status"] == "pass" else 1


def inspect_runtime(
    timeout_ms: int,
    include_acquisition_ladder: bool = False,
    whisper_model: str = "tiny",
    whisper_clip_seconds: float = 45.0,
    audio_download_dir: Optional[str] = None,
    phase3_state_dir: Optional[str] = None,
) -> Dict[str, Any]:
    started = time.perf_counter()
    acquisition_started = time.perf_counter()
    bundle, corpus, acquisition_diagnostics = _acquire_real_sources(timeout_ms)
    acquisition_seconds = time.perf_counter() - acquisition_started

    pipeline_started = time.perf_counter()
    knowledge_objects = Pipeline().process(bundle)
    pipeline_seconds = time.perf_counter() - pipeline_started

    index_started = time.perf_counter()
    repo = KnowledgeRepository(InMemoryKnowledgeStore())
    for knowledge_object in knowledge_objects:
        repo.store(knowledge_object)
    retriever = KnowledgeRetrieverImpl(repo)
    index_seconds = time.perf_counter() - index_started

    retrieval_started = time.perf_counter()
    retrieval = _run_retrieval_checks(retriever)
    retrieval_seconds = time.perf_counter() - retrieval_started

    diagnostics = {
        "environment": _environment_diagnostics(),
        "acquisition": acquisition_diagnostics,
        "failures": [item for item in corpus if item["status"] != "success"],
        "acquisition_ladder": _acquisition_ladder_dependency_status(),
    }
    if include_acquisition_ladder:
        diagnostics["acquisition_ladder"] = _inspect_acquisition_ladder(
            timeout_ms=timeout_ms,
            whisper_model=whisper_model,
            whisper_clip_seconds=whisper_clip_seconds,
            audio_download_dir=audio_download_dir,
        )
    intelligence_collection = inspect_intelligence_runtime(phase3_state_dir) if phase3_state_dir else None

    chunk_count = sum(1 for item in knowledge_objects if item.type.value == "chunk")
    document_count = sum(1 for item in knowledge_objects if item.type.value == "document")
    segment_count = sum(item.get("segment_count", 0) for item in corpus if item["status"] == "success")
    speaker_counts = Counter()
    for item in corpus:
        speaker_counts.update(item.get("speaker_counts", {}))

    all_checks_passed = all(check["passed"] for check in retrieval["checks"])
    all_sources_successful = all(item["status"] == "success" for item in corpus)
    ladder_passed = True
    if include_acquisition_ladder:
        ladder_passed = all(path.get("status") == "success" for path in diagnostics["acquisition_ladder"].get("paths", []))
    phase3_passed = True if intelligence_collection is None else intelligence_collection["system_summary"]["status"] == "pass"
    status = "pass" if all_checks_passed and all_sources_successful and chunk_count > 0 and ladder_passed and phase3_passed else "fail"

    return {
        "system_summary": {
            "status": status,
            "generated_at": _now_iso(),
            "source_count": len(REAL_SOURCES),
            "successful_sources": sum(1 for item in corpus if item["status"] == "success"),
            "document_count": document_count,
            "chunk_count": chunk_count,
            "segment_count": segment_count,
            "speaker_counts": dict(sorted(speaker_counts.items())),
            "retrieval_checks_passed": sum(1 for check in retrieval["checks"] if check["passed"]),
            "retrieval_checks_total": len(retrieval["checks"]),
        },
        "corpus": corpus,
        "retrieval": retrieval,
        "intelligence_collection": intelligence_collection,
        "diagnostics": diagnostics,
        "performance": {
            "acquisition_seconds": round(acquisition_seconds, 3),
            "pipeline_seconds": round(pipeline_seconds, 3),
            "index_seconds": round(index_seconds, 3),
            "retrieval_seconds": round(retrieval_seconds, 3),
            "total_seconds": round(time.perf_counter() - started, 3),
            "segments_per_pipeline_second": round(segment_count / pipeline_seconds, 3) if pipeline_seconds else None,
            "chunks_per_pipeline_second": round(chunk_count / pipeline_seconds, 3) if pipeline_seconds else None,
        },
    }


def _acquire_real_sources(timeout_ms: int) -> tuple[AcquisitionBundle, List[Dict[str, Any]], List[Dict[str, Any]]]:
    provider = TranscriptProvider("runtime-inspector-transcript-provider")
    provider.initialize({"timeout_ms": timeout_ms})
    bundle = AcquisitionBundle(
        request_id="runtime-inspector-real-podcasts",
        plan_id="runtime-inspector",
        acquisition_timestamp=_now_iso(),
    )
    corpus: List[Dict[str, Any]] = []
    diagnostics: List[Dict[str, Any]] = []

    for source in REAL_SOURCES:
        started = time.perf_counter()
        metadata = {
            "transcript_id": source["id"],
            "source_url": source["url"],
            "show": source["show"],
            "episode": source["episode"],
            "episode_date": source["episode_date"],
        }
        response = provider.execute(ProviderRequest(
            target=source["url"],
            provider_type=ProviderType.API,
            options={
                "source": "published",
                "allow_fallback": False,
                "timeout_ms": timeout_ms,
                "metadata": metadata,
            },
        ))
        latency_ms = int((time.perf_counter() - started) * 1000)

        if response.error:
            bundle.add_execution_record(ExecutionRecord(
                step_id=source["id"],
                provider_name=provider.name,
                provider_type="api",
                target=source["url"],
                status="failed",
                latency_ms=latency_ms,
                error_code=response.error.code,
                error_message=response.error.message,
            ))
            item = {
                "id": source["id"],
                "url": source["url"],
                "show": source["show"],
                "episode": source["episode"],
                "source_note": source["source_note"],
                "status": "failed",
                "error_code": response.error.code,
                "error_message": response.error.message,
                "latency_ms": latency_ms,
            }
            corpus.append(item)
            diagnostics.append(item)
            continue

        content = response.content or ""
        segments = response.metadata.get("transcript_segments", [])
        speakers = Counter(segment.get("speaker", "unknown") for segment in segments)
        bundle.add_execution_record(ExecutionRecord(
            step_id=source["id"],
            provider_name=provider.name,
            provider_type="api",
            target=source["url"],
            status="success",
            latency_ms=latency_ms,
            response_metadata=response.metadata,
        ))
        bundle.add_document(DocumentRecord(
            document_id=source["id"],
            url=source["url"],
            provider_name=provider.name,
            content_type=response.content_type,
            raw_content=content,
            content_size_bytes=len(content.encode("utf-8")),
            acquired_at=_now_iso(),
            metadata=response.metadata,
            source_type="video_transcript",
        ))
        corpus.append({
            "id": source["id"],
            "url": source["url"],
            "show": source["show"],
            "episode": source["episode"],
            "episode_date": source["episode_date"],
            "source_note": source["source_note"],
            "status": "success",
            "content_type": response.content_type,
            "content_size_bytes": len(content.encode("utf-8")),
            "segment_count": len(segments),
            "speaker_counts": dict(sorted(speakers.items())),
            "first_segments": [
                {
                    "start_seconds": segment.get("start_seconds"),
                    "end_seconds": segment.get("end_seconds"),
                    "speaker": segment.get("speaker"),
                    "text": _truncate(segment.get("text", ""), 180),
                }
                for segment in segments[:3]
            ],
            "latency_ms": latency_ms,
        })

    return bundle, corpus, diagnostics


def _run_retrieval_checks(retriever: KnowledgeRetrieverImpl) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    for check in RETRIEVAL_CHECKS:
        started = time.perf_counter()
        results = search_quotes(
            retriever,
            query=check["query"],
            speaker=check.get("speaker"),
            show=check.get("show"),
            limit=check.get("limit", 3),
        )
        elapsed = time.perf_counter() - started
        result_dicts = [result.to_dict() for result in results]
        passed, failure = _evaluate_retrieval_check(check, result_dicts)
        checks.append({
            "name": check["name"],
            "query": check["query"],
            "speaker": check.get("speaker"),
            "show": check.get("show"),
            "result_count": len(results),
            "passed": passed,
            "failure": failure,
            "elapsed_seconds": round(elapsed, 4),
            "top_results": [_compact_result(result) for result in result_dicts[:3]],
        })
    return {"checks": checks}


def _evaluate_retrieval_check(check: Dict[str, Any], results: List[Dict[str, Any]]) -> tuple[bool, Optional[str]]:
    expect_min = check.get("expect_min")
    if expect_min is not None and len(results) < expect_min:
        return False, f"Expected at least {expect_min} results, observed {len(results)}"
    expect_max = check.get("expect_max")
    if expect_max is not None and len(results) > expect_max:
        return False, f"Expected at most {expect_max} results, observed {len(results)}"
    expected_speaker = check.get("expect_all_speaker")
    if expected_speaker and any(result.get("speaker") != expected_speaker for result in results):
        speakers = sorted({str(result.get("speaker")) for result in results})
        return False, f"Expected only speaker {expected_speaker}, observed {speakers}"
    return True, None


def _environment_diagnostics() -> Dict[str, Any]:
    modules = {}
    for module_name in ["httpx", "youtube_transcript_api", "yt_dlp", "whisper", "torch"]:
        modules[module_name] = importlib.util.find_spec(module_name) is not None
    commands = {command: _which(command) for command in ["agent-reach", "yt-dlp", "whisper", "ffmpeg", "mcporter", "curl"]}
    return {"modules": modules, "commands": commands}


def _acquisition_ladder_dependency_status() -> Dict[str, Any]:
    return {
        "executed": False,
        "dependencies": {
            "published_transcript": {"available": importlib.util.find_spec("httpx") is not None, "module": "httpx"},
            "youtube_captions": {"available": importlib.util.find_spec("youtube_transcript_api") is not None, "module": "youtube_transcript_api"},
            "yt_dlp_audio": {"available": importlib.util.find_spec("yt_dlp") is not None and _which("yt-dlp") is not None, "module": "yt_dlp", "command": _which("yt-dlp")},
            "whisper": {"available": importlib.util.find_spec("whisper") is not None, "module": "whisper", "command": _which("whisper")},
            "ffmpeg": {"available": _which("ffmpeg") is not None, "command": _which("ffmpeg")},
        },
        "paths": [
            {"acquisition_path": "published_transcript", "status": "not_executed"},
            {"acquisition_path": "youtube_captions", "status": "not_executed"},
            {"acquisition_path": "whisper_fallback", "status": "not_executed"},
        ],
    }


def _inspect_acquisition_ladder(
    timeout_ms: int,
    whisper_model: str,
    whisper_clip_seconds: float,
    audio_download_dir: Optional[str],
) -> Dict[str, Any]:
    provider = TranscriptProvider("runtime-inspector-acquisition-ladder")
    provider.initialize({"timeout_ms": timeout_ms, "whisper_model": whisper_model})
    audio_dir = audio_download_dir or tempfile.mkdtemp(prefix="knowledge_service_runtime_inspector_audio_")
    paths = [
        {
            "acquisition_path": "published_transcript",
            "target": "https://lexfridman.com/sam-altman-2-transcript/",
            "options": {
                "source": "published",
                "allow_fallback": False,
                "timeout_ms": timeout_ms,
                "metadata": {
                    "transcript_id": "inspector-published-lex-sam-altman",
                    "source_url": "https://lexfridman.com/sam-altman-2-transcript/",
                    "show": "Lex Fridman Podcast",
                    "episode": "Sam Altman published transcript",
                },
            },
        },
        {
            "acquisition_path": "youtube_captions",
            "target": "https://youtube.com/watch?v=jvqFAi7vkBc",
            "options": {
                "source": "youtube_captions",
                "allow_fallback": False,
                "timeout_ms": timeout_ms,
                "languages": ["en"],
                "metadata": {
                    "transcript_id": "inspector-youtube-captions-lex-sam-altman",
                    "source_url": "https://youtube.com/watch?v=jvqFAi7vkBc",
                    "show": "Lex Fridman Podcast",
                    "episode": "Sam Altman YouTube captions",
                },
            },
        },
        {
            "acquisition_path": "whisper_fallback",
            "target": "https://youtube.com/watch?v=jvqFAi7vkBc",
            "options": {
                "source": "whisper_fallback",
                "allow_fallback": False,
                "timeout_ms": timeout_ms,
                "audio_download_dir": audio_dir,
                "audio_clip_start_seconds": 0,
                "audio_clip_duration_seconds": whisper_clip_seconds,
                "whisper_model": whisper_model,
                "language": "en",
                "whisper_options": {"fp16": False, "verbose": False},
                "metadata": {
                    "transcript_id": "inspector-whisper-lex-sam-altman",
                    "source_url": "https://youtube.com/watch?v=jvqFAi7vkBc",
                    "show": "Lex Fridman Podcast",
                    "episode": "Sam Altman Whisper audio clip",
                },
            },
        },
    ]
    results = []
    for path in paths:
        results.append(_execute_ladder_path(provider, path))
    return {
        **_acquisition_ladder_dependency_status(),
        "executed": True,
        "audio_download_dir": audio_dir,
        "paths": results,
        "last_successful_runtime": max(
            [result["completed_at"] for result in results if result.get("status") == "success"],
            default=None,
        ),
    }


def _execute_ladder_path(provider: TranscriptProvider, path: Dict[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    response = provider.execute(ProviderRequest(
        target=path["target"],
        provider_type=ProviderType.API,
        options=path["options"],
    ))
    elapsed = time.perf_counter() - started
    base = {
        "acquisition_path": path["acquisition_path"],
        "target": path["target"],
        "elapsed_seconds": round(elapsed, 3),
        "completed_at": _now_iso(),
    }
    if response.error:
        return {
            **base,
            "status": "failed",
            "error_code": response.error.code,
            "error_message": response.error.message,
            "failure_diagnostics": response.error.__dict__,
        }

    bundle = AcquisitionBundle(
        request_id=f"runtime-inspector-{path['acquisition_path']}",
        plan_id="runtime-inspector-acquisition-ladder",
        acquisition_timestamp=_now_iso(),
    )
    bundle.add_execution_record(ExecutionRecord(
        step_id=path["acquisition_path"],
        provider_name=provider.name,
        provider_type="api",
        target=path["target"],
        status="success",
        latency_ms=int(elapsed * 1000),
        response_metadata=response.metadata,
    ))
    bundle.add_document(DocumentRecord(
        document_id=path["options"].get("metadata", {}).get("transcript_id", path["acquisition_path"]),
        url=path["target"],
        provider_name=provider.name,
        content_type=response.content_type,
        raw_content=response.content or "",
        content_size_bytes=len((response.content or "").encode("utf-8")),
        acquired_at=_now_iso(),
        metadata=response.metadata,
        source_type="video_transcript",
    ))
    knowledge_objects = Pipeline().process(bundle)
    chunk_objects = [item for item in knowledge_objects if item.type.value == "chunk"]
    embedding_count = sum(1 for item in chunk_objects if item.structured_data and item.structured_data.get("embedding"))
    segments = response.metadata.get("transcript_segments", [])
    speakers = Counter(segment.get("speaker", "unknown") for segment in segments)
    return {
        **base,
        "status": "success",
        "transcript_source": response.metadata.get("transcript_source"),
        "content_type": response.content_type,
        "content_size_bytes": len((response.content or "").encode("utf-8")),
        "transcript_count": 1,
        "segment_count": len(segments),
        "chunk_count": len(chunk_objects),
        "embedding_count": embedding_count,
        "speaker_counts": dict(sorted(speakers.items())),
        "downloaded_audio_path": response.metadata.get("downloaded_audio_path"),
        "first_segments": segments[:3],
    }


def _which(command: str) -> Optional[str]:
    found = shutil.which(command)
    if found:
        return found
    venv_command = ROOT / ".venv" / "bin" / command
    return str(venv_command) if venv_command.exists() else None


def _compact_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "quote": _truncate(result.get("quote", ""), 260),
        "speaker": result.get("speaker"),
        "speaker_confidence": result.get("speaker_confidence"),
        "transcript_confidence": result.get("transcript_confidence"),
        "show": result.get("show"),
        "episode": result.get("episode"),
        "timestamp_start": result.get("timestamp_start"),
        "timestamp_end": result.get("timestamp_end"),
        "timestamped_source_url": result.get("timestamped_source_url"),
        "relevance_score": result.get("relevance_score"),
    }


def _to_markdown(report: Dict[str, Any]) -> str:
    lines = ["# Runtime Inspector", "", "## System Summary"]
    for key, value in report["system_summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Corpus"])
    for item in report["corpus"]:
        lines.append(f"- {item['id']}: {item['status']} ({item.get('segment_count', 0)} segments)")
    lines.extend(["", "## Retrieval"])
    for check in report["retrieval"]["checks"]:
        lines.append(f"- {check['name']}: {'pass' if check['passed'] else 'fail'} ({check['result_count']} results)")
    if report.get("intelligence_collection"):
        phase3 = report["intelligence_collection"]
        lines.extend(["", "## Intelligence Collection"])
        for key, value in phase3["system_summary"].items():
            lines.append(f"- {key}: {value}")
    lines.extend(["", "## Diagnostics", f"```json\n{json.dumps(report['diagnostics'], indent=2, sort_keys=True)}\n```"])
    lines.extend(["", "## Performance"])
    for key, value in report["performance"].items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _truncate(value: str, limit: int) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    raise SystemExit(main())
