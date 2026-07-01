"""Intelligence Analyst Pipeline — end-to-end Phase 4 orchestration."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..intelligence.corpus import CorpusManager
from ..intelligence.models import EpisodeStatus, now_iso, stable_id
from ..intelligence.state import FileStateStore
from .briefing.deep_dive import DeepDiveGenerator
from .briefing.morning_brief import MorningBriefGenerator
from .claims.extractor import ClaimExtractor
from .contradiction.detector import ContradictionDetector
from .cross_source.engine import CrossSourceEngine
from .importance.engine import ImportanceEngine
from .models import DeepDiveResponse, MorningBrief, ScoredClaim
from .novelty.engine import NoveltyEngine
from .relevance.engine import RelevanceEngine
from .store import AnalystStore
from .synthesis.models import IntelligenceBrief, IntelligenceDeepDive
from .synthesis.pipeline import IntelligenceSynthesisPipeline, SynthesisResult


@dataclass
class PipelineResult:
    run_id: str
    claims_extracted: int = 0
    claims_scored: int = 0
    clusters_found: int = 0
    contradictions_found: int = 0
    brief: Optional[MorningBrief] = None
    synthesis: Optional[SynthesisResult] = None
    intelligence_brief: Optional[IntelligenceBrief] = None
    latency_seconds: Dict[str, float] = field(default_factory=dict)
    status: str = "completed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "claims_extracted": self.claims_extracted,
            "claims_scored": self.claims_scored,
            "clusters_found": self.clusters_found,
            "contradictions_found": self.contradictions_found,
            "brief": self.brief.to_dict() if self.brief else None,
            "synthesis": self.synthesis.to_dict() if self.synthesis else None,
            "intelligence_brief": self.intelligence_brief.to_dict() if self.intelligence_brief else None,
            "latency_seconds": dict(self.latency_seconds),
            "status": self.status,
        }


class IntelligenceAnalystPipeline:
    """Run the full intelligence pipeline over an existing acquisition corpus."""

    def __init__(self, state_dir: str):
        self.state = FileStateStore(state_dir)
        self.corpus = CorpusManager(self.state)
        self.store = AnalystStore(self.state)
        self.extractor = ClaimExtractor()
        self.novelty_engine = NoveltyEngine()
        self.relevance_engine = RelevanceEngine()
        self.importance_engine = ImportanceEngine()
        self.cross_source_engine = CrossSourceEngine()
        self.contradiction_detector = ContradictionDetector()
        self.brief_generator = MorningBriefGenerator()
        self.deep_dive_generator = DeepDiveGenerator()
        self.synthesis_pipeline = IntelligenceSynthesisPipeline(state_dir)

    def run(self, episode_ids: Optional[List[str]] = None) -> PipelineResult:
        started = time.perf_counter()
        run_id = stable_id("analyst-run", now_iso())
        result = PipelineResult(run_id=run_id)

        profiles = self.corpus.load_profiles()
        episodes = [episode.to_dict() for episode in self.corpus.episodes() if episode.status == EpisodeStatus.PROCESSED]
        if episode_ids:
            allowed = set(episode_ids)
            episodes = [episode for episode in episodes if episode.get("episode_id") in allowed]

        knowledge_objects = self.corpus.knowledge_objects()
        extract_started = time.perf_counter()
        new_claims = self.extractor.extract_from_corpus(knowledge_objects, episodes, profiles)
        result.latency_seconds["claim_extraction"] = round(time.perf_counter() - extract_started, 3)
        result.claims_extracted = len(new_claims)

        historical = self.store.load_claims()
        historical_ids = {claim.claim_id for claim in historical}
        unique_new_claims = []
        seen_new_ids: set[str] = set()
        for claim in new_claims:
            if claim.claim_id in historical_ids or claim.claim_id in seen_new_ids:
                continue
            unique_new_claims.append(claim)
            seen_new_ids.add(claim.claim_id)
        claims_to_score = unique_new_claims
        self.store.append_claims(unique_new_claims)
        all_claims = self.store.load_claims()
        result.claims_extracted = len(unique_new_claims)

        score_started = time.perf_counter()
        scored_claims: List[ScoredClaim] = []
        for claim in claims_to_score:
            novelty = self.novelty_engine.score(claim, [c for c in all_claims if c.claim_id != claim.claim_id])
            relevance = self.relevance_engine.score(claim, profiles)
            contradictions = self.contradiction_detector.detect(
                claim,
                novelty,
                [c for c in all_claims if c.claim_id != claim.claim_id],
            )
            importance = self.importance_engine.score(claim, novelty, relevance, corroboration_count=0)
            scored_claims.append(ScoredClaim(
                claim=claim,
                novelty=novelty,
                relevance=relevance,
                importance=importance,
                contradictions=contradictions,
            ))
        result.latency_seconds["scoring"] = round(time.perf_counter() - score_started, 3)
        result.claims_scored = len(scored_claims)

        cluster_started = time.perf_counter()
        clusters = self.cross_source_engine.build_clusters(all_claims)
        scored_claims = self.cross_source_engine.apply_corroboration(scored_claims, clusters)
        for item in scored_claims:
            if item.corroboration_count:
                item.importance = self.importance_engine.score(
                    item.claim,
                    item.novelty,
                    item.relevance,
                    corroboration_count=item.corroboration_count,
                )
        self.store.save_clusters(clusters)
        result.latency_seconds["cross_source"] = round(time.perf_counter() - cluster_started, 3)
        result.clusters_found = len(clusters)

        existing_scored = self.store.load_scored_claims()
        merged_by_id = {item.claim.claim_id: item for item in existing_scored}
        for item in scored_claims:
            merged_by_id[item.claim.claim_id] = item
        merged_scored = list(merged_by_id.values())
        self.store.save_scored_claims(merged_scored)
        result.contradictions_found = sum(len(item.contradictions) for item in scored_claims)

        brief_started = time.perf_counter()
        brief = self.brief_generator.generate(merged_scored, profiles, pipeline_run_id=run_id)
        self.store.save_brief(brief)
        result.brief = brief
        result.latency_seconds["claim_brief_generation"] = round(time.perf_counter() - brief_started, 3)

        synthesis_started = time.perf_counter()
        synthesis = self.synthesis_pipeline.run(merged_scored, clusters, pipeline_run_id=run_id)
        result.synthesis = synthesis
        result.intelligence_brief = synthesis.brief
        result.latency_seconds["synthesis"] = round(time.perf_counter() - synthesis_started, 3)
        result.latency_seconds["total"] = round(time.perf_counter() - started, 3)

        self.store.record_run({
            "run_id": run_id,
            "started_at": now_iso(),
            "result": result.to_dict(),
        })
        return result

    def deep_dive(self, claim_id: str) -> Optional[DeepDiveResponse]:
        scored = self.store.load_scored_claims()
        claims = self.store.load_claims()
        return self.deep_dive_generator.generate(claim_id, scored, claims)

    def intelligence_deep_dive(self, intelligence_item_id: str) -> Optional[IntelligenceDeepDive]:
        scored = self.store.load_scored_claims()
        claims = self.store.load_claims()
        return self.synthesis_pipeline.deep_dive(intelligence_item_id, scored, claims)

    @classmethod
    def run_on_state(cls, state_dir: str) -> PipelineResult:
        return cls(state_dir).run()