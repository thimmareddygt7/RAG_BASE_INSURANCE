"""Run the whole project in the right order and stop at every point that needs a person.

  python scripts/run_everything.py                  # preflight, tests, PDFs, evidence check, STOP
  python scripts/run_everything.py --gold-answers-reviewed --absent-confirmed
                                                    # verify gold, run all stages, audit sheet
  python scripts/run_everything.py --dry-run        # print the plan only

It never decides anything a person must decide:
  * it will not mark gold rows verified unless you pass --gold-answers-reviewed
  * it will not mark unanswerable rows verified unless you also pass --absent-confirmed
  * it creates the judge-audit sheet but never fills in a verdict
It ends by checking the report for model drift and missing model records.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
BLIND = "data/gold/gold_questions_blind.csv"


@dataclass(frozen=True)
class Step:
    name: str
    cmd: list[str]
    needs: str = ""  # human-confirmation flag required before this step runs


def plan(gold_reviewed: bool, absent_confirmed: bool, skip_blind: bool) -> list[Step]:
    steps = [
        Step("unit tests", [PY, "-m", "unittest", "discover", "-s", "tests", "-t", "."]),
        Step("generate the PDFs", [PY, "scripts/generate_sample_pdfs.py"]),
        Step("check gold evidence (main)", [PY, "scripts/check_gold_evidence.py", "--ocr"]),
        Step("check gold evidence (blind)",
             [PY, "scripts/check_gold_evidence.py", "--ocr", "--gold", BLIND]),
    ]
    confirm = ["--confirm-absent"] if absent_confirmed else []
    steps += [
        Step("mark verified (main)", [PY, "scripts/check_gold_evidence.py", "--ocr",
                                      "--write-verified", *confirm], "gold_reviewed"),
        Step("mark verified (blind)", [PY, "scripts/check_gold_evidence.py", "--ocr", "--gold",
                                       BLIND, "--write-verified", *confirm], "gold_reviewed"),
        Step("strict gold validation (main)", [PY, "scripts/validate_gold.py", "--strict"],
             "gold_reviewed"),
        Step("strict gold validation (blind)",
             [PY, "scripts/validate_gold.py", "--gold", BLIND, "--strict", "--min-questions",
              "70", "--skip-mix-check"], "gold_reviewed"),
        Step("run five stages (main benchmark)", [PY, "scripts/run_eval_all.py"],
             "gold_reviewed"),
    ]
    if not skip_blind:
        steps.append(Step("run five stages (blind benchmark)",
                          [PY, "scripts/run_eval_all.py", "--gold", BLIND, "--tag", "blind"],
                          "gold_reviewed"))
    steps.append(Step("create the judge audit sheet",
                      [PY, "scripts/audit_sample.py", "create", "--stage", "stage4_rerank"],
                      "gold_reviewed"))
    return steps


def preflight() -> list[str]:
    problems = []
    tess_bin = str(ROOT / "tesseract_bin")
    if Path(tess_bin).exists() and tess_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = tess_bin + os.pathsep + os.environ.get("PATH", "")
        os.environ.setdefault("TESSDATA_PREFIX", str(ROOT / "tesseract_bin" / "tessdata"))

    env = (ROOT / ".env").read_text(encoding="utf-8") if (ROOT / ".env").exists() else ""
    key = next((ln.split("=", 1)[1].strip() for ln in env.splitlines()
                if ln.startswith("GROQ_API_KEY=")), os.environ.get("GROQ_API_KEY", ""))
    if not key or "your_" in key:
        problems.append("GROQ_API_KEY is missing or still a placeholder in .env")
    if not shutil.which("tesseract"):
        problems.append("tesseract is not installed (needed for the scanned rider)")
    try:
        urllib.request.urlopen("http://localhost:6333/healthz", timeout=3)
    except Exception:
        problems.append("Qdrant is not reachable on localhost:6333 (docker compose up -d qdrant)")
    try:
        import fitz  # noqa: F401
    except ImportError:
        problems.append("PyMuPDF is not installed (pip install -r requirements.txt)")
    return problems


def report_problems(report_paths: list[Path]) -> list[str]:
    """Things in the reports that mean the numbers must not be used."""
    issues = []
    for path in report_paths:
        if not path.exists():
            issues.append(f"{path.name} was not written")
            continue
        text = path.read_text(encoding="utf-8")
        for marker, meaning in (("MODEL DRIFT", "a different model answered"),
                                ("UNVERIFIED", "model identity was not recorded"),
                                ("no model-identity record", "model identity was not recorded"),
                                ("offline stand-ins", "results came from stand-in models")):
            if marker in text:
                issues.append(f"{path.name}: {meaning} ('{marker}')")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gold-answers-reviewed", action="store_true",
                        help="you have read every gold answer against the PDFs")
    parser.add_argument("--absent-confirmed", action="store_true",
                        help="you searched the PDFs for every unanswerable question")
    parser.add_argument("--skip-blind", action="store_true")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    steps = plan(args.gold_answers_reviewed, args.absent_confirmed, args.skip_blind)
    if args.dry_run:
        for i, s in enumerate(steps, 1):
            blocked = s.needs and not args.gold_answers_reviewed
            gate = "   [needs --gold-answers-reviewed]" if blocked else ""
            print(f"{i:2d}. {s.name}: {' '.join(s.cmd[1:])}{gate}")
        return 0

    if not args.skip_preflight:
        problems = preflight()
        if problems:
            print("Preflight failed:\n  - " + "\n  - ".join(problems))
            return 1
    for s in steps:
        if s.needs and not args.gold_answers_reviewed:
            print("\nSTOPPED before the evaluation. Do these by hand, then rerun with "
                  "--gold-answers-reviewed (and --absent-confirmed):\n"
                  "  1. Read every gold answer in data/gold/gold_questions.csv against the PDFs.\n"
                  "  2. Search the PDFs for every unanswerable question (main and blind).\n")
            return 0
        print(f"\n=== {s.name}")
        if subprocess.run(s.cmd, cwd=ROOT).returncode != 0:
            print(f"\nFAILED at: {s.name}. Fix it and rerun; finished steps are cheap to repeat.")
            return 1

    issues = report_problems([ROOT / "eval/results/REPORT.md"]
                             + ([] if args.skip_blind else [ROOT / "eval/results/REPORT_blind.md"]))
    if issues:
        print("\nDO NOT USE THESE NUMBERS:\n  - " + "\n  - ".join(issues))
        return 2
    print("\nAll automatic steps passed. Still to do by hand:\n"
          "  1. Fill human_verdict for all 20 rows in eval/audit/stage4_rerank_audit.csv, then run\n"
          "     python scripts/audit_sample.py score --sheet eval/audit/stage4_rerank_audit.csv\n"
          "  2. Inspect failures: python scripts/inspect_result.py --stage <stage> --id <id>\n"
          "  3. Fill docs/results.md from eval/results/REPORT*.md (numbers only from there)\n"
          "  4. git status (confirm .env is not listed), commit, push, check CI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
