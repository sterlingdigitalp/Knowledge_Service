from knowledge_service.interfaces.provider import ProviderResponse
from knowledge_service.intelligence.collector import IntelligenceCollector
from knowledge_service.intelligence.inspector import inspect_intelligence_runtime
from knowledge_service.intelligence.models import IntelligenceProfile, PodcastSource, WatchListEntry
from knowledge_service.intelligence.scheduler import RuntimeScheduler


class FakeTranscriptProvider:
    name = "fake-transcript-provider"

    def __init__(self):
        self.calls = 0

    def initialize(self, _config):
        return None

    def execute(self, request):
        self.calls += 1
        title = request.options["metadata"]["episode"]
        content = (
            "[00:00:00] Sam Altman: AI datacenters and inference are changing enterprise AI.\n"
            "[00:00:12] unknown: This episode discusses agents and compute.\n"
        )
        return ProviderResponse(
            content=content,
            content_type="text/transcript",
            status_code=200,
            metadata={
                **request.options["metadata"],
                "source_type": "video_transcript",
                "transcript_source": "published_transcript",
                "transcript_confidence": 0.95,
                "transcript_segments": [
                    {"segment_id": "s0", "start_seconds": 0.0, "end_seconds": 12.0, "speaker": "Sam Altman", "speaker_confidence": 1.0, "text": title},
                    {"segment_id": "s1", "start_seconds": 12.0, "end_seconds": 20.0, "speaker": "unknown", "speaker_confidence": 0.0, "text": "agents and compute"},
                ],
            },
        )


def make_profile():
    return IntelligenceProfile(
        name="AI",
        interests=["AI", "inference", "agents"],
        watch_list=[WatchListEntry(display_name="Sam Altman", aliases=["sama"])],
        required_podcasts=[PodcastSource(
            name="Configured Podcast",
            url="https://podscripts.co/podcasts/configured",
            episode_urls=["https://podscripts.co/podcasts/configured/sam-altman-enterprise-ai-agents"],
            max_episodes=1,
        )],
    )


def test_collector_builds_persistent_corpus_and_prevents_duplicate_after_restart(tmp_path):
    provider = FakeTranscriptProvider()
    collector = IntelligenceCollector(str(tmp_path), profiles=[make_profile()], provider=provider)

    first_job = collector.run_once()
    first_summary = collector.corpus.summary()

    restarted = IntelligenceCollector(str(tmp_path), profiles=[make_profile()], provider=provider)
    second_job = restarted.run_once()
    second_summary = restarted.corpus.summary()

    assert first_job.processed_count == 1
    assert first_summary["processed_episodes"] == 1
    assert first_summary["chunks"] > 0
    assert first_summary["embeddings"] == first_summary["chunks"]
    assert second_job.processed_count == 0
    assert second_job.duplicate_count >= 1
    assert second_summary["processed_episodes"] == 1
    assert provider.calls == 1


def test_source_graph_and_runtime_inspector_reflect_collection_state(tmp_path):
    collector = IntelligenceCollector(str(tmp_path), profiles=[make_profile()], provider=FakeTranscriptProvider())
    collector.run_once()

    report = inspect_intelligence_runtime(tmp_path)

    assert report["system_summary"]["status"] == "pass"
    assert report["profiles"][0]["watch_list_size"] == 1
    assert report["sources"]["people"][0]["person"] == "Sam Altman"
    assert report["corpus"]["processed_episodes"] == 1
    assert report["deduplication"]["transcript_hash_count"] == 1


def test_scheduler_runs_daemon_iteration_and_resumes_with_dedupe(tmp_path):
    provider = FakeTranscriptProvider()
    collector = IntelligenceCollector(str(tmp_path), profiles=[make_profile()], provider=provider)
    scheduler = RuntimeScheduler(collector, interval_seconds=0)

    result = scheduler.run_daemon(max_iterations=2)
    report = inspect_intelligence_runtime(tmp_path)

    assert result["iterations"] == 2
    assert result["jobs"][0]["processed_count"] == 1
    assert result["jobs"][1]["processed_count"] == 0
    assert report["runtime"]["scheduler"]["status"] == "completed"
    assert report["discovery"]["already_processed"] >= 1
    assert provider.calls == 1
