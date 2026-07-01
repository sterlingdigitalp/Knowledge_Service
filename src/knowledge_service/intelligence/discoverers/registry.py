"""Registry of information event discoverers."""

from __future__ import annotations

from typing import Dict, List, Optional

from ..discovery import DiscoveryResult
from ..models import IntelligenceProfile, now_iso, stable_id
from ..state import FileStateStore
from .base import DiscoveryContext, InformationEventDiscoverer
from .conference import ConferenceDiscoverer
from .earnings import EarningsCallDiscoverer
from .interview import InterviewDiscoverer
from .livestream import LivestreamDiscoverer
from .podcast import PodcastDiscoverer
from .presentation import PresentationDiscoverer


class DiscovererRegistry:
    """Coordinate discoverers without the collector knowing venue origins."""

    def __init__(self, discoverers: Optional[List[InformationEventDiscoverer]] = None):
        self._discoverers: Dict[str, InformationEventDiscoverer] = {}
        for discoverer in discoverers or self.default_discoverers():
            self._discoverers[discoverer.discoverer_id] = discoverer

    @staticmethod
    def default_discoverers() -> List[InformationEventDiscoverer]:
        return [
            PodcastDiscoverer(),
            ConferenceDiscoverer(),
            InterviewDiscoverer(),
            LivestreamDiscoverer(),
            EarningsCallDiscoverer(),
            PresentationDiscoverer(),
        ]

    def register(self, discoverer: InformationEventDiscoverer) -> None:
        self._discoverers[discoverer.discoverer_id] = discoverer

    def discover(self, profiles: List[IntelligenceProfile], context: DiscoveryContext) -> List[DiscoveryResult]:
        results: List[DiscoveryResult] = []
        for profile in profiles:
            if not profile.enabled:
                continue
            for discoverer in self._discoverers.values():
                if not discoverer.is_enabled(profile):
                    continue
                results.extend(discoverer.discover(profile, context))
        self._record_run(context.state, results)
        return results

    def discoverer_ids(self) -> List[str]:
        return list(self._discoverers.keys())

    def _record_run(self, state: FileStateStore, results: List[DiscoveryResult]) -> None:
        runs = state.read_json("discovery_runs.json", [])
        runs.append({
            "run_id": stable_id("discovery", now_iso(), len(runs)),
            "created_at": now_iso(),
            "discovery_mode": "person_centric",
            "discoverers": self.discoverer_ids(),
            "result_count": len(results),
            "episodes_found": sum(result.found_count for result in results),
            "information_events_found": sum(result.found_count for result in results),
            "queued": sum(result.queued_count for result in results),
            "duplicates": sum(result.duplicate_count for result in results),
            "skipped": sum(result.skipped_count for result in results),
            "failed": sum(result.failed_count for result in results),
            "results": [result.to_dict() for result in results],
        })
        state.write_json("discovery_runs.json", runs)