import json
import shutil
import tempfile
import unittest
from pathlib import Path

from app.config import load_settings
from app.embeddings import HashingEmbedder
from app.ingest.indexer import index_fingerprint, sync_corpus
from app.ingest.sources import SourceDoc, compute_latest, version_key
from app.store.memory import InMemoryStore


ROOM_RENT = "Room rent under this policy wording is {} per day for every insured person."


def make_doc(tmp: Path, doc_id: str, text: str, version="v1", product="P",
             groups=("agent",)) -> SourceDoc:
    path = tmp / f"{doc_id}.md"
    path.write_text(text, encoding="utf-8")
    return SourceDoc(doc_id, "t", "Ins", product, version, path, groups)


class Versions(unittest.TestCase):
    def test_version_ordering(self):
        self.assertLess(version_key("v2"), version_key("v10"))
        self.assertLess(version_key("2023-12"), version_key("2024-01"))

    def test_only_highest_version_is_latest_per_product(self):
        docs = [SourceDoc("A1", "", "Ins", "Basic", "v1", None, ("agent",)),
                SourceDoc("A2", "", "Ins", "Basic", "v2", None, ("agent",)),
                SourceDoc("B1", "", "Ins", "Gold", "v1", None, ("agent",)),
                SourceDoc("C", "", "Ins", "", "", None, ("agent",))]
        self.assertEqual(compute_latest(docs), {"A1": False, "A2": True, "B1": True, "C": True})


class IncrementalIndexing(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cfg = load_settings(env={}).cfg
        self.store, self.emb = InMemoryStore(), HashingEmbedder(32)
        self.manifest = self.tmp / "m.json"
        self.a = make_doc(self.tmp, "A", "Doc A talks about cataract waiting periods and limits.")
        self.b = make_doc(self.tmp, "B", "Doc B talks about maternity benefits and ambulance.")

    def sync(self, docs):
        self.store.calls.clear()
        return sync_corpus(docs, self.store, self.emb, self.cfg, self.manifest)

    def test_first_run_adds_everything_and_rerun_does_nothing(self):
        r1 = self.sync([self.a, self.b])
        self.assertEqual(sorted(r1.added), ["A", "B"])
        r2 = self.sync([self.a, self.b])
        self.assertEqual(sorted(r2.unchanged), ["A", "B"])
        self.assertEqual(self.store.calls, [])  # nothing touched

    def test_adding_one_file_touches_only_its_own_chunks(self):
        self.sync([self.a])
        c = make_doc(self.tmp, "C", "Doc C talks about renewal grace periods and free look.")
        report = self.sync([self.a, c])
        self.assertEqual((report.added, report.unchanged), (["C"], ["A"]))
        self.assertEqual({doc for _, doc in self.store.calls}, {"C"})

    def test_changed_file_replaces_only_its_chunks(self):
        self.sync([self.a, self.b])
        self.a.path.write_text("Doc A now says the cataract waiting period is twelve months.")
        report = self.sync([self.a, self.b])
        self.assertEqual((report.updated, report.unchanged), (["A"], ["B"]))
        self.assertEqual({doc for _, doc in self.store.calls}, {"A"})
        texts = " ".join(r.chunk.text for r in self.store._rows.values() if r.chunk.doc_id == "A")
        self.assertIn("twelve months", texts)
        self.assertNotIn("limits", texts)  # stale chunk gone

    def test_removed_source_deletes_its_chunks(self):
        self.sync([self.a, self.b])
        report = self.sync([self.a])
        self.assertEqual(report.removed, ["B"])
        self.assertEqual({r.chunk.doc_id for r in self.store._rows.values()}, {"A"})

    def test_changing_chunking_config_triggers_reindex(self):
        self.sync([self.a])
        self.cfg["ingest"] = dict(self.cfg["ingest"], strategy="structure")
        self.assertEqual(self.sync([self.a]).updated, ["A"])

    def test_changing_permissions_triggers_reindex(self):
        self.sync([self.a])
        opened = SourceDoc("A", "t", "Ins", "P", "v1", self.a.path, ("agent", "admin"))
        self.assertEqual(self.sync([opened]).updated, ["A"])

    def test_new_version_flips_old_one_to_not_latest_without_reindex(self):
        v1 = make_doc(self.tmp, "V1", ROOM_RENT.format("5,000"), "v1", "Basic")
        self.sync([SourceDoc("V1", "t", "Ins", "Basic", "v1", v1.path, ("agent",), True)])
        v2 = make_doc(self.tmp, "V2", ROOM_RENT.format("6,000"), "v2", "Basic")
        docs = [SourceDoc("V1", "t", "Ins", "Basic", "v1", v1.path, ("agent",), False),
                SourceDoc("V2", "t", "Ins", "Basic", "v2", v2.path, ("agent",), True)]
        report = self.sync(docs)
        self.assertEqual((report.added, report.unchanged), (["V2"], ["V1"]))
        flags = {r.chunk.doc_id: r.chunk.is_latest for r in self.store._rows.values()}
        self.assertEqual(flags, {"V1": False, "V2": True})

    def test_wiped_store_ignores_stale_manifest(self):
        self.sync([self.a])
        self.store = InMemoryStore()
        self.assertEqual(self.sync([self.a]).added, ["A"])

    def test_missing_file_is_reported_not_fatal(self):
        ghost = SourceDoc("G", "t", "I", "P", "v1", self.tmp / "nope.md", ("agent",))
        self.assertEqual(self.sync([ghost]).missing, ["G"])

    def test_document_with_no_usable_text_is_flagged_empty(self):
        tiny = make_doc(self.tmp, "T", "too short")
        self.assertEqual(self.sync([tiny]).empty, ["T"])

    def test_manifest_is_valid_json(self):
        self.sync([self.a])
        self.assertIn("A", json.loads(self.manifest.read_text()))

    def test_fingerprint_changes_with_embedding_model(self):
        cfg2 = json.loads(json.dumps(self.cfg))
        cfg2["embedding"]["model"] = "other"
        self.assertNotEqual(index_fingerprint(self.cfg), index_fingerprint(cfg2))


if __name__ == "__main__":
    unittest.main()
