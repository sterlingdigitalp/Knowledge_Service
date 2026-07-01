"""Deterministic lightweight embeddings for local semantic retrieval.

The production boundary is intentionally small: callers provide text and receive
a stable vector. Deployments can replace this module with an external embedding
provider without changing transcript processing or quote retrieval contracts.
"""

import hashlib
import math
import re
from typing import List


EMBEDDING_DIMENSIONS = 64
TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?", re.IGNORECASE)


def tokenize(text: str) -> List[str]:
    return [token.lower() for token in TOKEN_RE.findall(text or "")]


def embed_text(text: str, dimensions: int = EMBEDDING_DIMENSIONS) -> List[float]:
    vector = [0.0] * dimensions
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign

    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0.0:
        return vector
    return [value / magnitude for value in vector]


def cosine_similarity(left: List[float], right: List[float]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    return sum(left[i] * right[i] for i in range(size))
