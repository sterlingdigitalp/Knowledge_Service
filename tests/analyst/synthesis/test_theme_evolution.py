from knowledge_service.analyst.synthesis.models import Theme, ThemeEvolutionState
from knowledge_service.analyst.synthesis.themes.evolution import ThemeEvolutionEngine
from knowledge_service.retrieval.embedding import embed_text


def _theme(label: str, claim_count: int, *, source_count: int = 1) -> Theme:
    centroid = embed_text(label)
    return Theme(
        theme_id=f"theme-{label}-{claim_count}",
        label=label,
        claim_ids=[f"claim-{index}" for index in range(claim_count)],
        keywords=[label.lower()],
        entities=[],
        source_count=source_count,
        speaker_count=2,
        centroid_embedding=centroid,
    )


def test_new_theme_when_no_historical_memory():
    themes = [_theme("Agentic Workflows", 4)]

    evolutions = ThemeEvolutionEngine().evaluate(themes, [])

    assert len(evolutions) == 1
    assert evolutions[0].state == ThemeEvolutionState.NEW
    assert evolutions[0].prior_theme_id is None


def test_strengthening_when_claim_count_grows():
    label = "Enterprise AI Adoption"
    current = _theme(label, 6, source_count=3)
    prior = _theme(label, 2, source_count=1)
    prior.theme_id = "prior-theme"

    evolutions = ThemeEvolutionEngine().evaluate([current], [prior])
    match = evolutions[0]

    assert match.state == ThemeEvolutionState.STRENGTHENING
    assert match.claim_count_delta == 4
    assert match.source_count_delta == 2
    assert match.prior_theme_id == prior.theme_id


def test_fading_when_claim_count_drops():
    label = "Inference Cost Decline"
    current = _theme(label, 2, source_count=1)
    prior = _theme(label, 7, source_count=4)
    prior.theme_id = "prior-theme"

    evolutions = ThemeEvolutionEngine().evaluate([current], [prior])
    match = evolutions[0]

    assert match.state == ThemeEvolutionState.FADING
    assert match.claim_count_delta == -5
    assert match.prior_theme_id == prior.theme_id