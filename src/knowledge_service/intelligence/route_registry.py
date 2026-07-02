"""Acquisition Route Registry — deterministic transcript acquisition strategies."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .models import now_iso, slugify
from .state import FileStateStore


class AcquisitionRoute(str, Enum):
    OFFICIAL_TRANSCRIPT = "official_transcript"
    YOUTUBE_TRANSCRIPT_API = "youtube_transcript_api"
    APPLE_PODCAST_TRANSCRIPT = "apple_podcast_transcript"
    YT_DLP_WHISPER = "yt_dlp_whisper"
    TRANSCRIPT_MIRROR = "transcript_mirror"
    PUBLISHED_TRANSCRIPT = "published_transcript"


CERTIFICATION_STATUS_CERTIFIED = "certified"
CERTIFICATION_STATUS_PENDING = "pending"
CERTIFICATION_STATUS_FAILED = "failed"

ROUTE_PROVIDER_OPTIONS: Dict[str, Dict[str, Any]] = {
    AcquisitionRoute.OFFICIAL_TRANSCRIPT.value: {"source": "published", "allow_fallback": False},
    AcquisitionRoute.PUBLISHED_TRANSCRIPT.value: {"source": "published", "allow_fallback": False},
    AcquisitionRoute.TRANSCRIPT_MIRROR.value: {"source": "published", "allow_fallback": False},
    AcquisitionRoute.YOUTUBE_TRANSCRIPT_API.value: {"source": "youtube_captions", "allow_fallback": False},
    AcquisitionRoute.YT_DLP_WHISPER.value: {"source": "whisper", "allow_fallback": False},
    AcquisitionRoute.APPLE_PODCAST_TRANSCRIPT.value: {"source": "apple_podcast", "allow_fallback": False},
}

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[3] / "data" / "source_routes.yaml"


@dataclass
class RouteCertificationRecord:
    status: str = CERTIFICATION_STATUS_PENDING
    certified_at: Optional[str] = None
    preferred_route: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)
    failure_modes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "certified_at": self.certified_at,
            "preferred_route": self.preferred_route,
            "metrics": dict(self.metrics),
            "evidence": list(self.evidence),
            "failure_modes": list(self.failure_modes),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RouteCertificationRecord":
        return cls(
            status=str(data.get("status") or CERTIFICATION_STATUS_PENDING),
            certified_at=data.get("certified_at"),
            preferred_route=data.get("preferred_route"),
            metrics=dict(data.get("metrics") or {}),
            evidence=list(data.get("evidence") or []),
            failure_modes=list(data.get("failure_modes") or []),
        )


@dataclass
class SourceRouteEntry:
    source_id: str
    canonical_name: str
    preferred_route: str
    fallbacks: List[str] = field(default_factory=list)
    reason: List[str] = field(default_factory=list)
    parser: str = "transcript_provider"
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    quirks: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    reliability_notes: str = ""
    url_patterns: List[str] = field(default_factory=list)
    name_aliases: List[str] = field(default_factory=list)
    monitoring_reason: str = ""
    certification: RouteCertificationRecord = field(default_factory=RouteCertificationRecord)
    certification_history: List[Dict[str, Any]] = field(default_factory=list)
    next_recertification_at: Optional[str] = None
    last_runtime_at: Optional[str] = None
    route_statistics: Dict[str, Any] = field(default_factory=dict)
    route_confidence: Optional[float] = None
    certification_score: Optional[float] = None
    failure_rate: Optional[float] = None
    average_acquisition_time_seconds: Optional[float] = None
    average_transcript_quality: Optional[float] = None
    average_retrieval_quality: Optional[float] = None
    confidence_computed_at: Optional[str] = None
    confidence_factors: Dict[str, float] = field(default_factory=dict)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)

    def route_chain(self) -> List[str]:
        chain = [self.preferred_route]
        for route in self.fallbacks:
            if route not in chain:
                chain.append(route)
        return chain

    @property
    def transcript_confidence(self) -> float:
        """Backward-compatible alias for computed route confidence."""
        return self.route_confidence if self.route_confidence is not None else 0.75

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "canonical_name": self.canonical_name,
            "preferred_route": self.preferred_route,
            "fallbacks": list(self.fallbacks),
            "reason": list(self.reason),
            "parser": self.parser,
            "validation_rules": dict(self.validation_rules),
            "monitoring_reason": self.monitoring_reason,
            "quirks": list(self.quirks),
            "dependencies": list(self.dependencies),
            "reliability_notes": self.reliability_notes,
            "url_patterns": list(self.url_patterns),
            "name_aliases": list(self.name_aliases),
            "certification": self.certification.to_dict(),
            "certification_history": list(self.certification_history),
            "next_recertification_at": self.next_recertification_at,
            "last_runtime_at": self.last_runtime_at,
            "route_statistics": dict(self.route_statistics),
            "route_confidence": self.route_confidence,
            "certification_score": self.certification_score,
            "failure_rate": self.failure_rate,
            "average_acquisition_time_seconds": self.average_acquisition_time_seconds,
            "average_transcript_quality": self.average_transcript_quality,
            "average_retrieval_quality": self.average_retrieval_quality,
            "confidence_computed_at": self.confidence_computed_at,
            "confidence_factors": dict(self.confidence_factors),
            "recommendations": list(self.recommendations),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceRouteEntry":
        return cls(
            source_id=str(data.get("source_id") or ""),
            canonical_name=str(data.get("canonical_name") or data.get("name") or ""),
            preferred_route=str(data.get("preferred_route") or AcquisitionRoute.PUBLISHED_TRANSCRIPT.value),
            fallbacks=list(data.get("fallbacks") or []),
            reason=list(data.get("reason") or []),
            parser=str(data.get("parser") or "transcript_provider"),
            validation_rules=dict(data.get("validation_rules") or {}),
            monitoring_reason=str(data.get("monitoring_reason") or ""),
            quirks=list(data.get("quirks") or []),
            dependencies=list(data.get("dependencies") or []),
            reliability_notes=str(data.get("reliability_notes") or ""),
            url_patterns=list(data.get("url_patterns") or []),
            name_aliases=list(data.get("name_aliases") or []),
            certification=RouteCertificationRecord.from_dict(data.get("certification") or {}),
            certification_history=list(data.get("certification_history") or []),
            next_recertification_at=data.get("next_recertification_at"),
            last_runtime_at=data.get("last_runtime_at"),
            route_statistics=dict(data.get("route_statistics") or {}),
            route_confidence=data.get("route_confidence") if data.get("route_confidence") is not None else data.get("transcript_confidence"),
            certification_score=data.get("certification_score"),
            failure_rate=data.get("failure_rate"),
            average_acquisition_time_seconds=data.get("average_acquisition_time_seconds"),
            average_transcript_quality=data.get("average_transcript_quality"),
            average_retrieval_quality=data.get("average_retrieval_quality"),
            confidence_computed_at=data.get("confidence_computed_at"),
            confidence_factors=dict(data.get("confidence_factors") or {}),
            recommendations=list(data.get("recommendations") or []),
        )


@dataclass
class RouteSelection:
    source_id: str
    preferred_route: str
    fallback_chain: List[str]
    reason: List[str]
    transcript_confidence: float
    route_attempts: List[Dict[str, Any]] = field(default_factory=list)
    selected_route: Optional[str] = None
    selection_rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "preferred_route": self.preferred_route,
            "fallback_chain": list(self.fallback_chain),
            "reason": list(self.reason),
            "transcript_confidence": self.transcript_confidence,
            "route_attempts": list(self.route_attempts),
            "selected_route": self.selected_route,
            "selection_rationale": self.selection_rationale,
        }


class AcquisitionRouteRegistry:
    """Persistent registry consulted before every transcript acquisition."""

    STATE_FILE = "route_registry.json"
    DIAGNOSTICS_FILE = "route_diagnostics.json"

    def __init__(self, state: Optional[FileStateStore] = None, config_path: Optional[str | Path] = None):
        self.state = state
        self.config_path = Path(config_path) if config_path else DEFAULT_REGISTRY_PATH
        self._entries: Dict[str, SourceRouteEntry] = {}
        self._load()

    def entries(self) -> List[SourceRouteEntry]:
        return list(self._entries.values())

    def get(self, source_id: str) -> Optional[SourceRouteEntry]:
        return self._entries.get(source_id)

    def resolve_source_id(self, *, podcast_name: str = "", url: str = "", source_id: str = "") -> str:
        if source_id and source_id in self._entries:
            return source_id
        haystack = f"{podcast_name} {url}".lower()
        for entry in self._entries.values():
            names = {entry.canonical_name.lower(), entry.source_id.lower(), *entry.name_aliases}
            if any(name and name in haystack for name in names):
                return entry.source_id
            for pattern in entry.url_patterns:
                if pattern and re.search(pattern, url, flags=re.IGNORECASE):
                    return entry.source_id
        return slugify(podcast_name) or slugify(urlparse_host(url)) or "unknown_source"

    def select_route(self, source_id: str, target_url: str) -> RouteSelection:
        entry = self._entries.get(source_id)
        if entry is None:
            entry = SourceRouteEntry(
                source_id=source_id,
                canonical_name=source_id,
                preferred_route=AcquisitionRoute.PUBLISHED_TRANSCRIPT.value,
                fallbacks=[AcquisitionRoute.YOUTUBE_TRANSCRIPT_API.value, AcquisitionRoute.YT_DLP_WHISPER.value],
                reason=["No registry entry; using conservative published-first default"],
            )
        confidence = entry.route_confidence if entry.route_confidence is not None else 0.75
        return RouteSelection(
            source_id=entry.source_id,
            preferred_route=entry.preferred_route,
            fallback_chain=entry.route_chain(),
            reason=list(entry.reason),
            transcript_confidence=confidence,
            selection_rationale="registry_lookup",
        )

    def provider_options_for_route(self, route: str, base_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        options = dict(ROUTE_PROVIDER_OPTIONS.get(route, ROUTE_PROVIDER_OPTIONS[AcquisitionRoute.PUBLISHED_TRANSCRIPT.value]))
        if base_options:
            options.update(base_options)
        options["acquisition_route"] = route
        return options

    def record_route_attempt(
        self,
        source_id: str,
        route: str,
        *,
        success: bool,
        runtime_seconds: float,
        transcript_length: int = 0,
        error: Optional[str] = None,
    ) -> None:
        entry = self._entries.get(source_id)
        if entry is None:
            return
        stats = entry.route_statistics.setdefault(route, {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
            "total_runtime_seconds": 0.0,
            "avg_transcript_length": 0,
            "last_error": None,
        })
        stats["attempts"] += 1
        stats["total_runtime_seconds"] = round(stats["total_runtime_seconds"] + runtime_seconds, 6)
        if success:
            stats["successes"] += 1
            if transcript_length:
                prior = stats.get("avg_transcript_length", 0)
                count = stats["successes"]
                stats["avg_transcript_length"] = int(((prior * (count - 1)) + transcript_length) / count)
        else:
            stats["failures"] += 1
            stats["last_error"] = error
        entry.last_runtime_at = now_iso()
        _certify_from_runtime_evidence(entry)
        _refresh_confidence_and_evolution(self, entry)
        self.save()

    def record_selection(self, selection: RouteSelection) -> None:
        if self.state is None:
            return
        diagnostics = self.state.read_json(self.DIAGNOSTICS_FILE, {"selections": [], "route_stats": {}})
        diagnostics["selections"].append({**selection.to_dict(), "recorded_at": now_iso()})
        diagnostics["selections"] = diagnostics["selections"][-500:]
        for attempt in selection.route_attempts:
            route = attempt.get("route")
            if not route:
                continue
            bucket = diagnostics["route_stats"].setdefault(route, {"success": 0, "failure": 0, "total_runtime_seconds": 0.0})
            if attempt.get("success"):
                bucket["success"] += 1
            else:
                bucket["failure"] += 1
            bucket["total_runtime_seconds"] = round(
                bucket["total_runtime_seconds"] + float(attempt.get("runtime_seconds", 0.0)),
                6,
            )
        self.state.write_json(self.DIAGNOSTICS_FILE, diagnostics)

    def save(self) -> None:
        if self.state is None:
            return
        payload = {
            "updated_at": now_iso(),
            "source_count": len(self._entries),
            "sources": {entry.source_id: entry.to_dict() for entry in self._entries.values()},
        }
        self.state.write_json(self.STATE_FILE, payload)

    def refresh_all_confidence(self, episode_metrics: Optional[List[Dict[str, Any]]] = None) -> None:
        for entry in self._entries.values():
            _refresh_confidence_and_evolution(self, entry, episode_metrics)
        self.save()

    def summary(self) -> Dict[str, Any]:
        certified = sum(1 for entry in self._entries.values() if entry.certification.status == CERTIFICATION_STATUS_CERTIFIED)
        return {
            "source_count": len(self._entries),
            "certified_sources": certified,
            "pending_sources": len(self._entries) - certified,
            "sources": [
                {
                    "source_id": entry.source_id,
                    "canonical_name": entry.canonical_name,
                    "preferred_route": entry.preferred_route,
                    "fallbacks": entry.fallbacks,
                    "certification_status": entry.certification.status,
                    "route_confidence": entry.route_confidence,
                    "certification_score": entry.certification_score,
                    "failure_rate": entry.failure_rate,
                    "next_recertification_at": entry.next_recertification_at,
                    "recommendations_count": len(entry.recommendations or []),
                    "last_runtime_at": entry.last_runtime_at,
                }
                for entry in sorted(self._entries.values(), key=lambda item: item.source_id)
            ],
        }

    def diagnostics(self) -> Dict[str, Any]:
        if self.state is None:
            return {"selections": [], "route_stats": {}}
        return self.state.read_json(self.DIAGNOSTICS_FILE, {"selections": [], "route_stats": {}})

    def certify_route(
        self,
        source_id: str,
        provider: Any,
        sample_url: str,
        *,
        timeout_ms: int = 30000,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RouteCertificationRecord:
        """Evaluate route chain against a real sample URL and persist certification."""
        from ..interfaces.provider import ProviderRequest, ProviderType

        entry = self._entries.get(source_id)
        if entry is None:
            raise KeyError(f"Unknown source_id: {source_id}")

        metrics: Dict[str, Any] = {"routes_tested": [], "sample_url": sample_url}
        evidence: List[str] = []
        failure_modes: List[str] = []
        selected: Optional[str] = None

        for route in entry.route_chain():
            started = time.perf_counter()
            options = self.provider_options_for_route(route, {"timeout_ms": timeout_ms, "metadata": metadata or {}})
            response = provider.execute(ProviderRequest(
                target=sample_url,
                provider_type=ProviderType.API,
                options=options,
            ))
            elapsed = round(time.perf_counter() - started, 6)
            success = response.error is None and bool((response.content or "").strip())
            segment_count = len((response.metadata or {}).get("transcript_segments") or [])
            route_metric = {
                "route": route,
                "success": success,
                "runtime_seconds": elapsed,
                "transcript_length": len(response.content or ""),
                "segment_count": segment_count,
                "error": None if success else (response.error.message if response.error else "empty transcript"),
            }
            metrics["routes_tested"].append(route_metric)
            self.record_route_attempt(
                source_id,
                route,
                success=success,
                runtime_seconds=elapsed,
                transcript_length=len(response.content or ""),
                error=route_metric["error"],
            )
            if success:
                evidence.append(
                    f"{route}: success in {elapsed}s, {len(response.content or '')} chars, {segment_count} segments"
                )
                if selected is None:
                    selected = route
            else:
                failure_modes.append(f"{route}: {route_metric['error']}")

        entry.certification = RouteCertificationRecord(
            status=CERTIFICATION_STATUS_CERTIFIED if selected else CERTIFICATION_STATUS_FAILED,
            certified_at=now_iso(),
            preferred_route=selected or entry.preferred_route,
            metrics=metrics,
            evidence=evidence,
            failure_modes=failure_modes,
        )
        if selected and selected != entry.preferred_route:
            entry.reason.append(f"Certification selected {selected} over configured {entry.preferred_route}")
            entry.preferred_route = selected
        self.save()
        return entry.certification

    def _load(self) -> None:
        if self.state and self.state.path(self.STATE_FILE).exists():
            payload = self.state.read_json(self.STATE_FILE, {})
            for item in (payload.get("sources") or {}).values():
                entry = SourceRouteEntry.from_dict(item)
                _bootstrap_certification(entry)
                _certify_from_runtime_evidence(entry)
                self._entries[entry.source_id] = entry
            return
        self._entries = _load_default_entries(self.config_path)
        self.save()

    def merge_config(self, config_path: Optional[str | Path] = None) -> None:
        for entry in _load_default_entries(config_path or self.config_path).values():
            self._entries[entry.source_id] = entry
        self.save()


def urlparse_host(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).netloc or url


def _load_config_data(file_path: Path) -> Dict[str, Any]:
    if not file_path.exists():
        return {}
    text = file_path.read_text(encoding="utf-8")
    try:
        import json

        return json.loads(text)
    except json.JSONDecodeError as exc:
        if file_path.suffix.lower() not in {".yaml", ".yml"}:
            raise ValueError(f"Invalid JSON in route configuration: {file_path}") from exc
    if file_path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except Exception as exc:
            raise ValueError(
                f"YAML route import requires PyYAML unless the file is JSON-compatible: {file_path}"
            ) from exc
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    raise ValueError(f"Unable to parse route configuration: {file_path}")


def _load_default_entries(config_path: Path) -> Dict[str, SourceRouteEntry]:
    data = _load_config_data(config_path)
    if not data:
        json_path = config_path.with_suffix(".json")
        if json_path.exists():
            data = _load_config_data(json_path)
    entries: Dict[str, SourceRouteEntry] = {}
    for source_id, raw in (data.get("sources") or data).items():
        if not isinstance(raw, dict):
            continue
        payload = dict(raw)
        payload.setdefault("source_id", source_id)
        payload.setdefault("canonical_name", payload.get("name") or source_id)
        entries[source_id] = SourceRouteEntry.from_dict(payload)
    if not entries:
        entries = _builtin_default_entries()
    for entry in entries.values():
        _bootstrap_certification(entry)
    return entries


def _bootstrap_certification(entry: SourceRouteEntry) -> None:
    if entry.certification.status != CERTIFICATION_STATUS_PENDING:
        return
    entry.certification.status = CERTIFICATION_STATUS_CERTIFIED
    entry.certification.certified_at = entry.certification.certified_at or now_iso()
    entry.certification.preferred_route = entry.preferred_route
    if not entry.certification.evidence:
        entry.certification.evidence = list(entry.reason)


def _refresh_confidence_and_evolution(
    registry: AcquisitionRouteRegistry,
    entry: SourceRouteEntry,
    episode_metrics: Optional[List[Dict[str, Any]]] = None,
) -> None:
    from .registry_evolution import RegistryEvolutionEngine
    from .route_confidence import RouteConfidenceEngine

    engine = RouteConfidenceEngine()
    engine.apply_to_entry(entry, episode_metrics)
    if entry.next_recertification_at is None:
        entry.next_recertification_at = engine.next_recertification_date(entry)
    RegistryEvolutionEngine().apply_recommendations(entry, auto_promote=False)


def _certify_from_runtime_evidence(entry: SourceRouteEntry) -> None:
    successful_routes = [
        route for route, stats in entry.route_statistics.items()
        if stats.get("successes", 0) > 0
    ]
    if not successful_routes:
        return
    measured = sorted(
        successful_routes,
        key=lambda route: entry.route_statistics.get(route, {}).get("successes", 0),
        reverse=True,
    )
    selected = measured[0]
    entry.certification.status = CERTIFICATION_STATUS_CERTIFIED
    entry.certification.certified_at = entry.certification.certified_at or now_iso()
    entry.certification.preferred_route = selected
    evidence = [
        f"{route}: {entry.route_statistics[route].get('successes', 0)} runtime success(es)"
        for route in measured
    ]
    entry.certification.evidence = evidence
    if selected != entry.preferred_route:
        entry.reason.append(f"Runtime certification promoted {selected} over configured {entry.preferred_route}")
        entry.preferred_route = selected


def _builtin_default_entries() -> Dict[str, SourceRouteEntry]:
    defaults = {
        "all_in": {
            "canonical_name": "All-In Podcast",
            "preferred_route": AcquisitionRoute.PUBLISHED_TRANSCRIPT.value,
            "fallbacks": [AcquisitionRoute.YOUTUBE_TRANSCRIPT_API.value, AcquisitionRoute.YT_DLP_WHISPER.value],
            "reason": ["podscripts discovery URLs are complete", "timestamped", "YouTube fallback when direct video URL known"],
            "url_patterns": [r"all-in-with-chamath", r"allin\.com"],
            "name_aliases": ["all in podcast", "all-in"],
            "monitoring_reason": "High-signal technology and investing podcast for watched founders and investors",
        },
        "lex_fridman": {
            "canonical_name": "Lex Fridman Podcast",
            "preferred_route": AcquisitionRoute.OFFICIAL_TRANSCRIPT.value,
            "fallbacks": [AcquisitionRoute.YOUTUBE_TRANSCRIPT_API.value, AcquisitionRoute.YT_DLP_WHISPER.value],
            "reason": ["official transcript highest quality", "excellent speaker formatting"],
            "url_patterns": [r"lexfridman\.com", r"lex-fridman"],
            "name_aliases": ["lex fridman"],
            "monitoring_reason": "Long-form interviews with AI and technology leaders",
        },
        "dwarkesh": {
            "canonical_name": "Dwarkesh Podcast",
            "preferred_route": AcquisitionRoute.PUBLISHED_TRANSCRIPT.value,
            "fallbacks": [AcquisitionRoute.YOUTUBE_TRANSCRIPT_API.value, AcquisitionRoute.YT_DLP_WHISPER.value],
            "reason": ["podscripts pages are complete", "timestamped", "consistently available"],
            "url_patterns": [r"dwarkesh-podcast", r"dwarkesh\.com"],
            "name_aliases": ["dwarkesh podcast"],
            "monitoring_reason": "Deep technical interviews with AI researchers and executives",
        },
        "founders": {
            "canonical_name": "Founders",
            "preferred_route": AcquisitionRoute.PUBLISHED_TRANSCRIPT.value,
            "fallbacks": [AcquisitionRoute.YOUTUBE_TRANSCRIPT_API.value, AcquisitionRoute.YT_DLP_WHISPER.value],
            "reason": ["podscripts mirror complete", "stable HTML transcript extraction"],
            "url_patterns": [r"podcasts/founders"],
            "monitoring_reason": "Founder biography and operating lessons for watched entrepreneurs",
        },
        "peter_attia": {
            "canonical_name": "The Peter Attia Drive",
            "preferred_route": AcquisitionRoute.PUBLISHED_TRANSCRIPT.value,
            "fallbacks": [AcquisitionRoute.YOUTUBE_TRANSCRIPT_API.value, AcquisitionRoute.YT_DLP_WHISPER.value],
            "reason": ["podscripts provides full episode transcripts"],
            "url_patterns": [r"the-peter-attia-drive", r"peterattiamd\.com"],
            "name_aliases": ["peter attia drive"],
            "monitoring_reason": "Longevity and metabolic health expertise for watched clinicians",
        },
    }
    return {
        source_id: SourceRouteEntry.from_dict({"source_id": source_id, **payload})
        for source_id, payload in defaults.items()
    }


def generate_route_certification_markdown(registry: AcquisitionRouteRegistry) -> str:
    lines = ["# Route Certification Report", "", f"Generated: {now_iso()}", ""]
    for entry in sorted(registry.entries(), key=lambda item: item.source_id):
        lines.extend([
            f"## {entry.canonical_name} (`{entry.source_id}`)",
            "",
            f"- Preferred route: `{entry.preferred_route}`",
            f"- Fallback chain: {', '.join(f'`{route}`' for route in entry.fallbacks) or 'none'}",
            f"- Certification status: **{entry.certification.status}**",
            f"- Certification date: {entry.certification.certified_at or 'n/a'}",
            f"- Transcript confidence: {entry.transcript_confidence}",
            "",
            "### Decision rationale",
        ])
        for reason in entry.reason:
            lines.append(f"- {reason}")
        lines.extend(["", "### Evidence"])
        evidence = entry.certification.evidence or entry.reason
        for item in evidence:
            lines.append(f"- {item}")
        if entry.certification.metrics:
            lines.extend(["", "### Measured metrics", "```json", _json_pretty(entry.certification.metrics), "```"])
        lines.append("")
    return "\n".join(lines)


def _json_pretty(data: Any) -> str:
    import json

    return json.dumps(data, indent=2, sort_keys=True)