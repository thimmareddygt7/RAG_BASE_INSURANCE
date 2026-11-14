"""Rerankers: a real cross-encoder and a lexical offline stand-in."""

from __future__ import annotations

from typing import Protocol

from app.models import Hit
from app.text import content_words


class Reranker(Protocol):
    def rerank(self, query: str, hits: list[Hit]) -> list[Hit]: ...


class CrossEncoderReranker:
    def __init__(self, model_name: str):
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, hits: list[Hit]) -> list[Hit]:
        if not hits:
            return []
        scores = self._model.predict([(query, h.chunk.text) for h in hits])
        ranked = sorted(zip(hits, scores, strict=True),
                        key=lambda pair: float(pair[1]), reverse=True)
        return [Hit(h.chunk, float(s), "rerank") for h, s in ranked]


class OverlapReranker:
    """Scores chunks by the share of query content words they contain (offline stand-in)."""

    def rerank(self, query: str, hits: list[Hit]) -> list[Hit]:
        q = set(content_words(query))
        out = []
        for h in hits:
            c = set(content_words(h.chunk.text))
            out.append(Hit(h.chunk, len(q & c) / max(len(q), 1), "rerank"))
        return sorted(out, key=lambda h: h.score, reverse=True)
