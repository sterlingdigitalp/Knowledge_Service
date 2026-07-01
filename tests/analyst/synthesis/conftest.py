"""Shared helpers for Phase 4.1 synthesis tests."""

from __future__ import annotations

from typing import List

from knowledge_service.analyst.claims.extractor import ClaimExtractor
from knowledge_service.analyst.contradiction.detector import ContradictionDetector
from knowledge_service.analyst.cross_source.engine import CrossSourceEngine
from knowledge_service.analyst.importance.engine import ImportanceEngine
from knowledge_service.analyst.models import CorroborationCluster, ScoredClaim
from knowledge_service.analyst.novelty.engine import NoveltyEngine
from knowledge_service.analyst.relevance.engine import RelevanceEngine
from knowledge_service.intelligence.corpus import CorpusManager
from knowledge_service.intelligence.models import EpisodeStatus
from knowledge_service.intelligence.state import FileStateStore


def build_scored_claims_and_clusters(state_dir) -> tuple[List[ScoredClaim], List[CorroborationCluster]]:
    """Score all claims from a phase32 state copy the same way the analyst pipeline does."""
    corpus = CorpusManager(FileStateStore(state_dir))
    profiles = corpus.load_profiles()
    episodes = [
        episode.to_dict()
        for episode in corpus.episodes()
        if episode.status == EpisodeStatus.PROCESSED
    ]
    documents = [obj for obj in corpus.knowledge_objects() if obj.get("type") == "document"]
    claims = ClaimExtractor().extract_from_corpus(documents, episodes, profiles)

    novelty_engine = NoveltyEngine()
    relevance_engine = RelevanceEngine()
    importance_engine = ImportanceEngine()
    contradiction_detector = ContradictionDetector()
    cross_source_engine = CrossSourceEngine()

    clusters = cross_source_engine.build_clusters(claims)
    scored: List[ScoredClaim] = []
    for claim in claims:
        novelty = novelty_engine.score(claim, [c for c in claims if c.claim_id != claim.claim_id])
        relevance = relevance_engine.score(claim, profiles)
        contradictions = contradiction_detector.detect(
            claim,
            novelty,
            [c for c in claims if c.claim_id != claim.claim_id],
        )
        importance = importance_engine.score(claim, novelty, relevance, corroboration_count=0)
        scored.append(
            ScoredClaim(
                claim=claim,
                novelty=novelty,
                relevance=relevance,
                importance=importance,
                contradictions=contradictions,
            )
        )

    scored = cross_source_engine.apply_corroboration(scored, clusters)
    for item in scored:
        if item.corroboration_count:
            item.importance = importance_engine.score(
                item.claim,
                item.novelty,
                item.relevance,
                corroboration_count=item.corroboration_count,
            )
    return scored, clusters