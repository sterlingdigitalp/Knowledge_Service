"""Optional sentence-transformers backend."""

from __future__ import annotations

from typing import List, Sequence

from .provider import EmbeddingProvider


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    name = "sentence_transformers"
    dimensions = 384

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)
        self.dimensions = int(self._model.get_sentence_embedding_dimension())

    def embed(self, text: str) -> List[float]:
        vector = self._model.encode(text or "", normalize_embeddings=True)
        return [float(value) for value in vector]

    def embed_batch(self, texts: Sequence[str]) -> List[List[float]]:
        vectors = self._model.encode(list(texts), normalize_embeddings=True)
        return [[float(value) for value in row] for row in vectors]