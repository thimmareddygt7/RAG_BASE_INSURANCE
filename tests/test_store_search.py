import unittest

from app.embeddings import HashingEmbedder
from app.models import Chunk, Hit
from app.search.fusion import rrf
from app.store.memory import InMemoryStore


def chunk(cid, doc, text, groups=("agent",), latest=True, page=1):
    return Chunk(cid, doc, doc, "v1", "P", page, "", text, groups, "text", latest)


def build(*chunks):
    emb, store = HashingEmbedder(64), InMemoryStore()
    store.upsert(list(chunks), emb.embed_documents([c.text for c in chunks]))
    return emb, store


class Permissions(unittest.TestCase):
    def setUp(self):
        self.emb, self.store = build(
            chunk("1", "PUBLIC", "waiting period is 24 months", ("policyholder", "agent")),
            chunk("2", "SECRET", "gold tier commission is 9% CANARY", ("agent",)))

    def test_dense_filter_applies_before_scoring(self):
        q = self.emb.embed_query("gold tier commission")
        ids = {h.chunk.doc_id for h in self.store.search_dense(q, 10, ["policyholder"])}
        self.assertEqual(ids, {"PUBLIC"})
        ids = {h.chunk.doc_id for h in self.store.search_dense(q, 10, ["agent"])}
        self.assertEqual(ids, {"PUBLIC", "SECRET"})

    def test_sparse_filter_and_no_hits_for_restricted_terms(self):
        self.assertEqual(self.store.search_sparse("commission CANARY", 5, ["policyholder"]), [])
        hits = self.store.search_sparse("commission", 5, ["agent"])
        self.assertEqual(hits[0].chunk.doc_id, "SECRET")

    def test_unknown_group_sees_nothing(self):
        q = self.emb.embed_query("anything")
        self.assertEqual(self.store.search_dense(q, 10, ["intruder"]), [])
        self.assertEqual(self.store.list_docs(["intruder"]), [])

    def test_list_docs_respects_groups(self):
        self.assertEqual([d["doc_id"] for d in self.store.list_docs(["policyholder"])], ["PUBLIC"])


class VersionsAndDelete(unittest.TestCase):
    def test_latest_only_hides_old_versions(self):
        emb, store = build(chunk("1", "V1", "room rent 5,000", ("agent",), latest=False),
                           chunk("2", "V2", "room rent 6,000", ("agent",), latest=True))
        q = emb.embed_query("room rent")
        self.assertEqual({h.chunk.doc_id for h in store.search_dense(q, 5, ["agent"], True)},
                         {"V2"})
        self.assertEqual({h.chunk.doc_id for h in store.search_dense(q, 5, ["agent"], False)},
                         {"V1", "V2"})
        store.set_is_latest("V1", True)
        self.assertEqual(len(store.search_dense(q, 5, ["agent"], True)), 2)

    def test_delete_doc(self):
        _, store = build(chunk("1", "A", "x y z"), chunk("2", "B", "x y z"))
        self.assertEqual(store.delete_doc("A"), 1)
        self.assertEqual(store.count(), 1)


class Ranking(unittest.TestCase):
    def test_bm25_prefers_rare_matching_terms(self):
        _, store = build(chunk("1", "A", "cataract surgery waiting period twelve months"),
                         chunk("2", "B", "general waiting period applies to claims"),
                         chunk("3", "C", "ambulance cover per hospitalisation"))
        top = store.search_sparse("cataract waiting", 3, ["agent"])[0]
        self.assertEqual(top.chunk.doc_id, "A")

    def test_rrf_rewards_agreement_and_is_deterministic(self):
        a, b, c = (chunk(i, i, i) for i in "abc")
        dense = [Hit(a, 0.9, "dense"), Hit(b, 0.8, "dense"), Hit(c, 0.1, "dense")]
        sparse = [Hit(b, 5.0, "sparse"), Hit(a, 4.0, "sparse")]
        fused = rrf([dense, sparse], k=60)
        self.assertEqual([h.chunk.chunk_id for h in fused], ["a", "b", "c"])
        self.assertAlmostEqual(fused[0].score, 1 / 61 + 1 / 62)
        self.assertEqual(rrf([dense, sparse], k=60, limit=1)[0].chunk.chunk_id, "a")


if __name__ == "__main__":
    unittest.main()
