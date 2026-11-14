import csv
import tempfile
import unittest
from pathlib import Path

from scripts.download import process, read_sources, sha256_of, write_sources

FIELDS = ["doc_id", "kind", "insurer", "product", "version", "source_url",
          "license_checked", "local_filename", "scanned", "allowed_groups", "sha256", "notes"]


def make_row(url, name="a.pdf", licensed="yes", sha=""):
    row = {f: "" for f in FIELDS}
    row.update(doc_id="D1", source_url=url, local_filename=name,
               license_checked=licensed, sha256=sha)
    return row


class Download(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.src = self.tmp / "source.pdf"
        self.src.write_bytes(b"%PDF-demo")
        self.url = self.src.as_uri()
        self.raw = self.tmp / "raw"
        self.raw.mkdir()

    def test_downloads_and_pins_hash(self):
        row = make_row(self.url)
        self.assertEqual(process(row, self.raw, pin=True), "downloaded")
        self.assertEqual(row["sha256"], sha256_of(self.src))

    def test_skips_unlicensed_and_placeholder_rows(self):
        self.assertEqual(process(make_row(self.url, licensed="no"), self.raw, False), "skipped")
        self.assertEqual(process(make_row("(paste official URL)"), self.raw, False), "skipped")
        self.assertFalse(any(self.raw.iterdir()))

    def test_rejects_path_traversal_filename(self):
        for name in ("../evil.pdf", "sub/x.pdf", ".hidden"):
            self.assertEqual(process(make_row(self.url, name=name), self.raw, False), "failed")

    def test_hash_mismatch_fails_and_removes_file(self):
        row = make_row(self.url, sha="0" * 64)
        self.assertEqual(process(row, self.raw, False), "failed")
        self.assertFalse((self.raw / "a.pdf").exists())

    def test_existing_file_is_kept(self):
        row = make_row(self.url)
        process(row, self.raw, True)
        self.assertEqual(process(row, self.raw, False), "exists")

    def test_sources_csv_roundtrip(self):
        path = self.tmp / "s.csv"
        write_sources(path, FIELDS, [make_row(self.url)])
        fields, rows = read_sources(path)
        self.assertEqual(fields, FIELDS)
        self.assertEqual(rows[0]["doc_id"], "D1")
        with path.open(newline="") as f:
            self.assertEqual(len(list(csv.reader(f))), 2)


if __name__ == "__main__":
    unittest.main()
