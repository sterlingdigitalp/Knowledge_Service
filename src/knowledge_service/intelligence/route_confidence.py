"""Route Confidence Engine — compute confidence from measured runtime behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .models import now_iso
from .route_registry import SourceRouteEntry


RECERTIFICATION_INTERVAL_DAYS = 30


@dataclass
class RouteConfidenceSnapshot:
    source_id: str
    preferred_route: str
    route_confidence: float
    certification_score: float
    failure_rate: float
    average_acquisition_time_seconds: float
    average_transcript_quality: float
    average_retrieval_quality: float
    computed_at: str = field(default_factory=now_iso)
    factors: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "preferred_route": self.preferred_route,
            "route_confidence": round(self.route_confidence, 4),
            "certification_score": round(self.certification_score, 4),
            "failure_rate": round(self.failure_rate, 4),
            "average_acquisition_time_seconds": round(self.average_acquisition_time_seconds, 4),
            "average_transcript_quality": round(self.average_transcript_quality, 4),
            "average_retrieval_quality": round(self.average_retrieval_quality, 4),
            "computed_at": self.computed_at,
            "factors": dict(self.factors),
        }


class RouteConfidenceEngine:
    """Derive route confidence from runtime statistics — never hardcode."""

    ROUTE_BASE_QUALITY = {
        "official_transcript": 0.95,
        "published_transcript": 0.9,
        "youtube_transcript_api": 0.85,
        "transcript_mirror": 0.8,
        "yt_dlp_whisper": 0.65,
        "apple_podcast_transcript": 0.75,
    }

    def compute(self, entry: SourceRouteEntry, episode_metrics: Optional[List[Dict[str, Any]]] = None) -> RouteConfidenceSnapshot:
        preferred = entry.preferred_route
        stats = entry.route_statistics.get(preferred, {})
        attempts = max(int(stats.get("attempts", 0)), 0)
        successes = int(stats.get("successes", 0))
        failures = int(stats.get("failures", 0))

        success_rate = successes / attempts if attempts else 0.0
        failure_rate = failures / attempts if attempts else 0.0
        avg_runtime = (
            float(stats.get("total_runtime_seconds", 0.0)) / attempts if attempts else 0.0
        )
        avg_length = int(stats.get("avg_transcript_length", 0))
        min_chars = int(entry.validation_rules.get("min_transcript_chars", 500))
        completeness = min(1.0, avg_length / max(min_chars, 1)) if avg_length else 0.0
        speed_score = 1.0 / (1.0 + avg_runtime) if avg_runtime else 0.5

        retrieval_scores = []
        if episode_metrics:
            for item in episode_metrics:
                if item.get("source_id") == entry.source_id and item.get("acquisition_route") == preferred:
                    if item.get("route_confidence") is not None:
                        retrieval_scores.append(float(item["route_confidence"]))
        retrieval_quality = sum(retrieval_scores) / len(retrieval_scores) if retrieval_scores else self.ROUTE_BASE_QUALITY.get(preferred, 0.75)

        base_quality = self.ROUTE_BASE_QUALITY.get(preferred, 0.75)
        transcript_quality = (0.6 * base_quality) + (0.4 * completeness) if attempts else base_quality * 0.5

        if attempts == 0:
            route_confidence = base_quality * 0.5
            certification_score = 0.5
        else:
            route_confidence = (
                0.35 * success_rate
                + 0.20 * (1.0 - failure_rate)
                + 0.20 * completeness
                + 0.10 * speed_score
                + 0.15 * retrieval_quality
            )
            certification_score = (
                0.40 * success_rate
                + 0.30 * transcript_quality
                + 0.20 * retrieval_quality
                + 0.10 * speed_score
            )

        return RouteConfidenceSnapshot(
            source_id=entry.source_id,
            preferred_route=preferred,
            route_confidence=min(1.0, max(0.0, route_confidence)),
            certification_score=min(1.0, max(0.0, certification_score)),
            failure_rate=failure_rate,
            average_acquisition_time_seconds=avg_runtime,
            average_transcript_quality=transcript_quality,
            average_retrieval_quality=retrieval_quality,
            factors={
                "success_rate": success_rate,
                "failure_rate": failure_rate,
                "completeness": completeness,
                "speed_score": speed_score,
                "attempts": float(attempts),
            },
        )

    def apply_to_entry(self, entry: SourceRouteEntry, episode_metrics: Optional[List[Dict[str, Any]]] = None) -> RouteConfidenceSnapshot:
        snapshot = self.compute(entry, episode_metrics)
        entry.route_confidence = snapshot.route_confidence
        entry.certification_score = snapshot.certification_score
        entry.failure_rate = snapshot.failure_rate
        entry.average_acquisition_time_seconds = snapshot.average_acquisition_time_seconds
        entry.average_transcript_quality = snapshot.average_transcript_quality
        entry.average_retrieval_quality = snapshot.average_retrieval_quality
        entry.confidence_computed_at = snapshot.computed_at
        entry.confidence_factors = snapshot.factors
        return snapshot

    def next_recertification_date(self, entry: SourceRouteEntry, interval_days: int = RECERTIFICATION_INTERVAL_DAYS) -> str:
        anchor = entry.certification.certified_at or entry.last_runtime_at or now_iso()
        try:
            dt = datetime.strptime(anchor, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            dt = datetime.now(timezone.utc)
        return (dt + timedelta(days=interval_days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def is_recertification_due(self, entry: SourceRouteEntry, interval_days: int = RECERTIFICATION_INTERVAL_DAYS) -> bool:
        if not entry.certification.certified_at and not entry.next_recertification_at:
            return True
        due_at = entry.next_recertification_at or self.next_recertification_date(entry, interval_days)
        try:
            due = datetime.strptime(due_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            return True
        return datetime.now(timezone.utc) >= due