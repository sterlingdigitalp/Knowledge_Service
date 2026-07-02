"""Integration Tests — Planning Layer with Real Infrastructure

Tests the complete flow:
Question -> Planner -> Provider Registry -> Search -> Crawl -> AcquisitionBundle

Uses real Crawl4AI and SearXNG infrastructure.
Skips if infrastructure is unavailable.
"""

import pytest
import sys
import os

_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

from integration_tests.searxng_helpers import require_searxng_results
from knowledge_service.registry.provider_registry import ProviderRegistry
from knowledge_service.planning.planner import RuleBasedPlanner
from knowledge_service.planning.executor import AcquisitionExecutor
from knowledge_service.planning.interfaces import AcquisitionPlan, PlanStep
from knowledge_service.interfaces.provider import ProviderType, HealthStatus


CRAWL4AI_AUTH_TOKEN = "SterlingKnowledge2026"
CRAWL4AI_ENDPOINT = "http://localhost:11235"
SEARXNG_ENDPOINT = "http://localhost:8080"


@pytest.fixture(scope="module")
def registry():
    """Create a provider registry with real providers if available."""
    from knowledge_service.providers.crawl4ai_provider import Crawl4AIProvider
    from knowledge_service.providers.searxng_search_provider import SearXNGSearchProvider

    reg = ProviderRegistry()
    crawl_available = False
    search_available = False

    crawl_provider = Crawl4AIProvider("crawl4ai-test")
    try:
        result = crawl_provider.initialize({
            "endpoint": CRAWL4AI_ENDPOINT,
            "auth_token": CRAWL4AI_AUTH_TOKEN,
            "timeout_ms": 30000,
        })
        reg.register(crawl_provider)
        crawl_available = True
    except Exception as e:
        print(f"Crawl4AI not available: {e}")

    search_provider = SearXNGSearchProvider("searxng-test")
    try:
        result = search_provider.initialize({
            "endpoint": SEARXNG_ENDPOINT,
            "timeout_ms": 15000,
        })
        reg.register(search_provider)
        search_available = True
    except Exception as e:
        print(f"SearXNG not available: {e}")

    if not crawl_available and not search_available:
        pytest.skip("No provider infrastructure available")

    return reg, crawl_available, search_available


class TestPlannerIntegration:

    def test_planner_creates_plan(self, registry):
        """Test that the planner creates a valid plan."""
        reg, crawl_avail, search_avail = registry
        planner = RuleBasedPlanner(reg)

        plan = planner.plan("What is Crawl4AI?", "test-req-1")

        assert plan.plan_id == "plan-test-req-1"
        assert plan.request_id == "test-req-1"
        assert plan.query == "What is Crawl4AI?"
        assert plan.step_count() > 0

        if search_avail:
            search_steps = [s for s in plan.steps if s.provider_type == ProviderType.SEARCH]
            assert len(search_steps) >= 1

        if crawl_avail:
            crawl_steps = [s for s in plan.steps if s.provider_type == ProviderType.CRAWL]
            assert len(crawl_steps) >= 1

    def test_planner_search_then_crawl_order(self, registry):
        """Test that search step comes before crawl step."""
        reg, crawl_avail, search_avail = registry
        if not search_avail:
            pytest.skip("No search provider available")

        planner = RuleBasedPlanner(reg)
        plan = planner.plan("Python programming", "test-req-2")

        step_types = [s.provider_type for s in plan.steps]
        search_idx = step_types.index(ProviderType.SEARCH)
        crawl_idx = step_types.index(ProviderType.CRAWL)
        assert search_idx < crawl_idx


class TestExecutorIntegration:

    def test_execute_search_step(self, registry):
        """Test executing a search step against real SearXNG."""
        reg, crawl_avail, search_avail = registry
        if not search_avail:
            pytest.skip("No search provider available")

        executor = AcquisitionExecutor(reg)
        plan = AcquisitionPlan(
            plan_id="plan-test-search",
            request_id="test-search",
            query="Crawl4AI web crawler",
        )
        plan.add_step(PlanStep(
            step_id="search-1",
            provider_type=ProviderType.SEARCH,
            target="Crawl4AI web crawler",
            options={"language": "en"},
        ))

        bundle = executor.execute(plan)

        assert bundle.request_id == "test-search"
        assert bundle.providers_queried >= 1
        assert bundle.providers_successful >= 1
        if not bundle.discovered_urls:
            metadata = {}
            for execution in bundle.provider_executions:
                metadata = execution.response_metadata or metadata
            require_searxng_results(metadata, endpoint=SEARXNG_ENDPOINT)
        assert len(bundle.discovered_urls) > 0

    def test_execute_crawl_step(self, registry):
        """Test executing a crawl step against real Crawl4AI."""
        reg, crawl_avail, search_avail = registry
        if not crawl_avail:
            pytest.skip("No crawl provider available")

        executor = AcquisitionExecutor(reg)
        plan = AcquisitionPlan(
            plan_id="plan-test-crawl",
            request_id="test-crawl",
            query="https://example.com",
        )
        plan.add_step(PlanStep(
            step_id="crawl-1",
            provider_type=ProviderType.CRAWL,
            target="https://example.com",
        ))

        bundle = executor.execute(plan)

        assert bundle.request_id == "test-crawl"
        assert bundle.providers_queried >= 1
        assert bundle.providers_successful >= 1
        assert len(bundle.acquired_documents) > 0

        doc = bundle.acquired_documents[0]
        assert doc.url == "https://example.com"
        assert len(doc.raw_content) > 0
        assert doc.content_size_bytes > 0


class TestEndToEndPlanning:

    def test_complete_search_and_crawl(self, registry):
        """Test the complete flow: search then crawl."""
        reg, crawl_avail, search_avail = registry
        if not search_avail or not crawl_avail:
            pytest.skip("Both search and crawl providers needed")

        planner = RuleBasedPlanner(reg)
        executor = AcquisitionExecutor(reg)

        plan = planner.plan("Crawl4AI", "test-e2e-1")
        bundle = executor.execute(plan)

        assert bundle.providers_queried >= 2
        assert len(bundle.discovered_urls) > 0
        assert len(bundle.acquired_documents) > 0
        assert bundle.total_duration_ms > 0

    def test_executor_records_execution_history(self, registry):
        """Test that the executor properly records execution history."""
        reg, crawl_avail, search_avail = registry
        if not search_avail:
            pytest.skip("No search provider available")

        executor = AcquisitionExecutor(reg)
        plan = AcquisitionPlan(
            plan_id="plan-test-history",
            request_id="test-history",
            query="test query",
        )
        plan.add_step(PlanStep(
            step_id="search-1",
            provider_type=ProviderType.SEARCH,
            target="test query",
        ))

        bundle = executor.execute(plan)

        assert len(bundle.provider_executions) > 0
        exec_record = bundle.provider_executions[0]
        assert exec_record.step_id == "search-1"
        assert exec_record.status == "success"
        assert exec_record.latency_ms > 0
        assert exec_record.provider_name == "searxng-test"
        assert exec_record.provider_type == "search"
