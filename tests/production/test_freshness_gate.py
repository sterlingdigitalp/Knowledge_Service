from datetime import datetime, timedelta, timezone

from knowledge_service.analyst.models import Claim, NoveltyClass
from knowledge_service.analyst.synthesis.models import IntelligenceItem, ThemeEvolution, ThemeEvolutionState
from knowledge_service.production.morning.freshness_gate import FreshnessGate


def _claim(*, claim_id: str, episode_id: str, days_old: int = 0) -> Claim:
    published = (datetime.now(timezone.utc) - timedelta(days=days_old)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return Claim(
        claim_text=f"claim {claim_id}",
        speaker="Speaker",
        timestamp_start=None,
        timestamp_end=None,
        timestamp_label="00:00",
        transcript_reference="ref",
        evidence="evidence",
        confidence=0.9,
        topic="topic",
        entities=[],
        supporting_context="",
        claim_id=claim_id,
        episode_id=episode_id,
        published_at=published,
        created_at=published,
    )


def _item(*, item_id: str, claim_ids: list[str], novelty: str = "new", score: float = 0.9) -> IntelligenceItem:
    return IntelligenceItem(
        item_id=item_id,
        title=f"Item {item_id}",
        executive_summary="summary",
        why_surfaced="surfaced",
        why_it_matters="matters",
        novelty_score=score,
        novelty_classification=novelty,
        importance_score=0.9,
        importance_band="high",
        confidence=0.9,
        corroboration_count=1,
        contradiction_count=0,
        theme_id="theme",
        theme_label="Theme",
        profile_ids=["ai"],
        profile_names=["AI"],
        supporting_claim_ids=claim_ids,
        supporting_evidence=[],
        timestamped_citations=[],
        speakers=["Speaker"],
        sources=["Source"],
        contradictions=[],
        historical_developments=[],
    )


def test_freshness_gate_accepts_new_episode_items():
    gate = FreshnessGate(headline_max_age_days=7)
    claims = {"c1": _claim(claim_id="c1", episode_id="ep-new")}
    items = [_item(item_id="i1", claim_ids=["c1"])]
    eligible, report = gate.filter_items(items, new_episode_ids={"ep-new"}, new_claim_ids=set(), claims_by_id=claims)
    assert len(eligible) == 1
    assert report.items_eligible == 1
    assert report.decisions[0].reason == "new_acquisition"


def test_freshness_gate_rejects_repeat_stale_items():
    gate = FreshnessGate(headline_max_age_days=3)
    claims = {"c1": _claim(claim_id="c1", episode_id="ep-old", days_old=30)}
    items = [_item(item_id="i1", claim_ids=["c1"], novelty=NoveltyClass.REPEAT.value, score=0.1)]
    eligible, report = gate.filter_items(items, new_episode_ids=set(), new_claim_ids=set(), claims_by_id=claims)
    assert eligible == []
    assert report.no_fresh_signal is True
    assert report.decisions[0].reason == "repeat_no_new_signal"


def test_freshness_gate_accepts_theme_evolution():
    gate = FreshnessGate()
    claims = {"c1": _claim(claim_id="c1", episode_id="ep-1", days_old=2)}
    item = _item(item_id="i1", claim_ids=["c1"], novelty=NoveltyClass.REFINEMENT.value, score=0.8)
    item.theme_evolution = ThemeEvolution(
        theme_id="t1",
        label="Theme",
        state=ThemeEvolutionState.STRENGTHENING,
        explanation="strengthening",
    )
    eligible, report = gate.filter_items([item], new_episode_ids=set(), new_claim_ids=set(), claims_by_id=claims)
    assert len(eligible) == 1
    assert report.decisions[0].reason == "theme_evolution"