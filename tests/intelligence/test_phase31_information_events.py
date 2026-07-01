from knowledge_service.intelligence.migration import migrate_corpus_state
from knowledge_service.intelligence.models import DiscoveredEpisode, InformationEventType
from knowledge_service.intelligence.route_registry import AcquisitionRouteRegistry
from knowledge_service.intelligence.state import FileStateStore


def test_discovered_episode_round_trips_information_event_fields():
    episode = DiscoveredEpisode(
        profile_id="ai",
        podcast_name="Dwarkesh Podcast",
        title="Sam Altman on AGI",
        url="https://example.com/episode",
        source_url="https://example.com/episode",
        matched_watch_entries=["Sam Altman"],
        source_id="dwarkesh",
        acquisition_route="published_transcript",
        route_confidence=0.92,
    )
    event = episode.as_information_event()
    assert event.event_type == InformationEventType.PODCAST_EPISODE
    assert event.venue == "Dwarkesh Podcast"
    assert event.participants == ["Sam Altman"]
    restored = DiscoveredEpisode.from_information_event(event)
    assert restored.podcast_name == episode.podcast_name
    assert restored.source_id == "dwarkesh"


def test_migration_backfills_legacy_episodes_without_losing_fields(tmp_path):
    state = FileStateStore(tmp_path)
    registry = AcquisitionRouteRegistry(state)
    legacy = {
        "episode_id": "legacy-1",
        "profile_id": "ai",
        "podcast_name": "Dwarkesh Podcast",
        "title": "Legacy Episode",
        "url": "https://podscripts.co/podcasts/dwarkesh-podcast/legacy",
        "source_url": "https://podscripts.co/podcasts/dwarkesh-podcast/legacy",
        "matched_watch_entries": ["Sam Altman"],
        "status": "processed",
    }
    state.write_json("episodes.json", [legacy])
    result = migrate_corpus_state(state, registry)
    migrated = state.read_json("episodes.json", [])
    events = state.read_json("information_events.json", [])
    assert result["episodes_migrated"] >= 1
    assert migrated[0]["source_id"] == "dwarkesh"
    assert migrated[0]["event_type"] == InformationEventType.PODCAST_EPISODE.value
    assert events[0]["participants"] == ["Sam Altman"]