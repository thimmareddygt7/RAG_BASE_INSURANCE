"""Qdrant store: dense + sparse (BM25) vectors in one collection, filtered inside the query.

NOTE: written against qdrant-client 1.12 and fastembed. It has not been run against a live
Qdrant server in the build environment, so check it with `make index` before relying on it.
"""

from __future__ import annotations

from app.models import Chunk, Hit


class QdrantStore:
    def __init__(self, host: str, port: int, collection: str, dimension: int,
                 dense_name: str = "dense", sparse_name: str = "bm25",
                 sparse_model: str = "Qdrant/bm25", client=None):
        from fastembed import SparseTextEmbedding
        from qdrant_client import QdrantClient, models

        self._m = models
        self._client = client or QdrantClient(host=host, port=port)
        self._collection = collection
        self._dim = dimension
        self._dense = dense_name
        self._sparse = sparse_name
        self._sparse_model = SparseTextEmbedding(sparse_model)
        self._ensure_collection()

    # ---- setup -------------------------------------------------------------------------
    def _ensure_collection(self) -> None:
        m = self._m
        existing = {c.name for c in self._client.get_collections().collections}
        if self._collection in existing:
            return
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config={self._dense: m.VectorParams(size=self._dim,
                                                        distance=m.Distance.COSINE)},
            sparse_vectors_config={self._sparse: m.SparseVectorParams(modifier=m.Modifier.IDF)},
        )
        for field in ("allowed_groups", "doc_id"):
            self._client.create_payload_index(self._collection, field_name=field,
                                              field_schema=m.PayloadSchemaType.KEYWORD)
        self._client.create_payload_index(self._collection, field_name="is_latest",
                                          field_schema=m.PayloadSchemaType.BOOL)

    # ---- helpers -----------------------------------------------------------------------
    def _filter(self, groups: list[str], latest_only: bool):
        m = self._m
        must = [m.FieldCondition(key="allowed_groups", match=m.MatchAny(any=list(groups)))]
        if latest_only:
            must.append(m.FieldCondition(key="is_latest", match=m.MatchValue(value=True)))
        return m.Filter(must=must)

    def _doc_filter(self, doc_id: str):
        m = self._m
        return m.Filter(must=[m.FieldCondition(key="doc_id", match=m.MatchValue(value=doc_id))])

    @staticmethod
    def _to_hit(point, source: str) -> Hit:
        return Hit(Chunk.from_payload(str(point.id), point.payload), float(point.score), source)

    def _sparse_vec(self, emb):
        return self._m.SparseVector(indices=emb.indices.tolist(), values=emb.values.tolist())

    # ---- VectorStore API ---------------------------------------------------------------
    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if not chunks:
            return
        sparse = list(self._sparse_model.passage_embed([c.text for c in chunks]))
        points = [
            self._m.PointStruct(
                id=c.chunk_id,
                vector={self._dense: v, self._sparse: self._sparse_vec(s)},
                payload=c.payload(),
            )
            for c, v, s in zip(chunks, vectors, sparse, strict=True)
        ]
        self._client.upsert(collection_name=self._collection, points=points)

    def delete_doc(self, doc_id: str) -> int:
        flt = self._doc_filter(doc_id)
        n = self._client.count(self._collection, count_filter=flt, exact=True).count
        self._client.delete(self._collection,
                            points_selector=self._m.FilterSelector(filter=flt))
        return n

    def set_is_latest(self, doc_id: str, flag: bool) -> None:
        self._client.set_payload(self._collection, payload={"is_latest": flag},
                                 points=self._doc_filter(doc_id))

    def search_dense(self, vector, k, groups, latest_only=False):
        res = self._client.query_points(
            self._collection, query=vector, using=self._dense,
            query_filter=self._filter(groups, latest_only), limit=k, with_payload=True)
        return [self._to_hit(p, "dense") for p in res.points]

    def search_sparse(self, query, k, groups, latest_only=False):
        emb = list(self._sparse_model.query_embed(query))[0]
        res = self._client.query_points(
            self._collection, query=self._sparse_vec(emb), using=self._sparse,
            query_filter=self._filter(groups, latest_only), limit=k, with_payload=True)
        return [self._to_hit(p, "sparse") for p in res.points]

    def list_docs(self, groups, latest_only=False):
        docs: dict[str, dict] = {}
        offset = None
        while True:
            points, offset = self._client.scroll(
                self._collection, scroll_filter=self._filter(groups, latest_only),
                limit=256, offset=offset, with_payload=["doc_id", "title", "version", "is_latest"],
                with_vectors=False)
            for p in points:
                pl = p.payload
                d = docs.setdefault(pl["doc_id"], {"doc_id": pl["doc_id"], "title": pl["title"],
                                                   "version": pl["version"],
                                                   "is_latest": pl["is_latest"], "chunks": 0})
                d["chunks"] += 1
            if offset is None:
                break
        return sorted(docs.values(), key=lambda d: d["doc_id"])

    def count(self) -> int:
        return self._client.count(self._collection, exact=True).count
