"""Reciprocal rank fusion."""

from __future__ import annotations

from app.models import Hit


def rrf(rankings: list[list[Hit]], k: int = 60, limit: int | None = None) -> list[Hit]:
    """Fuse ranked lists: score(d) = sum over lists of 1 / (k + rank)."""
    scores: dict[str, float] = {}
    chunks = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            cid = hit.chunk.chunk_id
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            chunks[cid] = hit.chunk
    fused = [Hit(chunks[cid], s, "fused") for cid, s in scores.items()]
    fused.sort(key=lambda h: (-h.score, h.chunk.chunk_id))
    return fused[:limit] if limit else fused
