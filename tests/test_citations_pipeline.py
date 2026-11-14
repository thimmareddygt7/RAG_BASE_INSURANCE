import unittest

from app.answer.citations import claim_supported, extract_claims, verify_citations
from app.llm import CachedLLM, ExtractiveLLM
from app.models import Chunk, Hit
from app.pipeline import RagPipeline
from app.embeddings import HashingEmbedder
from app.store.memory import InMemoryStore
from tests.helpers import offline_pipeline


def hit(doc, page, text):
    return Hit(Chunk("id", doc, doc, "v1", "P", page, "", text, ("agent",)), 1.0, "dense")


class Citations(unittest.TestCase):
    def test_extract_claims_handles_period_before_and_after_marker(self):
        a = "The waiting period is 24 months [POL_A p.3]."
        b = "The waiting period is 24 months. [POL_A p.3]"
        for text in (a, b):
            (doc, page, claim), = extract_claims(text)
            self.assertEqual((doc, page), ("POL_A", 3))
            self.assertIn("24 months", claim)

    def test_adjacent_markers_share_a_claim(self):
        claims = extract_claims("Cover is 5,000 per day [A p.1] [B p.2]")
        self.assertEqual([c[:2] for c in claims], [("A", 1), ("B", 2)])
        self.assertEqual(claims[0][2], claims[1][2])

    def test_only_last_sentence_is_the_claim(self):
        (_, _, claim), = extract_claims("Intro sentence here. Cataract waits 12 months [A p.1]")
        self.assertEqual(claim, "Cataract waits 12 months")

    def test_numbers_must_match(self):
        evidence = "Cataract surgery waiting period is 12 months."
        self.assertTrue(claim_supported("Cataract waiting period is 12 months", evidence))
        self.assertFalse(claim_supported("Cataract waiting period is 24 months", evidence))

    def test_unrelated_claim_not_supported(self):
        self.assertFalse(claim_supported("Maternity covers twins", "Cataract waits 12 months"))
        self.assertFalse(claim_supported("", "anything"))

    def test_citation_to_page_not_in_context_is_unverified(self):
        hits = [hit("A", 1, "Cataract surgery waiting period is 12 months")]
        good, wrong_page, wrong_doc = verify_citations(
            "Cataract waiting period is 12 months [A p.1] "
            "Cataract waiting period is 12 months [A p.9] "
            "Cataract waiting period is 12 months [Z p.1]", hits)
        self.assertTrue(good.verified)
        self.assertFalse(wrong_page.in_context or wrong_page.verified)
        self.assertFalse(wrong_doc.in_context or wrong_doc.verified)


class OfflinePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings, cls.pipe, cls.dataset, cls.report = offline_pipeline("stage4_rerank")

    def test_answers_with_verified_page_citation(self):
        r = self.pipe.ask("What is the waiting period for cataract surgery?", "policyholder")
        self.assertFalse(r.refused)
        self.assertIn("12 months", r.answer)
        self.assertTrue(r.citation_ok)
        self.assertEqual((r.citations[0].doc_id, r.citations[0].page), ("SAMPLE_POLICY_V2", 1))

    def test_latest_scope_hides_old_version_and_all_scope_shows_it(self):
        latest = self.pipe.ask("What is the room rent limit per day?", "admin", "latest")
        self.assertEqual({h.chunk.doc_id for h in latest.retrieved}, {"SAMPLE_POLICY_V2",
                                                                      "AGENT_GUIDE_FAKE"})
        everything = self.pipe.ask("What is the room rent limit per day?", "admin", "all")
        self.assertIn("SAMPLE_POLICY_V1", {h.chunk.doc_id for h in everything.retrieved})

    def test_unanswerable_question_is_refused_with_no_citations(self):
        r = self.pipe.ask("What is the annual premium for a 45-year-old?", "admin")
        self.assertTrue(r.refused)
        self.assertEqual(r.citations, [])
        self.assertIn("do not have enough information", r.answer)

    def test_no_documents_means_no_llm_call(self):
        calls = []

        class Spy:
            def complete(self, system, user):
                calls.append(user)
                return "x"

        empty = RagPipeline(self.settings, InMemoryStore(), HashingEmbedder(384), None, Spy())
        r = empty.ask("anything at all", "admin")
        self.assertTrue(r.refused)
        self.assertEqual((r.refusal_reason, calls), ("no_results", []))

    def test_low_score_threshold_refuses_before_calling_llm(self):
        calls = []

        class Spy:
            def complete(self, system, user):
                calls.append(1)
                return "x"

        strict = RagPipeline(self.settings, self.pipe.store, self.pipe.embedder, None, Spy(),
                             threshold=10.0)
        r = strict.ask("What is the grace period?", "admin")
        self.assertEqual((r.refusal_reason, calls), ("low_support", []))

    def test_stages_change_chunking_as_configured(self):
        _, baseline, _, _ = offline_pipeline("stage2_baseline")
        _, structured, _, _ = offline_pipeline("stage5_structure")
        self.assertGreater(structured.store.count(), baseline.store.count())
        kinds = {r.chunk.kind for r in structured.store._rows.values()}
        self.assertIn("table", kinds)

    def test_hybrid_stage_uses_both_retrievers(self):
        _, hybrid, _, _ = offline_pipeline("stage3_hybrid")
        r = hybrid.ask("cataract surgery waiting", "admin")
        self.assertEqual({h.source for h in r.retrieved}, {"fused"})
        self.assertIn("sparse_fusion", r.timings_ms)


class Llms(unittest.TestCase):
    def test_extractive_llm_refuses_when_nothing_matches(self):
        llm = ExtractiveLLM("REFUSED")
        prompt = ("CONTEXT:\n### SOURCE doc=A version=v1 page=1\nBananas are yellow.\n\n"
                  "QUESTION: premium?")
        self.assertEqual(llm.complete("", prompt), "REFUSED")

    def test_cached_llm_calls_inner_once(self):
        import tempfile
        from pathlib import Path

        calls = []

        class Inner:
            def complete(self, system, user):
                calls.append(user)
                return "reply"

        llm = CachedLLM(Inner(), Path(tempfile.mkdtemp()), "m")
        self.assertEqual((llm.complete("s", "u"), llm.complete("s", "u")), ("reply", "reply"))
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
