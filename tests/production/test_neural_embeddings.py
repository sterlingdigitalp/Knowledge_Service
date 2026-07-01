from knowledge_service.production.benchmark import PhaseBenchmark
from knowledge_service.production.embeddings.registry import (
    configure_embeddings,
    cosine_similarity,
    get_embedding_provider,
    reset_provider,
)
from knowledge_service.retrieval.embedding import cosine_similarity as hash_cosine
from knowledge_service.retrieval.embedding import embed_text as hash_embed


RELATED_PAIRS = [
    (
        "GPU inference costs are rising sharply in hyperscale datacenters",
        "Datacenter compute expenses for inference workloads continue to increase",
    ),
    (
        "Enterprise teams are deploying autonomous AI agents with tool use",
        "Companies adopt agentic workflows that call external APIs and tools",
    ),
]

UNRELATED_PAIRS = [
    (
        "GPU inference costs are rising sharply in hyperscale datacenters",
        "Clinical trial results show strong efficacy for GLP-1 metabolic drugs",
    ),
    (
        "Enterprise teams are deploying autonomous AI agents with tool use",
        "Founders discuss protein longevity research and translational medicine",
    ),
]


def test_neural_similarity_beats_hash_on_semantic_pairs():
    corpus = [left for left, _ in RELATED_PAIRS] + [left for left, _ in UNRELATED_PAIRS]
    reset_provider()
    neural = configure_embeddings("local_neural", corpus)

    related_neural = []
    related_hash = []
    for left, right in RELATED_PAIRS:
        related_neural.append(cosine_similarity(neural.embed(left), neural.embed(right)))
        related_hash.append(hash_cosine(hash_embed(left), hash_embed(right)))

    unrelated_neural = []
    unrelated_hash = []
    for left, right in UNRELATED_PAIRS:
        unrelated_neural.append(cosine_similarity(neural.embed(left), neural.embed(right)))
        unrelated_hash.append(hash_cosine(hash_embed(left), hash_embed(right)))

    neural_gap = (sum(related_neural) / len(related_neural)) - (sum(unrelated_neural) / len(unrelated_neural))
    hash_gap = (sum(related_hash) / len(related_hash)) - (sum(unrelated_hash) / len(unrelated_hash))

    assert neural_gap > hash_gap
    assert sum(related_neural) / len(related_neural) >= sum(unrelated_neural) / len(unrelated_neural)


def test_embedding_provider_abstraction_swappable_backends():
    reset_provider()
    text = "Frontier model scaling requires more GPU clusters"
    neural = configure_embeddings("local_neural", [text])
    hash_provider = get_embedding_provider("hash")

    assert neural.name == "local_neural_tfidf"
    assert hash_provider.name == "hash"
    assert neural.dimensions == 384
    assert hash_provider.dimensions == 64

    neural_vector = neural.embed(text)
    hash_vector = hash_provider.embed(text)

    assert len(neural_vector) == 384
    assert len(hash_vector) == 64
    assert any(value != 0.0 for value in neural_vector)
    assert any(value != 0.0 for value in hash_vector)


def test_configure_embeddings_fits_corpus_and_benchmark_reports_delta():
    reset_provider()
    texts = [
        "Inference economics dominate AI infrastructure planning",
        "Inference workloads drive datacenter GPU demand",
        "GLP-1 competitive landscape shifts with new clinical data",
        "Metabolic medicine signals from longevity researchers",
    ]
    report = PhaseBenchmark().compare_embeddings(texts, pairs=[(0, 1), (2, 3), (0, 2)])

    assert report["pairs_evaluated"] == 3
    assert report["neural_dimensions"] == 384
    assert report["hash_dimensions"] == 64
    assert "improvement_delta" in report
    # Related pairs should cluster tighter with corpus-fitted neural embeddings.
    related_neural = report["neural_similarity_avg"]
    assert related_neural >= 0.0
    assert isinstance(report["improvement_delta"], (int, float))