from knowledge_service.analyst.synthesis.models import Theme, ThemeEvolution, ThemeEvolutionState
from knowledge_service.production.trends.acceleration import TrendAccelerationEngine


def _theme(label: str, claim_count: int, *, source_count: int = 1, theme_id: str | None = None) -> Theme:
    return Theme(
        theme_id=theme_id or f"theme-{label}",
        label=label,
        claim_ids=[f"claim-{index}" for index in range(claim_count)],
        keywords=[label.lower()],
        entities=[],
        source_count=source_count,
        speaker_count=2,
    )


def test_accelerating_theme_when_claim_or_source_velocity_rises():
    engine = TrendAccelerationEngine()
    theme = _theme("Inference Economics", 8, source_count=4)
    history = [{
        "themes": [{
            "label": "Inference Economics",
            "claim_count": 4,
            "source_count": 2,
        }],
    }]
    evolution = ThemeEvolution(
        theme_id=theme.theme_id,
        label=theme.label,
        state=ThemeEvolutionState.STRENGTHENING,
        explanation="Claim volume is expanding across monitored sources.",
    )

    trends = engine.analyze([theme], [evolution], history)
    match = trends[0]

    assert match["acceleration"] == "accelerating"
    assert match["claim_velocity"] == 4
    assert match["source_velocity"] == 2
    assert match["consensus"] == "forming"
    assert "accelerating" in match["explanation"].lower()


def test_decaying_theme_when_claim_velocity_drops():
    engine = TrendAccelerationEngine()
    theme = _theme("Agentic Workflows", 2, source_count=1)
    history = [{
        "themes": [{
            "label": "Agentic Workflows",
            "claim_count": 6,
            "source_count": 3,
        }],
    }]

    trends = engine.analyze([theme], [], history)
    match = trends[0]

    assert match["acceleration"] == "decaying"
    assert match["claim_velocity"] == -4
    assert match["consensus"] == "early"
    assert "decaying" in match["explanation"].lower()


def test_snapshot_records_theme_counts_and_trend_rows():
    engine = TrendAccelerationEngine()
    themes = [_theme("Frontier Model Scaling", 5, source_count=3)]
    trends = engine.analyze(themes, [], [])

    snapshot = engine.snapshot(themes, trends)

    assert snapshot["themes"][0]["claim_count"] == 5
    assert snapshot["themes"][0]["source_count"] == 3
    assert snapshot["trends"][0]["label"] == "Frontier Model Scaling"
    assert "recorded_at" in snapshot