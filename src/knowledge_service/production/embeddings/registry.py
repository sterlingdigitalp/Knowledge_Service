"""Embedding provider registry — configurable backend selection."""

from __future__ import annotations

import importlib.util
from typing import Optional, Sequence

from ...retrieval.embedding import embed_text as hash_embed
from .neural import LocalNeuralEmbeddingProvider
from .provider import EmbeddingProvider


_active_provider: Optional[EmbeddingProvider] = None
DEFAULT_PROVIDER = "local_neural"


class HashEmbeddingProvider(EmbeddingProvider):
    name = "hash"
    dimensions = 64

    def embed(self, text: str) -> list[float]:
        return hash_embed(text, self.dimensions)


def get_embedding_provider(name: str | None = None) -> EmbeddingProvider:
    global _active_provider
    selected = name or DEFAULT_PROVIDER
    if _active_provider is not None and getattr(_active_provider, "_configured_name", None) == selected:
        return _active_provider

    if selected == "local_neural":
        provider: EmbeddingProvider = LocalNeuralEmbeddingProvider()
    elif selected == "sentence_transformers":
        provider = _sentence_transformer_provider()
    elif selected == "hash":
        provider = HashEmbeddingProvider()
    else:
        provider = LocalNeuralEmbeddingProvider()
    provider._configured_name = selected  # type: ignore[attr-defined]
    _active_provider = provider
    return provider


def configure_embeddings(name: str, corpus: Sequence[str] | None = None) -> EmbeddingProvider:
    global _active_provider
    _active_provider = None
    provider = get_embedding_provider(name)
    if corpus:
        provider.fit(corpus)
    _active_provider = provider
    return provider


def embed_text(text: str) -> list[float]:
    return get_embedding_provider().embed(text)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    return sum(left[i] * right[i] for i in range(size))


def _sentence_transformer_provider() -> EmbeddingProvider:
    if importlib.util.find_spec("sentence_transformers") is None:
        return LocalNeuralEmbeddingProvider()
    from .sentence_transformer import SentenceTransformerEmbeddingProvider
    return SentenceTransformerEmbeddingProvider()


def reset_provider() -> None:
    global _active_provider
    _active_provider = None