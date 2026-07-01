"""Base interface for information event discovery."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..dedupe import DeduplicationStore
from ..discovery import DiscoveryResult
from ..models import IntelligenceProfile
from ..route_registry import AcquisitionRouteRegistry
from ..state import FileStateStore


@dataclass
class DiscoveryContext:
    state: FileStateStore
    dedupe: DeduplicationStore
    route_registry: Optional[AcquisitionRouteRegistry] = None
    timeout_seconds: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class InformationEventDiscoverer(ABC):
    """Discover information events for watched people from a specific venue type."""

    @property
    @abstractmethod
    def discoverer_id(self) -> str:
        ...

    @property
    @abstractmethod
    def event_types(self) -> List[str]:
        ...

    @abstractmethod
    def discover(self, profile: IntelligenceProfile, context: DiscoveryContext) -> List[DiscoveryResult]:
        ...

    def is_enabled(self, profile: IntelligenceProfile) -> bool:
        return profile.enabled