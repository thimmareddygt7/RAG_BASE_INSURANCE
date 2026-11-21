"""Vector store interface. Every search takes the caller's groups and filters INSIDE the query."""

from __future__ import annotations

from typing import Protocol

from app.models import Chunk, Hit


class VectorStore(Protocol):
    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...

    def delete_doc(self, doc_id: str) -> int: ...

    def set_is_latest(self, doc_id: str, flag: bool) -> None: ...

    def search_dense(self, vector: list[float], k: int, groups: list[str],
                     latest_only: bool = False) -> list[Hit]: ...

    def search_sparse(self, query: str, k: int, groups: list[str],
                      latest_only: bool = False) -> list[Hit]: ...

    def list_docs(self, groups: list[str], latest_only: bool = False) -> list[dict]: ...

    def count(self) -> int: ...
