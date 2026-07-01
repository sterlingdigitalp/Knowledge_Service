"""Embedding provider abstraction — swappable neural backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Sequence


class EmbeddingProvider(ABC):
    name: str = "base"
    dimensions: int = 384

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        raise NotImplementedError

    def embed_batch(self, texts: Sequence[str]) -> List[List[float]]:
        return [self.embed(text) for text in texts]

    def fit(self, corpus: Sequence[str]) -> None:
        """Optional corpus warm-up for providers that need vocabulary statistics."""