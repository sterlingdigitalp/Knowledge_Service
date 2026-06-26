"""Provider Compliance Tests — Phase 1.1C

Verifies all providers implement the Provider interface correctly.
Tests are provider-agnostic: providers should be interchangeable at the interface level.
"""

import pytest
import sys
import os

_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

from knowledge_service.interfaces.provider import Provider, ProviderRequest, ProviderType, HealthStatus, InitResult, ProviderResponse, HealthCheckResult

CRAWL4AI_AUTH_TOKEN = "SterlingKnowledge2026"


@pytest.fixture(scope="module")
def crawl4ai_provider():
    from knowledge_service.providers.crawl4ai_provider import Crawl4AIProvider
    provider = Crawl4AIProvider("test-crawl")
    try:
        provider.initialize({
            "endpoint": "http://localhost:11235",
            "auth_token": CRAWL4AI_AUTH_TOKEN,
            "timeout_ms": 10000,
        })
    except Exception as exc:
        pytest.skip(f"Crawl4AI service not available: {exc}")
    return provider


@pytest.fixture(scope="module")
def searxng_provider():
    from knowledge_service.providers.searxng_search_provider import SearXNGSearchProvider
    provider = SearXNGSearchProvider("test-searxng")
    try:
        provider.initialize({
            "endpoint": "http://localhost:8080",
            "timeout_ms": 15000,
        })
    except Exception as exc:
        pytest.skip(f"SearXNG service not available: {exc}")
    return provider


class TestProviderInterfaceCompliance:
    """Test that all providers implement the Provider interface correctly"""

    def test_provider_has_initialize_method(self):
        assert hasattr(Provider, 'initialize')
        assert callable(getattr(Provider, 'initialize'))

    def test_provider_has_execute_method(self):
        assert hasattr(Provider, 'execute')
        assert callable(getattr(Provider, 'execute'))

    def test_provider_has_health_method(self):
        assert hasattr(Provider, 'health')
        assert callable(getattr(Provider, 'health'))

    def test_provider_has_shutdown_method(self):
        assert hasattr(Provider, 'shutdown')
        assert callable(getattr(Provider, 'shutdown'))

    def test_initialize_returns_init_result(self, crawl4ai_provider):
        provider = crawl4ai_provider
        result = provider.initialize({
            "endpoint": "http://localhost:11235",
            "auth_token": CRAWL4AI_AUTH_TOKEN,
            "timeout_ms": 10000
        })
        assert isinstance(result, InitResult)
        assert isinstance(result.name, str)
        assert isinstance(result.capabilities, dict)

    def test_health_returns_health_check_result(self, searxng_provider):
        provider = searxng_provider
        health_result = provider.health()
        assert isinstance(health_result, HealthCheckResult)
        assert health_result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]

    def test_execute_returns_provider_response(self, searxng_provider):
        provider = searxng_provider
        request = ProviderRequest(
            target="test query",
            provider_type=ProviderType.SEARCH,
            options={}
        )
        response = provider.execute(request)
        assert isinstance(response, ProviderResponse)
        assert hasattr(response, 'content')
        assert hasattr(response, 'content_type')
        assert hasattr(response, 'status_code')
        assert hasattr(response, 'metadata')
        assert hasattr(response, 'error')


class TestProviderAbstraction:
    """Test that provider abstraction is respected — no provider-specific types escape"""

    def test_crawl4ai_response_is_provider_response(self, crawl4ai_provider):
        from knowledge_service.interfaces.provider import ProviderResponse
        provider = crawl4ai_provider
        request = ProviderRequest(
            target="https://example.com",
            provider_type=ProviderType.CRAWL
        )
        response = provider.execute(request)
        assert isinstance(response, ProviderResponse)

    def test_searxng_response_is_provider_response(self, searxng_provider):
        from knowledge_service.interfaces.provider import ProviderResponse
        provider = searxng_provider
        request = ProviderRequest(
            target="test",
            provider_type=ProviderType.SEARCH,
            options={}
        )
        response = provider.execute(request)
        assert isinstance(response, ProviderResponse)

    def test_both_providers_have_same_interface(self):
        from knowledge_service.providers.crawl4ai_provider import Crawl4AIProvider
        from knowledge_service.providers.searxng_search_provider import SearXNGSearchProvider
        abstract_methods = ['initialize', 'execute', 'health', 'shutdown']
        for method in abstract_methods:
            assert callable(getattr(Crawl4AIProvider, method))
            assert callable(getattr(SearXNGSearchProvider, method))
