"""Runs the gold set through the pipeline and records one result row per question."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.llm import LLM
from app.pipeline import RagPipeline
from eval.judge import judge_correct, judge_faithful
from eval.metrics import reciprocal_rank

REFUSAL_GOLD = "not in the documents"


def gold_pages(row: dict[str, str]) -> set[tuple[str, int]]:
    pages: set[tuple[str, int]] = set()
    if row["doc_id"] and row["page"].strip().isdigit():
        pages.add((row["doc_id"], int(row["page"])))
    if row["page_2"].strip().isdigit():
        pages.add((row["doc_id_2"] or row["doc_id"], int(row["page_2"])))
    return pages


def calibration_ids(ids: list[str], fraction: float, seed: int) -> set[str]:
    """Deterministic calibration subset: hash-ordered, so it never depends on file order."""
    ranked = sorted(ids, key=lambda i: hashlib.sha256(f"{seed}:{i}".encode()).hexdigest())
    return set(ranked[: round(len(ids) * fraction)])


def calibration_ids_stratified(rows: list[dict[str, str]], fraction: float,
                               seed: int) -> set[str]:
    """Calibration split that keeps the answerable / unanswerable mix, chosen by hash order."""
    chosen: set[str] = set()
    for answerable in ("yes", "no"):
        ids = [r["id"] for r in rows if r["answerable"] == answerable]
        chosen |= calibration_ids(ids, fraction, seed)
    return chosen


def select_questions(rows: list[dict[str, str]], include_drafts: bool) -> list[dict[str, str]]:
    allowed = {"verified", "drafted"} if include_drafts else {"verified"}
    return [r for r in rows if r["status"] in allowed]


def run_question(pipeline: RagPipeline, judge: LLM, row: dict[str, str], ks: list[int],
                 in_calibration: bool) -> dict[str, Any]:
    cal_tag = "cal" if in_calibration else "test"
    print(f"[{row['id']}] {row['type']} ({cal_tag}) - {row['question'][:45]}...", flush=True)
    answerable = row["answerable"] == "yes"
    scope = "all" if row["type"] == "compare_two" else "latest"
    result = pipeline.ask(row["question"], group="admin", version_scope=scope)
    gold = gold_pages(row)
    depth = max(ks)
    ranked = [(h.chunk.doc_id, h.chunk.page) for h in result.retrieved[:depth]]

    rec: dict[str, Any] = {
        "id": row["id"], "type": row["type"], "answerable": answerable,
        "question": row["question"], "gold_pages": sorted(gold), "in_calibration": in_calibration,
        "retrieved": [[h.chunk.doc_id, h.chunk.page, round(h.score, 6)]
                      for h in result.retrieved[:depth]],
        "top_score": result.retrieved[0].score if result.retrieved else None,
        "answer": result.answer, "refused": result.refused,
        "refusal_reason": result.refusal_reason,
        "citations": [{"doc_id": c.doc_id, "page": c.page, "verified": c.verified,
                       "in_context": c.in_context} for c in result.citations],
        "latency_ms": round(result.timings_ms.get("total", 0.0), 2),
        "retrieval_ms": round(sum(v for k, v in result.timings_ms.items()
                                  if k not in ("llm", "total")), 2),
        "llm_ms": round(result.timings_ms.get("llm", 0.0), 2),
        "answer_model": result.answer_model,
        "llm_cached": result.llm_cached,
    }
    if answerable:
        rec["hit"] = {str(k): any(p in gold for p in ranked[:k]) for k in ks}
        rec["rr"] = reciprocal_rank(ranked, gold)
        rec["correct"] = (not result.refused) and judge_correct(
            judge, row["question"], row["gold_answer"], result.answer)
        context = "\n\n".join(h.chunk.text for h in result.context_hits)
        rec["faithful"] = None if result.refused else judge_faithful(judge, context, result.answer)
        cited = {(c.doc_id, c.page) for c in result.citations}
        rec["citation_ok"] = (not result.refused) and result.citation_ok
        rec["gold_page_cited"] = bool(cited & gold)
    else:
        rec["correct"] = result.refused  # for unanswerable questions, refusing is correct
    return rec


def run_stage(pipeline: RagPipeline, judge: LLM, rows: list[dict[str, str]], settings,
              offline: bool, dataset: str, limit: int | None = None) -> dict[str, Any]:
    ks = [int(k) for k in settings.get("eval.k_values")]
    cal = calibration_ids_stratified(rows, float(settings.get("eval.calibration_fraction")),
                                     int(settings.get("eval.seed")))
    selected = rows[:limit] if limit else rows
    records = [run_question(pipeline, judge, r, ks, r["id"] in cal) for r in selected]
    return {
        "stage": settings.stage, "dataset": dataset, "offline": offline, "k_values": ks,
        "settings": {k: settings.get(k) for k in ("ingest", "ocr", "tables", "retrieval")},
        "models": {"llm": settings.get("llm.model"), "judge": settings.get("judge.model"),
                   "embedding": settings.get("embedding.model")},
        "records": records,
    }


def integrity_block(configured: dict[str, str], answer_llm, judge, threshold, applied: bool,
                    gold_file: str) -> dict[str, Any]:
    """Which models really answered and judged, and whether that matches the configuration."""
    used = {"answer": dict(getattr(answer_llm, "models_used", {})),
            "judge": dict(getattr(judge, "models_used", {}))}
    drift = any(m != configured[role] for role, models in used.items() for m in models)
    return {"configured_models": configured, "models_used": used, "model_drift": drift,
            "answer_cache_hits": getattr(answer_llm, "cache_hits", 0),
            "answer_cache_misses": getattr(answer_llm, "cache_misses", 0),
            "threshold": threshold, "threshold_applied": applied, "gold_file": gold_file}


def save_results(result: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
