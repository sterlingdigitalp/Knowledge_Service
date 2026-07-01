from knowledge_service.intelligence.collector import IntelligenceCollector
from knowledge_service.intelligence.corpus_audit import audit_corpus, generate_corpus_audit_markdown
from knowledge_service.intelligence.models import IntelligenceProfile, PodcastSource, WatchListEntry
from knowledge_service.interfaces.provider import ProviderResponse


class FakeProvider:
    name = "fake"

    def initialize(self, _):
        return None

    def execute(self, request):
        return ProviderResponse(
            content="[00:00:00] Sam Altman: AI infrastructure.\n",
            content_type="text/transcript",
            metadata={**request.options["metadata"], "transcript_source": "published_transcript", "acquisition_route": "published_transcript"},
        )


def test_corpus_audit_passes_after_collection(tmp_path):
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
    collector = IntelligenceCollector(str(tmp_path), profiles=[profile], provider=FakeProvider())
    collector.run_once()
    audit = audit_corpus(collector.state)
    assert audit["processed_episodes"] == 1
    assert audit["status"] == "pass"
    assert "CORPUS AUDIT" in generate_corpus_audit_markdown(audit).upper() or "# Corpus Audit" in generate_corpus_audit_markdown(audit)