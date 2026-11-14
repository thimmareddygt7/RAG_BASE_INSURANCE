"""RagPipeline: retrieve (permission-filtered) -> answer -> verify citations -> refuse if needed."""

from __future__ import annotations

import json
import time
from pathlib import Path

from app.answer.citations import verify_citations
from app.answer.prompt import build_user_prompt
from app.config import ROOT, Settings
from app.embeddings import Embedder, HashingEmbedder, SentenceTransformerEmbedder
from app.llm import LLM, ExtractiveLLM, GroqLLM
from app.models import AskResult
from app.rerank import CrossEncoderReranker, OverlapReranker, Reranker
from app.search.retriever import Retriever
from app.store.base import VectorStore
from app.store.memory import InMemoryStore

REFUSAL_MARKER = "do not have enough information"


class RagPipeline:
    def __init__(self, settings: Settings, store: VectorStore, embedder: Embedder,
                 reranker: Reranker | None, llm: LLM, threshold: float | None = None):
        self.settings = settings
        self.store = store
        self.embedder = embedder
        self._retriever = Retriever(store, embedder, reranker, settings.get("retrieval"))
        self._llm = llm
        self._threshold = threshold
        self._system = settings.get("llm.system_prompt")
        self._refusal = settings.get("refusal.message")
        self._context_k = int(settings.get("retrieval.context_k"))

    def ask(self, question: str, group: str, version_scope: str = "latest") -> AskResult:
        """`group` must come from a verified token, never from the request body."""
        t0 = time.perf_counter()
        retrieval = self._retriever.retrieve(question, group, latest_only=version_scope != "all")
        result = AskResult(question, group, "", False, retrieved=retrieval.hits,
                           context_hits=retrieval.hits[: self._context_k],
                           timings_ms=dict(retrieval.timings_ms), stage=self.settings.stage)
        top = retrieval.hits[0].score if retrieval.hits else None

        if not result.context_hits:
            return self._refuse(result, "no_results", t0)
        if self._threshold is not None and top is not None and top < self._threshold:
            return self._refuse(result, "low_support", t0)

        result.prompt = build_user_prompt(question, result.context_hits)
        t1 = time.perf_counter()
        reply = self._llm.complete(self._system, result.prompt).strip()
        measured = (time.perf_counter() - t1) * 1000
        info = getattr(self._llm, "last_info", None)
        reported = info.latency_ms if info else measured  # live time, even on a cache hit
        if info:
            result.answer_model, result.llm_cached = info.model, info.cached
        result.timings_ms["llm"] = reported
        saved = measured - reported  # wall time we did not spend because of the cache
        if REFUSAL_MARKER in reply.lower():
            return self._refuse(result, "model_refused", t0, saved)

        reply = reply.replace("【", "[").replace("】", "]")
        result.answer = reply
        result.citations = verify_citations(reply, result.context_hits)
        result.timings_ms["total"] = (time.perf_counter() - t0) * 1000 - saved
        return result

    def _refuse(self, result: AskResult, reason: str, t0: float,
                saved: float = 0.0) -> AskResult:
        result.answer, result.refused, result.refusal_reason = self._refusal, True, reason
        result.citations = []
        result.timings_ms["total"] = (time.perf_counter() - t0) * 1000 - saved
        return result

    @property
    def llm(self) -> LLM:
        return self._llm

    def set_llm(self, llm: LLM) -> None:
        """Swap the LLM (used to add the answer cache for evaluation runs)."""
        self._llm = llm

    @property
    def threshold(self) -> float | None:
        return self._threshold


def load_threshold(settings: Settings) -> float | None:
    """Per-stage refusal threshold written by `python -m eval.calibrate`, else the config value."""
    stage = settings.stage
    if stage:
        tag = settings.get("refusal.threshold_tag", "") or ""
        name = f"threshold_{stage}{'__' + tag if tag else ''}.json"
        path = ROOT / settings.get("refusal.threshold_dir") / name
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))["threshold"]
    return settings.get("refusal.min_support_score")


def collection_name(settings: Settings, offline: bool) -> str:
    base = settings.get("vector_store.collection_name")
    suffix = f"_{settings.stage}" if settings.stage else ""
    return f"{base}{'_offline' if offline else ''}{suffix}"


def build_pipeline(settings: Settings, offline: bool = False,
                   use_threshold: bool = True) -> RagPipeline:
    """Assemble real components, or deterministic offline stand-ins when offline=True."""
    refusal = settings.get("refusal.message")
    dim = int(settings.get("embedding.dimension"))
    use_rerank = bool(settings.get("retrieval.rerank"))
    threshold = (
        load_threshold(settings)
        if (use_threshold and not offline)
        else (settings.get("refusal.min_support_score") if use_threshold else None)
    )

    if offline:
        return RagPipeline(settings, InMemoryStore(), HashingEmbedder(dim),
                           OverlapReranker() if use_rerank else None,
                           ExtractiveLLM(refusal), threshold)

    from app.store.qdrant_store import QdrantStore

    embedder = SentenceTransformerEmbedder(
        settings.get("embedding.model"), dim, settings.get("embedding.query_instruction", ""),
        int(settings.get("ingest.batch_size")))
    store = QdrantStore(settings.qdrant_host, settings.qdrant_port,
                        collection_name(settings, False), dim,
                        settings.get("vector_store.dense_vector_name"),
                        settings.get("vector_store.sparse_vector_name"),
                        settings.get("vector_store.sparse_model"))
    reranker = CrossEncoderReranker(settings.get("retrieval.rerank_model")) if use_rerank else None
    llm = GroqLLM(settings.require_groq_key(), settings.get("llm.model"),
                  float(settings.get("llm.temperature")), int(settings.get("llm.max_tokens")),
                  int(settings.get("llm.max_retries")),
                  allow_fallback=bool(settings.get("llm.allow_fallback", False)),
                  fallback_models=tuple(settings.get("llm.fallback_models", []) or []),
                  max_wait_seconds=float(settings.get("llm.max_wait_seconds", 120)))
    return RagPipeline(settings, store, embedder, reranker, llm, threshold)


def manifest_path(settings: Settings, offline: bool) -> Path:
    return ROOT / "data" / "vectorstore" / f"manifest_{collection_name(settings, offline)}.json"
