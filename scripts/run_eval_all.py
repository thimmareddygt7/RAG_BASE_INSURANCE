"""Script to run all evaluation stages sequentially with caching and error handling."""

import argparse
import subprocess
import sys
import time

STAGES = [
    "stage2_baseline",
    "stage3_hybrid",
    "stage4_rerank",
    "stage5_structure",
    "stage6_ocr_tables",
]


def run_cmd(cmd):
    print(f"\n>>> Running: {' '.join(cmd)}")
    t0 = time.time()
    res = subprocess.run(cmd)
    dt = time.time() - t0
    print(f">>> Exit code {res.returncode} ({dt:.1f}s)")
    if res.returncode != 0:
        print(f"Error running {' '.join(cmd)}")
        sys.exit(res.returncode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stages", nargs="*", default=STAGES)
    parser.add_argument("--gold", help="gold CSV, e.g. data/gold/gold_questions_blind.csv")
    parser.add_argument("--tag", default="", help="result tag, e.g. blind")
    args = parser.parse_args()
    extra = (["--gold", args.gold] if args.gold else []) + (["--tag", args.tag] if args.tag else [])
    tag_args = ["--tag", args.tag] if args.tag else []
    print(f"Running stages: {args.stages}")
    for stage in args.stages:
        print("\n==========================================")
        print(f"STAGE: {stage}")
        print("==========================================")
        common = ["--cache-answers", *extra]
        run_cmd([sys.executable, "-m", "eval.run", "--stage", stage, "--no-threshold", *common])
        run_cmd([sys.executable, "-m", "eval.calibrate", "--stage", stage, *tag_args])
        run_cmd([sys.executable, "-m", "eval.run", "--stage", stage, *common])

    print("\n==========================================")
    print("Generating Final Evaluation Report...")
    print("==========================================")
    out = f"eval/results/REPORT{('_' + args.tag) if args.tag else ''}.md"
    run_cmd([sys.executable, "-m", "eval.report", "--write", out, *tag_args])
    print("\nAll stages completed. Read the 'Run integrity' table before trusting any number.")


if __name__ == "__main__":
    main()
