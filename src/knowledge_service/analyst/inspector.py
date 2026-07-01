"""Analyst runtime inspector — Phase 4.1 diagnostics."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from ..intelligence.corpus import CorpusManager
from ..intelligence.state import FileStateStore
from .store import AnalystStore
from .synthesis.store import SynthesisStore


def inspect_analyst_runtime(state_dir: str | Path) -> Dict[str, Any]:
    state = FileStateStore(state_dir)
    corpus = CorpusManager(state)
    store = AnalystStore(state)
    synthesis_store = SynthesisStore(state)

    claims = store.load_claims()
    scored = store.load_scored_claims()
    clusters = store.load_clusters()
    claim_briefs = store.load_briefs()
    runs = store.load_runs()

    themes = synthesis_store.load_themes()
    items = synthesis_store.load_items()
    intel_briefs = synthesis_store.load_briefs()
    theme_history = synthesis_store.load_theme_history()
    synthesis_runs = synthesis_store.load_runs()
    synthesis_summary = synthesis_store.summary(claims_count=len(claims))

    novelty_counts = Counter(item.novelty.classification.value for item in scored)
    importance_counts = Counter(item.importance.band.value for item in scored)
    evolution_counts = Counter(record.state.value for record in theme_history[-len(themes):] if themes)

    latest_intel_brief = intel_briefs[-1] if intel_briefs else None
    latest_run = runs[-1] if runs else None
    latest_synthesis = synthesis_runs[-1] if synthesis_runs else None
    latency = (latest_run or {}).get("result", {}).get("latency_seconds", {})
    synthesis_latency = (latest_synthesis or {}).get("result", {}).get("latency_seconds", {})

    warnings: List[str] = []
    if not claims:
        warnings.append("No claims extracted yet")
    if not themes:
        warnings.append("No themes discovered yet")
    if not items:
        warnings.append("No intelligence items synthesized yet")
    if not intel_briefs:
        warnings.append("No intelligence brief generated yet")
    if latest_intel_brief and latest_intel_brief.reading_time_seconds > 60:
        warnings.append(f"Brief reading time {latest_intel_brief.reading_time_seconds}s exceeds 60s target")

    status = "pass"
    if not claims or not items or not intel_briefs:
        status = "fail"
    if latest_intel_brief and not (5 <= latest_intel_brief.total_items <= 15):
        warnings.append(f"Brief has {latest_intel_brief.total_items} items (target 5-15)")

    return {
        "phase": "4.1",
        "status": status,
        "claims": {
            "total": len(claims),
            "by_speaker": dict(Counter(claim.speaker for claim in claims).most_common(10)),
            "by_topic": dict(Counter(claim.topic for claim in claims).most_common(10)),
            "by_episode": len({claim.episode_id for claim in claims}),
        },
        "novelty": {
            "distribution": dict(novelty_counts),
            "average_score": round(sum(item.novelty.score for item in scored) / len(scored), 4) if scored else 0.0,
        },
        "importance": {
            "distribution": dict(importance_counts),
            "average_score": round(sum(item.importance.score for item in scored) / len(scored), 4) if scored else 0.0,
        },
        "cross_source": {
            "clusters": len(clusters),
            "top_clusters": [cluster.to_dict() for cluster in clusters[:5]],
        },
        "synthesis": {
            **synthesis_summary,
            "theme_labels": [theme.label for theme in themes[:10]],
            "theme_evolution": dict(evolution_counts),
            "item_titles": [item.title for item in items[:10]],
            "evidence_counts": sum(len(item.supporting_evidence) for item in items),
            "contradictions": sum(item.contradiction_count for item in items),
            "corroboration_total": sum(item.corroboration_count for item in items),
        },
        "briefing": {
            "claim_brief_count": len(claim_briefs),
            "intelligence_brief_count": len(intel_briefs),
            "latest_brief_id": latest_intel_brief.brief_id if latest_intel_brief else None,
            "latest_total_items": latest_intel_brief.total_items if latest_intel_brief else 0,
            "reading_time_seconds": latest_intel_brief.reading_time_seconds if latest_intel_brief else 0,
            "compression_ratio": latest_intel_brief.compression_ratio if latest_intel_brief else 0.0,
            "version": latest_intel_brief.version if latest_intel_brief else None,
        },
        "pipeline": {
            "run_count": len(runs),
            "synthesis_run_count": len(synthesis_runs),
            "latest_run_id": latest_run.get("run_id") if latest_run else None,
            "latency_seconds": latency,
            "synthesis_latency_seconds": synthesis_latency,
        },
        "profiles": [
            {"profile_id": profile.profile_id, "name": profile.name, "enabled": profile.enabled}
            for profile in corpus.load_profiles()
        ],
        "warnings": warnings,
        "storage": {
            "state_dir": str(Path(state_dir)),
            "claims_file": str(state.path(store.CLAIMS_FILE)),
            "intelligence_items_file": str(state.path(synthesis_store.ITEMS_FILE)),
            "intelligence_briefs_file": str(state.path(synthesis_store.BRIEFS_FILE)),
        },
    }