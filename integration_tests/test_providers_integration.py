"""Integration Tests for Crawl4AI & SearXNG Providers - Phase 1.1C

Contracts verified against live infrastructure.
"""

import pytest
import sys
import os

_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

from knowledge_service.providers.crawl4ai_provider import Crawl4AIProvider
from knowledge_service.providers.searxng_search_provider import SearXNGSearchProvider
from knowledge_service.interfaces.provider import ProviderRequest, ProviderType, HealthStatus


CRAWL4AI_AUTH_TOKEN = "SterlingKnowledge2026"
CRAWL4AI_ENDPOINT = "http://localhost:11235"
SEARXNG_ENDPOINT = "http://localhost:8080"


class TestCrawl4AIProviderIntegration:
    """Integration tests for Crawl4AI provider — verified against live http://localhost:11235"""

    @pytest.fixture
    def crawl_provider(self):
        provider = Crawl4AIProvider("crawl4ai-test")
        try:
            provider.initialize({
                "endpoint": CRAWL4AI_ENDPOINT,
                "auth_token": CRAWL4AI_AUTH_TOKEN,
                "timeout_ms": 30000
            })
        except Exception as e:
            pytest.skip(f"Crawl4AI service not available: {e}")
        return provider

    def test_provider_initialization(self, crawl_provider):
        assert crawl_provider.name == "crawl4ai-test"
        assert crawl_provider._is_initialized is True
        assert crawl_provider._version == "0.9.0"
        caps = crawl_provider.capabilities
        assert caps["can_crawl"] is True
        assert "text/markdown" in caps["supported_content_types"]

    def test_provider_health_check(self, crawl_provider):
        health_result = crawl_provider.health()
        assert health_result.status == HealthStatus.HEALTHY

    def test_provider_execute_crawl_request(self, crawl_provider):
        request = ProviderRequest(
            target="https://example.com",
            provider_type=ProviderType.CRAWL,
            options={"config": {"include_markdown": True}}
        )
        response = crawl_provider.execute(request)
        assert response is not None
        assert response.error is None, f"Expected no error, got: {response.error}"
        assert response.content, "Expected non-empty content"
        assert response.content_type in ["text/markdown", "text/html", "text/plain"]

    def test_provider_execute_returns_metadata(self, crawl_provider):
        request = ProviderRequest(
            target="https://example.com",
            provider_type=ProviderType.CRAWL
        )
        response = crawl_provider.execute(request)
        assert response.metadata is not None
        assert "url" in response.metadata
        assert response.metadata["url"] == "https://example.com"
        assert "status_code" in response.metadata
        assert "session_id" in response.metadata

    def test_provider_execute_invalid_url(self, crawl_provider):
        request = ProviderRequest(
            target="https://thissitedoesnotexist.example.com",
            provider_type=ProviderType.CRAWL
        )
        response = crawl_provider.execute(request)
        assert response.error is not None
        assert response.error.code in ["SERVER_ERROR", "NETWORK_ERROR", "FORBIDDEN"]

    def test_provider_shutdown(self, crawl_provider):
        crawl_provider.shutdown()
        assert crawl_provider._is_initialized is False


class TestSearXNGProviderIntegration:
    """Integration tests for SearXNG provider — verified against live http://localhost:8080"""

    @pytest.fixture
    def searxng_provider(self):
        provider = SearXNGSearchProvider("searxng-test")
        try:
            provider.initialize({
                "endpoint": SEARXNG_ENDPOINT,
                "timeout_ms": 15000
            })
        except Exception as e:
            pytest.skip(f"SearXNG service not available: {e}")
        return provider

    def test_provider_initialization(self, searxng_provider):
        assert searxng_provider.name == "searxng-test"
        assert searxng_provider._is_initialized is True
        caps = searxng_provider.capabilities
        assert caps["can_search"] is True
        assert "application/json" in caps["supported_content_types"]

    def test_provider_health_check(self, searxng_provider):
        health_result = searxng_provider.health()
        assert health_result.status == HealthStatus.HEALTHY

    def test_provider_execute_search_request(self, searxng_provider):
        request = ProviderRequest(
            target="Crawl4AI",
            provider_type=ProviderType.SEARCH,
            options={"language": "en"}
        )
        response = searxng_provider.execute(request)
        assert response is not None
        assert response.error is None, f"Expected no error, got: {response.error}"
        assert response.metadata is not None
        assert "results" in response.metadata
        assert len(response.metadata["results"]) > 0

    def test_search_results_have_expected_fields(self, searxng_provider):
        request = ProviderRequest(
            target="Crawl4AI",
            provider_type=ProviderType.SEARCH
        )
        response = searxng_provider.execute(request)
        result = response.metadata["results"][0]
        assert "url" in result
        assert "title" in result
        assert "content" in result
        assert "engine" in result
        assert "score" in result

    def test_search_returns_metadata_fields(self, searxng_provider):
        request = ProviderRequest(
            target="Crawl4AI",
            provider_type=ProviderType.SEARCH
        )
        response = searxng_provider.execute(request)
        assert "query" in response.metadata
        assert "suggestions" in response.metadata
        assert "answers" in response.metadata
        assert "infoboxes" in response.metadata
        assert "unresponsive_engines" in response.metadata

    def test_search_with_empty_query(self, searxng_provider):
        request = ProviderRequest(
            target="",
            provider_type=ProviderType.SEARCH
        )
        response = searxng_provider.execute(request)
        assert response is not None
        assert response.metadata is not None

    def test_provider_shutdown(self, searxng_provider):
        searxng_provider.shutdown()
        assert searxng_provider._is_initialized is False
