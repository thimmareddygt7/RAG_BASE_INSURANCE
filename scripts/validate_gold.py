"""Validate the gold question set before it is frozen.

Default mode checks structure. `--strict` also requires a finished, frozen benchmark:
at least 100 questions, all verified, and the target question-type mix.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLUMNS = [
    "id", "type", "question", "doc_id", "page", "gold_answer", "evidence_text",
    "doc_id_2", "page_2", "answerable", "status", "notes",
]
TARGET_MIX = {
    "table_lookup": 0.40,
    "plain_text": 0.25,
    "cross_reference": 0.15,
    "compare_two": 0.10,
    "unanswerable": 0.10,
}
STATUSES = {"todo", "drafted", "verified"}
REFUSAL_ANSWER = "not in the documents"
MIX_TOLERANCE = 0.05
MIN_QUESTIONS = 100


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _is_page(value: str) -> bool:
    return value.strip().isdigit() and int(value) >= 1


def validate(
    rows: list[dict[str, str]], source_ids: set[str], strict: bool = False,
    min_questions: int = MIN_QUESTIONS, check_mix: bool = True
) -> tuple[list[str], list[str]]:
    """Return (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    if rows and set(COLUMNS) - set(rows[0].keys()):
        missing = sorted(set(COLUMNS) - set(rows[0].keys()))
        return [f"Missing columns: {missing}"], warnings

    ids = Counter(r["id"] for r in rows)
    errors += [f"Duplicate id {i}" for i, c in ids.items() if c > 1]
    questions = Counter(r["question"].strip().lower() for r in rows)
    warnings += [f"Duplicate question text: {q[:60]}" for q, c in questions.items() if c > 1]

    for r in rows:
        rid = r["id"]
        qtype = r["type"]
        if qtype not in TARGET_MIX:
            errors.append(f"{rid}: unknown type '{qtype}'")
            continue
        if not r["question"].strip():
            errors.append(f"{rid}: empty question")
        if r["status"] not in STATUSES:
            errors.append(f"{rid}: status must be one of {sorted(STATUSES)}")
        if r["answerable"] not in {"yes", "no"}:
            errors.append(f"{rid}: answerable must be yes or no")
        if (qtype == "unanswerable") != (r["answerable"] == "no"):
            errors.append(f"{rid}: answerable must be 'no' exactly for unanswerable questions")

        if r["status"] == "todo":
            continue

        # Drafted and verified rows must be complete.
        if qtype == "unanswerable":
            if r["gold_answer"].strip().lower() != REFUSAL_ANSWER:
                errors.append(f"{rid}: gold_answer must be '{REFUSAL_ANSWER}'")
            if r["doc_id"].strip():
                errors.append(f"{rid}: unanswerable questions must have an empty doc_id")
            continue
        if r["doc_id"] not in source_ids:
            errors.append(f"{rid}: doc_id '{r['doc_id']}' is not in sources.csv")
        if not _is_page(r["page"]):
            errors.append(f"{rid}: page must be a 1-indexed integer")
        if not r["gold_answer"].strip():
            errors.append(f"{rid}: gold_answer is empty")
        if not r["evidence_text"].strip():
            errors.append(f"{rid}: evidence_text is empty")
        if qtype == "cross_reference" and not _is_page(r["page_2"]):
            errors.append(f"{rid}: cross_reference needs page_2")
        if qtype == "compare_two":
            if r["doc_id_2"] not in source_ids:
                errors.append(f"{rid}: compare_two needs a valid doc_id_2")
            if not _is_page(r["page_2"]):
                errors.append(f"{rid}: compare_two needs page_2")

    if strict:
        if len(rows) < min_questions:
            errors.append(f"Strict: need at least {min_questions} questions, found {len(rows)}")
        not_verified = [r["id"] for r in rows if r["status"] != "verified"]
        if not_verified:
            errors.append(f"Strict: {len(not_verified)} questions are not verified")
        if check_mix:
            counts = Counter(r["type"] for r in rows)
            for qtype, target in TARGET_MIX.items():
                share = counts.get(qtype, 0) / max(len(rows), 1)
                if abs(share - target) > MIX_TOLERANCE:
                    errors.append(
                        f"Strict: {qtype} is {share:.0%} of questions, target {target:.0%} "
                        f"(tolerance {MIX_TOLERANCE:.0%})"
                    )
    return errors, warnings


def summarize(rows: list[dict[str, str]]) -> str:
    status = Counter(r["status"] for r in rows)
    types = Counter(r["type"] for r in rows)
    lines = [f"{len(rows)} questions | status: {dict(status)}", "type mix (actual vs target):"]
    for qtype, target in TARGET_MIX.items():
        share = types.get(qtype, 0) / max(len(rows), 1)
        lines.append(f"  {qtype:16s} {types.get(qtype, 0):3d}  {share:4.0%} vs {target:.0%}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=ROOT / "data/gold/gold_questions.csv")
    parser.add_argument("--sources", type=Path, default=ROOT / "data/gold/sources.csv")
    parser.add_argument("--strict", action="store_true", help="require a finished benchmark")
    parser.add_argument("--min-questions", type=int, default=MIN_QUESTIONS,
                        help="strict mode: minimum number of questions")
    parser.add_argument("--skip-mix-check", action="store_true",
                        help="strict mode: do not require the 40/25/15/10/10 type mix")
    args = parser.parse_args(argv)

    rows = read_csv(args.gold)
    source_ids = {r["doc_id"] for r in read_csv(args.sources)}
    errors, warnings = validate(rows, source_ids, strict=args.strict,
                                min_questions=args.min_questions,
                                check_mix=not args.skip_mix_check)

    print(summarize(rows))
    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    print("OK" if not errors else f"FAILED with {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
