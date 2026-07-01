"""Stub discoverers — interfaces documented for future venue types."""

from __future__ import annotations

from typing import List

from ..discovery import DiscoveryResult
from ..models import IntelligenceProfile
from .base import DiscoveryContext, InformationEventDiscoverer


class _StubDiscoverer(InformationEventDiscoverer):
    def __init__(self, discoverer_id: str, event_types: List[str], description: str):
        self._discoverer_id = discoverer_id
        self._event_types = event_types
        self._description = description

    @property
    def discoverer_id(self) -> str:
        return self._discoverer_id

    @property
    def event_types(self) -> List[str]:
        return self._event_types

    def discover(self, profile: IntelligenceProfile, context: DiscoveryContext) -> List[DiscoveryResult]:
        return []


class ConferenceDiscoverer(_StubDiscoverer):
    def __init__(self) -> None:
        super().__init__(
            "conference",
            ["conference_keynote", "panel_discussion"],
            "Discovers conference keynotes and panel appearances from configured conference indexes.",
        )


class InterviewDiscoverer(_StubDiscoverer):
    def __init__(self) -> None:
        super().__init__(
            "interview",
            ["interview", "fireside_chat", "ama"],
            "Discovers interviews and AMA sessions from news sites and publisher feeds.",
        )


class LivestreamDiscoverer(_StubDiscoverer):
    def __init__(self) -> None:
        super().__init__(
            "livestream",
            ["livestream"],
            "Discovers livestream appearances from YouTube, Twitch, and similar platforms.",
        )


class EarningsCallDiscoverer(_StubDiscoverer):
    def __init__(self) -> None:
        super().__init__(
            "earnings_call",
            ["earnings_call"],
            "Discovers earnings calls and investor presentations from SEC and IR feeds.",
        )


class PresentationDiscoverer(_StubDiscoverer):
    def __init__(self) -> None:
        super().__init__(
            "presentation",
            ["research_presentation", "university_lecture", "product_launch", "congressional_testimony"],
            "Discovers research presentations, lectures, product launches, and testimony.",
        )