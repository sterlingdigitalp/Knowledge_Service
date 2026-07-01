"""Importance Engine — explainable ranking of intelligence claims."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from ..models import (
    Claim,
    ImportanceBand,
    ImportanceFactors,
    ImportanceResult,
    NoveltyClass,
    NoveltyResult,
    RelevanceResult,
)


WEIGHTS = {
    "novelty": 0.28,
    "source_credibility": 0.12,
    "corroboration": 0.18,
    "potential_impact": 0.12,
    "profile_relevance": 0.18,
    "freshness": 0.07,
    "evidence_quality": 0.05,
}


class ImportanceEngine:
    """Compute explainable importance scores for claims."""

    def score(
        self,
        claim: Claim,
        novelty: NoveltyResult,
        relevance: List[RelevanceResult],
        corroboration_count: int = 0,
    ) -> ImportanceResult:
        factors = ImportanceFactors(
            novelty=_novelty_factor(novelty),
            source_credibility=_source_credibility(claim),
            corroboration=_corroboration_factor(corroboration_count),
            potential_impact=_impact_factor(claim, novelty),
            profile_relevance=_relevance_factor(relevance),
            freshness=_freshness_factor(claim.published_at),
            evidence_quality=_evidence_quality(claim),
        )

        weighted = (
            factors.novelty * WEIGHTS["novelty"]
            + factors.source_credibility * WEIGHTS["source_credibility"]
            + factors.corroboration * WEIGHTS["corroboration"]
            + factors.potential_impact * WEIGHTS["potential_impact"]
            + factors.profile_relevance * WEIGHTS["profile_relevance"]
            + factors.freshness * WEIGHTS["freshness"]
            + factors.evidence_quality * WEIGHTS["evidence_quality"]
        )
        score = round(min(1.0, weighted), 3)
        band = _importance_band(score)

        explanation = (
            f"Importance {band.value.replace('_', ' ')} ({score:.2f}): "
            f"novelty={factors.novelty:.2f}, relevance={factors.profile_relevance:.2f}, "
            f"corroboration={factors.corroboration:.2f}, credibility={factors.source_credibility:.2f}, "
            f"freshness={factors.freshness:.2f}, evidence={factors.evidence_quality:.2f}."
        )

        return ImportanceResult(score=score, band=band, factors=factors, explanation=explanation)


def _novelty_factor(novelty: NoveltyResult) -> float:
    if novelty.classification == NoveltyClass.REPEAT:
        return 0.1
    if novelty.classification == NoveltyClass.CONTRADICTION:
        return max(0.75, novelty.score)
    return novelty.score


def _source_credibility(claim: Claim) -> float:
    if claim.route_confidence is not None:
        return min(1.0, float(claim.route_confidence))
    return 0.65


def _corroboration_factor(count: int) -> float:
    if count <= 0:
        return 0.0
    return min(1.0, 0.35 + count * 0.2)


def _impact_factor(claim: Claim, novelty: NoveltyResult) -> float:
    impact = 0.35
    if claim.entities:
        impact += 0.2
    if novelty.classification in {NoveltyClass.NEW, NoveltyClass.UPDATE, NoveltyClass.CONTRADICTION}:
        impact += 0.25
    if len(claim.claim_text) > 120:
        impact += 0.1
    return min(1.0, impact)


def _relevance_factor(relevance: List[RelevanceResult]) -> float:
    if not relevance:
        return 0.0
    return max(item.score for item in relevance)


def _freshness_factor(published_at: str) -> float:
    if not published_at:
        return 0.5
    try:
        normalized = published_at.replace("Z", "+00:00")
        published = datetime.fromisoformat(normalized)
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - published).days
        if age_days <= 2:
            return 1.0
        if age_days <= 7:
            return 0.8
        if age_days <= 30:
            return 0.55
        return 0.3
    except ValueError:
        return 0.5


def _evidence_quality(claim: Claim) -> float:
    quality = claim.confidence
    if claim.timestamp_start is not None:
        quality += 0.15
    if claim.transcript_reference:
        quality += 0.05
    return min(1.0, quality)


def _importance_band(score: float) -> ImportanceBand:
    if score >= 0.82:
        return ImportanceBand.VERY_HIGH
    if score >= 0.65:
        return ImportanceBand.HIGH
    if score >= 0.45:
        return ImportanceBand.MEDIUM
    if score >= 0.25:
        return ImportanceBand.LOW
    return ImportanceBand.IGNORE