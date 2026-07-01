#!/usr/bin/env python3
"""Certify all transcript acquisition ladder paths against real podcast data."""

import csv
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from knowledge_service.acquisition.acquisition_bundle import AcquisitionBundle, DocumentRecord, ExecutionRecord
from knowledge_service.interfaces.provider import ProviderRequest, ProviderType
from knowledge_service.processing.pipeline import Pipeline
from knowledge_service.providers.transcript_provider import TranscriptProvider
from knowledge_service.retrieval.quotes import search_quotes
from knowledge_service.retrieval.retriever import KnowledgeRetrieverImpl
from knowledge_service.storage.postgres.in_memory_store import InMemoryKnowledgeStore
from knowledge_service.storage.repositories.knowledge_repository import KnowledgeRepository
from runtime_inspector import inspect_runtime


YOUTUBE_URL = "https://youtube.com/watch?v=jvqFAi7vkBc"
PUBLISHED_URL = "https://lexfridman.com/sam-altman-2-transcript/"
COMPARISON_QUERY = "end of this decade capable systems remarkable road AGI"

PATHS: List[Dict[str, Any]] = [
    {
        "path_id": "published_transcript",
        "tier": 1,
        "target": PUBLISHED_URL,
        "min_segments": 400,
        "options": {
            "source": "published",
            "allow_fallback": False,
            "timeout_ms": 30000,
            "metadata": {
                "transcript_id": "ladder-published-lex-sam-altman",
                "source_url": PUBLISHED_URL,
                "show": "Lex Fridman Podcast",
                "episode": "Sam Altman published transcript",
            },
        },
        "primary_search": {"query": COMPARISON_QUERY, "speaker": "Sam Altman", "show": "Lex Fridman Podcast", "limit": 3},
        "negative_search": {"query": COMPARISON_QUERY, "speaker": "Bill Ackman", "show": "Lex Fridman Podcast", "limit": 3},
    },
    {
        "path_id": "youtube_captions",
        "tier": 2,
        "target": YOUTUBE_URL,
        "min_segments": 1000,
        "options": {
            "source": "youtube_captions",
            "allow_fallback": False,
            "timeout_ms": 30000,
            "languages": ["en"],
            "metadata": {
                "transcript_id": "ladder-youtube-captions-lex-sam-altman",
                "source_url": YOUTUBE_URL,
                "show": "Lex Fridman Podcast",
                "episode": "Sam Altman YouTube captions",
            },
        },
        "primary_search": {"query": COMPARISON_QUERY, "show": "Lex Fridman Podcast", "limit": 3},
        "negative_search": {"query": COMPARISON_QUERY, "speaker": "Sam Altman", "show": "Lex Fridman Podcast", "limit": 3},
    },
    {
        "path_id": "whisper_fallback",
        "tier": 3,
        "target": YOUTUBE_URL,
        "min_segments": 5,
        "options": {
            "source": "whisper_fallback",
            "allow_fallback": False,
            "timeout_ms": 30000,
            "audio_clip_start_seconds": 0,
            "audio_clip_duration_seconds": 45,
            "whisper_model": "tiny",
            "language": "en",
            "whisper_options": {"fp16": False, "verbose": False},
            "metadata": {
                "transcript_id": "ladder-whisper-lex-sam-altman",
                "source_url": YOUTUBE_URL,
                "show": "Lex Fridman Podcast",
                "episode": "Sam Altman Whisper audio clip",
            },
        },
        "primary_search": {"query": COMPARISON_QUERY, "show": "Lex Fridman Podcast", "limit": 3},
        "negative_search": {"query": COMPARISON_QUERY, "speaker": "Sam Altman", "show": "Lex Fridman Podcast", "limit": 3},
    },
]


def main() -> int:
    output_dir = _new_output_dir(ROOT / "runtime_evidence")
    for relative in ["raw", "transcripts", "segments", "knowledge_objects", "search_results", "audio", "logs"]:
        (output_dir / relative).mkdir(parents=True, exist_ok=True)

    dependency_report = _dependency_report()
    provider = TranscriptProvider("acquisition-ladder-certifier")
    provider.initialize({"timeout_ms": 30000, "whisper_model": "tiny"})

    path_results = []
    for config in PATHS:
        run_config = json.loads(json.dumps(config))
        if run_config["path_id"] == "whisper_fallback":
            run_config["options"]["audio_download_dir"] = str(output_dir / "audio")
        path_results.append(_run_path(output_dir, provider, run_config))

    comparative = _compare_paths(path_results)
    runtime_inspector_output = inspect_runtime(
        timeout_ms=30000,
        include_acquisition_ladder=True,
        whisper_model="tiny",
        whisper_clip_seconds=45.0,
        audio_download_dir=str(output_dir / "audio"),
    )
    _write_json(output_dir / "UPDATED_RUNTIME_INSPECTOR_OUTPUT.json", runtime_inspector_output)
    _write_text(output_dir / "UPDATED_RUNTIME_INSPECTOR_OUTPUT.md", _markdown_json("Updated Runtime Inspector Output", runtime_inspector_output))

    blockers = _remaining_blockers(dependency_report, path_results)
    _write_json(output_dir / "raw" / "path_results.json", path_results)
    _write_json(output_dir / "raw" / "comparative.json", comparative)
    _write_json(output_dir / "raw" / "dependency_report.json", dependency_report)
    _write_csv(output_dir / "raw" / "path_summary.csv", _path_summary_rows(path_results))

    _write_text(output_dir / "ACQUISITION_LADDER_CERTIFICATION_REPORT.md", _certification_report(path_results, blockers, output_dir))
    _write_text(output_dir / "DEPENDENCY_INSTALLATION_REPORT.md", _dependency_installation_report(dependency_report))
    _write_text(output_dir / "RUNTIME_VALIDATION_RESULTS.md", _runtime_validation_results(path_results))
    _write_text(output_dir / "COMPARATIVE_TRANSCRIPT_ANALYSIS.md", _comparative_report(comparative, path_results))
    _write_text(output_dir / "PERFORMANCE_COMPARISON.md", _performance_report(path_results, comparative))
    _write_text(output_dir / "REMAINING_EXTERNAL_BLOCKERS.md", _blockers_report(blockers))
    _write_text(output_dir / "README.md", _readme(output_dir))

    print(str(output_dir))
    return 0 if not blockers and all(result["status"] == "success" for result in path_results) else 1


def _run_path(output_dir: Path, provider: TranscriptProvider, config: Dict[str, Any]) -> Dict[str, Any]:
    attempts = []
    accepted_response = None
    accepted_elapsed = 0.0
    for attempt_number in range(1, 4):
        started = time.perf_counter()
        response = provider.execute(ProviderRequest(
            target=config["target"],
            provider_type=ProviderType.API,
            options=config["options"],
        ))
        elapsed = time.perf_counter() - started
        if response.error:
            attempts.append({
                "attempt_number": attempt_number,
                "status": "failed",
                "elapsed_seconds": round(elapsed, 6),
                "error_code": response.error.code,
                "error_message": response.error.message,
            })
            time.sleep(1.0)
            continue
        segment_count = len(response.metadata.get("transcript_segments", []))
        valid = segment_count >= config["min_segments"]
        attempts.append({
            "attempt_number": attempt_number,
            "status": "success" if valid else "validation_failed",
            "elapsed_seconds": round(elapsed, 6),
            "segment_count": segment_count,
            "minimum_required_segments": config["min_segments"],
            "content_bytes": len((response.content or "").encode("utf-8")),
        })
        if valid:
            accepted_response = response
            accepted_elapsed = elapsed
            break
        time.sleep(1.0)

    path_id = config["path_id"]
    if accepted_response is None:
        result = {
            "path_id": path_id,
            "tier": config["tier"],
            "target": config["target"],
            "status": "failed",
            "attempts": attempts,
        }
        _write_json(output_dir / "logs" / f"{path_id}_failed.json", result)
        return result

    response = accepted_response
    segments = response.metadata.get("transcript_segments", [])
    transcript_path = output_dir / "transcripts" / f"{path_id}.txt"
    segment_path = output_dir / "segments" / f"{path_id}.jsonl"
    transcript_path.write_text(response.content or "", encoding="utf-8")
    _write_jsonl(segment_path, segments)

    processing_started = time.perf_counter()
    bundle = _bundle_for_response(path_id, config, provider, response, accepted_elapsed)
    knowledge_objects = Pipeline().process(bundle)
    processing_elapsed = time.perf_counter() - processing_started

    storage_started = time.perf_counter()
    store = InMemoryKnowledgeStore()
    repo = KnowledgeRepository(store)
    stored_ids = [repo.store(ko) for ko in knowledge_objects]
    storage_elapsed = time.perf_counter() - storage_started
    retriever = KnowledgeRetrieverImpl(repo)

    retrieval_started = time.perf_counter()
    primary_results = search_quotes(retriever, **config["primary_search"])
    negative_results = search_quotes(retriever, **config["negative_search"])
    retrieval_elapsed = time.perf_counter() - retrieval_started

    ko_path = output_dir / "knowledge_objects" / f"{path_id}.jsonl"
    _write_jsonl(ko_path, [ko.to_dict() for ko in knowledge_objects])
    primary_search_path = output_dir / "search_results" / f"{path_id}_primary.json"
    negative_search_path = output_dir / "search_results" / f"{path_id}_negative_speaker_filter.json"
    _write_json(primary_search_path, [result.to_dict() for result in primary_results])
    _write_json(negative_search_path, [result.to_dict() for result in negative_results])

    chunks = [ko for ko in knowledge_objects if ko.type.value == "chunk"]
    docs = [ko for ko in knowledge_objects if ko.type.value == "document"]
    embedding_count = sum(1 for chunk in chunks if chunk.structured_data and chunk.structured_data.get("embedding"))
    citation_count = sum(len(ko.citations) for ko in knowledge_objects)
    speaker_counts = Counter(segment.get("speaker", "unknown") for segment in segments)
    duration = max([segment.get("end_seconds") or segment.get("start_seconds") or 0.0 for segment in segments], default=0.0)
    word_count = len((response.content or "").split())
    equivalent_shape = _equivalent_shape(docs, chunks)

    return {
        "path_id": path_id,
        "tier": config["tier"],
        "target": config["target"],
        "status": "success",
        "attempts": attempts,
        "transcript_source": response.metadata.get("transcript_source"),
        "content_type": response.content_type,
        "content_bytes": len((response.content or "").encode("utf-8")),
        "word_count": word_count,
        "segment_count": len(segments),
        "duration_seconds": duration,
        "speaker_counts": dict(sorted(speaker_counts.items())),
        "document_count": len(docs),
        "chunk_count": len(chunks),
        "embedding_count": embedding_count,
        "citation_count": citation_count,
        "knowledge_object_ids": [ko.id for ko in knowledge_objects],
        "stored_ids": stored_ids,
        "storage_backend": "InMemoryKnowledgeStore",
        "equivalent_knowledge_object_shape": equivalent_shape,
        "downloaded_audio_path": response.metadata.get("downloaded_audio_path"),
        "files": {
            "transcript": str(transcript_path.relative_to(output_dir)),
            "segments": str(segment_path.relative_to(output_dir)),
            "knowledge_objects": str(ko_path.relative_to(output_dir)),
            "primary_search": str(primary_search_path.relative_to(output_dir)),
            "negative_search": str(negative_search_path.relative_to(output_dir)),
        },
        "retrieval": {
            "primary_input": config["primary_search"],
            "primary_count": len(primary_results),
            "primary_results": [result.to_dict() for result in primary_results],
            "negative_input": config["negative_search"],
            "negative_count": len(negative_results),
            "negative_results": [result.to_dict() for result in negative_results],
        },
        "performance": {
            "acquisition_seconds": round(accepted_elapsed, 6),
            "processing_seconds": round(processing_elapsed, 6),
            "storage_seconds": round(storage_elapsed, 6),
            "retrieval_seconds": round(retrieval_elapsed, 6),
            "total_runtime_seconds": round(accepted_elapsed + processing_elapsed + storage_elapsed + retrieval_elapsed, 6),
        },
    }


def _bundle_for_response(path_id: str, config: Dict[str, Any], provider: TranscriptProvider, response: Any, elapsed: float) -> AcquisitionBundle:
    bundle = AcquisitionBundle(
        request_id=f"acquisition-ladder-{path_id}",
        plan_id="acquisition-ladder-certification",
        acquisition_timestamp=_now_iso(),
    )
    bundle.add_execution_record(ExecutionRecord(
        step_id=path_id,
        provider_name=provider.name,
        provider_type="api",
        target=config["target"],
        status="success",
        latency_ms=int(elapsed * 1000),
        response_metadata=response.metadata,
    ))
    bundle.add_document(DocumentRecord(
        document_id=config["options"].get("metadata", {}).get("transcript_id", path_id),
        url=config["target"],
        provider_name=provider.name,
        content_type=response.content_type,
        raw_content=response.content or "",
        content_size_bytes=len((response.content or "").encode("utf-8")),
        acquired_at=_now_iso(),
        metadata=response.metadata,
        source_type="video_transcript",
    ))
    return bundle


def _equivalent_shape(documents: List[Any], chunks: List[Any]) -> Dict[str, Any]:
    first_doc = documents[0] if documents else None
    chunks_with_embeddings = [chunk for chunk in chunks if chunk.structured_data and chunk.structured_data.get("embedding")]
    chunks_with_citations = [chunk for chunk in chunks if chunk.citations]
    chunks_with_timestamps = [chunk for chunk in chunks if chunk.structured_data and chunk.structured_data.get("timestamp_start") is not None]
    return {
        "has_document": first_doc is not None,
        "document_source_type": first_doc.source_type.value if first_doc else None,
        "document_has_raw_transcript": bool(first_doc and first_doc.structured_data and first_doc.structured_data.get("raw_transcript")),
        "chunk_count": len(chunks),
        "chunks_with_embeddings": len(chunks_with_embeddings),
        "chunks_with_citations": len(chunks_with_citations),
        "chunks_with_timestamps": len(chunks_with_timestamps),
        "equivalent": bool(first_doc and first_doc.source_type.value == "video_transcript" and chunks and len(chunks_with_embeddings) == len(chunks) and len(chunks_with_citations) == len(chunks)),
    }


def _compare_paths(path_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    successful = [result for result in path_results if result["status"] == "success"]
    by_id = {result["path_id"]: result for result in successful}
    published_duration = by_id.get("published_transcript", {}).get("duration_seconds") or 0.0
    published_primary = _top_result(by_id.get("published_transcript"))
    rows = []
    for result in successful:
        top = _top_result(result)
        timestamp_delta = None
        quote_overlap = None
        if published_primary and top:
            if top.get("timestamp_start") is not None and published_primary.get("timestamp_start") is not None:
                timestamp_delta = round(abs(float(top["timestamp_start"]) - float(published_primary["timestamp_start"])), 3)
            quote_overlap = _token_overlap(published_primary.get("quote", ""), top.get("quote", ""))
        rows.append({
            "path_id": result["path_id"],
            "segment_count": result["segment_count"],
            "word_count": result["word_count"],
            "duration_seconds": result["duration_seconds"],
            "completeness_vs_published_duration": round(result["duration_seconds"] / published_duration, 4) if published_duration else None,
            "speaker_counts": result["speaker_counts"],
            "primary_top_quote": top.get("quote") if top else None,
            "primary_top_timestamp": top.get("timestamp_start") if top else None,
            "timestamp_delta_vs_published_top_seconds": timestamp_delta,
            "quote_token_overlap_vs_published_top": quote_overlap,
            "retrieval_score": top.get("relevance_score") if top else None,
            "negative_speaker_filter_result_count": result["retrieval"]["negative_count"],
            "acquisition_seconds": result["performance"]["acquisition_seconds"],
        })
    return {"comparison_query": COMPARISON_QUERY, "rows": rows}


def _dependency_report() -> Dict[str, Any]:
    modules = {}
    for module in ["youtube_transcript_api", "yt_dlp", "whisper", "torch", "numpy", "httpx"]:
        modules[module] = {"available": importlib.util.find_spec(module) is not None}
    commands = {command: _which(command) for command in ["yt-dlp", "whisper", "ffmpeg", "agent-reach"]}
    version_commands = {
        "python": [str(ROOT / ".venv" / "bin" / "python"), "--version"],
        "pip_show_youtube_transcript_api": [str(ROOT / ".venv" / "bin" / "python"), "-m", "pip", "show", "youtube-transcript-api"],
        "pip_show_yt_dlp": [str(ROOT / ".venv" / "bin" / "python"), "-m", "pip", "show", "yt-dlp"],
        "pip_show_openai_whisper": [str(ROOT / ".venv" / "bin" / "python"), "-m", "pip", "show", "openai-whisper"],
        "yt_dlp_version": [str(ROOT / ".venv" / "bin" / "yt-dlp"), "--version"],
        "ffmpeg_version": ["ffmpeg", "-version"],
    }
    return {
        "installation_command_executed": "./.venv/bin/python -m pip install youtube-transcript-api yt-dlp openai-whisper",
        "modules": modules,
        "commands": commands,
        "version_commands": {name: _run_command(command) for name, command in version_commands.items()},
    }


def _remaining_blockers(dependency_report: Dict[str, Any], path_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    blockers = []
    for module, info in dependency_report["modules"].items():
        if not info["available"]:
            blockers.append({"type": "dependency", "name": module, "reason": "module unavailable"})
    for command in ["yt-dlp", "whisper", "ffmpeg"]:
        if dependency_report["commands"].get(command) is None:
            blockers.append({"type": "command", "name": command, "reason": "command unavailable"})
    for result in path_results:
        if result["status"] != "success":
            blockers.append({"type": "runtime_path", "name": result["path_id"], "reason": "runtime validation failed", "attempts": result.get("attempts", [])})
    return blockers


def _certification_report(path_results: List[Dict[str, Any]], blockers: List[Dict[str, Any]], output_dir: Path) -> str:
    lines = ["# Acquisition Ladder Certification Report", "", f"Generated: {_now_iso()}", f"Artifact directory: `{output_dir}`", ""]
    lines.append("## Ladder Results")
    for result in path_results:
        lines.extend([
            f"### {result['path_id']}",
            f"- tier: {result['tier']}",
            f"- status: {result['status']}",
            f"- target: {result['target']}",
            f"- transcript_source: {result.get('transcript_source')}",
            f"- segment_count: {result.get('segment_count')}",
            f"- chunk_count: {result.get('chunk_count')}",
            f"- embedding_count: {result.get('embedding_count')}",
            f"- citation_count: {result.get('citation_count')}",
            f"- equivalent_knowledge_object_shape: {result.get('equivalent_knowledge_object_shape', {}).get('equivalent')}",
            "",
        ])
    lines.extend(["## Remaining Blockers", "```json", json.dumps(blockers, indent=2, sort_keys=True), "```", ""])
    return "\n".join(lines)


def _dependency_installation_report(report: Dict[str, Any]) -> str:
    return _markdown_json("Dependency Installation Report", report)


def _runtime_validation_results(path_results: List[Dict[str, Any]]) -> str:
    lines = ["# Runtime Validation Results", ""]
    for result in path_results:
        lines.extend([
            f"## {result['path_id']}",
            "```json",
            json.dumps(_to_plain(result), indent=2, sort_keys=True),
            "```",
            "",
        ])
    return "\n".join(lines)


def _comparative_report(comparative: Dict[str, Any], path_results: List[Dict[str, Any]]) -> str:
    lines = ["# Comparative Transcript Analysis", "", f"Comparison query: `{comparative['comparison_query']}`", ""]
    headers = ["path", "segments", "words", "duration", "completion vs published", "timestamp delta", "quote overlap", "speaker counts", "retrieval score", "negative speaker results"]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in comparative["rows"]:
        lines.append("| " + " | ".join([
            str(row["path_id"]),
            str(row["segment_count"]),
            str(row["word_count"]),
            str(round(row["duration_seconds"], 3)),
            str(row["completeness_vs_published_duration"]),
            str(row["timestamp_delta_vs_published_top_seconds"]),
            str(row["quote_token_overlap_vs_published_top"]),
            json.dumps(row["speaker_counts"], sort_keys=True),
            str(row["retrieval_score"]),
            str(row["negative_speaker_filter_result_count"]),
        ]) + " |")
    lines.extend(["", "## Raw Comparison", "```json", json.dumps(comparative, indent=2, sort_keys=True), "```"])
    return "\n".join(lines)


def _performance_report(path_results: List[Dict[str, Any]], comparative: Dict[str, Any]) -> str:
    lines = ["# Performance Comparison", ""]
    lines.append("| path | acquisition_seconds | processing_seconds | storage_seconds | retrieval_seconds | total_runtime_seconds |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for result in path_results:
        perf = result.get("performance", {})
        lines.append("| " + " | ".join([
            result["path_id"],
            str(perf.get("acquisition_seconds")),
            str(perf.get("processing_seconds")),
            str(perf.get("storage_seconds")),
            str(perf.get("retrieval_seconds")),
            str(perf.get("total_runtime_seconds")),
        ]) + " |")
    lines.extend(["", "## Raw Performance", "```json", json.dumps({"path_results": path_results, "comparative": comparative}, indent=2, sort_keys=True), "```"])
    return "\n".join(lines)


def _blockers_report(blockers: List[Dict[str, Any]]) -> str:
    return _markdown_json("Remaining External Blockers", blockers)


def _readme(output_dir: Path) -> str:
    return "\n".join([
        "# Acquisition Ladder Certification Artifacts",
        "",
        f"Directory: `{output_dir}`",
        "",
        "Files:",
        "- `ACQUISITION_LADDER_CERTIFICATION_REPORT.md`",
        "- `DEPENDENCY_INSTALLATION_REPORT.md`",
        "- `RUNTIME_VALIDATION_RESULTS.md`",
        "- `COMPARATIVE_TRANSCRIPT_ANALYSIS.md`",
        "- `UPDATED_RUNTIME_INSPECTOR_OUTPUT.json`",
        "- `UPDATED_RUNTIME_INSPECTOR_OUTPUT.md`",
        "- `PERFORMANCE_COMPARISON.md`",
        "- `REMAINING_EXTERNAL_BLOCKERS.md`",
        "- `raw/`, `transcripts/`, `segments/`, `knowledge_objects/`, `search_results/`, `audio/`, `logs/`",
    ])


def _path_summary_rows(path_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{
        "path_id": result["path_id"],
        "status": result["status"],
        "segment_count": result.get("segment_count"),
        "chunk_count": result.get("chunk_count"),
        "embedding_count": result.get("embedding_count"),
        "citation_count": result.get("citation_count"),
        "acquisition_seconds": result.get("performance", {}).get("acquisition_seconds"),
        "retrieval_primary_count": result.get("retrieval", {}).get("primary_count"),
        "retrieval_negative_count": result.get("retrieval", {}).get("negative_count"),
    } for result in path_results]


def _top_result(result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not result or not result.get("retrieval", {}).get("primary_results"):
        return None
    return result["retrieval"]["primary_results"][0]


def _token_overlap(left: str, right: str) -> float:
    left_tokens = {token.lower() for token in left.split()}
    right_tokens = {token.lower() for token in right.split()}
    if not left_tokens or not right_tokens:
        return 0.0
    return round(len(left_tokens & right_tokens) / len(left_tokens | right_tokens), 4)


def _new_output_dir(parent: Path) -> Path:
    parent.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = parent / f"acquisition_ladder_{stamp}"
    if not base.exists():
        return base
    index = 1
    while True:
        candidate = parent / f"acquisition_ladder_{stamp}_{index}"
        if not candidate.exists():
            return candidate
        index += 1


def _which(command: str) -> Optional[str]:
    found = shutil.which(command)
    if found:
        return found
    venv_command = ROOT / ".venv" / "bin" / command
    return str(venv_command) if venv_command.exists() else None


def _run_command(command: List[str]) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
        }
    except Exception as exc:
        return {
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": round(time.perf_counter() - started, 6),
        }


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_to_plain(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(_to_plain(row), sort_keys=True, ensure_ascii=False) + "\n")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _markdown_json(title: str, payload: Any) -> str:
    return f"# {title}\n\n```json\n{json.dumps(_to_plain(payload), indent=2, sort_keys=True, ensure_ascii=False)}\n```\n"


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


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    raise SystemExit(main())
