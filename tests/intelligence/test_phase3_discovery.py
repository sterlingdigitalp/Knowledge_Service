from knowledge_service.intelligence.dedupe import DeduplicationStore
from knowledge_service.intelligence.discovery import DiscoveryEngine
from knowledge_service.intelligence.models import IntelligenceProfile, PodcastSource, WatchListEntry
from knowledge_service.intelligence.state import FileStateStore


def test_discovery_queues_required_podcast_episode_without_manual_transcript_fetch(tmp_path):
    state = FileStateStore(tmp_path)
    dedupe = DeduplicationStore(state)
    profile = IntelligenceProfile(
        name="AI",
        interests=["datacenters"],
        watch_list=[WatchListEntry(display_name="Sam Altman")],
        required_podcasts=[PodcastSource(
            name="Configured Podcast",
            url="https://podscripts.co/podcasts/configured",
            episode_urls=["https://podscripts.co/podcasts/configured/sam-altman-on-ai-datacenters"],
        )],
    )

    result = DiscoveryEngine(state, dedupe).discover([profile])[0]

    assert result.status == "success"
    assert result.found_count == 1
    assert result.queued_count == 1
    assert result.episodes[0].matched_watch_entries == ["Sam Altman"]
    assert result.episodes[0].matched_interests == ["datacenters"]


def test_optional_podcast_skips_when_no_profile_match(tmp_path):
    state = FileStateStore(tmp_path)
    dedupe = DeduplicationStore(state)
    profile = IntelligenceProfile(
        name="Longevity",
        interests=["longevity"],
        watch_list=[WatchListEntry(display_name="Peter Attia")],
        optional_podcasts=[PodcastSource(
            name="Generic Podcast",
            url="https://podscripts.co/podcasts/generic",
            episode_urls=["https://podscripts.co/podcasts/generic/macroeconomics-roundtable"],
        )],
    )

    result = DiscoveryEngine(state, dedupe).discover([profile])[0]

    assert result.queued_count == 0
    assert result.skipped_count == 1
    assert result.episodes[0].error == "No watched-person or interest match"
