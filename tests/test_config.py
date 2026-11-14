import unittest

from app.config import (
    ConfigError,
    Settings,
    apply_stage,
    deep_merge,
    load_settings,
)


class DeepMerge(unittest.TestCase):
    def test_merges_nested_without_mutating_input(self):
        base = {"a": {"x": 1, "y": 2}, "b": 1}
        merged = deep_merge(base, {"a": {"y": 3}})
        self.assertEqual(merged, {"a": {"x": 1, "y": 3}, "b": 1})
        self.assertEqual(base["a"]["y"], 2)


class Stages(unittest.TestCase):
    def test_base_config_is_vector_only_baseline(self):
        s = load_settings(env={})
        self.assertFalse(s.get("retrieval.hybrid_search"))
        self.assertFalse(s.get("retrieval.rerank"))
        self.assertEqual(s.get("ingest.strategy"), "fixed")

    def test_each_stage_adds_one_change(self):
        hybrid = load_settings(stage="stage3_hybrid", env={})
        rerank = load_settings(stage="stage4_rerank", env={})
        structure = load_settings(stage="stage5_structure", env={})
        self.assertTrue(hybrid.get("retrieval.hybrid_search"))
        self.assertFalse(hybrid.get("retrieval.rerank"))
        self.assertTrue(rerank.get("retrieval.rerank"))
        self.assertEqual(rerank.get("ingest.strategy"), "fixed")
        self.assertEqual(structure.get("ingest.strategy"), "structure")

    def test_models_never_change_between_stages(self):
        base = load_settings(env={})
        for stage in ("stage2_baseline", "stage3_hybrid", "stage4_rerank",
                      "stage5_structure", "stage6_ocr_tables"):
            s = load_settings(stage=stage, env={})
            for key in ("llm.model", "judge.model", "embedding.model"):
                self.assertEqual(s.get(key), base.get(key), f"{stage} changed {key}")

    def test_locked_setting_cannot_be_overridden(self):
        stages = {"locked": ["llm"], "stages": {"bad": {"overrides": {"llm": {"model": "x"}}}}}
        with self.assertRaises(ConfigError):
            apply_stage({"llm": {"model": "y"}}, stages, "bad")

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ConfigError):
            load_settings(stage="nope", env={})

    def test_env_overrides_qdrant_and_stage(self):
        s = load_settings(env={"QDRANT_HOST": "qdrant", "QDRANT_PORT": "1234",
                               "RAG_STAGE": "stage4_rerank"})
        self.assertEqual((s.qdrant_host, s.qdrant_port, s.stage), ("qdrant", 1234, "stage4_rerank"))

    def test_empty_stage_env_means_base_config(self):
        self.assertIsNone(load_settings(env={"RAG_STAGE": ""}).stage)


class Secrets(unittest.TestCase):
    def _settings(self, **kw):
        base = dict(cfg={}, stage=None, qdrant_host="h", qdrant_port=1,
                    groq_api_key=None, auth_secret_key=None)
        base.update(kw)
        return Settings(**base)

    def test_rejects_missing_short_and_placeholder_secrets(self):
        for bad in (None, "", "short", "replace_with_a_long_random_string_min_32_chars"):
            with self.assertRaises(ConfigError):
                self._settings(auth_secret_key=bad).require_auth_secret()

    def test_accepts_long_random_secret(self):
        secret = "x" * 40
        self.assertEqual(self._settings(auth_secret_key=secret).require_auth_secret(), secret)

    def test_rejects_placeholder_groq_key(self):
        with self.assertRaises(ConfigError):
            self._settings(groq_api_key="your_groq_api_key_here").require_groq_key()


if __name__ == "__main__":
    unittest.main()
