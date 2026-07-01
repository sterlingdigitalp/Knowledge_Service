"""Route benchmarking — compare acquisition routes with measured evidence."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .models import now_iso
from .route_registry import AcquisitionRoute, AcquisitionRouteRegistry
from .recertification import _speaker_quality, _timestamp_quality


BENCHMARK_ROUTES = [
    AcquisitionRoute.OFFICIAL_TRANSCRIPT.value,
    AcquisitionRoute.YOUTUBE_TRANSCRIPT_API.value,
    AcquisitionRoute.APPLE_PODCAST_TRANSCRIPT.value,
    AcquisitionRoute.YT_DLP_WHISPER.value,
    AcquisitionRoute.TRANSCRIPT_MIRROR.value,
    AcquisitionRoute.PUBLISHED_TRANSCRIPT.value,
]


class RouteBenchmarkService:
    def __init__(self, registry: AcquisitionRouteRegistry, provider: Any, *, timeout_ms: int = 30000):
        self.registry = registry
        self.provider = provider
        self.timeout_ms = timeout_ms

    def benchmark_source(self, source_id: str, sample_url: str) -> Dict[str, Any]:
        from ..interfaces.provider import ProviderRequest, ProviderType

        entry = self.registry.get(source_id)
        if entry is None:
            raise KeyError(source_id)

        results: List[Dict[str, Any]] = []
        for route in BENCHMARK_ROUTES:
            started = time.perf_counter()
            options = self.registry.provider_options_for_route(route, {"timeout_ms": self.timeout_ms})
            response = self.provider.execute(ProviderRequest(
                target=sample_url,
                provider_type=ProviderType.API,
                options=options,
            ))
            elapsed = round(time.perf_counter() - started, 6)
            segments = (response.metadata or {}).get("transcript_segments") or []
            success = response.error is None and bool((response.content or "").strip())
            results.append({
                "route": route,
                "success": success,
                "runtime_seconds": elapsed,
                "transcript_length": len(response.content or ""),
                "segment_count": len(segments),
                "timestamp_quality": _timestamp_quality(segments),
                "speaker_quality": _speaker_quality(segments),
                "retrieval_quality": (response.metadata or {}).get("transcript_confidence"),
                "error": None if success else (response.error.message if response.error else "empty"),
                "dependency": _route_dependency(route),
                "maintenance_burden": _maintenance_burden(route),
            })

        ranked = sorted(
            [r for r in results if r["success"]],
            key=lambda r: (
                r.get("speaker_quality", 0),
                r.get("timestamp_quality", 0),
                r.get("transcript_length", 0),
                -r.get("runtime_seconds", 999),
            ),
            reverse=True,
        )
        recommended = ranked[0]["route"] if ranked else entry.preferred_route

        report = {
            "source_id": source_id,
            "sample_url": sample_url,
            "benchmarked_at": now_iso(),
            "routes_tested": results,
            "recommended_route": recommended,
            "current_preferred": entry.preferred_route,
            "alignment": recommended == entry.preferred_route,
        }
        entry.certification_history.append({"event": "benchmark", **report})
        self.registry.save()
        return report

    def benchmark_all(self, sample_urls: Dict[str, str]) -> List[Dict[str, Any]]:
        return [self.benchmark_source(sid, url) for sid, url in sample_urls.items() if self.registry.get(sid)]


def _route_dependency(route: str) -> str:
    return {
        "official_transcript": "httpx",
        "published_transcript": "httpx",
        "transcript_mirror": "httpx",
        "youtube_transcript_api": "youtube_transcript_api",
        "yt_dlp_whisper": "yt-dlp, whisper, ffmpeg",
        "apple_podcast_transcript": "apple_podcast_api",
    }.get(route, "unknown")


def _maintenance_burden(route: str) -> str:
    return {
        "official_transcript": "low",
        "published_transcript": "low",
        "transcript_mirror": "medium",
        "youtube_transcript_api": "medium",
        "yt_dlp_whisper": "high",
        "apple_podcast_transcript": "medium",
    }.get(route, "unknown")


def generate_route_benchmarks_markdown(reports: List[Dict[str, Any]]) -> str:
    lines = ["# Route Benchmarks", "", f"Generated: {now_iso()}", ""]
    for report in reports:
        lines.extend([
            f"## {report['source_id']}",
            f"- Sample: `{report['sample_url']}`",
            f"- Recommended: `{report['recommended_route']}`",
            f"- Current preferred: `{report['current_preferred']}`",
            f"- Aligned: {report['alignment']}",
            "",
            "| Route | Success | Runtime | Length | Timestamps | Speakers |",
            "|-------|---------|---------|--------|------------|----------|",
        ])
        for row in report["routes_tested"]:
            lines.append(
                f"| {row['route']} | {row['success']} | {row.get('runtime_seconds', 'n/a')}s "
                f"| {row.get('transcript_length', 0)} | {row.get('timestamp_quality', 0)} "
                f"| {row.get('speaker_quality', 0)} |"
            )
        lines.append("")
    return "\n".join(lines)