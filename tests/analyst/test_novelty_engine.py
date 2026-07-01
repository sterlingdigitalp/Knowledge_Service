from knowledge_service.analyst.models import NoveltyClass
from knowledge_service.analyst.novelty.engine import NoveltyEngine
from knowledge_service.retrieval.embedding import embed_text

from .conftest import make_claim


def test_novelty_classifies_new_without_historical_match():
    claim = make_claim(
        "Enterprise AI adoption will accelerate as inference costs continue to fall across the industry."
    )
    result = NoveltyEngine().score(claim, [])

    assert result.classification == NoveltyClass.NEW
    assert result.score == 1.0
    assert "No close semantic match" in result.explanation


def test_novelty_classifies_repeat_for_identical_cross_episode_claim():
    text = (
        "Large language model scaling laws continue to drive datacenter buildouts and enterprise AI adoption."
    )
    prior = make_claim(text, episode_id="episode-a", podcast_name="Dwarkesh Podcast")
    current = make_claim(text, episode_id="episode-b", podcast_name="All-In Podcast")
    prior.embedding = embed_text(text)
    current.embedding = embed_text(text)

    result = NoveltyEngine().score(current, [prior])

    assert result.classification == NoveltyClass.REPEAT
    assert result.prior_claim_id == prior.claim_id
    assert result.prior_similarity is not None
    assert result.prior_similarity >= 0.82


def test_novelty_classifies_refinement_for_related_claim():
    prior = make_claim(
        "Enterprise AI adoption is accelerating because inference costs are falling across major cloud providers."
    )
    current = make_claim(
        "Enterprise AI adoption is accelerating because inference costs are falling and agent workflows are maturing.",
        episode_id="episode-b",
    )

    result = NoveltyEngine().score(current, [prior])

    assert result.classification in {NoveltyClass.REFINEMENT, NoveltyClass.UPDATE}
    assert result.prior_claim_id == prior.claim_id
    assert 0.0 < result.score < 1.0


def test_novelty_classifies_contradiction_for_conflicting_claim():
    base = "Markets will increase through the second half of the year as enterprise AI spending grows."
    prior = make_claim(base, episode_id="episode-a")
    current = make_claim(
        "Markets will decrease through the second half of the year as enterprise AI spending grows.",
        episode_id="episode-b",
    )
    prior.embedding = embed_text(base)
    current.embedding = embed_text(current.claim_text)

    result = NoveltyEngine().score(current, [prior])

    assert result.classification == NoveltyClass.CONTRADICTION
    assert result.prior_claim_id == prior.claim_id
    assert result.evidence


def test_novelty_ignores_same_episode_history():
    text = "AI datacenter buildouts will continue to accelerate through 2027 across major cloud providers."
    claim = make_claim(text, episode_id="shared-episode")
    duplicate = make_claim(text, episode_id="shared-episode")

    result = NoveltyEngine().score(duplicate, [claim])

    assert result.classification == NoveltyClass.NEW