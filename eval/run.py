"""Run one experiment stage end to end.

Examples:
  python -m eval.run --stage stage2_baseline                 # real models (needs Qdrant, Groq)
  python -m eval.run --stage stage4_rerank --dataset synthetic --offline   # code smoke test
"""

from __future__ import annotations

import argparse
import csv
import sys

from app.config import ROOT, load_settings
from app.dataset import get_dataset, load_docs, sync_dataset
from app.llm import CachedLLM, GroqLLM
from app.pipeline import build_pipeline
from eval.judge import LexicalJudge
from eval.permissions import read_permission_tests, run_permission_tests
from eval.runner import integrity_block, run_stage, save_results, select_questions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--dataset", choices=["real", "synthetic"], default="real")
    parser.add_argument("--offline", action="store_true",
                        help="deterministic stand-ins for models; results are for testing only")
    parser.add_argument("--include-drafts", action="store_true")
    parser.add_argument("--no-threshold", action="store_true",
                        help="ignore any calibrated refusal threshold (calibration pass)")
    parser.add_argument("--cache-answers", action="store_true",
                        help="cache answer replies on disk for cheap reruns; the stored LIVE "
                             "latency and model are reported, never cache-read time")
    parser.add_argument("--allow-model-drift", action="store_true",
                        help="do not fail the run if a model other than the configured one answered")
    parser.add_argument("--gold", help="gold CSV to use instead of the dataset default")
    parser.add_argument("--tag", default="", help="suffix for the result file, e.g. blind")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)

    settings = load_settings(stage=args.stage)
    if args.tag:  # a separate benchmark gets its own calibrated threshold
        settings.cfg.setdefault("refusal", {})["threshold_tag"] = args.tag
    dataset = get_dataset(settings, args.dataset)
    pipeline = build_pipeline(settings, offline=args.offline, use_threshold=not args.no_threshold)
    report = sync_dataset(pipeline, settings, dataset, args.offline)
    print(f"index: {report.as_dict()}")

    gold_path = ROOT / args.gold if args.gold else dataset.gold_csv
    with gold_path.open(newline="", encoding="utf-8") as f:
        rows = select_questions(list(csv.DictReader(f)), args.include_drafts)
    if not rows:
        print("No verified questions to run. Finish Stage 1 (see docs/data.md) or use "
              "--include-drafts / --dataset synthetic.")
        return 1

    if args.offline:
        judge = LexicalJudge()
    else:
        raw = GroqLLM(settings.require_groq_key(), settings.get("judge.model"),
                      float(settings.get("judge.temperature")), 256,
                      int(settings.get("llm.max_retries")),
                      allow_fallback=bool(settings.get("llm.allow_fallback", False)),
                      fallback_models=tuple(settings.get("llm.fallback_models", []) or []),
                      max_wait_seconds=float(settings.get("llm.max_wait_seconds", 120)))
        judge = CachedLLM(raw, ROOT / "eval/results/cache", settings.get("judge.model"))
        if args.cache_answers:
            pipeline.set_llm(CachedLLM(pipeline.llm, ROOT / "eval/results/cache",
                                       settings.get("llm.model")))

    result = run_stage(pipeline, judge, rows, settings, args.offline, args.dataset, args.limit)
    drift = False
    if not args.offline:
        configured = {"answer": settings.get("llm.model"), "judge": settings.get("judge.model")}
        gold_name = (str(gold_path.relative_to(ROOT)) if gold_path.is_relative_to(ROOT)
                     else str(gold_path))
        result["integrity"] = integrity_block(configured, pipeline.llm, judge, pipeline.threshold,
                                              not args.no_threshold, gold_name)
        drift = result["integrity"]["model_drift"]
        result["tag"] = args.tag
        if drift:
            print(f"MODEL DRIFT: configured {configured} but used "
                  f"{result['integrity']['models_used']}. These results are NOT comparable "
                  "across stages.")
    out_dir = ROOT / settings.get("eval.results_dir")
    if args.offline or args.dataset == "synthetic":
        out_dir = out_dir / "offline"
    out = out_dir / f"{args.stage}{('__' + args.tag) if args.tag else ''}.json"
    save_results(result, out)
    print(f"wrote {out} ({len(result['records'])} questions)")

    perm_rows = read_permission_tests(ROOT / settings.get("data.permission_tests_csv"))
    perms = run_permission_tests(pipeline, load_docs(settings, dataset), perm_rows)
    failed = [p for p in perms if not p["passed"]]
    leaks = sum(len(p["leaked"]) for p in perms)
    print(f"permission tests: {len(perms) - len(failed)}/{len(perms)} passed, leaks: {leaks}")
    for p in failed:
        print(f"  FAIL {p['id']}: {p['failures']}")
    if leaks > 0:
        return 1
    if drift and not args.allow_model_drift:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
