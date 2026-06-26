"""Planner — Query analysis and provider selection

The Planner analyzes a query and builds an AcquisitionPlan.
It selects providers by capability type, never by implementation name.
It knows only provider capabilities and interfaces.
"""

from typing import Optional

from ..interfaces.provider import ProviderType
from ..registry.provider_registry import ProviderRegistry
from .interfaces import AcquisitionPlan, Planner, PlanStep


class RuleBasedPlanner:
    """Rule-based planner that builds acquisition plans.

    Strategy:
    1. Search for the query using a search provider
    2. Crawl the first result URL using a crawl provider

    This is a deterministic, rule-based planner. No learning, no adaptation.
    """

    def __init__(self, registry: ProviderRegistry):
        self._registry = registry

    def plan(self, query: str, request_id: str) -> AcquisitionPlan:
        """Analyze a query and produce an acquisition plan."""
        plan = AcquisitionPlan(
            plan_id=f"plan-{request_id}",
            request_id=request_id,
            query=query,
        )

        # Step 1: Search for the query
        search_providers = self._registry.get_providers_by_type(ProviderType.SEARCH)
        if search_providers:
            plan.add_step(
                PlanStep(
                    step_id="search-1",
                    provider_type=ProviderType.SEARCH,
                    target=query,
                    options={
                        "language": "en",
                        "max_results": 5,
                        "engines": "bing,yahoo",
                    },
                    fallback_strategy="skip",
                )
            )

        # Step 2: Crawl the first result (target will be filled at execution time)
        crawl_providers = self._registry.get_providers_by_type(ProviderType.CRAWL)
        if crawl_providers:
            plan.add_step(
                PlanStep(
                    step_id="crawl-1",
                    provider_type=ProviderType.CRAWL,
                    target=query,  # placeholder; executor replaces with URLs from search
                    options={},
                    fallback_strategy="skip",
                )
            )

        return plan
