from knowledge_service.analyst.synthesis.models import IntelligenceItem
from knowledge_service.intelligence.state import FileStateStore
from knowledge_service.production.personalization.feedback import UserFeedbackEngine
from knowledge_service.production.personalization.ranking import PersonalizedRankingEngine
from knowledge_service.production.personalization.store import PersonalizationStore


def _item(
    item_id: str,
    *,
    title: str,
    theme_label: str,
    importance_score: float = 0.7,
    profile_names: list[str] | None = None,
) -> IntelligenceItem:
    return IntelligenceItem(
        item_id=item_id,
        title=title,
        executive_summary=f"Summary for {title}",
        why_surfaced=f"Matched: {theme_label}",
        why_it_matters="Strategic relevance for monitored profiles.",
        novelty_score=0.8,
        novelty_classification="new",
        importance_score=importance_score,
        importance_band="high",
        confidence=0.85,
        corroboration_count=2,
        contradiction_count=0,
        theme_id=f"theme-{item_id}",
        theme_label=theme_label,
        profile_ids=["ai"],
        profile_names=profile_names or ["AI"],
        supporting_claim_ids=["claim-a", "claim-b"],
        supporting_evidence=[{"excerpt": "Evidence line", "speaker": "Analyst", "source": "Podcast"}],
        timestamped_citations=[],
        speakers=["Analyst"],
        sources=["Podcast"],
        contradictions=[],
        historical_developments=[],
        star_rating=4,
        claim_count=2,
    )


def test_feedback_events_persist_and_update_preferences(tmp_path):
    store = PersonalizationStore(FileStateStore(tmp_path))
    feedback = UserFeedbackEngine(store)

    tell_me_more = feedback.tell_me_more("item-lead", duration_seconds=120, profile_id="ai")
    saved = feedback.save("item-lead", profile_id="ai")
    dismissed = feedback.dismiss("item-tail", profile_id="ai")
    brief_view = feedback.brief_view(seconds=48, items_viewed=7)

    prefs = store.load_preferences()
    events = store.load_feedback()

    assert tell_me_more["event_type"] == "tell_me_more"
    assert saved["event_type"] == "save"
    assert dismissed["event_type"] == "dismiss"
    assert brief_view["event_type"] == "brief_view"
    assert len(events) == 4
    assert "item-lead" in prefs["tell_me_more_items"]
    assert "item-lead" in prefs["saved_items"]
    assert "item-tail" in prefs["dismissed_items"]
    assert prefs["deep_dive_seconds"]["item-lead"] == 120

    summary = feedback.summary()
    assert summary["event_count"] == 4
    assert summary["tell_me_more_items"] == 1
    assert summary["saved_items"] == 1
    assert summary["dismissed_items"] == 1


def test_ranking_applies_boosts_penalties_and_learns_from_feedback(tmp_path):
    store = PersonalizationStore(FileStateStore(tmp_path))
    feedback = UserFeedbackEngine(store)
    ranking = PersonalizedRankingEngine(store)

    lead = _item("item-lead", title="Inference Economics", theme_label="inference economics", importance_score=0.72)
    runner = _item("item-runner", title="Enterprise AI Agents", theme_label="enterprise agents", importance_score=0.71)
    tail = _item("item-tail", title="GLP-1 Landscape", theme_label="glp-1 landscape", importance_score=0.70)

    feedback.tell_me_more("item-lead")
    feedback.save("item-runner")
    feedback.dismiss("item-tail")

    topic_weights = ranking.learn_from_feedback([lead, runner, tail])
    assert topic_weights["inference economics"] > 0
    assert topic_weights["enterprise agents"] > 0

    ranked = ranking.rank([tail, runner, lead])
    ranked_ids = [item.item_id for item in ranked]

    assert "item-tail" not in ranked_ids
    assert ranked_ids[0] == "item-lead"
    assert ranked[0].importance_score > lead.importance_score - 0.01
    assert ranked[1].importance_score > runner.importance_score - 0.01