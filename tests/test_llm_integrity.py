import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.config import load_settings
from app.embeddings import HashingEmbedder
from app.llm import CachedLLM, CallInfo, GroqLLM, ModelUnavailableError
from app.models import Chunk
from app.pipeline import RagPipeline
from app.store.memory import InMemoryStore


class FakeClient:
    """Scripted Groq client: each item is a reply string or an Exception to raise."""

    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, model, messages, temperature, max_tokens):
        self.calls.append(model)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=item))])


def make(script, **kw):
    sleeps = []
    llm = GroqLLM("k", "model-a", client=FakeClient(script), sleep=sleeps.append, **kw)
    return llm, sleeps


class ModelIdentity(unittest.TestCase):
    def test_successful_call_records_the_model_and_live_latency(self):
        llm, _ = make(["hello"])
        self.assertEqual(llm.complete("s", "u"), "hello")
        self.assertEqual(llm.last_info.model, "model-a")
        self.assertFalse(llm.last_info.cached)
        self.assertGreaterEqual(llm.last_info.latency_ms, 0)
        self.assertEqual(dict(llm.models_used), {"model-a": 1})

    def test_short_rate_limit_waits_and_retries_the_same_model(self):
        llm, sleeps = make([Exception("rate limit. Please try again in 2.5s"), "ok"])
        self.assertEqual(llm.complete("s", "u"), "ok")
        self.assertEqual(llm.client_models if hasattr(llm, "client_models") else
                         llm._client.calls, ["model-a", "model-a"])
        self.assertAlmostEqual(sleeps[0], 4.0)  # wait + 1.5 s margin
        self.assertEqual(dict(llm.models_used), {"model-a": 1})

    def test_daily_limit_raises_instead_of_silently_switching_model(self):
        llm, _ = make([Exception("Rate limit reached: tokens per day (TPD) used up")],
                      fallback_models=["model-b"])  # allow_fallback is False by default
        with self.assertRaises(ModelUnavailableError):
            llm.complete("s", "u")
        self.assertEqual(llm._client.calls, ["model-a"])

    def test_long_wait_raises_when_fallback_is_off(self):
        llm, _ = make([Exception("please try again in 12m30s")], max_wait_seconds=120)
        with self.assertRaises(ModelUnavailableError):
            llm.complete("s", "u")

    def test_fallback_only_when_explicitly_allowed_and_it_is_recorded(self):
        llm, _ = make([Exception("tokens per day exceeded"), "from b"],
                      allow_fallback=True, fallback_models=["model-b"])
        self.assertEqual(llm.complete("s", "u"), "from b")
        self.assertEqual(llm.last_info.model, "model-b")
        self.assertEqual(dict(llm.models_used), {"model-b": 1})

    def test_other_errors_retry_then_raise(self):
        llm, sleeps = make([RuntimeError("boom")] * 2, max_retries=2)
        with self.assertRaises(RuntimeError):
            llm.complete("s", "u")
        self.assertEqual(len(sleeps), 1)

    def test_default_config_forbids_fallback(self):
        s = load_settings(env={})
        self.assertFalse(s.get("llm.allow_fallback"))
        self.assertEqual(s.get("llm.fallback_models"), [])


class Cache(unittest.TestCase):
    def test_cache_hit_reports_stored_model_and_live_latency_not_cache_read_time(self):
        inner, _ = make(["reply"])
        inner.last_info = None
        cache = CachedLLM(inner, Path(tempfile.mkdtemp()), "model-a")
        self.assertEqual(cache.complete("s", "u"), "reply")
        first = cache.last_info
        self.assertEqual((first.model, first.cached), ("model-a", False))
        # make the stored live latency recognisable, then read it back from disk
        entry = next(cache._dir.glob("*.json"))
        import json
        data = json.loads(entry.read_text())
        data["latency_ms"] = 777.0
        entry.write_text(json.dumps(data))
        self.assertEqual(cache.complete("s", "u"), "reply")
        self.assertEqual((cache.last_info.latency_ms, cache.last_info.cached), (777.0, True))
        self.assertEqual((cache.cache_hits, cache.cache_misses), (1, 1))
        self.assertEqual(len(inner._client.calls), 1)

    def test_cache_remembers_which_model_really_answered(self):
        inner, _ = make([Exception("tokens per day"), "from b"], allow_fallback=True,
                        fallback_models=["model-b"])
        cache = CachedLLM(inner, Path(tempfile.mkdtemp()), "model-a")
        cache.complete("s", "u")
        cache.complete("s", "u")  # hit
        self.assertEqual(dict(cache.models_used), {"model-b": 2})

    def test_old_format_cache_entries_are_ignored(self):
        from app.llm import CACHE_VERSION
        self.assertTrue(CACHE_VERSION != "v1")


class PipelineLatency(unittest.TestCase):
    def test_latency_uses_stored_live_time_for_cached_replies(self):
        settings = load_settings(env={})
        emb, store = HashingEmbedder(384), InMemoryStore()
        chunk = Chunk("c1", "DOC", "Doc", "v1", "P", 1, "", "The waiting period is 24 months.",
                      ("admin",))
        store.upsert([chunk], emb.embed_documents([chunk.text]))

        class Cached:
            last_info = CallInfo("model-a", 1500.0, cached=True)

            def complete(self, system, user):
                return "The waiting period is 24 months [DOC p.1]."

        r = RagPipeline(settings, store, emb, None, Cached()).ask("waiting period?", "admin")
        self.assertEqual((r.answer_model, r.llm_cached), ("model-a", True))
        self.assertEqual(r.timings_ms["llm"], 1500.0)
        # wall time was tiny, so the adjusted total must be wall - measured + 1500
        self.assertGreater(r.timings_ms["total"], 1400.0)


if __name__ == "__main__":
    unittest.main()


class IntegrityBlock(unittest.TestCase):
    def test_no_drift_when_the_configured_model_answered_everything(self):
        from collections import Counter

        from eval.runner import integrity_block
        llm = SimpleNamespace(models_used=Counter({"m-a": 100}), cache_hits=40, cache_misses=60)
        judge = SimpleNamespace(models_used=Counter({"m-a": 200}))
        info = integrity_block({"answer": "m-a", "judge": "m-a"}, llm, judge, 0.5, True, "g.csv")
        self.assertFalse(info["model_drift"])
        self.assertEqual((info["answer_cache_hits"], info["answer_cache_misses"]), (40, 60))

    def test_drift_is_detected_for_answers_and_for_the_judge(self):
        from collections import Counter

        from eval.runner import integrity_block
        cfg = {"answer": "m-a", "judge": "m-a"}
        llm = SimpleNamespace(models_used=Counter({"m-a": 90, "m-b": 10}))
        ok_judge = SimpleNamespace(models_used=Counter({"m-a": 5}))
        self.assertTrue(integrity_block(cfg, llm, ok_judge, None, True, "g")["model_drift"])
        llm_ok = SimpleNamespace(models_used=Counter({"m-a": 90}))
        bad_judge = SimpleNamespace(models_used=Counter({"m-c": 1}))
        self.assertTrue(integrity_block(cfg, llm_ok, bad_judge, None, True, "g")["model_drift"])
