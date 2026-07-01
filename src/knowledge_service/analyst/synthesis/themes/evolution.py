"""Theme Evolution — track how themes change over time."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from ....retrieval.embedding import cosine_similarity
from ..models import Theme, ThemeEvolution, ThemeEvolutionState


PRIOR_MATCH_THRESHOLD = 0.72
STRENGTHENING_DELTA = 2
FADING_DELTA = -3


class ThemeEvolutionEngine:
    """Compare discovered themes against historical theme memory."""

    def evaluate(
        self,
        current_themes: Sequence[Theme],
        historical_themes: Sequence[Theme],
    ) -> List[ThemeEvolution]:
        used_prior: set[str] = set()
        results: List[ThemeEvolution] = []

        for theme in current_themes:
            prior, similarity = _best_prior_match(theme, historical_themes, used_prior)
            if prior is None:
                results.append(ThemeEvolution(
                    theme_id=theme.theme_id,
                    label=theme.label,
                    state=ThemeEvolutionState.NEW,
                    explanation=f"'{theme.label}' is a newly emerging theme with {len(theme.claim_ids)} supporting claims.",
                ))
                continue

            used_prior.add(prior.theme_id)
            claim_delta = len(theme.claim_ids) - len(prior.claim_ids)
            source_delta = theme.source_count - prior.source_count
            state, explanation = _classify_evolution(theme, prior, similarity, claim_delta, source_delta)
            results.append(ThemeEvolution(
                theme_id=theme.theme_id,
                label=theme.label,
                state=state,
                explanation=explanation,
                prior_theme_id=prior.theme_id,
                similarity_to_prior=round(similarity, 4),
                claim_count_delta=claim_delta,
                source_count_delta=source_delta,
            ))
        return results

    def merge_history(self, current: Sequence[Theme], historical: Sequence[Theme]) -> List[Theme]:
        merged = {theme.theme_id: theme for theme in historical}
        for theme in current:
            merged[theme.theme_id] = theme
        return list(merged.values())


def _best_prior_match(
    theme: Theme,
    historical: Sequence[Theme],
    used: set[str],
) -> tuple[Optional[Theme], float]:
    best: Optional[Theme] = None
    best_similarity = 0.0
    for prior in historical:
        if prior.theme_id in used:
            continue
        if not theme.centroid_embedding or not prior.centroid_embedding:
            continue
        similarity = cosine_similarity(theme.centroid_embedding, prior.centroid_embedding)
        label_boost = 0.1 if theme.label.lower() == prior.label.lower() else 0.0
        combined = similarity + label_boost
        if combined > best_similarity:
            best_similarity = combined
            best = prior
    if best_similarity < PRIOR_MATCH_THRESHOLD:
        return None, 0.0
    return best, best_similarity


def _classify_evolution(
    theme: Theme,
    prior: Theme,
    similarity: float,
    claim_delta: int,
    source_delta: int,
) -> tuple[ThemeEvolutionState, str]:
    if claim_delta >= STRENGTHENING_DELTA or source_delta >= 1:
        return (
            ThemeEvolutionState.STRENGTHENING,
            f"'{theme.label}' is strengthening: +{claim_delta} claims, +{source_delta} sources since last run.",
        )
    if claim_delta <= FADING_DELTA:
        return (
            ThemeEvolutionState.FADING,
            f"'{theme.label}' discussion is fading: {claim_delta} claims vs prior snapshot.",
        )
    if similarity < 0.80 and claim_delta != 0:
        return (
            ThemeEvolutionState.MATERIAL_CHANGE,
            f"'{theme.label}' has materially shifted (similarity {similarity:.2f}, delta {claim_delta} claims).",
        )
    return (
        ThemeEvolutionState.STABLE,
        f"'{theme.label}' remains stable with {len(theme.claim_ids)} claims across {theme.source_count} sources.",
    )