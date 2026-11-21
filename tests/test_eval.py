import tempfile
import unittest
from pathlib import Path

from eval.calibrate import choose_threshold
from eval.report import aggregate, paired_test, render
from eval.runner import calibration_ids, gold_pages, run_stage, save_results, select_questions
from eval.judge import LexicalJudge
from scripts.validate_gold import read_csv
from tests.helpers import offline_pipeline


class Helpers(unittest.TestCase):
    def test_gold_pages_for_each_question_shape(self):
        base = {"doc_id": "A", "page": "3", "doc_id_2": "", "page_2": ""}
        self.assertEqual(gold_pages(base), {("A", 3)})
        self.assertEqual(gold_pages(dict(base, page_2="5")), {("A", 3), ("A", 5)})
        self.assertEqual(gold_pages(dict(base, doc_id_2="B", page_2="1")), {("A", 3), ("B", 1)})
        self.assertEqual(gold_pages({"doc_id": "", "page": "", "doc_id_2": "", "page_2": ""}),
                         set())

    def test_calibration_split_is_deterministic_and_sized(self):
        ids = [f"Q{i}" for i in range(100)]
        a, b = calibration_ids(ids, 0.2, 42), calibration_ids(list(reversed(ids)), 0.2, 42)
        self.assertEqual((len(a), a), (20, b))
        self.assertNotEqual(a, calibration_ids(ids, 0.2, 7))

    def test_only_verified_questions_run_by_default(self):
        rows = [{"status": "todo"}, {"status": "drafted"}, {"status": "verified"}]
        self.assertEqual(len(select_questions(rows, False)), 1)
        self.assertEqual(len(select_questions(rows, True)), 2)

    def test_threshold_separates_the_two_classes(self):
        t = choose_threshold([0.8, 0.9, 0.7], [0.1, 0.2, 0.3])
        self.assertTrue(0.3 < t <= 0.7)
        self.assertIsNone(choose_threshold([], [0.1]))
        self.assertIsNone(choose_threshold([0.5], []))

    def test_threshold_handles_overlapping_scores(self):
        t = choose_threshold([0.4, 0.6, 0.9], [0.2, 0.5])
        self.assertTrue(0.2 < t < 0.9)


class OfflineRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings, cls.pipe, cls.dataset, _ = offline_pipeline("stage4_rerank")
        rows = read_csv(cls.dataset.gold_csv)
        cls.result = run_stage(cls.pipe, LexicalJudge(), rows, cls.settings, True, "synthetic")

    def test_every_question_gets_a_record(self):
        self.assertEqual(len(self.result["records"]), 12)
        self.assertTrue(self.result["offline"])

    def test_aggregate_counts_are_consistent(self):
        agg = aggregate(self.result)
        self.assertEqual(agg["n_answerable"], 10)
        hits, n = agg["hit@5"]
        self.assertEqual(n, 10)
        self.assertGreaterEqual(hits, 8)  # lexical retrieval finds the right page for most
        self.assertLessEqual(agg["hit@1"][0], agg["hit@5"][0])
        self.assertTrue(0 <= agg["mrr"] <= 1)

    def test_unanswerable_questions_are_refused(self):
        unans = [r for r in self.result["records"] if not r["answerable"]]
        self.assertEqual(len(unans), 2)
        self.assertTrue(all(r["refused"] and r["correct"] for r in unans))

    def test_compare_questions_search_all_versions(self):
        rec = next(r for r in self.result["records"] if r["type"] == "compare_two")
        self.assertIn("SAMPLE_POLICY_V1", {d for d, _, _ in rec["retrieved"]})

    def test_report_renders_with_offline_warning_and_pvalue(self):
        later = {**self.result, "stage": "stage5_structure"}
        text = render([self.result, later])
        self.assertIn("WARNING", text)
        self.assertIn("stage5_structure", text)
        self.assertEqual(paired_test(self.result, later), 1.0)  # identical runs

    def test_results_roundtrip_to_disk(self):
        path = Path(tempfile.mkdtemp()) / "offline" / "r.json"
        save_results(self.result, path)
        self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
