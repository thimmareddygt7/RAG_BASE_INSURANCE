"""Look at one question in a result file, to test a diagnosis against the data.

  python scripts/inspect_result.py --stage stage6_ocr_tables --id Q068
  python scripts/inspect_result.py --stage stage4_rerank --tag blind --id B012 \\
      --gold data/gold/gold_questions_blind.csv

Shows the gold pages, which pages retrieval returned (gold pages marked), whether the model
refused and why, the answer, the citations and the model that answered. Use it before writing
a "what failed" explanation: say what the data shows, and label anything else as a hypothesis.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def describe(record: dict, gold_row: dict | None, top_k: int = 5, context_k: int = 3) -> str:
    gold = {(d, p) for d, p in record["gold_pages"]}
    ranked = record["retrieved"]
    lines = [f"{record['id']} ({record['type']}): {record['question']}"]
    if gold_row:
        lines.append(f"gold answer: {gold_row['gold_answer']}")
    lines.append(f"gold pages: {sorted(gold) or 'none (unanswerable)'}")
    lines.append("retrieved (rank, doc, page, score):")
    for rank, (doc, page, score) in enumerate(ranked, start=1):
        mark = "  <== GOLD" if (doc, page) in gold else ""
        zone = "context" if rank <= context_k else ("top-k" if rank <= top_k else "")
        lines.append(f"  {rank:2d} {doc} p.{page} {score:.4f} {zone}{mark}")
    for g in sorted(gold):
        pos = next((i for i, (d, p, _) in enumerate(ranked, start=1) if (d, p) == g), None)
        lines.append(f"gold page {g[0]} p.{g[1]}: "
                     + (f"rank {pos}" + (" (in the context given to the model)"
                                         if pos <= context_k else " (NOT in the context)")
                        if pos else f"not retrieved in the top {len(ranked)}"))
    lines.append(f"refused: {record['refused']} ({record['refusal_reason'] or 'n/a'}); "
                 f"correct: {record.get('correct')}; faithful: {record.get('faithful')}")
    lines.append(f"answer model: {record.get('answer_model') or 'n/a'}; "
                 f"cached: {record.get('llm_cached')}; retrieval {record.get('retrieval_ms')} ms, "
                 f"llm {record.get('llm_ms')} ms")
    lines.append(f"citations: {record['citations']}")
    lines.append(f"answer: {record['answer']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--tag", default="")
    parser.add_argument("--gold", default="data/gold/gold_questions.csv")
    args = parser.parse_args()
    suffix = f"__{args.tag}" if args.tag else ""
    data = json.loads((ROOT / "eval/results" / f"{args.stage}{suffix}.json")
                      .read_text(encoding="utf-8"))
    rec = next((r for r in data["records"] if r["id"] == args.id), None)
    if rec is None:
        print(f"{args.id} not found in {args.stage}{suffix}.json")
        return 1
    with (ROOT / args.gold).open(newline="", encoding="utf-8") as f:
        gold = {r["id"]: r for r in csv.DictReader(f)}
    print(describe(rec, gold.get(args.id)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
