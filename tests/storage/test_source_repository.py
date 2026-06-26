"""Source Repository tests — SourceRegistry registration and querying."""

import os
import sys

_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

import pytest

from src.knowledge_service.storage.postgres.in_memory_store import InMemorySourceStore
from src.knowledge_service.storage.repositories.source_repository import SourceRepository


@pytest.fixture
def store():
    return InMemorySourceStore()


@pytest.fixture
def repo(store):
    return SourceRepository(store)


class TestSourceRegistryCrud:

    def test_register_and_get_source_with_url_canonicalization(self, repo):
        created = repo.register_source(
            source_id="crawl4ai-main",
            name="Crawl4AI",
            url="HTTPS://Example.COM/Docs/?b=2&a=1#section",
            source_type="api",
            trust_score=0.8,
            freshness_score=0.9,
            topics=["Web", "Automation", "Web"],
            cache_policy={"max_age_seconds": 1200},
        )
        assert created is True

        source = repo.get_source("crawl4ai-main")
        assert source is not None
        assert source.id == "crawl4ai-main"
        assert source.url == "https://example.com/Docs?a=1&b=2"
        assert source.name == "Crawl4AI"
        assert source.topics == ["web", "automation"]
        assert source.cache_policy["max_age_seconds"] == 1200
        assert source.status == "healthy"

        duplicate = repo.register_source(
            source_id="crawl4ai-main",
            name="Duplicate",
            url="https://example.com/other",
            source_type="api",
        )
        assert duplicate is False

    def test_update_source_metrics_and_status(self, repo):
        repo.register_source(
            source_id="search-api",
            name="Search API",
            url="https://search.example.org",
            source_type="api",
            trust_score=0.92,
            freshness_score=0.95,
        )

        ok = repo.update_source_metrics(
            source_id="search-api",
            trust_score=0.4,
            freshness_score=0.4,
            avg_latency_ms=150,
            success_rate=0.55,
            last_acquired_at="2026-06-25T12:00:00Z",
        )
        assert ok is True

        updated = repo.get_source("search-api")
        assert updated is not None
        assert updated.trust_score == 0.4
        assert updated.freshness_score == 0.4
        assert updated.avg_latency_ms == 150
        assert updated.success_rate == 0.55
        assert updated.last_acquired_at == "2026-06-25T12:00:00Z"
        assert updated.status == "unhealthy"

    def test_update_missing_source_returns_false(self, repo):
        ok = repo.update_source_metrics(source_id="missing", trust_score=0.5)
        assert ok is False


class TestSourceRegistryQueries:

    def test_list_sources_filter_by_status_and_limit(self, repo):
        repo.register_source("src-web", "Web", "https://web.example", "web_page")
        repo.register_source("src-api", "Api", "https://api.example", "api_response")
        repo.update_source_metrics("src-api", success_rate=0.4)

        all_sources = repo.list_sources(limit=10)
        assert len(all_sources) == 2

        unhealthy = repo.list_sources(status="unhealthy")
        assert len(unhealthy) == 1
        assert unhealthy[0].id == "src-api"

        limited = repo.list_sources(limit=1)
        assert len(limited) == 1

    def test_search_by_topic_respects_min_confidence(self, repo):
        repo.register_source("topic-strong", "Strong", "https://strong.example", "web_page", topics=["python"]) 
        repo.register_source("topic-weak", "Weak", "https://weak.example", "web_page", topics=["python"])

        # Directly lower confidence for second source to test threshold filtering.
        source = repo.get_source("topic-weak")
        assert source is not None
        source.topic_scores["python"] = 0.2

        matches = repo.search_by_topic("python", min_confidence=0.3)
        matched_ids = {item.id for item in matches}
        assert "topic-strong" in matched_ids
        assert "topic-weak" not in matched_ids

    def test_search_by_topic_returns_high_confidence(self, repo):
        repo.register_source("topic-weak", "Weak", "https://weak.example", "web_page", topics=["ops"])
        source = repo.get_source("topic-weak")
        assert source is not None
        source.topic_scores["ops"] = 0.2

        assert repo.search_by_topic("ops", min_confidence=0.1)[0].id == "topic-weak"


class TestSourceRegistryValidation:

    def test_reject_invalid_metric_values(self, repo):
        repo.register_source("val-src", "Val", "https://val.example", "web_page")

        with pytest.raises(ValueError):
            repo.update_source_metrics("val-src", trust_score=1.2)

        with pytest.raises(ValueError):
            repo.update_source_metrics("val-src", freshness_score=-0.1)

        with pytest.raises(ValueError):
            repo.update_source_metrics("val-src", avg_latency_ms=-10)
