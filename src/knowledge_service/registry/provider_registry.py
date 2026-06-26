"""Provider Registry — Register and discover providers by capability

The Registry knows only provider capabilities and interfaces.
It never imports concrete provider implementations.
"""

from typing import Dict, List, Optional, Any
from ..interfaces.provider import Provider, ProviderType, HealthStatus


class ProviderRegistry:
    """Registry for discovering providers by capability type.

    Providers register themselves with their capabilities.
    The registry resolves lookups by ProviderType (search, crawl, api, etc.)
    without knowing any provider implementation details.
    """

    def __init__(self):
        self._providers: Dict[str, Provider] = {}
        self._by_type: Dict[ProviderType, List[str]] = {}

    def register(self, provider: Provider) -> None:
        """Register a provider instance."""
        name = provider.name
        self._providers[name] = provider
        caps = provider.capabilities
        for ptype in ProviderType:
            cap_key = f"can_{ptype.value}"
            if caps.get(cap_key, False):
                if ptype not in self._by_type:
                    self._by_type[ptype] = []
                self._by_type[ptype].append(name)

    def unregister(self, name: str) -> None:
        """Remove a provider from the registry."""
        if name in self._providers:
            del self._providers[name]
        for ptype in list(self._by_type.keys()):
            if name in self._by_type[ptype]:
                self._by_type[ptype].remove(name)

    def get_provider(self, name: str) -> Optional[Provider]:
        """Get a provider by name."""
        return self._providers.get(name)

    def get_providers_by_type(self, provider_type: ProviderType) -> List[Provider]:
        """Get all providers that support a given capability type."""
        names = self._by_type.get(provider_type, [])
        return [self._providers[n] for n in names if n in self._providers]

    def get_first_healthy(self, provider_type: ProviderType) -> Optional[Provider]:
        """Get the first healthy provider supporting a capability type."""
        for provider in self.get_providers_by_type(provider_type):
            try:
                health = provider.health()
                if health.status == HealthStatus.HEALTHY:
                    return provider
            except Exception:
                continue
        return None

    def list_providers(self) -> List[Dict[str, Any]]:
        """List all registered providers with their capabilities."""
        result = []
        for name, provider in self._providers.items():
            result.append({
                "name": name,
                "capabilities": provider.capabilities,
            })
        return result

    def count(self) -> int:
        """Number of registered providers."""
        return len(self._providers)
