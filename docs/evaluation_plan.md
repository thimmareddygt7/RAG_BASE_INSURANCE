# Evaluation plan

## Principles
- The gold set (`data/gold/gold_questions.csv`) is **frozen** once all rows are `verified`. Questions are never edited after seeing results.
- LLM, judge, embedding model and gold set are **locked** (`eval/stages.yaml`). One change per stage.
- Retrieval metrics and answer metrics are reported **separately**, because a model can answer wrongly even when given the right page.
- Results are reported as **counts with 95% confidence intervals**, e.g. `117/150 (78.0%, 95% CI 70.7-83.9)`.
- Stage-to-stage comparisons use the **exact McNemar test** on the same questions. With about 110 questions, a gap of a few points is usually noise, and the report says so.

## Stages

| Stage | Change | Config key |
|---|---|---|
| 2 | Vector search, fixed-size chunks (baseline) | `stage2_baseline` |
| 3 | Add BM25 sparse search with RRF | `stage3_hybrid` |
| 4 | Add cross-encoder reranker | `stage4_rerank` |
| 5 | Structure-aware chunking | `stage5_structure` |
| 6 | OCR and table parsing | `stage6_ocr_tables` |

Run a stage with `RAG_STAGE=stage4_rerank`.

## How to run a stage

```bash
docker compose up -d qdrant
make eval-stage STAGE=stage2_baseline   # runs, calibrates the refusal threshold, reruns
make report                             # writes eval/results/REPORT.md
```
`eval-stage` runs three steps: (1) a pass with no threshold, (2) `eval.calibrate` picks the refusal threshold from the 20% calibration questions only, (3) the final pass with that threshold. Run stages in order (2 to 6). Each stage reindexes automatically because its settings change the index fingerprint.

## Version handling in evaluation
Questions run as the admin group. Comparison questions search all versions. All other questions search only the latest version of each policy, so gold pages for them must point at the latest version.

## Metrics
- **Retrieval:** page-level hit@k (k = 1, 3, 5, 10) and MRR, matched on (doc_id, page).
- **Answer:** correctness and faithfulness (LLM judge with a fixed prompt), citation accuracy (cited page contains the support), refusal accuracy on unanswerable questions, and false-refusal rate on answerable ones.
- **Security:** permission leaks, which must be 0 (`data/gold/permission_tests.csv`).
- **Cost:** latency per question (p50 and p95).

## Question mix (target)
40% table lookup, 25% plain text, 15% cross-reference, 10% compare two policies, 10% unanswerable. Results are broken down by type.

## Known risks
- **Judge bias:** the judge and the answer model are the same model, which can favour its own style. Mitigation: hand-check 20 judged answers and report the agreement count.
- **Rate limits and model drift:** Groq limits requests and tokens. The client waits and retries the same model and stops with an error if the limit is long or daily. Each result file records the model used for every call (`integrity.models_used`), and a run that used a different model exits with code 2 and is flagged in the report.
- **Latency:** `--cache-answers` stores the live latency and model with each reply, so cached reruns report the true LLM time. The report shows retrieval and LLM time separately.
- **Page numbers:** use 1-indexed PDF pages, not printed page numbers.
- **Refusal threshold:** reranker and RRF scores are on different scales, so the threshold is calibrated per stage on a stratified 20% calibration split. It is only fitted when that split has at least 5 answerable and 5 unanswerable questions, and it may refuse at most 10% of the answerable ones. Otherwise no threshold is used. Refusal metrics are reported only on questions outside the split.

## Two benchmarks
- `data/gold/gold_questions.csv` (100 questions, frozen after verification) names the product and version in almost every question. It checks the whole system but cannot separate retrieval stages.
- `data/gold/gold_questions_blind.csv` (71 questions) rewords the questions, removes version, page and clause hints, and adds 25 near-miss unanswerable questions. Run it with `python scripts/run_eval_all.py --gold data/gold/gold_questions_blind.csv --tag blind`. Its refusal threshold is calibrated separately.

## Before you trust a result
1. Rows are `verified` (`scripts/check_gold_evidence.py --write-verified --ocr`) and you read the gold answers yourself.
2. The report's "Run integrity" table shows one answer model, one judge model, `Drift = no`, and the expected cache use.
3. You audited 20 judged answers by hand (`scripts/audit_sample.py`) and report the agreement with its confidence interval.
