import unittest

from app.ingest.chunking import (DocMeta, build_chunks, fixed_chunks, is_heading,
                                 split_blocks, structure_chunks)
from app.ingest.loaders import html_to_text, parse_front_matter, split_pages
from app.models import Page
from app.text import count_tokens

META = DocMeta("DOC", "Acme Policy", "v1", "Basic", ("agent",))
FIXED = {"strategy": "fixed", "chunk_size": 20, "chunk_overlap": 5, "min_chunk_chars": 10,
         "keep_tables_whole": False, "prepend_heading": False}
STRUCT = dict(FIXED, strategy="structure", chunk_size=60, keep_tables_whole=True,
              prepend_heading=True)


class Headings(unittest.TestCase):
    def test_heading_detection(self):
        for line in ("## 2. Benefits", "4.2 Waiting Period", "EXCLUSIONS", "Section 5 Claims"):
            self.assertTrue(is_heading(line), line)
        for line in ("The waiting period is 24 months.", "| Room rent | 6,000 |", "ok"):
            self.assertFalse(is_heading(line), line)

    def test_blocks_split_tables_and_paragraphs(self):
        text = "## Benefits\nIntro line.\n| A | B |\n|---|---|\n| 1 | 2 |\nTail text."
        kinds = [b.kind for b in split_blocks(text)]
        self.assertEqual(kinds, ["heading", "text", "table", "text"])


class FixedChunking(unittest.TestCase):
    def test_overlap_and_page_boundaries(self):
        text = " ".join(f"w{i}" for i in range(50))
        chunks = fixed_chunks(META, [Page(1, text), Page(2, "second page has its own text here")],
                              FIXED)
        self.assertGreater(len([c for c in chunks if c.page == 1]), 2)
        self.assertEqual({c.page for c in chunks}, {1, 2})
        self.assertTrue(all(count_tokens(c.text) <= 20 for c in chunks))
        first, second = chunks[0].text.split(), chunks[1].text.split()
        self.assertEqual(first[-5:], second[:5])  # 5-token overlap

    def test_invalid_overlap_rejected(self):
        with self.assertRaises(ValueError):
            fixed_chunks(META, [Page(1, "x " * 50)], dict(FIXED, chunk_overlap=20))

    def test_chunk_ids_are_deterministic_and_unique(self):
        pages = [Page(1, " ".join(f"w{i}" for i in range(80)))]
        a, b = fixed_chunks(META, pages, FIXED), fixed_chunks(META, pages, FIXED)
        self.assertEqual([c.chunk_id for c in a], [c.chunk_id for c in b])
        self.assertEqual(len({c.chunk_id for c in a}), len(a))


class StructureChunking(unittest.TestCase):
    PAGE = ("## 2. Benefits\nIntro text about the benefit table in this policy wording.\n"
            "| Benefit | Limit |\n|---|---|\n| Room rent | 6,000 |\n| ICU | 12,000 |")

    def test_table_kept_whole_with_title_and_heading(self):
        chunks = structure_chunks(META, [Page(1, self.PAGE)], STRUCT)
        table = [c for c in chunks if c.kind == "table"]
        self.assertEqual(len(table), 1)
        self.assertIn("| Room rent | 6,000 |", table[0].text)
        self.assertIn("| ICU | 12,000 |", table[0].text)
        self.assertTrue(table[0].text.startswith("Acme Policy\n2. Benefits"))
        self.assertEqual(table[0].section, "2. Benefits")

    def test_oversized_table_splits_by_rows_and_repeats_header(self):
        rows = "\n".join(f"| Item {i} | {i * 1000} |" for i in range(40))
        page = f"## Table\n| Item | Cost |\n|---|---|\n{rows}"
        chunks = [c for c in structure_chunks(META, [Page(1, page)],
                                              dict(STRUCT, chunk_size=40)) if c.kind == "table"]
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertIn("| Item | Cost |", c.text)
        body = "\n".join(c.text for c in chunks)
        self.assertEqual(sum(f"| Item {i} |" in body for i in range(40)), 40)

    def test_heading_carries_across_pages(self):
        pages = [Page(1, "## 4. Exclusions\nCosmetic surgery is not covered by this policy."),
                 Page(2, "Dental treatment is excluded unless caused by an accident.")]
        chunks = structure_chunks(META, pages, STRUCT)
        self.assertEqual([c.section for c in chunks], ["4. Exclusions", "4. Exclusions"])
        self.assertEqual([c.page for c in chunks], [1, 2])

    def test_tables_are_ordinary_text_when_not_kept_whole(self):
        chunks = structure_chunks(META, [Page(1, self.PAGE)],
                                  dict(STRUCT, keep_tables_whole=False))
        self.assertTrue(all(c.kind == "text" for c in chunks))

    def test_unknown_strategy_rejected(self):
        with self.assertRaises(ValueError):
            build_chunks(META, [Page(1, "x")], dict(FIXED, strategy="magic"))


class Loaders(unittest.TestCase):
    def test_front_matter_and_page_markers(self):
        raw = "---\ntitle: T\nallowed_groups: [a]\n---\n<!-- page 1 -->\nOne\n<!-- page 2 -->\nTwo"
        front, body = parse_front_matter(raw)
        pages = split_pages(body)
        self.assertEqual(front["title"], "T")
        self.assertEqual([(p.number, p.text) for p in pages], [(1, "One"), (2, "Two")])

    def test_no_markers_means_single_page(self):
        self.assertEqual([p.number for p in split_pages("just text")], [1])

    def test_html_to_text_drops_scripts(self):
        html = "<html><script>x=1</script><h1>Title</h1><p>Body text</p></html>"
        text = html_to_text(html)
        self.assertIn("Title", text)
        self.assertIn("Body text", text)
        self.assertNotIn("x=1", text)


if __name__ == "__main__":
    unittest.main()
