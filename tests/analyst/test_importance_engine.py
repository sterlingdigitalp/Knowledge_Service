from knowledge_service.analyst.importance.engine import ImportanceEngine
from knowledge_service.analyst.models import ImportanceBand, NoveltyClass, NoveltyResult, RelevanceResult

from .conftest import make_claim


def _relevance(score: float = 0.7) -> list[RelevanceResult]:
    return [
        RelevanceResult(
            profile_id="ai",
            profile_name="AI",
            score=score,
            matched_interests=["AI"],
            explanation="Matched interests: AI",
        )
    ]


def test_importance_produces_explainable_factors():
    claim = make_claim(
        "Enterprise AI adoption will accelerate as inference costs fall and datacenter capacity expands."
    )
    novelty = NoveltyResult(
        score=0.9,
        classification=NoveltyClass.NEW,
        explanation="No close semantic match found in historical corpus.",
    )

    result = ImportanceEngine().score(claim, novelty, _relevance())

    assert 0.0 < result.score <= 1.0
    assert result.band in ImportanceBand
    assert result.explanation.startswith("Importance")
    factors = result.factors.to_dict()
    assert set(factors) == {
        "novelty",
        "source_credibility",
        "corroboration",
        "potential_impact",
        "profile_relevance",
        "freshness",
        "evidence_quality",
    }
    assert all(0.0 <= value <= 1.0 for value in factors.values())


def test_importance_increases_with_corroboration():
    claim = make_claim(
        "Enterprise AI adoption will accelerate as inference costs fall and datacenter capacity expands."
    )
    novelty = NoveltyResult(score=0.9, classification=NoveltyClass.NEW, explanation="New claim.")
    engine = ImportanceEngine()

    baseline = engine.score(claim, novelty, _relevance(), corroboration_count=0)
    corroborated = engine.score(claim, novelty, _relevance(), corroboration_count=2)

    assert corroborated.factors.corroboration > baseline.factors.corroboration
    assert corroborated.score >= baseline.score


def test_importance_low_for_repeat_novelty():
    claim = make_claim("Enterprise AI adoption will accelerate as inference costs fall.")
    novelty = NoveltyResult(
        score=0.15,
        classification=NoveltyClass.REPEAT,
        explanation="Highly similar claim already recorded.",
    )

    result = ImportanceEngine().score(claim, novelty, _relevance(score=0.8))

    assert result.factors.novelty <= 0.1
    assert result.score < 0.65