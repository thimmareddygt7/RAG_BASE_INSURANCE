import unittest

from scripts.validate_gold import COLUMNS, read_csv, validate
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = {"DOC1", "DOC2"}


def row(**kw):
    base = {c: "" for c in COLUMNS}
    base.update(id="Q1", type="plain_text", question="Is X covered?", answerable="yes",
                status="verified", doc_id="DOC1", page="3", gold_answer="Yes",
                evidence_text="X is covered.")
    base.update(kw)
    return base


class GoldValidation(unittest.TestCase):
    def test_shipped_gold_file_is_structurally_valid(self):
        rows = read_csv(ROOT / "data/gold/gold_questions.csv")
        sources = {r["doc_id"] for r in read_csv(ROOT / "data/gold/sources.csv")}
        errors, _ = validate(rows, sources)
        self.assertEqual(errors, [])

    def test_complete_row_passes(self):
        self.assertEqual(validate([row()], SOURCES)[0], [])

    def test_unknown_doc_and_zero_indexed_page_fail(self):
        errors, _ = validate([row(doc_id="NOPE", page="0")], SOURCES)
        self.assertTrue(any("not in sources" in e for e in errors))
        self.assertTrue(any("1-indexed" in e for e in errors))

    def test_duplicate_ids_fail(self):
        errors, _ = validate([row(), row()], SOURCES)
        self.assertTrue(any("Duplicate id" in e for e in errors))

    def test_unanswerable_rules(self):
        good = row(type="unanswerable", answerable="no", doc_id="", page="",
                   gold_answer="not in the documents", evidence_text="")
        self.assertEqual(validate([good], SOURCES)[0], [])
        bad = row(type="unanswerable", answerable="no", gold_answer="Maybe")
        self.assertTrue(validate([bad], SOURCES)[0])

    def test_answerable_flag_must_match_type(self):
        errors, _ = validate([row(answerable="no")], SOURCES)
        self.assertTrue(any("answerable" in e for e in errors))

    def test_cross_reference_and_compare_need_second_page(self):
        self.assertTrue(validate([row(type="cross_reference")], SOURCES)[0])
        self.assertTrue(validate([row(type="compare_two", doc_id_2="DOC2")], SOURCES)[0])
        ok = row(type="compare_two", doc_id_2="DOC2", page_2="4")
        self.assertEqual(validate([ok], SOURCES)[0], [])

    def test_todo_rows_skip_content_checks(self):
        self.assertEqual(validate([row(status="todo", doc_id="", page="", gold_answer="")],
                                  SOURCES)[0], [])

    def test_strict_mode_requires_finished_benchmark(self):
        errors, _ = validate([row()], SOURCES, strict=True)
        self.assertTrue(any("at least 100" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
