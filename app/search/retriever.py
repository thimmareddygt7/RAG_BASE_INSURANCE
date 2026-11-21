"""Retrieval: dense, optional sparse + RRF, optional reranker. Permissions pass into the store."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.embeddings import Embedder
from app.models import Hit
from app.rerank import Reranker
from app.search.fusion import rrf
from app.store.base import VectorStore


@dataclass
class RetrievalResult:
    hits: list[Hit]
    timings_ms: dict[str, float] = field(default_factory=dict)


class Retriever:
    def __init__(self, store: VectorStore, embedder: Embedder, reranker: Reranker | None,
                 cfg: dict[str, Any]):
        self._store = store
        self._embedder = embedder
        self._reranker = reranker
        self._cfg = cfg

    def retrieve(self, query: str, group: str, latest_only: bool = True) -> RetrievalResult:
        cfg = self._cfg
        groups = [group]
        k = int(cfg["candidate_k"])
        t0 = time.perf_counter()
        dense = self._store.search_dense(self._embedder.embed_query(query), k, groups, latest_only)
        timings = {"dense": (time.perf_counter() - t0) * 1000}

        hits = dense
        if cfg["hybrid_search"]:
            t1 = time.perf_counter()
            sparse = self._store.search_sparse(query, k, groups, latest_only)
            hits = rrf([dense, sparse], k=int(cfg["rrf_k"]), limit=k)
            timings["sparse_fusion"] = (time.perf_counter() - t1) * 1000

        if cfg["rerank"] and self._reranker is not None:
            t2 = time.perf_counter()
            hits = self._reranker.rerank(query, hits)
            timings["rerank"] = (time.perf_counter() - t2) * 1000
        return RetrievalResult(hits, timings)
