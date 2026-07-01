from knowledge_service.analyst.claims.extractor import ClaimExtractor
from knowledge_service.analyst.cross_source.engine import CrossSourceEngine
from knowledge_service.analyst.importance.engine import ImportanceEngine
from knowledge_service.analyst.models import ScoredClaim
from knowledge_service.analyst.novelty.engine import NoveltyEngine
from knowledge_service.analyst.relevance.engine import RelevanceEngine
from knowledge_service.intelligence.corpus import CorpusManager
from knowledge_service.intelligence.models import EpisodeStatus
from knowledge_service.intelligence.state import FileStateStore


def _load_full_document_claims(state_dir):
    corpus = CorpusManager(FileStateStore(state_dir))
    profiles = corpus.load_profiles()
    episodes = [
        episode.to_dict()
        for episode in corpus.episodes()
        if episode.status == EpisodeStatus.PROCESSED
    ]
    documents = [obj for obj in corpus.knowledge_objects() if obj.get("type") == "document"]
    return ClaimExtractor().extract_from_corpus(documents, episodes, profiles)


def test_build_clusters_finds_multi_episode_convergence_on_real_corpus(phase32_state_dir):
    claims = _load_full_document_claims(phase32_state_dir)
    clusters = CrossSourceEngine().build_clusters(claims)

    assert claims
    assert clusters
    multi_source = [cluster for cluster in clusters if cluster.corroboration_count >= 1]
    assert multi_source
    cluster = multi_source[0]
    assert len(cluster.claim_ids) >= 2
    assert len(cluster.source_ids) >= 2
    assert cluster.explanation
    assert cluster.topic_label


def test_clusters_require_different_episodes():
    from .conftest import make_claim

    shared_text = (
        "Enterprise AI adoption will accelerate as inference costs fall across major cloud providers."
    )
    claims = [
        make_claim(shared_text, episode_id="episode-a", podcast_name="Dwarkesh Podcast"),
        make_claim(shared_text, episode_id="episode-b", podcast_name="All-In Podcast"),
    ]

    clusters = CrossSourceEngine().build_clusters(claims)

    assert len(clusters) == 1
    assert clusters[0].corroboration_count == 1


def test_apply_corroboration_updates_scored_claims(sample_claim, phase32_profiles):
    from .conftest import make_claim

    first = sample_claim
    second = make_claim(
        first.claim_text,
        episode_id="episode-b",
        podcast_name="All-In Podcast",
        speaker=first.speaker,
    )
    clusters = CrossSourceEngine().build_clusters([first, second])
    assert clusters

    novelty = NoveltyEngine().score(first, [second])
    relevance = RelevanceEngine().score(first, phase32_profiles)
    importance = ImportanceEngine().score(first, novelty, relevance)
    scored = [
        ScoredClaim(
            claim=first,
            novelty=novelty,
            relevance=relevance,
            importance=importance,
        )
    ]

    updated = CrossSourceEngine().apply_corroboration(scored, clusters)

    assert updated[0].corroboration_cluster_id == clusters[0].cluster_id
    assert updated[0].corroboration_count == clusters[0].corroboration_count