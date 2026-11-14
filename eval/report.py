"""Turns result files into the stage-by-stage table, with confidence intervals and p-values."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from eval.metrics import format_count, mcnemar_exact

ROOT = Path(__file__).resolve().parent.parent
STAGE_ORDER = ["stage2_baseline", "stage3_hybrid", "stage4_rerank", "stage5_structure",
               "stage6_ocr_tables"]


def aggregate(result: dict[str, Any]) -> dict[str, Any]:
    recs = result["records"]
    ans = [r for r in recs if r["answerable"]]
    non_cal = [r for r in recs if not r["in_calibration"]]
    answered = [r for r in ans if not r["refused"]]
    unans_nc = [r for r in non_cal if not r["answerable"]]
    ans_nc = [r for r in non_cal if r["answerable"]]
    agg: dict[str, Any] = {"n_questions": len(recs), "n_answerable": len(ans)}
    for k in result["k_values"]:
        agg[f"hit@{k}"] = (sum(r["hit"][str(k)] for r in ans), len(ans))
    agg["mrr"] = statistics.mean(r["rr"] for r in ans) if ans else 0.0
    agg["correct"] = (sum(r["correct"] for r in ans), len(ans))
    agg["faithful"] = (sum(bool(r["faithful"]) for r in answered), len(answered))
    agg["citation_ok"] = (sum(r["citation_ok"] and r["gold_page_cited"] for r in answered),
                          len(answered))
    agg["refusal_acc"] = (sum(r["refused"] for r in unans_nc), len(unans_nc))
    agg["false_refusal"] = (sum(r["refused"] for r in ans_nc), len(ans_nc))
    lat = sorted(r["latency_ms"] for r in recs)
    agg["p50_ms"] = statistics.median(lat) if lat else 0.0
    agg["p95_ms"] = lat[min(len(lat) - 1, int(0.95 * len(lat)))] if lat else 0.0
    agg["p50_retrieval_ms"] = statistics.median(r.get("retrieval_ms", 0.0) for r in recs) \
        if recs else 0.0
    llm_ms = [r["llm_ms"] for r in recs if r.get("llm_ms")]
    agg["p50_llm_ms"] = statistics.median(llm_ms) if llm_ms else 0.0
    with_llm = [r for r in recs if r.get("answer_model")]
    agg["cached_share"] = (sum(bool(r.get("llm_cached")) for r in with_llm), len(with_llm))
    agg["threshold_refusals"] = sum(r["refusal_reason"] == "low_support" for r in recs)
    agg["model_refusals"] = sum(r["refusal_reason"] == "model_refused" for r in recs)
    agg["cal_counts"] = (sum(r["in_calibration"] and r["answerable"] for r in recs),
                         sum(r["in_calibration"] and not r["answerable"] for r in recs))
    by_type: dict[str, tuple[int, int]] = {}
    for t in sorted({r["type"] for r in ans}):
        group = [r for r in ans if r["type"] == t]
        by_type[t] = (sum(r["correct"] for r in group), len(group))
    agg["correct_by_type"] = by_type
    return agg


def paired_test(prev: dict[str, Any], cur: dict[str, Any], field: str = "correct") -> float | None:
    """Exact McNemar p-value on questions both stages answered (same ids)."""
    a = {r["id"]: bool(r[field]) for r in prev["records"] if r["answerable"]}
    b = {r["id"]: bool(r[field]) for r in cur["records"] if r["answerable"]}
    common = set(a) & set(b)
    if not common:
        return None
    only_a = sum(a[i] and not b[i] for i in common)
    only_b = sum(b[i] and not a[i] for i in common)
    return mcnemar_exact(only_a, only_b)


def fmt_p(p: float | None) -> str:
    if p is None:
        return "-"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def _models(d: dict[str, int]) -> str:
    return ", ".join(f"{m} x{n}" for m, n in sorted(d.items())) or "-"


def integrity_table(results: list[dict[str, Any]]) -> list[str]:
    """Run integrity: which model answered, drift, cache use, threshold and refusal sources."""
    lines = ["\nRun integrity (read this before trusting the numbers):\n",
             "| Stage | Answer model(s) | Judge model(s) | Drift | Cached answers | "
             "Threshold | Calibration (ans/unans) | Refusals: threshold / model |",
             "|---|---|---|---|---|---|---|---|"]
    for res in results:
        a = aggregate(res)
        info = res.get("integrity")
        if info is None:
            lines.append(f"| {res['stage']} | not recorded | not recorded | UNVERIFIED | - | - | "
                         f"{a['cal_counts'][0]}/{a['cal_counts'][1]} | "
                         f"{a['threshold_refusals']} / {a['model_refusals']} |")
            continue
        used = info["models_used"]
        thr = info.get("threshold")
        thr_text = "none" if thr is None else f"{thr:.4f}" + ("" if info.get("threshold_applied") else " (not applied)")
        hits, total = info.get("answer_cache_hits", 0), info.get("answer_cache_hits", 0) + info.get("answer_cache_misses", 0)
        lines.append(
            f"| {res['stage']} | {_models(used['answer'])} | {_models(used['judge'])} | "
            f"{'YES' if info['model_drift'] else 'no'} | {hits}/{total} | {thr_text} | "
            f"{a['cal_counts'][0]}/{a['cal_counts'][1]} | "
            f"{a['threshold_refusals']} / {a['model_refusals']} |")
    return lines


def _cell(pair: tuple[int, int]) -> str:
    return format_count(*pair) if pair[1] else "-"


def render(results: list[dict[str, Any]]) -> str:
    lines = []
    if any(r.get("offline") for r in results):
        lines.append("> WARNING: some results use offline stand-ins (not real models). "
                     "They test the code, not the system, and must not be reported.\n")
    for res in results:
        info = res.get("integrity")
        if info is None and not res.get("offline"):
            lines.append(f"> WARNING: {res['stage']} has no model-identity record, so it cannot be "
                         "shown that one fixed model produced it. Rerun it.\n")
        elif info and info["model_drift"]:
            lines.append(f"> WARNING: MODEL DRIFT in {res['stage']}: a model other than the "
                         "configured one answered. Stage comparisons are not valid.\n")
    lines += ["| Stage | n | hit@5 | MRR | Correct | Faithful | Cited correctly | "
              "Refusal acc. | False refusal | p50 total ms (retrieval + LLM) | p vs prev |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    prev = None
    for res in results:
        a = aggregate(res)
        p = paired_test(prev, res) if prev else None
        lines.append(
            f"| {res['stage']} | {a['n_questions']} | {_cell(a.get('hit@5', (0, 0)))} | "
            f"{a['mrr']:.3f} | {_cell(a['correct'])} | {_cell(a['faithful'])} | "
            f"{_cell(a['citation_ok'])} | {_cell(a['refusal_acc'])} | "
            f"{_cell(a['false_refusal'])} | {a['p50_ms']:.0f} "
            f"({a['p50_retrieval_ms']:.0f} + {a['p50_llm_ms']:.0f}) | {fmt_p(p)} |")
        prev = res
    lines.append("\nCorrect answers by question type:\n")
    lines.append("| Stage | " + " | ".join(sorted({t for r in results
                                                    for t in aggregate(r)['correct_by_type']}))
                 + " |")
    types = sorted({t for r in results for t in aggregate(r)["correct_by_type"]})
    lines.append("|---|" + "---|" * len(types))
    for res in results:
        bt = aggregate(res)["correct_by_type"]
        lines.append(f"| {res['stage']} | " + " | ".join(
            f"{bt[t][0]}/{bt[t][1]}" if t in bt else "-" for t in types) + " |")
    lines += integrity_table(results)
    lines.append("\nNotes: LLM time is the stored live call time even for cached replies. "
                 "Refusal metrics use only questions outside the calibration split. With about a "
                 "hundred questions, gaps of a few points are usually noise: check the confidence "
                 "intervals and the p-value before claiming an improvement.")
    return "\n".join(lines)


def load_results(directory: Path, tag: str = "") -> list[dict[str, Any]]:
    """Result files for one benchmark: `<stage>.json`, or `<stage>__<tag>.json` for a tag."""
    found = {}
    for path in directory.glob("stage*.json"):
        has_tag = "__" in path.stem
        if (tag and not path.stem.endswith(f"__{tag}")) or (not tag and has_tag):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        found[data["stage"]] = data
    return [found[s] for s in STAGE_ORDER if s in found]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=ROOT / "eval/results")
    parser.add_argument("--write", type=Path, help="also write the table to this file")
    parser.add_argument("--tag", default="", help="benchmark tag, e.g. blind")
    args = parser.parse_args(argv)
    results = load_results(args.dir, args.tag)
    if not results:
        print(f"No stage result files in {args.dir}. Run: make eval-stage STAGE=stage2_baseline")
        return 1
    table = render(results)
    print(table)
    if args.write:
        args.write.write_text(table + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
