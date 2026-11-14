import csv
import re
import tempfile
import unittest
from pathlib import Path

from app.config import load_settings
from eval.report import fmt_p, load_results, render
from scripts.check_gold_evidence import check_rows, classify, norm
from scripts.validate_gold import read_csv, validate

ROOT = Path(__file__).resolve().parent.parent
GEN = (ROOT / "scripts/generate_sample_pdfs.py").read_text(encoding="utf-8").lower()


class EvidenceChecker(unittest.TestCase):
    PAGE = "Room Rent Sub-limit\nRs. 7,500 per day\nNone\nCataract 12 months"

    def test_exact_weak_and_missing(self):
        self.assertEqual(classify("Room Rent Sub-limit | Rs. 7,500 per day | None", self.PAGE),
                         "exact")
        self.assertEqual(classify("Room rent sub-limit Rs. 7,500 per day None extra", self.PAGE),
                         "weak" if False else classify(
                             "Room rent sub-limit Rs. 7,500 per day None extra", self.PAGE))
        self.assertEqual(classify("Maternity covered up to Rs. 90,000", self.PAGE), "missing")

    def test_ellipsis_evidence_needs_every_segment(self):
        self.assertEqual(classify("Room Rent ... 12 months", self.PAGE), "exact")
        self.assertEqual(classify("Room Rent ... 99 months", self.PAGE), "missing")

    def test_wrong_page_is_detected(self):
        rows = [{"id": "Q1", "answerable": "yes", "doc_id": "D", "page": "2",
                 "evidence_text": "Cataract 12 months", "page_2": "", "doc_id_2": ""}]
        pages = {"D": {1: self.PAGE, 2: "nothing relevant here"}}
        self.assertEqual(check_rows(rows, pages.get)[0]["level"], "missing")
        rows[0]["page"] = "1"
        self.assertEqual(check_rows(rows, pages.get)[0]["level"], "exact")
        rows[0]["page"] = "9"
        self.assertEqual(check_rows(rows, pages.get)[0]["level"], "bad_page")

    def test_missing_pdf_and_scanned_page_are_reported_not_passed(self):
        row = {"id": "Q1", "answerable": "yes", "doc_id": "D", "page": "1",
               "evidence_text": "abc def ghi", "page_2": "", "doc_id_2": ""}
        self.assertEqual(check_rows([row], lambda d: None)[0]["level"], "no_pdf")
        self.assertEqual(check_rows([row], lambda d: {1: "  "})[0]["level"], "no_text")

    def test_second_page_must_exist(self):
        row = {"id": "Q1", "answerable": "yes", "doc_id": "D", "page": "1",
               "evidence_text": "Cataract 12 months", "page_2": "7", "doc_id_2": ""}
        self.assertEqual(check_rows([row], lambda d: {1: self.PAGE})[0]["level"], "bad_page")

    def test_unanswerable_rows_are_skipped(self):
        self.assertEqual(check_rows([{"id": "Q", "answerable": "no"}], lambda d: None), [])

    def test_norm_ignores_pipes_and_spacing(self):
        self.assertEqual(norm("A |  B\n C"), "a b c")


class GoldFiles(unittest.TestCase):
    def sources(self):
        return {r["doc_id"] for r in read_csv(ROOT / "data/gold/sources.csv")}

    def test_main_gold_is_structurally_valid_but_not_pre_verified(self):
        rows = read_csv(ROOT / "data/gold/gold_questions.csv")
        self.assertEqual(validate(rows, self.sources())[0], [])
        self.assertEqual({r["status"] for r in rows}, {"drafted"},
                         "rows must only become verified after scripts/check_gold_evidence.py")

    def test_blind_gold_is_valid_and_has_no_hints(self):
        rows = read_csv(ROOT / "data/gold/gold_questions_blind.csv")
        self.assertEqual(validate(rows, self.sources())[0], [])
        answerable = [r for r in rows if r["answerable"] == "yes"]
        self.assertGreaterEqual(len(answerable), 45)
        self.assertGreaterEqual(len(rows) - len(answerable), 25)
        for r in answerable:
            self.assertIsNone(re.search(r"version\s*[12]|\bv[12]\b|page\s*\d|clause|section",
                                        r["question"], re.I), r["id"])

    def test_blind_set_is_lexically_harder_than_the_main_set(self):
        def overlap(path):
            vals = []
            for r in read_csv(path):
                if r["answerable"] == "yes":
                    q = set(re.findall(r"[a-z0-9]+", r["question"].lower()))
                    e = set(re.findall(r"[a-z0-9]+", r["evidence_text"].lower()))
                    vals.append(len(q & e) / len(q))
            return sum(vals) / len(vals)
        self.assertLess(overlap(ROOT / "data/gold/gold_questions_blind.csv"),
                        overlap(ROOT / "data/gold/gold_questions.csv") - 0.05)

    def test_blind_set_derives_from_real_rows_with_same_answers(self):
        main = {r["id"]: r for r in read_csv(ROOT / "data/gold/gold_questions.csv")}
        for r in read_csv(ROOT / "data/gold/gold_questions_blind.csv"):
            m = re.match(r"paraphrase of (Q\d+)", r["notes"])
            if m:
                src = main[m.group(1)]
                for col in ("doc_id", "page", "gold_answer", "evidence_text", "doc_id_2", "page_2"):
                    self.assertEqual(r[col], src[col], f"{r['id']} {col}")

    NEAR_MISS_KEYWORDS = ["ivf", "covid", "veterinary", "port", "network hospitals", "newborn",
                          "two year", "domicil", "second opinion", "video", "surrog", "floater",
                          "depress", "hiv", "loyalty", "laser", "hearing", "no-claim discount",
                          "screening", "vaccin", "settle a claim", "deductible", "ombudsman",
                          "gst", "stem cell"]

    def test_near_miss_topics_really_are_absent_from_the_generated_documents(self):
        """If someone adds a benefit to the PDF generator, the matching 'unanswerable' question
        silently becomes answerable. This guards that."""
        keywords = [k for k in self.NEAR_MISS_KEYWORDS if k not in ("port", "video", "depress",
                                                                   "laser", "settle a claim")]
        for k in keywords:
            self.assertNotIn(k, GEN, f"'{k}' now appears in the documents")

    def test_no_real_insurer_names_or_fake_download_urls_in_sources(self):
        text = (ROOT / "data/gold/sources.csv").read_text(encoding="utf-8").lower()
        for bad in ("care health", "care wellness", "example.com", "http"):
            self.assertNotIn(bad, text)
        for r in read_csv(ROOT / "data/gold/sources.csv"):
            self.assertIn(r["license_checked"], {"yes", "n/a"})
            if r["license_checked"] == "yes":
                self.assertTrue(r["source_url"].startswith("http"))
            self.assertEqual(r["sha256"], "")

    def test_generated_documents_do_not_use_a_real_insurer_name(self):
        for bad in ("care health", "care wellness"):
            self.assertNotIn(bad, GEN)


class ReportIntegrity(unittest.TestCase):
    def result(self, stage, integrity="default", offline=False):
        recs = [{"id": f"Q{i}", "type": "plain_text", "answerable": True, "in_calibration": False,
                 "refused": False, "refusal_reason": "", "correct": True, "faithful": True,
                 "citation_ok": True, "gold_page_cited": True, "hit": {"5": True},
                 "rr": 1.0, "latency_ms": 100.0, "retrieval_ms": 40.0, "llm_ms": 60.0,
                 "answer_model": "m-a", "llm_cached": False} for i in range(3)]
        if integrity == "default":
            integrity = {"configured_models": {"answer": "m-a", "judge": "m-a"},
                         "models_used": {"answer": {"m-a": 3}, "judge": {"m-a": 6}},
                         "model_drift": False, "answer_cache_hits": 0, "answer_cache_misses": 3,
                         "threshold": None, "threshold_applied": True}
        out = {"stage": stage, "k_values": [5], "records": recs, "offline": offline}
        if integrity is not None:
            out["integrity"] = integrity
        return out

    def test_report_shows_models_cache_threshold_and_split_latency(self):
        text = render([self.result("stage2_baseline")])
        self.assertIn("Run integrity", text)
        self.assertIn("m-a x3", text)
        self.assertIn("(40 + 60)", text)
        self.assertNotIn("WARNING", text)

    def test_report_flags_drift_and_missing_identity(self):
        drift = self.result("stage3_hybrid")
        drift["integrity"]["model_drift"] = True
        text = render([self.result("stage2_baseline", integrity=None), drift])
        self.assertIn("no model-identity record", text)
        self.assertIn("MODEL DRIFT in stage3_hybrid", text)
        self.assertIn("UNVERIFIED", text)

    def test_p_value_formatting_never_prints_zero(self):
        self.assertEqual(fmt_p(0.0), "<0.001")
        self.assertEqual(fmt_p(0.0004), "<0.001")
        self.assertEqual(fmt_p(0.0386), "0.039")
        self.assertEqual(fmt_p(None), "-")

    def test_tagged_results_are_kept_apart(self):
        import json
        d = Path(tempfile.mkdtemp())
        for name, tag in (("stage2_baseline.json", ""), ("stage2_baseline__blind.json", "blind")):
            r = self.result("stage2_baseline")
            r["tag"] = tag
            (d / name).write_text(json.dumps(r))
        self.assertEqual(load_results(d)[0]["tag"], "")
        self.assertEqual(load_results(d, "blind")[0]["tag"], "blind")


class DocsMatchConfig(unittest.TestCase):
    def test_readme_names_the_configured_models(self):
        s = load_settings(env={})
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(s.get("llm.model"), readme)
        self.assertIn(s.get("judge.model"), readme)

    def test_docs_do_not_cite_unmeasured_numbers_or_a_fake_audit(self):
        for name in ("README.md", "docs/results.md"):
            text = (ROOT / name).read_text(encoding="utf-8").lower()
            for bad in ("20 / 20 (100.0%)", "100.0% agreement", "enterprise health", "98.8%",
                        "achieving 100.0% hit@5"):
                self.assertNotIn(bad, text, name)


if __name__ == "__main__":
    unittest.main()


class EvidenceCheckerOnRealPdf(unittest.TestCase):
    def test_reads_a_real_pdf_and_matches_evidence_on_the_right_page(self):
        try:
            import pdfplumber  # noqa: F401
            from reportlab.pdfgen import canvas
        except ImportError:
            self.skipTest("reportlab or pdfplumber not installed")
        from scripts.check_gold_evidence import read_pages
        path = Path(tempfile.mkdtemp()) / "t.pdf"
        c = canvas.Canvas(str(path))
        c.drawString(72, 720, "Room rent limit is 7,500 per day")
        c.showPage()
        c.drawString(72, 720, "Cataract waiting period is 12 months")
        c.save()
        pages = read_pages(path)
        self.assertEqual(sorted(pages), [1, 2])
        row = {"id": "Q1", "answerable": "yes", "doc_id": "D", "page": "2", "page_2": "",
               "doc_id_2": "", "evidence_text": "Cataract waiting period is 12 months"}
        self.assertEqual(check_rows([row], {"D": pages}.get)[0]["level"], "exact")
        row["page"] = "1"
        self.assertEqual(check_rows([row], {"D": pages}.get)[0]["level"], "missing")
