"""Embedding backends: a real sentence-transformers model and a deterministic offline stand-in."""

from __future__ import annotations

import hashlib
import math
from typing import Protocol

from app.text import words


class Embedder(Protocol):
    dimension: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class SentenceTransformerEmbedder:
    """Real embedder (BAAI/bge-small-en-v1.5 by default). Imported lazily."""

    def __init__(self, model_name: str, dimension: int, query_instruction: str = "",
                 batch_size: int = 32):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.dimension = dimension
        self._instruction = query_instruction
        self._batch = batch_size

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, batch_size=self._batch, normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        vector = self._model.encode([self._instruction + text], normalize_embeddings=True)[0]
        return vector.tolist()


class HashingEmbedder:
    """Deterministic bag-of-words hashing embedder.

    Offline stand-in for tests and the no-API-key demo. It is NOT a semantic model.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dimension
        for word in words(text):
            digest = hashlib.md5(word.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[index] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
