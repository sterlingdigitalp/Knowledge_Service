# Neural Embeddings

Phase 5 replaces Phase 4 hash-bucket embeddings with **corpus-aware neural-style vectors** for novelty scoring, theme clustering, and benchmark comparison. The embedding layer is swappable — local TF-IDF by default, optional `sentence-transformers` when installed.

## Modules

| Path | Class | Role |
|------|-------|------|
| `knowledge_service.production.embeddings.provider` | `EmbeddingProvider` | Abstract embedding interface |
| `knowledge_service.production.embeddings.neural` | `LocalNeuralEmbeddingProvider` | Corpus-fitted TF-IDF vectors (default) |
| `knowledge_service.production.embeddings.sentence_transformer` | `SentenceTransformerEmbeddingProvider` | Optional MiniLM backend |
| `knowledge_service.production.embeddings.registry` | `configure_embeddings`, `get_embedding_provider` | Provider selection and warm-up |

## Provider Backends

| Provider name | Class | Dimensions | When used |
|---------------|-------|------------|-----------|
| `local_neural` | `LocalNeuralEmbeddingProvider` | 384 | Default Phase 5 backend |
| `sentence_transformers` | `SentenceTransformerEmbeddingProvider` | model-dependent | When `sentence_transformers` package installed |
| `hash` | `HashEmbeddingProvider` | 64 | Phase 4 baseline (certification blocker if active) |

`LocalNeuralEmbeddingProvider` name: `local_neural_tfidf`.

## Local Neural Algorithm

Corpus-aware TF-IDF with L2 normalization — no external ML dependencies.

1. **Tokenize** — lowercase alphanumeric tokens; strip stopwords; minimum length 3.
2. **Fit vocabulary** — top `max_features` (384) tokens by document frequency across corpus.
3. **IDF** — `log((1 + docs) / (1 + df)) + 1.0` per vocabulary slot.
4. **Embed** — sublinear TF (`0.5 + 0.5 × count/max_tf`) × IDF; L2-normalize.

```text
dimensions     = 384
max_features   = 384
normalization  = L2 unit vector
```

## Registry API

```python
from knowledge_service.production.embeddings.registry import configure_embeddings, cosine_similarity

provider = configure_embeddings("local_neural", corpus=claim_texts)
vector = provider.embed("Frontier model scaling costs are rising")
similarity = cosine_similarity(vector_a, vector_b)
```

| Function | Purpose |
|----------|---------|
| `get_embedding_provider(name)` | Resolve provider singleton |
| `configure_embeddings(name, corpus)` | Reset provider, optional `fit(corpus)` |
| `embed_text(text)` | Embed via active provider |
| `cosine_similarity(left, right)` | Dot product on aligned dimensions |
| `reset_provider()` | Clear singleton (testing) |

## Corpus Re-embedding

`ProductionEnhancementLayer._reembed_corpus()` runs on every Phase 5 pipeline execution:

1. Fit provider on all claim texts.
2. Re-embed every `Claim` in `analyst/claims.jsonl`.
3. Re-embed every `ScoredClaim` in `analyst/scored_claims.jsonl`.
4. Recompute theme centroid embeddings from up to 20 claim texts per theme.

Downstream novelty and theme engines consume the updated vectors on subsequent analyst runs.

## Benchmark vs Hash

`PhaseBenchmark.compare_embeddings()` evaluates hash vs neural similarity on claim-text pairs:

| Metric | Source field |
|--------|--------------|
| Hash similarity avg | `hash_similarity_avg` |
| Neural similarity avg | `neural_similarity_avg` |
| Improvement delta | `improvement_delta` |
| Neural dimensions | `neural_dimensions` |

Saved to `state/production/benchmark_vs_phase41.json`.

## Configuration

Default provider is `local_neural`. Select `sentence_transformers` via registry when the package is available; registry falls back to `LocalNeuralEmbeddingProvider` if import fails.

## Certification Gate

Phase 5 certification fails when `production.embedding_provider == "hash"`. Active neural provider (`local_neural_tfidf` or `sentence_transformers`) is required.

## Entry Point

```python
from knowledge_service.production.embeddings.registry import configure_embeddings

provider = configure_embeddings("local_neural", corpus)
claim.embedding = provider.embed(claim.claim_text)
```

## Design Invariant

Embeddings are **corpus-fitted** — vocabulary and IDF statistics derive from the live claim corpus, not a static lexicon. Phase 5 never certifies on hash-only vectors.