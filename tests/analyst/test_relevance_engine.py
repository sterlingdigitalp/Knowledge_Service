from knowledge_service.analyst.relevance.engine import RelevanceEngine


def test_relevance_scores_every_enabled_profile(sample_claim, phase32_profiles):
    enabled_profiles = [profile for profile in phase32_profiles if profile.enabled]
    results = RelevanceEngine().score(sample_claim, phase32_profiles)

    assert len(results) == len(enabled_profiles)
    assert {item.profile_id for item in results} == {profile.profile_id for profile in enabled_profiles}
    assert all(0.0 <= item.score <= 1.0 for item in results)
    assert all(item.explanation for item in results)


def test_relevance_detects_matched_interests_from_real_claim(sample_claim, phase32_profiles):
    results = RelevanceEngine().score(sample_claim, phase32_profiles)
    ai_result = next(item for item in results if item.profile_id == "ai")

    assert ai_result.profile_name == "AI"
    assert ai_result.score > 0.2
    assert "AI" in ai_result.matched_interests or ai_result.matched_topics


def test_relevance_profile_origin_boost_for_collecting_profile(sample_claim, phase32_profiles):
    sample_claim.profile_id = "ai"
    results = RelevanceEngine().score(sample_claim, phase32_profiles)
    ai_result = next(item for item in results if item.profile_id == "ai")
    investing_result = next(item for item in results if item.profile_id == "investing")

    assert "Collected under AI profile" in ai_result.explanation
    assert ai_result.score >= investing_result.score