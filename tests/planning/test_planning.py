"""Planning Layer — Unit Tests

Tests the Planner, ProviderRegistry, and AcquisitionExecutor with mock providers.
No real infrastructure needed.
"""

import os, sys
_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

import pytest
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from knowledge_service.registry.provider_registry import ProviderRegistry
from knowledge_service.planning.planner import RuleBasedPlanner
from knowledge_service.planning.executor import AcquisitionExecutor
from knowledge_service.planning.interfaces import AcquisitionPlan, PlanStep
from knowledge_service.interfaces.provider import (
     Provider, ProviderRequest, ProviderResponse, ProviderError,
     InitResult, HealthCheckResult, HealthStatus, ProviderType,
)
from knowledge_service.storage.postgres.in_memory_store import InMemorySourceStore
from knowledge_service.storage.repositories.source_repository import SourceRepository


# ---------------------------------------------------------------------------
# Mock Providers
# ---------------------------------------------------------------------------

class MockSearchProvider(Provider):
    def __init__(self, name="mock-search"):
        self._name = name
        self._healthy = True

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> Dict[str, Any]:
        return {"can_search": True, "can_crawl": False, "max_results": 5}

    def initialize(self, config: Dict[str, Any]) -> InitResult:
        return InitResult(name=self._name)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        return ProviderResponse(
            content=None,
            content_type="application/json",
            status_code=200,
            metadata={
                "results": [
                    {"url": "https://example.com/result1", "title": "Result 1",
                     "content": "First result content", "engine": "mock", "score": 0.95},
                    {"url": "https://example.com/result2", "title": "Result 2",
                     "content": "Second result content", "engine": "mock", "score": 0.85},
                ],
                "query": request.target,
            }
        )

    def health(self) -> HealthCheckResult:
        return HealthCheckResult(
            status=HealthStatus.HEALTHY if self._healthy else HealthStatus.UNHEALTHY
        )

    def shutdown(self):
        pass


class MockCrawlProvider(Provider):
    def __init__(self, name="mock-crawl"):
        self._name = name
        self._healthy = True

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> Dict[str, Any]:
        return {"can_search": False, "can_crawl": True}

    def initialize(self, config: Dict[str, Any]) -> InitResult:
        return InitResult(name=self._name)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        return ProviderResponse(
            content=f"<html><body><h1>Crawled: {request.target}</h1><p>Mock content.</p></body></html>",
            content_type="text/html",
            status_code=200,
            metadata={"url": request.target, "status_code": 200},
        )

    def health(self) -> HealthCheckResult:
        return HealthCheckResult(
            status=HealthStatus.HEALTHY if self._healthy else HealthStatus.UNHEALTHY
        )

    def shutdown(self):
        pass


class FailingProvider(Provider):
    def __init__(self, name="failing-provider"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> Dict[str, Any]:
        return {"can_search": False, "can_crawl": True}

    def initialize(self, config: Dict[str, Any]) -> InitResult:
        return InitResult(name=self._name)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        return ProviderResponse(
            error=ProviderError(code="SERVER_ERROR", message="Mock failure", retryable=True)
        )

    def health(self) -> HealthCheckResult:
        return HealthCheckResult(status=HealthStatus.HEALTHY)

    def shutdown(self):
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def registry():
    reg = ProviderRegistry()
    reg.register(MockSearchProvider("mock-search-1"))
    reg.register(MockCrawlProvider("mock-crawl-1"))
    return reg


@pytest.fixture
def planner(registry):
    return RuleBasedPlanner(registry)


@pytest.fixture
def executor(registry):
    return AcquisitionExecutor(registry)


@pytest.fixture
def source_repository():
    return SourceRepository(InMemorySourceStore())


@pytest.fixture
def executor_with_source(registry, source_repository):
    return AcquisitionExecutor(registry, source_repository)


# ---------------------------------------------------------------------------
# Provider Registry Tests
# ---------------------------------------------------------------------------

class TestProviderRegistry:

    def test_register_provider(self):
        reg = ProviderRegistry()
        provider = MockSearchProvider("test-provider")
        reg.register(provider)
        assert reg.count() == 1

    def test_get_provider_by_name(self, registry):
        provider = registry.get_provider("mock-search-1")
        assert provider is not None
        assert provider.name == "mock-search-1"

    def test_get_providers_by_type(self, registry):
        search_providers = registry.get_providers_by_type(ProviderType.SEARCH)
        assert len(search_providers) >= 1
        assert search_providers[0].capabilities.get("can_search") is True

    def test_get_first_healthy(self, registry):
        provider = registry.get_first_healthy(ProviderType.SEARCH)
        assert provider is not None
        assert provider.name == "mock-search-1"

    def test_skip_unhealthy_providers(self):
        reg = ProviderRegistry()
        unhealthy = MockSearchProvider("unhealthy-search")
        unhealthy._healthy = False
        reg.register(unhealthy)

        provider = reg.get_first_healthy(ProviderType.SEARCH)
        assert provider is None

    def test_unregister_provider(self, registry):
        registry.unregister("mock-search-1")
        assert registry.get_provider("mock-search-1") is None

    def test_list_providers(self, registry):
        providers_list = registry.list_providers()
        assert len(providers_list) >= 2


# ---------------------------------------------------------------------------
# Planner Tests
# ---------------------------------------------------------------------------

class TestPlanner:

    def test_planner_creates_plan(self, planner):
        plan = planner.plan("test query", "req-1")
        assert isinstance(plan, AcquisitionPlan)
        assert plan.plan_id == "plan-req-1"
        assert plan.request_id == "req-1"
        assert plan.query == "test query"

    def test_plan_has_search_and_crawl_steps(self, planner):
        plan = planner.plan("test query", "req-2")
        step_types = [s.provider_type for s in plan.steps]
        assert ProviderType.SEARCH in step_types
        assert ProviderType.CRAWL in step_types

    def test_plan_steps_ordered_search_first(self, planner):
        plan = planner.plan("test query", "req-3")
        step_types = [s.provider_type for s in plan.steps]
        search_idx = step_types.index(ProviderType.SEARCH)
        crawl_idx = step_types.index(ProviderType.CRAWL)
        assert search_idx < crawl_idx

    def test_plan_with_no_search_provider(self):
        reg = ProviderRegistry()
        reg.register(MockCrawlProvider("only-crawl"))
        p = RuleBasedPlanner(reg)
        plan = p.plan("test", "req-4")
        step_types = [s.provider_type for s in plan.steps]
        assert ProviderType.SEARCH not in step_types

    def test_plan_with_no_crawl_provider(self):
        reg = ProviderRegistry()
        reg.register(MockSearchProvider("only-search"))
        p = RuleBasedPlanner(reg)
        plan = p.plan("test", "req-5")
        step_types = [s.provider_type for s in plan.steps]
        assert ProviderType.CRAWL not in step_types


# ---------------------------------------------------------------------------
# AcquisitionExecutor Tests
# ---------------------------------------------------------------------------

class TestAcquisitionExecutor:

    def test_execute_search_returns_discovered_urls(self, executor):
        plan = AcquisitionPlan(plan_id="p1", request_id="r1", query="test")
        plan.add_step(PlanStep(
            step_id="search-1", provider_type=ProviderType.SEARCH, target="test",
        ))
        bundle = executor.execute(plan)
        assert len(bundle.discovered_urls) >= 2
        assert bundle.providers_successful >= 1

    def test_execute_crawl_returns_document(self, executor):
        plan = AcquisitionPlan(plan_id="p2", request_id="r2", query="test")
        plan.add_step(PlanStep(
            step_id="crawl-direct", provider_type=ProviderType.CRAWL, target="https://example.com",
        ))
        bundle = executor.execute(plan)
        assert len(bundle.acquired_documents) >= 1
        doc = bundle.acquired_documents[0]
        assert doc.url == "https://example.com"
        assert len(doc.raw_content) > 0

    def test_executor_updates_source_registry(self, executor_with_source, source_repository):
        plan = AcquisitionPlan(plan_id="p7", request_id="r7", query="test")
        plan.add_step(PlanStep(
            step_id="search-1", provider_type=ProviderType.SEARCH, target="test",
        ))

        bundle = executor_with_source.execute(plan)
        assert len(bundle.provider_executions) >= 1

        source = source_repository.get_source("mock-search-1")
        assert source is not None
        assert source.success_rate == 1.0
        assert source.avg_latency_ms >= 0
        assert source.status == "healthy"

    def test_complete_search_then_crawl(self, executor):
        plan = AcquisitionPlan(plan_id="p3", request_id="r3", query="test")
        plan.add_step(PlanStep(
            step_id="search-1", provider_type=ProviderType.SEARCH, target="test",
        ))
        plan.add_step(PlanStep(
            step_id="crawl-1", provider_type=ProviderType.CRAWL, target="placeholder",
        ))
        bundle = executor.execute(plan)
        assert len(bundle.discovered_urls) >= 2
        assert len(bundle.acquired_documents) >= 2  # crawled each discovered URL
        assert bundle.providers_queried >= 3  # 1 search + at least 2 crawls

    def test_executor_handles_failing_provider(self):
        reg = ProviderRegistry()
        reg.register(FailingProvider("fail-crawl"))
        exec_ = AcquisitionExecutor(reg)

        plan = AcquisitionPlan(plan_id="p4", request_id="r4", query="test")
        plan.add_step(PlanStep(
            step_id="crawl-fail", provider_type=ProviderType.CRAWL,
            target="https://example.com",
        ))
        bundle = exec_.execute(plan)
        assert bundle.providers_failed >= 1
        assert len(bundle.acquired_documents) == 0

    def test_executor_updates_source_registry_on_failure(self, source_repository):
        reg = ProviderRegistry()
        reg.register(FailingProvider("fail-crawl"))
        exec_ = AcquisitionExecutor(reg, source_repository)

        plan = AcquisitionPlan(plan_id="p9", request_id="r9", query="test")
        plan.add_step(PlanStep(
            step_id="crawl-fail-src", provider_type=ProviderType.CRAWL,
            target="https://example.com/fail",
        ))
        bundle = exec_.execute(plan)

        assert bundle.providers_failed >= 1
        source = source_repository.get_source("fail-crawl")
        assert source is not None
        assert source.success_rate == 0.0
        assert source.status == "unhealthy"

    def test_executor_records_latency(self, executor):
        plan = AcquisitionPlan(plan_id="p5", request_id="r5", query="test")
        plan.add_step(PlanStep(
            step_id="search-1", provider_type=ProviderType.SEARCH, target="test",
        ))
        bundle = executor.execute(plan)
        assert bundle.search_duration_ms >= 0
        assert bundle.total_duration_ms >= 0

    def test_executor_records_execution_chain(self, executor):
        plan = AcquisitionPlan(plan_id="p6", request_id="r6", query="test")
        plan.add_step(PlanStep(
            step_id="search-1", provider_type=ProviderType.SEARCH, target="test",
        ))
        bundle = executor.execute(plan)
        assert len(bundle.provider_executions) >= 1
        record = bundle.provider_executions[0]
        assert record.step_id == "search-1"
        assert record.status == "success"
        assert record.latency_ms >= 0

    def test_executor_bundle_has_correct_metadata(self, executor):
        plan = AcquisitionPlan(plan_id="plan-r7", request_id="r7", query="test")
        plan.add_step(PlanStep(
            step_id="search-1", provider_type=ProviderType.SEARCH, target="test",
        ))
        bundle = executor.execute(plan)
        assert bundle.request_id == "r7"
        assert bundle.plan_id == "plan-r7"
        assert bundle.acquisition_timestamp is not None


# ---------------------------------------------------------------------------
# End-to-End with Mocks
# ---------------------------------------------------------------------------

class TestEndToEndWithMocks:

    def test_full_plan_execute_cycle(self, registry, planner, executor):
        plan = planner.plan("Crawl4AI framework", "e2e-1")
        bundle = executor.execute(plan)

        assert bundle.providers_queried > 0
        assert bundle.providers_successful > 0
        assert len(bundle.acquired_documents) > 0 or len(bundle.discovered_urls) > 0

    def test_deterministic_planning(self, registry):
        planner = RuleBasedPlanner(registry)
        plan1 = planner.plan("same query", "req-a")
        plan2 = planner.plan("same query", "req-b")
        assert len(plan1.steps) == len(plan2.steps)
        for s1, s2 in zip(plan1.steps, plan2.steps):
            assert s1.provider_type == s2.provider_type
