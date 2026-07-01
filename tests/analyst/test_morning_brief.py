from knowledge_service.analyst.briefing.morning_brief import MorningBriefGenerator
from knowledge_service.analyst.importance.engine import ImportanceEngine
from knowledge_service.analyst.models import ImportanceBand, NoveltyClass, ScoredClaim
from knowledge_service.analyst.novelty.engine import NoveltyEngine
from knowledge_service.analyst.relevance.engine import RelevanceEngine


def _build_scored_claims(claims, profiles):
    engine = NoveltyEngine()
    relevance_engine = RelevanceEngine()
    importance_engine = ImportanceEngine()
    historical = []
    scored = []
    for claim in claims:
        novelty = engine.score(claim, historical)
        relevance = relevance_engine.score(claim, profiles)
        importance = importance_engine.score(claim, novelty, relevance)
        scored.append(
            ScoredClaim(
                claim=claim,
                novelty=novelty,
                relevance=relevance,
                importance=importance,
            )
        )
        historical.append(claim)
    return scored


def test_morning_brief_generates_all_profile_sections(extracted_claims, phase32_profiles):
    scored = _build_scored_claims(extracted_claims[:40], phase32_profiles)

    brief = MorningBriefGenerator().generate(scored, phase32_profiles, pipeline_run_id="test-run")

    assert set(brief.sections.keys()) == {"AI", "Investing", "Founders", "Longevity"}
    assert brief.total_items > 0
    assert 30 <= brief.reading_time_seconds <= 90
    assert brief.pipeline_run_id == "test-run"


def test_morning_brief_items_have_evidence_and_explainability(extracted_claims, phase32_profiles):
    scored = _build_scored_claims(extracted_claims[:40], phase32_profiles)
    brief = MorningBriefGenerator().generate(scored, phase32_profiles)

    items = [item for section in brief.sections.values() for item in section]
    assert items
    item = items[0]
    assert item.evidence_summary
    assert item.claim_id
    assert item.source_url
    assert item.timestamp_label
    assert item.explainability.get("importance_factors")
    assert item.explainability.get("novelty_explanation")


def test_morning_brief_filters_repeats_and_low_importance(extracted_claims, phase32_profiles):
    scored = _build_scored_claims(extracted_claims[:40], phase32_profiles)
    for item in scored:
        item.novelty.classification = NoveltyClass.REPEAT
        item.importance.band = ImportanceBand.IGNORE

    brief = MorningBriefGenerator().generate(scored, phase32_profiles)

    assert brief.total_items == 0
    assert all(len(items) == 0 for items in brief.sections.values())