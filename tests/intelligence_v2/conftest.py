"""Fixtures for IL2 tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge_service.analyst.synthesis.models import IntelligenceItem


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def golden_failures() -> list[dict]:
    path = FIXTURES_DIR / "golden_failures.json"
    return json.loads(path.read_text(encoding="utf-8"))


def make_item(
    *,
    title: str,
    excerpt: str,
    item_id: str = "test-item",
    corroboration: int = 3,
    importance: float = 0.82,
) -> IntelligenceItem:
    return IntelligenceItem(
        item_id=item_id,
        title=title,
        executive_summary=f"Summary for {title}",
        why_surfaced=f"Matched: {title}",
        why_it_matters="High importance signal.",
        novelty_score=0.9,
        novelty_classification="new",
        importance_score=importance,
        importance_band="very_high",
        confidence=0.9,
        corroboration_count=corroboration,
        contradiction_count=0,
        theme_id="theme-1",
        theme_label=title,
        profile_ids=["ai"],
        profile_names=["AI"],
        supporting_claim_ids=["c1"],
        supporting_evidence=[{"excerpt": excerpt, "speaker": "Host", "source": "Test Podcast"}],
        timestamped_citations=[],
        speakers=["Host"],
        sources=["Test Podcast"],
        contradictions=[],
        historical_developments=[],
        claim_count=3,
    )