from knowledge_service.intelligence.registry_evolution import RegistryEvolutionEngine
from knowledge_service.intelligence.route_registry import SourceRouteEntry


def test_recommends_fallback_when_preferred_fails_repeatedly():
    entry = SourceRouteEntry(
        source_id="all_in",
        canonical_name="All-In",
        preferred_route="youtube_transcript_api",
        fallbacks=["published_transcript"],
        route_statistics={
            "youtube_transcript_api": {"attempts": 5, "successes": 0, "failures": 5},
            "published_transcript": {"attempts": 5, "successes": 5, "failures": 0},
        },
    )
    recs = RegistryEvolutionEngine().analyze(entry)
    assert any(r["type"] == "promote_fallback" for r in recs)
    assert recs[0]["recommended_route"] == "published_transcript"