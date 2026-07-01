"""Runtime inspection — permanent engineering console for acquisition health."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List
import importlib.util
import shutil

from ..analyst.inspector import inspect_analyst_runtime
from .analyst import PHASE4_RUNS_FILE, PHASE4_SUMMARY_FILE
from .briefing import LATEST_MORNING_BRIEF_FILE, MORNING_BRIEFS_FILE
from .claims import CLAIMS_FILE
from .corpus import CorpusManager
from .corpus_audit import audit_corpus
from .correlation import CORRELATION_FILE
from .deep_dive import DEEP_DIVES_FILE, LATEST_DEEP_DIVES_FILE
from .dedupe import DeduplicationStore
from .importance import IMPORTANCE_FILE
from .models import EpisodeStatus
from .novelty import NOVELTY_FILE
from .recertification import RouteRecertificationService
from .relevance import RELEVANCE_FILE
from .route_confidence import RouteConfidenceEngine
from .route_registry import AcquisitionRouteRegistry
from .state import FileStateStore


def inspect_intelligence_runtime(state_dir: str | Path) -> Dict[str, Any]:
    state = FileStateStore(state_dir)
    corpus = CorpusManager(state)
    dedupe = DeduplicationStore(state)
    route_registry = AcquisitionRouteRegistry(state)
    confidence_engine = RouteConfidenceEngine()
    profiles = corpus.load_profiles()
    episodes = corpus.episodes()
    information_events = corpus.information_events()
    jobs = state.read_json("jobs.json", [])
    scheduler = state.read_json("scheduler.json", {"status": "idle", "jobs": []})
    discovery_runs = state.read_json("discovery_runs.json", [])
    certification_history = state.read_json(RouteRecertificationService.HISTORY_FILE, [])
    corpus_summary = corpus.summary()
    status_counts = Counter(episode.status.value if isinstance(episode.status, EpisodeStatus) else episode.status for episode in episodes)
    enabled_profiles = [profile for profile in profiles if profile.enabled]
    failures = [episode.to_dict() for episode in episodes if episode.status == EpisodeStatus.FAILED]
    warnings: List[str] = []
    if not profiles:
        warnings.append("No intelligence profiles configured")
    if route_registry.summary()["source_count"] == 0:
        warnings.append("Acquisition route registry is empty")

    episode_metrics = [
        {"source_id": e.source_id, "acquisition_route": e.acquisition_route, "route_confidence": e.route_confidence}
        for e in episodes if e.acquisition_route
    ]
    route_registry.refresh_all_confidence(episode_metrics)

    recert_due = []
    for entry in route_registry.entries():
        if confidence_engine.is_recertification_due(entry):
            recert_due.append(entry.source_id)

    recent_events = sorted(information_events, key=lambda item: item.get("discovered_at") or "", reverse=True)[:20]
    route_diagnostics = _route_diagnostics(route_registry, episodes)
    corpus_integrity = audit_corpus(state)
    if corpus_integrity["issue_count"]:
        warnings.append(f"Corpus audit found {corpus_integrity['issue_count']} issues")
    phase4 = _phase4_intelligence_summary(state, profiles)
    if phase4["artifacts_present"] and phase4["status"] != "pass":
        warnings.extend([f"Phase 4: {warning}" for warning in phase4["warnings"]])

    discoverers = []
    if discovery_runs:
        discoverers = discovery_runs[-1].get("discoverers", ["podcast"])

    job_performance = [
        {"job_id": j.get("job_id"), "total_seconds": (j.get("performance") or {}).get("total_seconds"), "processed": j.get("processed_count")}
        for j in jobs[-10:]
    ]

    analyst = inspect_analyst_runtime(state_dir)
    from ..production.inspector import inspect_production_runtime
    production = inspect_production_runtime(state_dir)

    return {
        "phase": "5.1.2",
        "system_summary": {
            "status": "pass" if enabled_profiles and not failures and corpus_integrity["status"] == "pass" else "fail",
            "profile_count": len(profiles),
            "enabled_profiles": len(enabled_profiles),
            "episodes": len(episodes),
            "information_events": len(information_events),
            "processed_episodes": status_counts.get(EpisodeStatus.PROCESSED.value, 0),
            "failed_episodes": status_counts.get(EpisodeStatus.FAILED.value, 0),
            "knowledge_objects": corpus_summary["knowledge_objects"],
            "chunks": corpus_summary["chunks"],
            "embeddings": corpus_summary["embeddings"],
            "certified_sources": route_registry.summary()["certified_sources"],
            "corpus_integrity": corpus_integrity["status"],
            "phase4_status": phase4["status"],
            "claims": phase4["claims"]["total"],
            "brief_items": phase4["brief_generation"]["item_count"],
            "deep_dives": phase4["deep_dives"]["total"],
        },
        "route_registry": {
            **route_registry.summary(),
            "recertification_due": recert_due,
            "certification_history_count": len(certification_history),
        },
        "information_events": {
            "total": len(information_events),
            "recent": recent_events,
            "by_status": dict(status_counts),
            "with_acquisition_route": sum(1 for event in information_events if event.get("acquisition_route")),
            "participants": _participant_index(information_events),
        },
        "discovery": {
            "mode": "person_centric",
            "discoverers": discoverers,
            "run_count": len(discovery_runs),
            "latest_run": discovery_runs[-1] if discovery_runs else None,
            "episodes_found": sum(run.get("episodes_found", 0) for run in discovery_runs),
            "information_events_found": sum(run.get("information_events_found", run.get("episodes_found", 0)) for run in discovery_runs),
            "new_events": status_counts.get(EpisodeStatus.DISCOVERED.value, 0) + status_counts.get(EpisodeStatus.QUEUED.value, 0),
            "already_processed": sum(run.get("duplicates", 0) for run in discovery_runs),
            "duplicates": status_counts.get(EpisodeStatus.DUPLICATE.value, 0),
            "skipped": status_counts.get(EpisodeStatus.SKIPPED.value, 0),
            "failed": status_counts.get(EpisodeStatus.FAILED.value, 0),
            "pending": status_counts.get(EpisodeStatus.QUEUED.value, 0),
            "queued": status_counts.get(EpisodeStatus.QUEUED.value, 0),
        },
        "corpus": {
            **corpus_summary,
            "integrity": corpus_integrity,
            "growth_history_count": len(corpus_summary.get("growth_history", [])),
        },
        "personal_intelligence": phase4,
        "runtime": {
            "scheduler": scheduler,
            "jobs": jobs,
            "current_jobs": [job for job in jobs if job.get("status") in {"queued", "running"}],
            "queue": {
                "queued_episodes": status_counts.get(EpisodeStatus.QUEUED.value, 0),
                "failed_episodes": status_counts.get(EpisodeStatus.FAILED.value, 0),
            },
            "performance": job_performance,
            "errors": failures,
            "warnings": warnings,
        },
        "diagnostics": {
            **route_diagnostics,
            "provider_health": _provider_health(),
            "recertification": {
                "due_sources": recert_due,
                "interval_days": 30,
                "history_entries": len(certification_history),
            },
            "registry_recommendations": _registry_recommendations(route_registry),
        },
        "profiles": [
            {
                "profile_id": profile.profile_id,
                "name": profile.name,
                "enabled": profile.enabled,
                "interest_count": len(profile.interests),
                "watch_list_size": len(profile.watch_list),
                "required_podcasts": len(profile.required_podcasts),
                "optional_podcasts": len(profile.optional_podcasts),
            }
            for profile in profiles
        ],
        "sources": {
            "people": [graph.to_dict() for graph in corpus.source_graphs()],
            "podcasts": corpus_summary["sources"],
        },
        "deduplication": dedupe.summary(),
        "storage": {
            "state_dir": str(Path(state_dir)),
            "route_registry_file": str(state.path(route_registry.STATE_FILE)),
            "information_events_file": str(state.path("information_events.json")),
            "certification_history_file": str(state.path(RouteRecertificationService.HISTORY_FILE)),
            "phase4_summary_file": str(state.path(PHASE4_SUMMARY_FILE)),
            "latest_morning_brief_file": str(state.path(LATEST_MORNING_BRIEF_FILE)),
            "latest_deep_dives_file": str(state.path(LATEST_DEEP_DIVES_FILE)),
        },
        "analyst": analyst,
        "production": production,
    }


def _participant_index(events: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for event in events:
        for person in event.get("participants") or event.get("matched_watch_entries") or []:
            counts[person] = counts.get(person, 0) + 1
    return counts


def _route_diagnostics(route_registry: AcquisitionRouteRegistry, episodes: List[Any]) -> Dict[str, Any]:
    diagnostics = route_registry.diagnostics()
    route_stats = diagnostics.get("route_stats", {})
    for route, bucket in route_stats.items():
        attempts = bucket.get("success", 0) + bucket.get("failure", 0)
        bucket["success_rate"] = round(bucket.get("success", 0) / attempts, 4) if attempts else 0.0
        bucket["failure_rate"] = round(bucket.get("failure", 0) / attempts, 4) if attempts else 0.0
        if attempts:
            bucket["average_runtime_seconds"] = round(bucket.get("total_runtime_seconds", 0.0) / attempts, 4)

    route_failures = []
    for entry in route_registry.entries():
        for route, stats in entry.route_statistics.items():
            if stats.get("failures", 0) > 0:
                route_failures.append({
                    "source_id": entry.source_id,
                    "route": route,
                    "failures": stats.get("failures"),
                    "last_error": stats.get("last_error"),
                })

    warnings = []
    for source in route_registry.summary()["sources"]:
        if source.get("certification_status") != "certified":
            warnings.append(f"Source {source['source_id']} is not certified")
        if source.get("route_confidence") is not None and source["route_confidence"] < 0.5:
            warnings.append(f"Source {source['source_id']} has low route confidence")

    return {
        "per_route_statistics": route_stats,
        "route_failures": route_failures,
        "recent_selections": diagnostics.get("selections", [])[-20:],
        "warnings": warnings,
    }


def _provider_health() -> Dict[str, Any]:
    return {
        "published_transcript": {"available": importlib.util.find_spec("httpx") is not None},
        "youtube_captions": {"available": importlib.util.find_spec("youtube_transcript_api") is not None},
        "whisper_fallback": {"available": importlib.util.find_spec("whisper") is not None, "ffmpeg": shutil.which("ffmpeg")},
        "yt_dlp": {"available": importlib.util.find_spec("yt_dlp") is not None},
    }


def _registry_recommendations(route_registry: AcquisitionRouteRegistry) -> List[Dict[str, Any]]:
    recs = []
    for entry in route_registry.entries():
        for rec in (entry.recommendations or [])[-3:]:
            recs.append({**rec, "source_id": entry.source_id})
    return recs


def _phase4_intelligence_summary(state: FileStateStore, profiles: List[Any]) -> Dict[str, Any]:
    claims = state.read_jsonl(CLAIMS_FILE)
    novelty = state.read_jsonl(NOVELTY_FILE)
    relevance = state.read_jsonl(RELEVANCE_FILE)
    clusters = state.read_jsonl(CORRELATION_FILE)
    importance = state.read_jsonl(IMPORTANCE_FILE)
    latest_brief = state.read_json(LATEST_MORNING_BRIEF_FILE, None)
    brief_history = state.read_jsonl(MORNING_BRIEFS_FILE)
    latest_dives = state.read_json(LATEST_DEEP_DIVES_FILE, {"deep_dives": []})
    deep_dive_rows = state.read_jsonl(DEEP_DIVES_FILE)
    runs = state.read_json(PHASE4_RUNS_FILE, [])
    phase4_summary = state.read_json(PHASE4_SUMMARY_FILE, None)
    artifacts_present = any([claims, novelty, relevance, clusters, importance, latest_brief, deep_dive_rows, runs, phase4_summary])

    profile_ids = [profile.profile_id for profile in profiles]
    expected_relevance = len(claims) * len(profile_ids)
    profile_coverage = Counter(item.get("profile_id") for item in relevance if item.get("profile_id"))
    all_profiles_evaluated = expected_relevance > 0 and len(relevance) == expected_relevance
    evidence_backed_claims = sum(1 for claim in claims if claim.get("evidence", {}).get("quote") and claim.get("transcript_reference"))
    brief_items = _brief_items(latest_brief)
    brief_explainable = all(
        item.get("what_is_new") and item.get("why_user_cares") and item.get("why_it_matters") and item.get("where_evidence_is")
        for item in brief_items
    ) if brief_items else False
    dives = latest_dives.get("deep_dives", []) if isinstance(latest_dives, dict) else []
    warnings = []
    if artifacts_present:
        if not claims:
            warnings.append("No claims extracted")
        if claims and evidence_backed_claims != len(claims):
            warnings.append("Some claims are missing quote or transcript evidence")
        if expected_relevance and len(relevance) != expected_relevance:
            warnings.append(f"Expected {expected_relevance} claim/profile relevance scores, observed {len(relevance)}")
        if latest_brief and not brief_items:
            warnings.append("Latest Morning Brief has no surfaced items")
        if latest_brief and not brief_explainable:
            warnings.append("Latest Morning Brief items are missing required explanations")
        if claims and not dives:
            warnings.append("No Interactive Deep Dives generated")

    last_run = runs[-1] if runs else None
    status = "not_run"
    if artifacts_present:
        status = "pass" if not warnings and all_profiles_evaluated and bool(brief_items) and bool(dives) else "fail"
    return {
        "status": status,
        "artifacts_present": artifacts_present,
        "claims": {
            "total": len(claims),
            "evidence_backed": evidence_backed_claims,
            "topics": dict(Counter(claim.get("topic") or "general" for claim in claims)),
            "sources": dict(Counter(claim.get("source_id") or claim.get("source_name") or "unknown" for claim in claims)),
        },
        "novelty": {
            "total": len(novelty),
            "labels": dict(Counter(item.get("novelty_label") or "unknown" for item in novelty)),
        },
        "relevance": {
            "total": len(relevance),
            "expected_total": expected_relevance,
            "all_profiles_evaluated": all_profiles_evaluated,
            "profile_coverage": dict(profile_coverage),
        },
        "importance": {
            "total": len(importance),
            "bands": dict(Counter(item.get("importance_band") or "low" for item in importance)),
            "top": _top_importance(importance),
        },
        "cross_source": {
            "clusters": len(clusters),
            "corroborated_clusters": sum(1 for cluster in clusters if cluster.get("corroboration_count", 0) > 0),
            "contradiction_candidates": sum(len(cluster.get("contradictions") or []) for cluster in clusters),
        },
        "brief_generation": {
            "history_count": len(brief_history),
            "latest_brief_id": latest_brief.get("brief_id") if latest_brief else None,
            "item_count": latest_brief.get("item_count", 0) if latest_brief else 0,
            "section_count": len(latest_brief.get("sections", [])) if latest_brief else 0,
            "estimated_read_seconds": latest_brief.get("estimated_read_seconds") if latest_brief else None,
            "required_explanations_present": brief_explainable,
        },
        "deep_dives": {
            "total": len(dives),
            "persisted_rows": len(deep_dive_rows),
            "with_context": sum(1 for dive in dives if dive.get("surrounding_context")),
            "with_evidence_trail": sum(1 for dive in dives if dive.get("evidence_trail")),
            "latest_ids": [dive.get("deep_dive_id") for dive in dives[:10]],
        },
        "latency": {
            "last_run_seconds": last_run.get("elapsed_seconds") if last_run else None,
            "run_count": len(runs),
        },
        "warnings": warnings,
    }


def _brief_items(latest_brief: Any) -> List[Dict[str, Any]]:
    if not latest_brief:
        return []
    output = []
    for section in latest_brief.get("sections", []):
        output.extend(section.get("items") or [])
    return output


def _top_importance(importance: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "claim_id": item.get("claim_id"),
            "profile_id": item.get("profile_id"),
            "importance_score": item.get("importance_score"),
            "importance_band": item.get("importance_band"),
        }
        for item in sorted(importance, key=lambda row: row.get("importance_score", 0.0), reverse=True)[:20]
    ]
