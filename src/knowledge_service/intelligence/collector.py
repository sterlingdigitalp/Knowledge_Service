"""Profile-driven intelligence collection orchestration."""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional

from ..acquisition.acquisition_bundle import AcquisitionBundle, DocumentRecord, ExecutionRecord
from ..interfaces.provider import ProviderRequest, ProviderType
from ..processing.pipeline import Pipeline
from ..providers.transcript_provider import TranscriptProvider
from .config import load_profiles
from .corpus import CorpusManager
from .dedupe import DeduplicationStore
from .discovery import DiscoveryEngine, DiscoveryResult
from .migration import migrate_corpus_state
from .models import CollectionJob, DiscoveredEpisode, EpisodeStatus, IntelligenceProfile, JobStatus, now_iso, stable_id
from .recertification import RouteRecertificationService
from .route_confidence import RouteConfidenceEngine
from .route_registry import AcquisitionRouteRegistry, RouteSelection
from .state import FileStateStore


class IntelligenceCollector:
    """Runs discovery, deduplication, acquisition, processing, and corpus updates."""

    def __init__(
        self,
        state_dir: str,
        profiles: Optional[List[IntelligenceProfile]] = None,
        profile_config_path: Optional[str] = None,
        provider: Optional[TranscriptProvider] = None,
        route_registry: Optional[AcquisitionRouteRegistry] = None,
        route_config_path: Optional[str] = None,
        timeout_ms: int = 30000,
    ):
        self.state = FileStateStore(state_dir)
        self.corpus = CorpusManager(self.state)
        if profile_config_path:
            profiles = load_profiles(profile_config_path)
        self.profiles = profiles if profiles is not None else self.corpus.load_profiles()
        self.corpus.save_profiles(self.profiles)
        self.dedupe = DeduplicationStore(self.state)
        self.route_registry = route_registry or AcquisitionRouteRegistry(self.state, config_path=route_config_path)
        self.discovery = DiscoveryEngine(
            self.state,
            self.dedupe,
            route_registry=self.route_registry,
            timeout_seconds=timeout_ms / 1000.0,
        )
        self.provider = provider or TranscriptProvider("intelligence-transcript-provider")
        self.provider.initialize({"timeout_ms": timeout_ms})
        self.timeout_ms = timeout_ms
        migrate_corpus_state(self.state, self.route_registry)
        self._bootstrap_registry_metrics()

    def _bootstrap_registry_metrics(self) -> None:
        episode_metrics = [
            {
                "source_id": e.source_id,
                "acquisition_route": e.acquisition_route,
                "route_confidence": e.route_confidence,
            }
            for e in self.corpus.episodes()
            if e.acquisition_route
        ]
        self.route_registry.refresh_all_confidence(episode_metrics)
        recert = RouteRecertificationService(self.route_registry, self.provider, timeout_ms=self.timeout_ms)
        recert.run_if_due()

    def run_once(self, profile_ids: Optional[Iterable[str]] = None, mode: str = "manual") -> CollectionJob:
        selected_profiles = self._selected_profiles(profile_ids)
        job = CollectionJob(job_id=stable_id("job", mode, now_iso()), mode=mode, profile_ids=[p.profile_id for p in selected_profiles])
        started = time.perf_counter()
        self._save_job(job)
        job.status = JobStatus.RUNNING
        job.started_at = now_iso()
        try:
            job.current_step = "discovery"
            self._save_job(job)
            discovery_results = self.discovery.discover(selected_profiles)
            all_episodes = [episode for result in discovery_results for episode in result.episodes]
            self.corpus.record_discovered_episodes(all_episodes)
            job.discovered_count = sum(result.found_count for result in discovery_results)
            job.queued_count = sum(1 for episode in all_episodes if episode.status == EpisodeStatus.QUEUED)
            job.duplicate_count = sum(1 for episode in all_episodes if episode.status == EpisodeStatus.DUPLICATE)
            job.skipped_count = sum(1 for episode in all_episodes if episode.status == EpisodeStatus.SKIPPED)

            job.current_step = "acquisition"
            self._save_job(job)
            queued = [item for item in all_episodes if item.status == EpisodeStatus.QUEUED]
            for index, episode in enumerate(queued):
                if index > 0:
                    time.sleep(float(self.state.read_json("collector_config.json", {}).get("acquisition_delay_seconds", 0)))
                self._process_episode(episode, job)
            job.current_step = "complete"
            job.status = JobStatus.COMPLETED if job.failed_count == 0 else JobStatus.PARTIAL
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.errors.append(str(exc))
        job.completed_at = now_iso()
        job.performance["total_seconds"] = round(time.perf_counter() - started, 6)
        self._save_job(job)
        return job

    def _process_episode(self, episode: DiscoveredEpisode, job: CollectionJob) -> None:
        started = time.perf_counter()
        source_id = episode.source_id or self.route_registry.resolve_source_id(
            podcast_name=episode.podcast_name,
            url=episode.url,
        )
        episode.source_id = source_id
        selection = self.route_registry.select_route(source_id, episode.url)
        metadata = {
            "profile_id": episode.profile_id,
            "episode_id": episode.episode_id,
            "event_id": episode.episode_id,
            "transcript_id": episode.episode_id,
            "source_url": episode.url,
            "source_id": source_id,
            "show": episode.podcast_name,
            "venue": episode.podcast_name,
            "episode": episode.title,
            "episode_date": episode.episode_date,
            "matched_watch_entries": episode.matched_watch_entries,
            "participants": episode.matched_watch_entries,
            "matched_interests": episode.matched_interests,
        }
        response, selection = self._acquire_with_route_chain(episode.url, selection, metadata)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        episode.route_selection_reason = list(selection.reason)
        episode.fallback_routes_attempted = [
            attempt["route"] for attempt in selection.route_attempts if attempt.get("route") != selection.selected_route
        ]
        if response.error:
            self.route_registry.record_selection(selection)
            self.corpus.record_failed_episode(episode, f"{response.error.code}: {response.error.message}")
            job.failed_count += 1
            job.errors.append(f"{episode.title}: {response.error.code}")
            return
        transcript = response.content or ""
        episode.acquisition_route = selection.selected_route or (response.metadata or {}).get("acquisition_route")
        entry = self.route_registry.get(source_id)
        computed_confidence = entry.route_confidence if entry and entry.route_confidence is not None else selection.transcript_confidence
        episode.route_confidence = computed_confidence
        episode.transcript_provenance = {
            "acquisition_route": episode.acquisition_route,
            "route_confidence": episode.route_confidence,
            "route_selection_reason": episode.route_selection_reason,
            "fallback_routes_attempted": episode.fallback_routes_attempted,
            "provider": self.provider.name,
            "transcript_source": (response.metadata or {}).get("transcript_source"),
            "source_id": source_id,
        }
        self.route_registry.record_selection(selection)
        transcript_hash, duplicate_of = self.dedupe.register_acquisition(episode, transcript)
        episode.transcript_hash = transcript_hash
        if duplicate_of:
            self.corpus.record_duplicate_episode(episode, duplicate_of)
            job.duplicate_count += 1
            return
        bundle = AcquisitionBundle(
            request_id=f"intelligence-{episode.episode_id}",
            plan_id=f"profile-{episode.profile_id}",
            acquisition_timestamp=now_iso(),
        )
        response_metadata = dict(response.metadata or {})
        response_metadata.update(episode.transcript_provenance)
        bundle.add_execution_record(ExecutionRecord(
            step_id=episode.episode_id,
            provider_name=self.provider.name,
            provider_type="api",
            target=episode.url,
            status="success",
            response_metadata=response_metadata,
            latency_ms=elapsed_ms,
        ))
        bundle.add_document(DocumentRecord(
            document_id=episode.episode_id,
            url=episode.url,
            provider_name=self.provider.name,
            content_type=response.content_type,
            raw_content=transcript,
            content_size_bytes=len(transcript.encode("utf-8")),
            acquired_at=now_iso(),
            metadata=response_metadata,
            source_type="video_transcript",
        ))
        knowledge_objects = Pipeline().process(bundle)
        self.corpus.record_processed_episode(episode, knowledge_objects)
        job.processed_count += 1

    def _selected_profiles(self, profile_ids: Optional[Iterable[str]]) -> List[IntelligenceProfile]:
        ids = set(profile_ids or [])
        profiles = [profile for profile in self.profiles if profile.enabled]
        return [profile for profile in profiles if not ids or profile.profile_id in ids]

    def _save_job(self, job: CollectionJob) -> None:
        jobs = {item["job_id"]: CollectionJob.from_dict(item) for item in self.state.read_json("jobs.json", [])}
        jobs[job.job_id] = job
        self.state.write_json("jobs.json", [item.to_dict() for item in jobs.values()])

    def jobs(self) -> List[CollectionJob]:
        return [CollectionJob.from_dict(item) for item in self.state.read_json("jobs.json", [])]

    def _acquire_with_route_chain(
        self,
        target: str,
        selection: RouteSelection,
        metadata: Dict[str, Any],
    ):
        from ..interfaces.provider import ProviderResponse

        last_response = ProviderResponse(error=None)
        max_retries = 3
        for route in selection.fallback_chain:
            route_started = time.perf_counter()
            options = self.route_registry.provider_options_for_route(route, {
                "timeout_ms": self.timeout_ms,
                "metadata": metadata,
            })
            response = last_response
            for retry in range(max_retries):
                response = self.provider.execute(ProviderRequest(
                    target=target,
                    provider_type=ProviderType.API,
                    options=options,
                ))
                if response.error is None or not getattr(response.error, "retryable", False):
                    break
                time.sleep(0.5 * (retry + 1))
            elapsed = round(time.perf_counter() - route_started, 6)
            success = response.error is None and bool((response.content or "").strip())
            attempt = {
                "route": route,
                "success": success,
                "runtime_seconds": elapsed,
                "error": None if success else (response.error.message if response.error else "empty transcript"),
            }
            selection.route_attempts.append(attempt)
            self.route_registry.record_route_attempt(
                selection.source_id,
                route,
                success=success,
                runtime_seconds=elapsed,
                transcript_length=len(response.content or ""),
                error=attempt["error"],
            )
            if success:
                selection.selected_route = route
                if response.metadata is not None:
                    response.metadata["acquisition_route"] = route
                return response, selection
            last_response = response
        selection.selection_rationale = "all_routes_failed"
        return last_response, selection

    def runtime_state(self) -> Dict[str, Any]:
        jobs = self.jobs()
        return {
            "profiles": [profile.to_dict() for profile in self.profiles],
            "jobs": [job.to_dict() for job in jobs],
            "dedupe": self.dedupe.summary(),
            "corpus": self.corpus.summary(),
            "route_registry": self.route_registry.summary(),
            "latest_job": jobs[-1].to_dict() if jobs else None,
        }
