# Results

> **Status: no results are reported yet.** The first five-stage run is archived in `eval/results/archive_unverified/` and must not be cited. This page is filled from `eval/results/REPORT.md` after you rerun the stages.

## Why the first run was archived
- The Groq client could silently switch to other models on a rate limit, and the result files recorded only the configured model, so it cannot be shown that one model produced every answer.
- Answer replies were cached, so the reported latency (about 20 ms for the LLM) was cache reads. The jump to 4.7 s at stage 6 was a different mix of cached and live calls, not a stage effect.
- Refusal thresholds were fitted on 2 unanswerable questions. The stage 3 threshold (0.0327) sat almost at the maximum possible RRF score (about 0.0328), which is why false refusals jumped. That is a calibration artifact, not a finding about RRF.
- The main gold set names the product and version in almost every question, so Hit@5 was already 89/90 at baseline.
- The gold rows had been stamped `verified` by the generating script, and the "hand-checked 20/20" audit was a script that printed `YES` for every row. Neither was a real human check.

## How to produce numbers you can cite
```bash
python scripts/generate_sample_pdfs.py
python scripts/check_gold_evidence.py --write-verified --ocr     # then read the gold answers
python scripts/run_eval_all.py                                   # main benchmark
python scripts/run_eval_all.py --gold data/gold/gold_questions_blind.csv --tag blind
python scripts/audit_sample.py create --stage stage4_rerank      # fill human_verdict yourself
python scripts/audit_sample.py score --sheet eval/audit/stage4_rerank_audit.csv
```
Before quoting anything, check the "Run integrity" table: one answer model, one judge model, `Drift = no`, and thresholds either `none` or fitted on at least 5 + 5 calibration questions.

## Table to fill from the report
| Stage | Change | hit@5 | Correct | Cited correctly | False refusal | Refusal acc. | p50 total ms |
|---|---|---|---|---|---|---|---|
| 2 | Vector, fixed chunks | - | - | - | - | - | - |
| 3 | + hybrid (BM25 + RRF) | - | - | - | - | - | - |
| 4 | + reranker | - | - | - | - | - | - |
| 5 | + structure-aware chunking | - | - | - | - | - | - |
| 6 | + OCR and tables | - | - | - | - | - | - |

Report counts with the confidence interval and the McNemar p-value, written as `<0.001` rather than `0.000`.

## Judge audit
Not done yet. After `scripts/audit_sample.py score`, paste the agreement line (with its confidence interval) here.

## What failed
Fill this in from your own reruns, with real examples. Do not describe a failure mode unless you saw it in the result files.
