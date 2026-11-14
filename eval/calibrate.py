"""Calibrate the refusal threshold on the calibration split only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config import load_settings

ROOT = Path(__file__).resolve().parent.parent


def choose_threshold(answerable_scores: list[float], unanswerable_scores: list[float],
                     min_per_class: int = 1, max_false_refusal: float = 1.0) -> float | None:
    """Pick the cut-off (refuse if top score < t) with the best balanced accuracy.

    Guards against fitting noise: returns None if either class has fewer than `min_per_class`
    questions, and never picks a threshold that would refuse more than `max_false_refusal` of the
    answerable calibration questions. Ties pick the lowest threshold (refuse as little as possible).
    """
    if (len(answerable_scores) < max(min_per_class, 1)
            or len(unanswerable_scores) < max(min_per_class, 1)):
        return None
    values = sorted(set(answerable_scores + unanswerable_scores))
    candidates = ([values[0] - 1e-9]
                  + [(a + b) / 2 for a, b in zip(values, values[1:], strict=False)])
    best_t, best_score = candidates[0], -1.0
    for t in candidates:
        false_refusal = sum(s < t for s in answerable_scores) / len(answerable_scores)
        if false_refusal > max_false_refusal + 1e-12:
            continue
        refuse_unans = sum(s < t for s in unanswerable_scores) / len(unanswerable_scores)
        answer_ans = 1.0 - false_refusal
        score = (refuse_unans + answer_ans) / 2
        if score > best_score + 1e-12:
            best_t, best_score = t, score
    return best_t


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--dir", type=Path, default=ROOT / "eval/results")
    parser.add_argument("--tag", default="", help="benchmark tag, e.g. blind")
    parser.add_argument("--min-per-class", type=int)
    parser.add_argument("--max-false-refusal", type=float)
    args = parser.parse_args(argv)
    settings = load_settings(stage=args.stage)
    min_per_class = args.min_per_class or int(settings.get("eval.calibration_min_per_class", 5))
    max_fr = (args.max_false_refusal if args.max_false_refusal is not None
              else float(settings.get("eval.calibration_max_false_refusal", 0.10)))
    suffix = f"__{args.tag}" if args.tag else ""
    path = args.dir / f"{args.stage}{suffix}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    cal = [r for r in data["records"] if r["in_calibration"] and r["top_score"] is not None]
    ans = [r["top_score"] for r in cal if r["answerable"]]
    unans = [r["top_score"] for r in cal if not r["answerable"]]
    out = args.dir / f"threshold_{args.stage}{suffix}.json"
    threshold = choose_threshold(ans, unans, min_per_class, max_fr)
    if threshold is None:
        out.unlink(missing_ok=True)  # never leave a stale threshold behind
        print(f"No refusal threshold fitted: {len(ans)} answerable and {len(unans)} unanswerable "
              f"calibration questions (need at least {min_per_class} of each). The model's own "
              "refusal is used instead. Add more unanswerable questions to calibrate.")
        return 0
    out.write_text(json.dumps({"stage": args.stage, "threshold": threshold,
                               "n_answerable": len(ans), "n_unanswerable": len(unans),
                               "max_false_refusal": max_fr}, indent=2), encoding="utf-8")
    print(f"threshold {threshold:.6f} from {len(ans)} answerable / {len(unans)} unanswerable "
          f"calibration questions -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
