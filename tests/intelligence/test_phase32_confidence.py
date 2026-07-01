from knowledge_service.intelligence.route_confidence import RouteConfidenceEngine
from knowledge_service.intelligence.route_registry import SourceRouteEntry


def test_confidence_computed_from_runtime_not_hardcoded():
    entry = SourceRouteEntry(
        source_id="dwarkesh",
        canonical_name="Dwarkesh",
        preferred_route="published_transcript",
        route_statistics={
            "published_transcript": {
                "attempts": 10,
                "successes": 9,
                "failures": 1,
                "total_runtime_seconds": 5.0,
                "avg_transcript_length": 50000,
            }
        },
    )
    engine = RouteConfidenceEngine()
    snapshot = engine.compute(entry)
    assert snapshot.route_confidence > 0.5
    assert snapshot.failure_rate == 0.1
    assert snapshot.average_acquisition_time_seconds == 0.5


def test_confidence_zero_attempts_uses_base_not_config_hardcode():
    entry = SourceRouteEntry(source_id="new", canonical_name="New", preferred_route="published_transcript")
    snapshot = RouteConfidenceEngine().compute(entry)
    assert snapshot.route_confidence < 0.75
    assert snapshot.factors["attempts"] == 0.0


def test_next_recertification_scheduled_30_days_out():
    entry = SourceRouteEntry(
        source_id="dwarkesh",
        canonical_name="Dwarkesh",
        preferred_route="published_transcript",
        certification_history=[],
    )
    engine = RouteConfidenceEngine()
    next_date = engine.next_recertification_date(entry)
    assert next_date > "2026-01-01"
    assert engine.is_recertification_due(entry) is True