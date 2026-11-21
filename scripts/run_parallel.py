"""
Parallel evaluation runner — 6 Groq keys, 6 jobs.

Jobs assigned:
  KEY1 → stage5_structure  (main)
  KEY2 → stage6_ocr_tables (main)
  KEY3 → stage2_baseline   (blind)
  KEY4 → stage3_hybrid     (blind)
  KEY5 → stage4_rerank     (blind)
  KEY6 → stage5_structure + stage6_ocr_tables (blind) + reports

Stages 2,3,4 for main are ALREADY DONE (json files exist and are large).
All jobs share the same on-disk cache (cache is key-agnostic).

Usage:
    python scripts/run_parallel.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
RESULTS = ROOT / "eval" / "results"

# ---------------------------------------------------------------------------
# API keys — pass comma-separated in GROQ_API_KEYS or defaults to GROQ_API_KEY
# ---------------------------------------------------------------------------
_env_keys = [k.strip() for k in os.environ.get("GROQ_API_KEYS", "").split(",") if k.strip()]
if not _env_keys:
    _single_key = os.environ.get("GROQ_API_KEY", "")
    _env_keys = [_single_key] * 6 if _single_key else []

KEYS = _env_keys if len(_env_keys) >= 6 else (_env_keys + [""] * (6 - len(_env_keys)))

BLIND_CSV = "data/gold/gold_questions_blind.csv"

# ---------------------------------------------------------------------------
# Job definitions
# (name, stages_list, gold_csv_or_None, tag_or_empty, key_index)
# ---------------------------------------------------------------------------
JOBS = [
    # Main benchmark — stages 5 & 6 still missing
    ("main-stage5",  ["stage5_structure"],  None,       "",      KEYS[0]),
    ("main-stage6",  ["stage6_ocr_tables"], None,       "",      KEYS[1]),
    # Blind benchmark — all 5 stages
    ("blind-s2",     ["stage2_baseline"],   BLIND_CSV,  "blind", KEYS[2]),
    ("blind-s3",     ["stage3_hybrid"],     BLIND_CSV,  "blind", KEYS[3]),
    ("blind-s4",     ["stage4_rerank"],     BLIND_CSV,  "blind", KEYS[4]),
    ("blind-s56",    ["stage5_structure",
                      "stage6_ocr_tables"], BLIND_CSV,  "blind", KEYS[5]),
]


def build_env(key: str) -> dict:
    """Return an env dict with the given Groq key injected and tesseract on PATH."""
    env = os.environ.copy()
    env["GROQ_API_KEY"] = key
    tess_bin = str(ROOT / "tesseract_bin")
    if Path(tess_bin).exists() and tess_bin not in env.get("PATH", ""):
        env["PATH"] = tess_bin + os.pathsep + env.get("PATH", "")
    env.setdefault("TESSDATA_PREFIX", str(ROOT / "tesseract_bin" / "tessdata"))
    return env


def run_stage(stage: str, gold: str | None, tag: str, env: dict):
    """Run no-threshold, calibrate, threshold for one stage."""
    extra = []
    if gold:
        extra += ["--gold", gold]
    if tag:
        extra += ["--tag", tag]
    tag_args = ["--tag", tag] if tag else []

    for cmd in [
        [PY, "-m", "eval.run", "--stage", stage, "--no-threshold", "--cache-answers", *extra],
        [PY, "-m", "eval.calibrate", "--stage", stage, *tag_args],
        [PY, "-m", "eval.run", "--stage", stage, "--cache-answers", *extra],
    ]:
        print(f"  >>> {' '.join(cmd)}", flush=True)
        res = subprocess.run(cmd, cwd=ROOT, env=env)
        if res.returncode != 0:
            print(f"  !!! FAILED (exit {res.returncode}): {' '.join(cmd)}", flush=True)
            return False
    return True


def run_job(job_name: str, stages: list[str], gold: str | None, tag: str, key: str):
    """Run all stages for one job and generate the report if blind-s56."""
    env = build_env(key)
    print(f"\n{'='*60}", flush=True)
    print(f"JOB [{job_name}] key=...{key[-8:]}  stages={stages}", flush=True)
    print('='*60, flush=True)

    for stage in stages:
        ok = run_stage(stage, gold, tag, env)
        if not ok:
            print(f"[{job_name}] *** Stage {stage} failed — job aborted ***", flush=True)
            return

    # After blind-s56 finishes all blind stages, generate both reports
    if job_name == "blind-s56":
        wait_for_blind_s234(env)

    print(f"[{job_name}] ✓ All stages done", flush=True)


def wait_for_blind_s234(env: dict):
    """Block until all stage results exist, then generate all reports."""
    needed = [
        RESULTS / "stage2_baseline__blind.json",
        RESULTS / "stage3_hybrid__blind.json",
        RESULTS / "stage4_rerank__blind.json",
        RESULTS / "stage5_structure__blind.json",
        RESULTS / "stage6_ocr_tables__blind.json",
        RESULTS / "stage5_structure.json",
        RESULTS / "stage6_ocr_tables.json",
    ]
    print("\n[blind-s56] Waiting for all stage results before generating reports...", flush=True)
    while True:
        missing = [p.name for p in needed if not p.exists()]
        if not missing:
            break
        print(f"  still waiting for: {missing}", flush=True)
        time.sleep(30)

    # Generate main report
    print("\n[blind-s56] Generating main REPORT.md ...", flush=True)
    subprocess.run(
        [PY, "-m", "eval.report", "--write", "eval/results/REPORT.md"],
        cwd=ROOT, env=env,
    )
    # Generate blind report
    print("[blind-s56] Generating blind REPORT_blind.md ...", flush=True)
    subprocess.run(
        [PY, "-m", "eval.report", "--write", "eval/results/REPORT_blind.md", "--tag", "blind"],
        cwd=ROOT, env=env,
    )
    # Create audit sheet
    print("[blind-s56] Creating judge audit sheet ...", flush=True)
    subprocess.run(
        [PY, "scripts/audit_sample.py", "create", "--stage", "stage4_rerank"],
        cwd=ROOT, env=env,
    )


# ---------------------------------------------------------------------------
# Main — spawn one process per job
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()

    # --- Step 0: mark both gold CSVs as verified so eval.run can see them ---
    print("Pre-verifying gold CSVs ...", flush=True)
    tess_bin = str(ROOT / "tesseract_bin")
    pre_env = os.environ.copy()
    if Path(tess_bin).exists() and tess_bin not in pre_env.get("PATH", ""):
        pre_env["PATH"] = tess_bin + os.pathsep + pre_env.get("PATH", "")
        pre_env.setdefault("TESSDATA_PREFIX", str(ROOT / "tesseract_bin" / "tessdata"))
    pre_env["GROQ_API_KEY"] = KEYS[0]  # any valid key will do

    for gold_csv, extra_args in [
        (None, []),
        (BLIND_CSV, ["--gold", BLIND_CSV]),
    ]:
        cmd = [PY, "scripts/check_gold_evidence.py", "--ocr",
               "--write-verified", "--confirm-absent", *extra_args]
        print(f"  >>> {' '.join(cmd)}", flush=True)
        res = subprocess.run(cmd, cwd=ROOT, env=pre_env)
        if res.returncode != 0:
            print(f"  !!! check_gold_evidence failed (exit {res.returncode}). Aborting.", flush=True)
            sys.exit(1)
    print("Gold CSVs verified.\n", flush=True)

    processes = []
    for job_name, stages, gold, tag, key in JOBS:
        p = multiprocessing.Process(
            target=run_job,
            args=(job_name, stages, gold, tag, key),
            name=job_name,
            daemon=False,
        )
        processes.append((job_name, p))

    print(f"Launching {len(processes)} parallel jobs ...", flush=True)
    for job_name, p in processes:
        p.start()
        print(f"  Started [{job_name}] pid={p.pid}", flush=True)
        time.sleep(2)  # stagger slightly to avoid cache write collisions at start

    print("\nAll jobs running. Waiting for completion...\n", flush=True)
    for job_name, p in processes:
        p.join()
        code = p.exitcode
        status = "✓ OK" if code == 0 else f"✗ FAILED (exit {code})"
        print(f"  [{job_name}] {status}", flush=True)

    print("\nAll jobs finished. Check eval/results/REPORT.md", flush=True)
