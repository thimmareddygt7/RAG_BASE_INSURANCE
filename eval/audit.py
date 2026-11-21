"""Human audit of the LLM judge.

The judge (an LLM) decides whether each answer is correct. To know whether to trust it, a
person reads a sample of answers and gives their own verdict. Agreement is computed ONLY from
those human verdicts. Nothing here ever invents a verdict, and scoring refuses to run while any
verdict is blank.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any

from eval.metrics import wilson_interval

SHEET_COLUMNS = ["id", "type", "question", "gold_answer", "evidence_text", "model_answer",
                 "refused", "citations", "judge_verdict", "human_verdict", "notes"]
VALID = {"CORRECT", "INCORRECT"}


def stratified_sample(records: list[dict[str, Any]], n: int = 20,
                      seed: int = 42) -> list[dict[str, Any]]:
    """Deterministic sample spread evenly across question types (round robin over hash order),
    so rare types such as unanswerable or comparison questions are not drowned out."""
    def order(rec: dict[str, Any]) -> str:
        return hashlib.sha256(f"{seed}:{rec['id']}".encode()).hexdigest()

    queues: dict[str, list[dict[str, Any]]] = {}
    for rec in sorted(records, key=order):
        queues.setdefault(rec["type"], []).append(rec)
    chosen: list[dict[str, Any]] = []
    target = min(n, len(records))
    while len(chosen) < target:
        for t in sorted(queues):
            if queues[t] and len(chosen) < target:
                chosen.append(queues[t].pop(0))
    return sorted(chosen, key=lambda r: r["id"])


def build_sheet(sample: list[dict[str, Any]], gold: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for rec in sample:
        g = gold.get(rec["id"], {})
        cites = "; ".join(f"{c['doc_id']} p.{c['page']}{'' if c['verified'] else ' (unverified)'}"
                          for c in rec.get("citations", []))
        rows.append({"id": rec["id"], "type": rec["type"], "question": rec["question"],
                     "gold_answer": g.get("gold_answer", ""),
                     "evidence_text": g.get("evidence_text", ""),
                     "model_answer": rec["answer"], "refused": str(rec["refused"]),
                     "citations": cites,
                     "judge_verdict": "CORRECT" if rec["correct"] else "INCORRECT",
                     "human_verdict": "", "notes": ""})
    return rows


def write_sheet(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SHEET_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class AuditIncomplete(ValueError):
    """Raised when human verdicts are missing or invalid."""


def score_sheet(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise AuditIncomplete("The audit sheet is empty.")
    missing = [r["id"] for r in rows if r["human_verdict"].strip().upper() not in VALID]
    if missing:
        raise AuditIncomplete(
            f"{len(missing)} of {len(rows)} rows have no valid human_verdict (CORRECT or "
            f"INCORRECT): {missing[:10]}. Read each answer and fill the column in. "
            "Agreement is not reported until every row is judged by a person.")
    agree = [r for r in rows if r["human_verdict"].strip().upper() == r["judge_verdict"]]
    low, high = wilson_interval(len(agree), len(rows))
    return {"n": len(rows), "agree": len(agree), "rate": len(agree) / len(rows),
            "ci_low": low, "ci_high": high,
            "disagreements": [{"id": r["id"], "judge": r["judge_verdict"],
                               "human": r["human_verdict"].strip().upper(),
                               "question": r["question"], "notes": r["notes"]}
                              for r in rows if r not in agree]}


def summary_markdown(result: dict[str, Any]) -> str:
    lines = [f"Judge vs human agreement: **{result['agree']}/{result['n']}** "
             f"({100 * result['rate']:.0f}%, 95% CI {100 * result['ci_low']:.0f}-"
             f"{100 * result['ci_high']:.0f}%). Verdicts were given by a person reading each "
             "answer against the gold answer and the source page.", ""]
    if result["disagreements"]:
        lines.append("Disagreements:")
        for d in result["disagreements"]:
            lines.append(f"- {d['id']}: judge {d['judge']}, human {d['human']}. {d['question']} "
                         f"{d['notes']}".rstrip())
    else:
        lines.append("No disagreements in this sample. A small sample cannot show the judge is "
                     "right more often than the lower confidence bound above.")
    return "\n".join(lines)
