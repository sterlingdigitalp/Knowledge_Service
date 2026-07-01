from knowledge_service.analyst.models import ImportanceBand, NoveltyClass
from knowledge_service.analyst.synthesis.themes.discovery import ThemeDiscoveryEngine

from .conftest import build_scored_claims_and_clusters


def test_discover_emergent_themes_from_phase32_scored_claims(phase32_state_dir):
    scored, _clusters = build_scored_claims_and_clusters(phase32_state_dir)

    themes = ThemeDiscoveryEngine().discover(scored)

    assert scored
    assert themes
    assert len(themes) >= 5
    for theme in themes:
        assert theme.theme_id
        assert theme.label
        assert len(theme.claim_ids) >= 3
        assert theme.keywords
        assert theme.source_count >= 1
        assert theme.speaker_count >= 1
        assert theme.centroid_embedding


def test_theme_discovery_excludes_repeats_and_low_importance(phase32_state_dir):
    scored, _clusters = build_scored_claims_and_clusters(phase32_state_dir)
    for item in scored:
        item.novelty.classification = NoveltyClass.REPEAT
        item.importance.band = ImportanceBand.IGNORE
        item.importance.score = 0.1

    themes = ThemeDiscoveryEngine().discover(scored)

    assert themes == []


def test_theme_labels_are_emergent_not_hardcoded(phase32_state_dir):
    scored, _clusters = build_scored_claims_and_clusters(phase32_state_dir)
    themes = ThemeDiscoveryEngine().discover(scored)

    labels = {theme.label.lower() for theme in themes}
    hardcoded = {"ai", "investing", "founders", "longevity"}
    assert not labels.issubset(hardcoded)
    assert any(len(theme.keywords) >= 2 for theme in themes)