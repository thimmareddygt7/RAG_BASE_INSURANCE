import csv
import json
import tempfile
import unittest
from pathlib import Path

from eval.audit import (AuditIncomplete, build_sheet, score_sheet, stratified_sample,
                        summary_markdown, write_sheet)
from eval.calibrate import choose_threshold, main as calibrate_main


def rec(i, qtype, correct=True):
    return {"id": f"Q{i:03d}", "type": qtype, "question": f"q{i}", "answer": f"a{i}",
            "refused": False, "citations": [], "correct": correct}


RECORDS = ([rec(i, "table_lookup") for i in range(1, 41)]
           + [rec(i, "plain_text") for i in range(41, 66)]
           + [rec(i, "cross_reference") for i in range(66, 81)]
           + [rec(i, "compare_two") for i in range(81, 91)]
           + [rec(i, "unanswerable") for i in range(91, 101)])


class Audit(unittest.TestCase):
    def test_sample_is_deterministic_and_covers_every_type_evenly(self):
        a, b = stratified_sample(RECORDS, 20), stratified_sample(list(reversed(RECORDS)), 20)
        self.assertEqual([r["id"] for r in a], [r["id"] for r in b])
        types = [r["type"] for r in a]
        self.assertEqual({t: types.count(t) for t in set(types)},
                         {"table_lookup": 4, "plain_text": 4, "cross_reference": 4,
                          "compare_two": 4, "unanswerable": 4})

    def test_sample_is_not_just_the_first_rows(self):
        self.assertNotEqual([r["id"] for r in stratified_sample(RECORDS, 20)],
                            [r["id"] for r in RECORDS[:20]])

    def sheet(self, verdicts):
        d = Path(tempfile.mkdtemp())
        sample = stratified_sample(RECORDS, 5)
        rows = build_sheet(sample, {r["id"]: {"gold_answer": "g", "evidence_text": "e"}
                                    for r in RECORDS})
        for row, v in zip(rows, verdicts):
            row["human_verdict"] = v
        write_sheet(rows, d / "a.csv")
        return d / "a.csv"

    def test_scoring_refuses_blank_verdicts(self):
        with self.assertRaises(AuditIncomplete) as cm:
            score_sheet(self.sheet(["CORRECT", "", "CORRECT", "CORRECT", "CORRECT"]))
        self.assertIn("1 of 5", str(cm.exception))

    def test_scoring_refuses_invalid_verdicts(self):
        with self.assertRaises(AuditIncomplete):
            score_sheet(self.sheet(["YES"] * 5))

    def test_agreement_comes_only_from_human_verdicts(self):
        # judge said CORRECT for every row; the human disagrees on two
        res = score_sheet(self.sheet(["correct", "CORRECT", "INCORRECT", "CORRECT", "INCORRECT"]))
        self.assertEqual((res["n"], res["agree"]), (5, 3))
        self.assertEqual(len(res["disagreements"]), 2)
        self.assertLess(res["ci_low"], res["rate"])
        text = summary_markdown(res)
        self.assertIn("3/5", text)
        self.assertIn("Disagreements", text)

    def test_the_old_script_that_printed_yes_for_everything_is_gone(self):
        self.assertFalse((Path(__file__).resolve().parent.parent
                          / "scripts/hand_check_20.py").exists())


class CalibrationGuards(unittest.TestCase):
    def test_too_few_examples_of_either_class_gives_no_threshold(self):
        ans = [0.9, 0.8, 0.7, 0.85, 0.75, 0.95]
        self.assertIsNone(choose_threshold(ans, [0.1, 0.2], min_per_class=5))
        self.assertIsNone(choose_threshold([0.9], [0.1] * 6, min_per_class=5))
        self.assertIsNotNone(choose_threshold(ans, [0.1, 0.2, 0.15, 0.12, 0.18],
                                              min_per_class=5))

    def test_threshold_cannot_refuse_more_answerable_questions_than_allowed(self):
        ans = [0.30, 0.35, 0.90, 0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97]
        unans = [0.10, 0.20, 0.32, 0.34, 0.36]
        t = choose_threshold(ans, unans, min_per_class=5, max_false_refusal=0.10)
        self.assertLessEqual(sum(s < t for s in ans) / len(ans), 0.10)
        # without the guard the best balanced cut-off wrongly refuses 20% of answerable questions
        unguarded = choose_threshold(ans, unans)
        self.assertGreater(sum(s < unguarded for s in ans) / len(ans), 0.10)

    def test_rrf_style_scores_cannot_force_a_near_maximum_threshold(self):
        """Regression: a threshold equal to the maximum possible RRF score (2/61) refused
        almost every question."""
        top = 2 / 61
        ans = [top * f for f in (0.5, 0.55, 0.6, 0.7, 0.8, 0.9, 0.95, 0.97, 0.99, 1.0)]
        unans = [top * f for f in (0.45, 0.5, 0.52, 0.55, 0.9)]
        t = choose_threshold(ans, unans, min_per_class=5, max_false_refusal=0.10)
        self.assertLess(t, top * 0.6)

    def test_cli_removes_a_stale_threshold_when_data_is_insufficient(self):
        d = Path(tempfile.mkdtemp())
        recs = [{"id": f"Q{i}", "in_calibration": True, "answerable": i > 1,
                 "top_score": 0.5} for i in range(10)]
        (d / "stage2_baseline.json").write_text(json.dumps({"records": recs}))
        stale = d / "threshold_stage2_baseline.json"
        stale.write_text(json.dumps({"threshold": 9.9}))
        self.assertEqual(calibrate_main(["--stage", "stage2_baseline", "--dir", str(d)]), 0)
        self.assertFalse(stale.exists())

    def test_cli_writes_threshold_with_counts_when_data_is_sufficient(self):
        d = Path(tempfile.mkdtemp())
        recs = ([{"id": f"A{i}", "in_calibration": True, "answerable": True,
                  "top_score": 0.8 + i / 100} for i in range(8)]
                + [{"id": f"U{i}", "in_calibration": True, "answerable": False,
                    "top_score": 0.1 + i / 100} for i in range(6)])
        (d / "stage2_baseline.json").write_text(json.dumps({"records": recs}))
        calibrate_main(["--stage", "stage2_baseline", "--dir", str(d)])
        out = json.loads((d / "threshold_stage2_baseline.json").read_text())
        self.assertEqual((out["n_answerable"], out["n_unanswerable"]), (8, 6))
        self.assertTrue(0.2 < out["threshold"] < 0.8)


if __name__ == "__main__":
    unittest.main()
