from knowledge_service.intelligence.models import DiscoveredEpisode, IntelligenceProfile, PodcastSource, WatchListEntry
from knowledge_service.intelligence.route_registry import (
    AcquisitionRoute,
    AcquisitionRouteRegistry,
    RouteSelection,
)
from knowledge_service.intelligence.state import FileStateStore


def test_registry_resolves_source_ids_deterministically(tmp_path):
    registry = AcquisitionRouteRegistry(FileStateStore(tmp_path))
    assert registry.resolve_source_id(podcast_name="Dwarkesh Podcast", url="https://podscripts.co/podcasts/dwarkesh-podcast/foo") == "dwarkesh"
    assert registry.resolve_source_id(podcast_name="Lex Fridman Podcast", url="https://lexfridman.com/sam-altman-transcript/") == "lex_fridman"


def test_registry_select_route_returns_ordered_chain(tmp_path):
    registry = AcquisitionRouteRegistry(FileStateStore(tmp_path))
    selection = registry.select_route("dwarkesh", "https://podscripts.co/podcasts/dwarkesh-podcast/example")
    assert selection.preferred_route == AcquisitionRoute.PUBLISHED_TRANSCRIPT.value
    assert selection.fallback_chain[0] == AcquisitionRoute.PUBLISHED_TRANSCRIPT.value
    assert AcquisitionRoute.YOUTUBE_TRANSCRIPT_API.value in selection.fallback_chain


def test_registry_persists_across_restart(tmp_path):
    first = AcquisitionRouteRegistry(FileStateStore(tmp_path))
    first.record_route_attempt("dwarkesh", "published_transcript", success=True, runtime_seconds=1.2, transcript_length=5000)
    restarted = AcquisitionRouteRegistry(FileStateStore(tmp_path))
    entry = restarted.get("dwarkesh")
    assert entry is not None
    assert entry.route_statistics["published_transcript"]["successes"] == 1


def test_provider_options_map_routes_to_transcript_provider_sources(tmp_path):
    registry = AcquisitionRouteRegistry(FileStateStore(tmp_path))
    published = registry.provider_options_for_route("published_transcript")
    youtube = registry.provider_options_for_route("youtube_transcript_api")
    assert published["source"] == "published"
    assert youtube["source"] == "youtube_captions"


class ScriptedProvider:
    name = "scripted-provider"

    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.calls = []

    def initialize(self, _config):
        return None

    def execute(self, request):
        from knowledge_service.interfaces.provider import ProviderError, ProviderResponse

        route = (request.options or {}).get("acquisition_route")
        self.calls.append(route)
        if route in self.outcomes:
            outcome = self.outcomes[route]
            if outcome == "success":
                return ProviderResponse(content="transcript text", content_type="text/transcript", metadata={"acquisition_route": route})
            return ProviderResponse(error=ProviderError(code="FAIL", message=f"{route} failed", retryable=False, recoverable=True))
        return ProviderResponse(error=ProviderError(code="MISSING", message="no script", retryable=False, recoverable=True))


def test_collector_uses_registry_fallback_chain(tmp_path):
    from knowledge_service.intelligence.collector import IntelligenceCollector

    profile = IntelligenceProfile(
        name="AI",
        watch_list=[WatchListEntry(display_name="Sam Altman")],
        required_podcasts=[PodcastSource(
            name="Dwarkesh Podcast",
            url="https://podscripts.co/podcasts/dwarkesh-podcast",
            episode_urls=["https://podscripts.co/podcasts/dwarkesh-podcast/sam-altman-test"],
            max_episodes=1,
        )],
    )
    provider = ScriptedProvider({
        "published_transcript": "fail",
        "youtube_transcript_api": "success",
    })
    collector = IntelligenceCollector(str(tmp_path), profiles=[profile], provider=provider)
    job = collector.run_once()

    episode = collector.corpus.episodes()[0]
    assert job.processed_count == 1
    assert episode.acquisition_route == "youtube_transcript_api"
    assert "published_transcript" in episode.fallback_routes_attempted
    assert episode.source_id == "dwarkesh"
    assert episode.transcript_provenance["acquisition_route"] == "youtube_transcript_api"