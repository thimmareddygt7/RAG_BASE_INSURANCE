"""Audit the LLM judge with a human.

Step 1:  python scripts/audit_sample.py create --stage stage4_rerank
         -> writes eval/audit/<stage>_audit.csv with a stratified sample of 20 answers.
Step 2:  open the CSV and fill `human_verdict` (CORRECT or INCORRECT) for every row by
         reading the answer against the gold answer and the source page. Do not look at
         `judge_verdict` first.
Step 3:  python scripts/audit_sample.py score --sheet eval/audit/<stage>_audit.csv
         -> agreement with a confidence interval. Refuses to run until every row is judged.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.audit import (AuditIncomplete, build_sheet, score_sheet, stratified_sample,  # noqa: E402
                        summary_markdown, write_sheet)

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create")
    c.add_argument("--stage", required=True)
    c.add_argument("--tag", default="")
    c.add_argument("--n", type=int, default=20)
    c.add_argument("--seed", type=int, default=42)
    c.add_argument("--gold", default="data/gold/gold_questions.csv")
    s = sub.add_parser("score")
    s.add_argument("--sheet", type=Path, required=True)
    args = parser.parse_args()

    if args.cmd == "create":
        suffix = f"__{args.tag}" if args.tag else ""
        data = json.loads((ROOT / "eval/results" / f"{args.stage}{suffix}.json")
                          .read_text(encoding="utf-8"))
        with (ROOT / args.gold).open(newline="", encoding="utf-8") as f:
            gold = {r["id"]: r for r in csv.DictReader(f)}
        sample = stratified_sample(data["records"], args.n, args.seed)
        out = ROOT / "eval/audit" / f"{args.stage}{suffix}_audit.csv"
        write_sheet(build_sheet(sample, gold), out)
        print(f"Wrote {len(sample)} rows to {out}. Fill in human_verdict for every row, then run: "
              f"python scripts/audit_sample.py score --sheet {out}")
        return 0

    try:
        result = score_sheet(args.sheet)
    except AuditIncomplete as exc:
        print(f"NOT SCORED: {exc}")
        return 1
    text = summary_markdown(result)
    print(text)
    args.sheet.with_suffix(".md").write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
