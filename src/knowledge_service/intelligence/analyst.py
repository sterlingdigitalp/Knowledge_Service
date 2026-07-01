"""Phase 4 Personal Intelligence Analyst orchestration."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .briefing import MorningBrief, MorningBriefGenerator
from .claims import ClaimExtractor, IntelligenceClaim
from .corpus import CorpusManager
from .correlation import CrossSourceCluster, CrossSourceIntelligenceEngine
from .deep_dive import InteractiveDeepDive, InteractiveDeepDiveGenerator
from .importance import ImportanceEngine, ImportanceResult
from .models import now_iso, stable_id
from .novelty import NoveltyEngine, NoveltyResult
from .relevance import RelevanceEngine, RelevanceResult
from .state import FileStateStore


PHASE4_RUNS_FILE = "phase4_runs.json"
PHASE4_SUMMARY_FILE = "phase4_summary.json"


@dataclass
class Phase4PipelineResult:
    run_id: str
    status: str
    generated_at: str
    elapsed_seconds: float
    profile_count: int
    claim_count: int
    novelty_count: int
    relevance_count: int
    cluster_count: int
    importance_count: int
    brief_id: str
    brief_item_count: int
    deep_dive_count: int
    profile_coverage: Dict[str, int] = field(default_factory=dict)
    top_claim_ids: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "generated_at": self.generated_at,
            "elapsed_seconds": self.elapsed_seconds,
            "profile_count": self.profile_count,
            "claim_count": self.claim_count,
            "novelty_count": self.novelty_count,
            "relevance_count": self.relevance_count,
            "cluster_count": self.cluster_count,
            "importance_count": self.importance_count,
            "brief_id": self.brief_id,
            "brief_item_count": self.brief_item_count,
            "deep_dive_count": self.deep_dive_count,
            "profile_coverage": dict(self.profile_coverage),
            "top_claim_ids": list(self.top_claim_ids),
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Phase4PipelineResult":
        return cls(
            run_id=str(data.get("run_id") or ""),
            status=str(data.get("status") or "fail"),
            generated_at=str(data.get("generated_at") or now_iso()),
            elapsed_seconds=float(data.get("elapsed_seconds", 0.0)),
            profile_count=int(data.get("profile_count", 0)),
            claim_count=int(data.get("claim_count", 0)),
            novelty_count=int(data.get("novelty_count", 0)),
            relevance_count=int(data.get("relevance_count", 0)),
            cluster_count=int(data.get("cluster_count", 0)),
            importance_count=int(data.get("importance_count", 0)),
            brief_id=str(data.get("brief_id") or ""),
            brief_item_count=int(data.get("brief_item_count", 0)),
            deep_dive_count=int(data.get("deep_dive_count", 0)),
            profile_coverage=dict(data.get("profile_coverage") or {}),
            top_claim_ids=list(data.get("top_claim_ids") or []),
            warnings=list(data.get("warnings") or []),
        )


class PersonalIntelligenceAnalyst:
    def __init__(self, state: FileStateStore):
        self.state = state
        self.corpus = CorpusManager(state)

    def run(self, max_items_per_profile: int = 5, max_deep_dives: int = 10) -> Phase4PipelineResult:
        started = time.perf_counter()
        generated_at = now_iso()
        profiles = self.corpus.load_profiles()
        knowledge_objects = self.corpus.knowledge_objects()

        claims = ClaimExtractor(self.state).extract(knowledge_objects)
        novelty = NoveltyEngine(self.state).score(claims)
        relevance = RelevanceEngine(self.state).score(claims, profiles)
        clusters = CrossSourceIntelligenceEngine(self.state).correlate(claims, novelty)
        importance = ImportanceEngine(self.state).score(claims, novelty, relevance, clusters)
        brief = MorningBriefGenerator(self.state).generate(
            profiles=profiles,
            claims=claims,
            novelty=novelty,
            relevance=relevance,
            importance=importance,
            clusters=clusters,
            max_items_per_profile=max_items_per_profile,
        )
        deep_dives = InteractiveDeepDiveGenerator(self.state).generate(
            claims=claims,
            novelty=novelty,
            relevance=relevance,
            importance=importance,
            clusters=clusters,
            max_deep_dives=max_deep_dives,
        )

        warnings = _warnings(profiles, knowledge_objects, claims, relevance, brief, deep_dives)
        profile_coverage = _profile_coverage(relevance)
        top_claim_ids = _top_claim_ids(importance)
        result = Phase4PipelineResult(
            run_id=stable_id("phase4", generated_at, len(claims), len(importance)),
            status="pass" if not warnings else "fail",
            generated_at=generated_at,
            elapsed_seconds=round(time.perf_counter() - started, 6),
            profile_count=len(profiles),
            claim_count=len(claims),
            novelty_count=len(novelty),
            relevance_count=len(relevance),
            cluster_count=len(clusters),
            importance_count=len(importance),
            brief_id=brief.brief_id,
            brief_item_count=brief.item_count,
            deep_dive_count=len(deep_dives),
            profile_coverage=profile_coverage,
            top_claim_ids=top_claim_ids,
            warnings=warnings,
        )
        self._record_run(result, claims, novelty, relevance, clusters, importance, brief, deep_dives)
        return result

    def _record_run(
        self,
        result: Phase4PipelineResult,
        claims: List[IntelligenceClaim],
        novelty: List[NoveltyResult],
        relevance: List[RelevanceResult],
        clusters: List[CrossSourceCluster],
        importance: List[ImportanceResult],
        brief: MorningBrief,
        deep_dives: List[InteractiveDeepDive],
    ) -> None:
        runs = self.state.read_json(PHASE4_RUNS_FILE, [])
        runs.append(result.to_dict())
        self.state.write_json(PHASE4_RUNS_FILE, runs)
        self.state.write_json(PHASE4_SUMMARY_FILE, {
            **result.to_dict(),
            "files": {
                "claims": str(self.state.path("claims.jsonl")),
                "novelty": str(self.state.path("claim_novelty.jsonl")),
                "relevance": str(self.state.path("claim_relevance.jsonl")),
                "correlation": str(self.state.path("cross_source_clusters.jsonl")),
                "importance": str(self.state.path("claim_importance.jsonl")),
                "morning_brief": str(self.state.path("latest_morning_brief.json")),
                "deep_dives": str(self.state.path("latest_deep_dives.json")),
            },
            "claim_evidence_count": sum(1 for claim in claims if claim.evidence and claim.transcript_reference),
            "novelty_labels": _count_by([item.novelty_label for item in novelty]),
            "importance_bands": _count_by([item.importance_band for item in importance]),
            "brief": brief.to_dict(),
            "deep_dive_ids": [dive.deep_dive_id for dive in deep_dives],
            "cluster_ids": [cluster.cluster_id for cluster in clusters],
        })


def run_phase4_pipeline(state_dir: str | Path, max_items_per_profile: int = 5, max_deep_dives: int = 10) -> Phase4PipelineResult:
    return PersonalIntelligenceAnalyst(FileStateStore(state_dir)).run(
        max_items_per_profile=max_items_per_profile,
        max_deep_dives=max_deep_dives,
    )


def _warnings(
    profiles: List[Any],
    knowledge_objects: List[Dict[str, Any]],
    claims: List[IntelligenceClaim],
    relevance: List[RelevanceResult],
    brief: MorningBrief,
    deep_dives: List[InteractiveDeepDive],
) -> List[str]:
    warnings = []
    if not profiles:
        warnings.append("No Intelligence Profiles available for relevance scoring")
    if not knowledge_objects:
        warnings.append("No KnowledgeObjects available for claim extraction")
    if not claims:
        warnings.append("No evidence-backed claims extracted")
    expected_relevance = len(claims) * len(profiles)
    if expected_relevance and len(relevance) != expected_relevance:
        warnings.append(f"Expected {expected_relevance} claim/profile relevance scores, observed {len(relevance)}")
    if claims and brief.item_count == 0:
        warnings.append("Morning Brief contains no surfaced intelligence items")
    if claims and not deep_dives:
        warnings.append("No Interactive Deep Dives generated")
    return warnings


def _profile_coverage(relevance: List[RelevanceResult]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in relevance:
        counts[item.profile_id] = counts.get(item.profile_id, 0) + 1
    return counts


def _top_claim_ids(importance: List[ImportanceResult]) -> List[str]:
    output = []
    seen = set()
    for item in sorted(importance, key=lambda score: score.importance_score, reverse=True):
        if item.claim_id in seen:
            continue
        output.append(item.claim_id)
        seen.add(item.claim_id)
        if len(output) >= 20:
            break
    return output


def _count_by(values: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts
