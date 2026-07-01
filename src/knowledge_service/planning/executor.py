"""Acquisition Executor — Executes acquisition plans against real providers

The Executor takes an AcquisitionPlan, executes each step against registered
providers, and produces an AcquisitionBundle. It knows only provider interfaces.
"""

import time
from datetime import datetime, timezone
from typing import Dict, Optional

from ..acquisition.acquisition_bundle import (
    AcquisitionBundle,
    DocumentRecord,
    ExecutionRecord,
)
from ..interfaces.provider import Provider, ProviderRequest, ProviderType
from ..registry.provider_registry import ProviderRegistry
from ..storage.repositories.source_repository import SourceRepository
from .interfaces import AcquisitionPlan, PlanStep


class AcquisitionExecutor:
    """Executes acquisition plans against real providers.

    Follows the plan step-by-step:
    1. For each step, selects a healthy provider by type
    2. Executes the provider request
    3. Records execution in the AcquisitionBundle
    4. For crawl steps, uses URLs discovered from search steps
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        source_repository: Optional[SourceRepository] = None,
    ):
        self._registry = registry
        self._source_repository = source_repository

    def execute(self, plan: AcquisitionPlan) -> AcquisitionBundle:
        """Execute an acquisition plan and produce an AcquisitionBundle."""
        bundle = AcquisitionBundle(
            request_id=plan.request_id,
            plan_id=plan.plan_id,
            acquisition_timestamp=datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        )

        discovered_urls: list[str] = []
        urls_to_crawl: list[str] = []
        source_stats: Dict[str, Dict[str, float]] = {}

        for step in plan.steps:
            provider = self._registry.get_first_healthy(step.provider_type)
            if provider is None:
                bundle.add_warning(
                    type(
                        "Warning",
                        (),
                        {
                            "code": "NO_HEALTHY_PROVIDER",
                            "message": f"No healthy {step.provider_type.value} provider available",
                            "affected_steps": [step.step_id],
                        },
                    )()
                )
                continue

            if step.provider_type == ProviderType.CRAWL and step.step_id == "crawl-1":
                # Use search-discovered URLs when available; otherwise allow direct crawl plans.
                targets = urls_to_crawl if urls_to_crawl else [step.target]
            else:
                targets = [step.target]

            for target in targets:
                exec_record = self._execute_step(provider, step, target)
                bundle.add_execution_record(exec_record)

                self._update_source_metrics(
                    provider=provider,
                    source_stats=source_stats,
                    exec_record=exec_record,
                    step_type=step.provider_type,
                )

                if exec_record.status == "success" and exec_record.raw_response:
                    response_data = exec_record.raw_response

                    if step.provider_type == ProviderType.SEARCH:
                        # Extract URLs from search results
                        results = response_data.get("metadata", {}).get("results", [])
                        for r in results:
                            url = r.get("url")
                            if url:
                                bundle.add_discovered_url(url)
                                urls_to_crawl.append(url)

                    if step.provider_type in {ProviderType.CRAWL, ProviderType.API, ProviderType.FILE_PROCESSOR}:
                        # Extract document-like content from provider responses.
                        content = response_data.get("content", "")
                        metadata = response_data.get("metadata", {}) or {}
                        content_type = response_data.get("content_type", "text/html")
                        url = metadata.get("source_url") or metadata.get("url", target)

                        if content:
                            doc = DocumentRecord(
                                document_id=f"doc-{plan.request_id}-{step.step_id}-{len(bundle.acquired_documents)}",
                                url=url,
                                provider_name=provider.name,
                                content_type=content_type,
                                raw_content=content,
                                content_size_bytes=len(content.encode("utf-8")),
                                acquired_at=bundle.acquisition_timestamp,
                                metadata=metadata,
                                source_type=metadata.get("source_type", "web_page"),
                            )
                            bundle.add_document(doc)

        bundle.total_duration_ms = bundle.search_duration_ms + bundle.crawl_duration_ms
        return bundle

    def _update_source_metrics(
        self,
        provider: Provider,
        source_stats: Dict[str, Dict[str, float]],
        exec_record: ExecutionRecord,
        step_type: ProviderType,
    ) -> None:
        """Update source metrics from execution results."""
        if self._source_repository is None:
            return

        source_id = provider.name
        metrics = source_stats.get(source_id)
        if metrics is None:
            metrics = {"total": 0.0, "success": 0.0, "latency_sum": 0.0}
            source_stats[source_id] = metrics

        metrics["total"] += 1
        if exec_record.status == "success":
            metrics["success"] += 1
        metrics["latency_sum"] += float(exec_record.latency_ms or 0)

        avg_latency_ms = (
            int(metrics["latency_sum"] / metrics["total"]) if metrics["total"] else 0
        )
        success_rate = (
            metrics["success"] / metrics["total"] if metrics["total"] else 0.0
        )

        self._source_repository.register_source(
            source_id=source_id,
            name=provider.name,
            url=exec_record.target,
            source_type=step_type.value,
            topics=[step_type.value],
            trust_score=1.0,
            freshness_score=1.0,
        )
        self._source_repository.update_source_metrics(
            source_id=source_id,
            avg_latency_ms=avg_latency_ms,
            success_rate=success_rate,
            last_acquired_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    def _execute_step(
        self, provider: Provider, step: PlanStep, target: str
    ) -> ExecutionRecord:
        """Execute a single provider step."""
        start = time.time()
        request = ProviderRequest(
            target=target,
            provider_type=step.provider_type,
            options=step.options,
        )

        try:
            response = provider.execute(request)
            latency_ms = int((time.time() - start) * 1000)

            if response.error:
                return ExecutionRecord(
                    step_id=step.step_id,
                    provider_name=provider.name,
                    provider_type=step.provider_type.value,
                    target=target,
                    status="failed",
                    latency_ms=latency_ms,
                    error_code=response.error.code,
                    error_message=response.error.message,
                )

            return ExecutionRecord(
                step_id=step.step_id,
                provider_name=provider.name,
                provider_type=step.provider_type.value,
                target=target,
                status="success",
                raw_response={
                    "content": response.content,
                    "content_type": response.content_type,
                    "status_code": response.status_code,
                    "metadata": response.metadata,
                },
                response_metadata=response.metadata,
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            return ExecutionRecord(
                step_id=step.step_id,
                provider_name=provider.name,
                provider_type=step.provider_type.value,
                target=target,
                status="failed",
                latency_ms=latency_ms,
                error_code="EXECUTION_ERROR",
                error_message=str(e),
            )
