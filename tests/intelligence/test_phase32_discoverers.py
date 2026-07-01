from knowledge_service.intelligence.discoverers import DiscovererRegistry, PodcastDiscoverer
from knowledge_service.intelligence.discoverers.conference import ConferenceDiscoverer
from knowledge_service.intelligence.models import IntelligenceProfile, PodcastSource, WatchListEntry


def test_discoverer_registry_includes_all_interfaces():
    registry = DiscovererRegistry()
    ids = registry.discoverer_ids()
    assert "podcast" in ids
    assert "conference" in ids
    assert "interview" in ids
    assert "livestream" in ids
    assert "earnings_call" in ids
    assert "presentation" in ids


def test_stub_discoverers_return_empty_without_error(tmp_path):
    from knowledge_service.intelligence.dedupe import DeduplicationStore
    from knowledge_service.intelligence.discoverers.base import DiscoveryContext
    from knowledge_service.intelligence.state import FileStateStore

    state = FileStateStore(tmp_path)
    context = DiscoveryContext(state=state, dedupe=DeduplicationStore(state))
    profile = IntelligenceProfile(name="AI", watch_list=[WatchListEntry(display_name="Sam Altman")])
    assert ConferenceDiscoverer().discover(profile, context) == []


def test_podcast_discoverer_is_only_implemented_channel():
    discoverer = PodcastDiscoverer()
    assert discoverer.discoverer_id == "podcast"
    assert "podcast_episode" in discoverer.event_types