"""In-memory store used by tests and the offline demo.

It applies the same permission and version filters as the Qdrant store, before scoring.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from app.models import Chunk, Hit
from app.text import words


@dataclass
class _Row:
    chunk: Chunk
    vector: list[float]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class InMemoryStore:
    def __init__(self) -> None:
        self._rows: dict[str, _Row] = {}
        self.calls: list[tuple[str, str]] = []  # ("upsert"|"delete", doc_id), for tests

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        for chunk, vector in zip(chunks, vectors, strict=True):
            self._rows[chunk.chunk_id] = _Row(chunk, vector)
            self.calls.append(("upsert", chunk.doc_id))

    def delete_doc(self, doc_id: str) -> int:
        ids = [cid for cid, r in self._rows.items() if r.chunk.doc_id == doc_id]
        for cid in ids:
            del self._rows[cid]
        self.calls.append(("delete", doc_id))
        return len(ids)

    def set_is_latest(self, doc_id: str, flag: bool) -> None:
        for r in self._rows.values():
            if r.chunk.doc_id == doc_id:
                r.chunk = replace(r.chunk, is_latest=flag)

    def _visible(self, groups: list[str], latest_only: bool) -> list[_Row]:
        allowed = set(groups)
        return [
            r for r in self._rows.values()
            if allowed & set(r.chunk.allowed_groups) and (r.chunk.is_latest or not latest_only)
        ]

    def search_dense(self, vector, k, groups, latest_only=False):
        scored = [(_cosine(vector, r.vector), r) for r in self._visible(groups, latest_only)]
        scored.sort(key=lambda p: p[0], reverse=True)
        return [Hit(r.chunk, s, "dense") for s, r in scored[:k]]

    def search_sparse(self, query, k, groups, latest_only=False):
        rows = self._visible(groups, latest_only)  # statistics use permitted chunks only
        if not rows:
            return []
        docs = [words(r.chunk.text) for r in rows]
        avg_len = sum(len(d) for d in docs) / len(docs) or 1.0
        n = len(docs)
        df: dict[str, int] = {}
        for d in docs:
            for term in set(d):
                df[term] = df.get(term, 0) + 1
        q_terms = set(words(query))
        k1, b = 1.5, 0.75
        scored = []
        for r, d in zip(rows, docs, strict=True):
            score = 0.0
            for term in q_terms:
                tf = d.count(term)
                if not tf:
                    continue
                idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(d) / avg_len))
            if score > 0:
                scored.append((score, r))
        scored.sort(key=lambda p: p[0], reverse=True)
        return [Hit(r.chunk, s, "sparse") for s, r in scored[:k]]

    def list_docs(self, groups, latest_only=False):
        docs: dict[str, dict] = {}
        for r in self._visible(groups, latest_only):
            c = r.chunk
            d = docs.setdefault(c.doc_id, {"doc_id": c.doc_id, "title": c.title,
                                           "version": c.version, "is_latest": c.is_latest,
                                           "chunks": 0})
            d["chunks"] += 1
        return sorted(docs.values(), key=lambda d: d["doc_id"])

    def count(self) -> int:
        return len(self._rows)
