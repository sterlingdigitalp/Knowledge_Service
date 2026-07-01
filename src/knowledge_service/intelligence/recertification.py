"""Automatic route re-certification on a scheduled interval."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .models import now_iso
from .route_confidence import RECERTIFICATION_INTERVAL_DAYS, RouteConfidenceEngine
from .route_registry import (
    CERTIFICATION_STATUS_CERTIFIED,
    CERTIFICATION_STATUS_FAILED,
    AcquisitionRouteRegistry,
    SourceRouteEntry,
)
from .registry_evolution import RegistryEvolutionEngine


class RouteRecertificationService:
    """Periodically re-test routes and update registry from measured evidence."""

    HISTORY_FILE = "certification_history.json"

    def __init__(
        self,
        registry: AcquisitionRouteRegistry,
        provider: Any,
        *,
        interval_days: int = RECERTIFICATION_INTERVAL_DAYS,
        timeout_ms: int = 30000,
    ):
        self.registry = registry
        self.provider = provider
        self.interval_days = interval_days
        self.timeout_ms = timeout_ms
        self.confidence_engine = RouteConfidenceEngine()
        self.evolution_engine = RegistryEvolutionEngine()

    def run_if_due(self, sample_urls: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        results = []
        for entry in self.registry.entries():
            if not self.confidence_engine.is_recertification_due(entry, self.interval_days):
                results.append({"source_id": entry.source_id, "status": "skipped", "reason": "not_due"})
                continue
            sample_url = (sample_urls or {}).get(entry.source_id)
            result = self.recertify_source(entry.source_id, sample_url)
            results.append(result)
        self._persist_history(results)
        return {"recertified": len([r for r in results if r.get("status") == "certified"]), "results": results}

    def recertify_source(self, source_id: str, sample_url: Optional[str] = None) -> Dict[str, Any]:
        entry = self.registry.get(source_id)
        if entry is None:
            return {"source_id": source_id, "status": "error", "reason": "unknown_source"}

        benchmark_results: List[Dict[str, Any]] = []
        selected: Optional[str] = None

        if sample_url:
            for route in entry.route_chain():
                started = time.perf_counter()
                options = self.registry.provider_options_for_route(route, {"timeout_ms": self.timeout_ms})
                from ..interfaces.provider import ProviderRequest, ProviderType

                response = self.provider.execute(ProviderRequest(
                    target=sample_url,
                    provider_type=ProviderType.API,
                    options=options,
                ))
                elapsed = round(time.perf_counter() - started, 6)
                success = response.error is None and bool((response.content or "").strip())
                segments = (response.metadata or {}).get("transcript_segments") or []
                metric = {
                    "route": route,
                    "success": success,
                    "runtime_seconds": elapsed,
                    "transcript_length": len(response.content or ""),
                    "segment_count": len(segments),
                    "timestamp_quality": _timestamp_quality(segments),
                    "speaker_quality": _speaker_quality(segments),
                }
                benchmark_results.append(metric)
                self.registry.record_route_attempt(
                    source_id,
                    route,
                    success=success,
                    runtime_seconds=elapsed,
                    transcript_length=len(response.content or ""),
                    error=None if success else (response.error.message if response.error else "empty"),
                )
                if success and selected is None:
                    selected = route
        else:
            selected = entry.preferred_route
            benchmark_results.append({
                "route": selected,
                "success": True,
                "note": "statistics-only recertification (no sample URL)",
            })

        history_record = {
            "source_id": source_id,
            "certified_at": now_iso(),
            "preferred_route": selected or entry.preferred_route,
            "benchmark_results": benchmark_results,
            "previous_preferred": entry.preferred_route,
        }

        if selected and selected != entry.preferred_route:
            recommendation = {
                "type": "recertification_promotion",
                "recommended_route": selected,
                "reason": f"Re-certification measured {selected} as best performing route",
                "created_at": now_iso(),
            }
            entry.recommendations = (entry.recommendations or []) + [recommendation]
            history_record["recommendation"] = recommendation

        entry.certification_history.append(history_record)
        entry.certification.status = CERTIFICATION_STATUS_CERTIFIED if selected or entry.route_statistics else CERTIFICATION_STATUS_FAILED
        entry.certification.certified_at = now_iso()
        entry.certification.preferred_route = selected or entry.preferred_route
        entry.certification.metrics = {"benchmark_results": benchmark_results}
        entry.certification.evidence = [
            f"{m['route']}: success={m.get('success')}, runtime={m.get('runtime_seconds', 'n/a')}s"
            for m in benchmark_results
        ]
        entry.next_recertification_at = self.confidence_engine.next_recertification_date(entry, self.interval_days)

        self.confidence_engine.apply_to_entry(entry)
        self.evolution_engine.apply_recommendations(entry, auto_promote=False)
        self.registry.save()

        return {
            "source_id": source_id,
            "status": entry.certification.status,
            "preferred_route": entry.preferred_route,
            "route_confidence": entry.route_confidence,
            "next_recertification_at": entry.next_recertification_at,
            "benchmark_results": benchmark_results,
        }

    def _persist_history(self, results: List[Dict[str, Any]]) -> None:
        if self.registry.state is None:
            return
        history = self.registry.state.read_json(self.HISTORY_FILE, [])
        history.append({"recorded_at": now_iso(), "results": results})
        history = history[-100:]
        self.registry.state.write_json(self.HISTORY_FILE, history)


def _timestamp_quality(segments: List[Dict[str, Any]]) -> float:
    if not segments:
        return 0.0
    with_timestamps = sum(1 for s in segments if s.get("start_seconds") is not None)
    return round(with_timestamps / len(segments), 4)


def _speaker_quality(segments: List[Dict[str, Any]]) -> float:
    if not segments:
        return 0.0
    known = sum(1 for s in segments if s.get("speaker") and s.get("speaker") != "unknown")
    return round(known / len(segments), 4)