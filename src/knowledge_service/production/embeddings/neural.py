"""Local neural-style embeddings using TF-IDF vectors (numpy, no external ML deps)."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Sequence

from .provider import EmbeddingProvider


TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?", re.IGNORECASE)
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "as", "is", "was", "are", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "that", "this", "these", "those", "it", "its", "they", "them", "their", "we", "you",
    "i", "he", "she", "his", "her", "my", "your", "our", "not", "no", "so", "if", "just",
    "like", "about", "into", "than", "then", "there", "when", "what", "which", "who",
    "how", "all", "also", "very", "can", "know", "think", "mean", "really", "going",
    "get", "got", "one", "two", "way", "make", "made", "say", "said", "because",
}


class LocalNeuralEmbeddingProvider(EmbeddingProvider):
    """Corpus-aware TF-IDF embeddings — materially better semantic clustering than hash buckets."""

    name = "local_neural_tfidf"
    dimensions = 384

    def __init__(self, max_features: int = 384):
        self.max_features = max_features
        self._vocab: Dict[str, int] = {}
        self._idf: List[float] = [1.0] * max_features
        self._fitted = False

    def fit(self, corpus: Sequence[str]) -> None:
        if not corpus:
            return
        doc_freq: Counter[str] = Counter()
        docs = 0
        for text in corpus:
            tokens = self._tokens(text)
            if not tokens:
                continue
            docs += 1
            for token in set(tokens):
                doc_freq[token] += 1

        ranked = [token for token, _ in doc_freq.most_common(self.max_features)]
        self._vocab = {token: index for index, token in enumerate(ranked)}
        self._idf = [1.0] * self.max_features
        for token, index in self._vocab.items():
            df = doc_freq[token]
            self._idf[index] = math.log((1 + docs) / (1 + df)) + 1.0
        self._fitted = True

    def embed(self, text: str) -> List[float]:
        vector = [0.0] * self.max_features
        tokens = self._tokens(text)
        if not tokens:
            return vector
        counts = Counter(tokens)
        max_tf = max(counts.values()) if counts else 1
        for token, count in counts.items():
            index = self._vocab.get(token)
            if index is None:
                continue
            tf = 0.5 + 0.5 * (count / max_tf)
            vector[index] = tf * self._idf[index]
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0.0:
            return vector
        return [value / magnitude for value in vector]

    def _tokens(self, text: str) -> List[str]:
        return [
            token.lower()
            for token in TOKEN_RE.findall(text or "")
            if token.lower() not in STOPWORDS and len(token) > 2
        ]