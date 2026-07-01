from knowledge_service.analyst.contradiction.detector import ContradictionDetector
from knowledge_service.analyst.models import NoveltyClass, NoveltyResult
from knowledge_service.retrieval.embedding import embed_text

from .conftest import make_claim


def test_detect_returns_contradiction_when_novelty_flags_conflict():
    prior_text = "Markets will increase through the second half of the year as enterprise AI spending grows."
    current_text = "Markets will decrease through the second half of the year as enterprise AI spending grows."
    prior = make_claim(prior_text, episode_id="episode-a")
    current = make_claim(current_text, episode_id="episode-b")
    novelty = NoveltyResult(
        score=0.85,
        classification=NoveltyClass.CONTRADICTION,
        explanation="Conflicting prior claim detected.",
        prior_claim_id=prior.claim_id,
        prior_similarity=0.9,
    )

    contradictions = ContradictionDetector().detect(current, novelty, [prior])

    assert len(contradictions) == 1
    assert contradictions[0].prior_claim_id == prior.claim_id
    assert contradictions[0].claim_text == current.claim_text
    assert contradictions[0].prior_claim_text == prior.claim_text
    assert "contradict" in contradictions[0].explanation.lower()


def test_detect_empty_when_not_contradiction(sample_claim):
    novelty = NoveltyResult(
        score=1.0,
        classification=NoveltyClass.NEW,
        explanation="No close semantic match found in historical corpus.",
    )

    contradictions = ContradictionDetector().detect(sample_claim, novelty, [])

    assert contradictions == []


def test_scan_corpus_finds_potential_conflicts():
    base = "Enterprise AI spending will grow through 2027 across major cloud providers and datacenters."
    prior = make_claim(base, episode_id="episode-a")
    current = make_claim(
        "Enterprise AI spending will not grow through 2027 across major cloud providers and datacenters.",
        episode_id="episode-b",
    )
    prior.embedding = embed_text(prior.claim_text)
    current.embedding = embed_text(current.claim_text)

    contradictions = ContradictionDetector().scan_corpus([prior, current])

    assert contradictions
    assert contradictions[0].claim_id == current.claim_id
    assert contradictions[0].prior_claim_id == prior.claim_id