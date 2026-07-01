"""Registry evolution — recommendations when measured behavior diverges from config."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import now_iso
from .route_registry import SourceRouteEntry


class RegistryEvolutionEngine:
    """Analyze runtime stats and generate route change recommendations."""

    PREFERRED_FAILURE_THRESHOLD = 3
    FALLBACK_SUCCESS_MARGIN = 2

    def analyze(self, entry: SourceRouteEntry) -> List[Dict[str, Any]]:
        recommendations: List[Dict[str, Any]] = []
        preferred = entry.preferred_route
        preferred_stats = entry.route_statistics.get(preferred, {})
        preferred_failures = int(preferred_stats.get("failures", 0))
        preferred_successes = int(preferred_stats.get("successes", 0))

        best_fallback: Optional[str] = None
        best_fallback_successes = 0
        for route in entry.fallbacks:
            stats = entry.route_statistics.get(route, {})
            successes = int(stats.get("successes", 0))
            if successes > best_fallback_successes:
                best_fallback = route
                best_fallback_successes = successes

        if (
            preferred_failures >= self.PREFERRED_FAILURE_THRESHOLD
            and best_fallback
            and best_fallback_successes >= preferred_successes + self.FALLBACK_SUCCESS_MARGIN
        ):
            recommendations.append({
                "type": "promote_fallback",
                "source_id": entry.source_id,
                "current_preferred": preferred,
                "recommended_route": best_fallback,
                "reason": (
                    f"Preferred route `{preferred}` failed {preferred_failures} times; "
                    f"fallback `{best_fallback}` succeeded {best_fallback_successes} times"
                ),
                "confidence_impact": "negative_on_current",
                "created_at": now_iso(),
                "auto_promote": False,
            })

        total_attempts = sum(int(s.get("attempts", 0)) for s in entry.route_statistics.values())
        total_failures = sum(int(s.get("failures", 0)) for s in entry.route_statistics.values())
        if total_attempts >= 5 and total_failures / total_attempts > 0.5:
            recommendations.append({
                "type": "recertify_urgent",
                "source_id": entry.source_id,
                "reason": f"Aggregate failure rate {round(total_failures / total_attempts, 2)} exceeds 50%",
                "created_at": now_iso(),
            })

        if entry.route_confidence is not None and entry.route_confidence < 0.5 and total_attempts >= 3:
            recommendations.append({
                "type": "low_confidence",
                "source_id": entry.source_id,
                "route_confidence": entry.route_confidence,
                "reason": "Computed route confidence below 0.5 threshold",
                "created_at": now_iso(),
            })

        return recommendations

    def apply_recommendations(self, entry: SourceRouteEntry, auto_promote: bool = False) -> List[Dict[str, Any]]:
        fresh = self.analyze(entry)
        entry.recommendations = (entry.recommendations or [])[-50:]
        for rec in fresh:
            if not any(
                existing.get("type") == rec.get("type")
                and existing.get("recommended_route") == rec.get("recommended_route")
                for existing in entry.recommendations
            ):
                entry.recommendations.append(rec)
        if auto_promote:
            for rec in fresh:
                if rec.get("type") == "promote_fallback" and rec.get("auto_promote"):
                    self.promote_route(entry, rec["recommended_route"], rec["reason"])
        return fresh

    def promote_route(self, entry: SourceRouteEntry, new_preferred: str, reason: str) -> None:
        if new_preferred == entry.preferred_route:
            return
        old = entry.preferred_route
        fallbacks = [route for route in entry.fallbacks if route != new_preferred]
        if old not in fallbacks:
            fallbacks.insert(0, old)
        entry.fallbacks = fallbacks
        entry.preferred_route = new_preferred
        entry.reason.append(f"Registry evolution: promoted {new_preferred} over {old} — {reason}")
        entry.certification_history.append({
            "event": "route_promoted",
            "from_route": old,
            "to_route": new_preferred,
            "reason": reason,
            "recorded_at": now_iso(),
        })