# Results

> **Status:** The five-stage benchmark was run on November 16, 2026. All five stages were executed against the verified 100-question main gold benchmark and the 71-question blind benchmark using fixed models (`openai/gpt-oss-20b`) for both generator and judge, with zero model drift.

## Run Integrity

| Stage | Answer model(s) | Judge model(s) | Drift | Cached answers | Threshold | Calibration (ans/unans) | Refusals: threshold / model |
|---|---|---|---|---|---|---|---|
| stage2_baseline | openai/gpt-oss-20b x100 | openai/gpt-oss-20b x170 | no | 100/100 | none | 18/2 | 0 / 15 |
| stage3_hybrid | openai/gpt-oss-20b x100 | openai/gpt-oss-20b x174 | no | 100/100 | none | 18/2 | 0 / 13 |
| stage4_rerank | openai/gpt-oss-20b x100 | openai/gpt-oss-20b x174 | no | 100/100 | none | 18/2 | 0 / 13 |
| stage5_structure | openai/gpt-oss-20b x100 | openai/gpt-oss-20b x174 | no | 100/100 | none | 18/2 | 0 / 13 |
| stage6_ocr_tables | openai/gpt-oss-20b x100 | openai/gpt-oss-20b x164 | no | 100/100 | none | 18/2 | 0 / 18 |

LLM times reflect live API calls. Refusal thresholds fell back to `none` as calibration had fewer than 5 unanswerable questions (18/2 split), preventing calibration artifacts.

## Main Benchmark Results (100 Questions)

Filled directly from `eval/results/REPORT.md`:

| Stage | Change | hit@5 | Correct | Cited correctly | False refusal | Refusal acc. | p50 total ms | p vs prev |
|---|---|---|---|---|---|---|---|---|
| 2 | Vector, fixed chunks | 89/90 (98.9%, 95% CI 94.0-99.8) | 81/90 (90.0%, 95% CI 82.1-94.6) | 77/85 (90.6%, 95% CI 82.5-95.2) | 3/72 (4.2%, 95% CI 1.4-11.5) | 8/8 (100.0%, 95% CI 67.6-100.0) | 7883 (2083 + 5798) | - |
| 3 | + hybrid (BM25 + RRF) | 89/90 (98.9%, 95% CI 94.0-99.8) | 84/90 (93.3%, 95% CI 86.2-96.9) | 78/87 (89.7%, 95% CI 81.5-94.5) | 2/72 (2.8%, 95% CI 0.8-9.6) | 8/8 (100.0%, 95% CI 67.6-100.0) | 6490 (4139 + 2353) | 0.250 |
| 4 | + reranker | 89/90 (98.9%, 95% CI 94.0-99.8) | 83/90 (92.2%, 95% CI 84.8-96.2) | 75/87 (86.2%, 95% CI 77.4-91.9) | 2/72 (2.8%, 95% CI 0.8-9.6) | 8/8 (100.0%, 95% CI 67.6-100.0) | 7286 (4804 + 2522) | 1.000 |
| 5 | + structure-aware chunking | 89/90 (98.9%, 95% CI 94.0-99.8) | 83/90 (92.2%, 95% CI 84.8-96.2) | 74/87 (85.1%, 95% CI 76.1-91.1) | 2/72 (2.8%, 95% CI 0.8-9.6) | 8/8 (100.0%, 95% CI 67.6-100.0) | 6604 (4955 + 1645) | 1.000 |
| 6 | + OCR and tables | 90/90 (100.0%, 95% CI 95.9-100.0) | 78/90 (86.7%, 95% CI 78.1-92.2) | 70/82 (85.4%, 95% CI 76.1-91.4) | 7/72 (9.7%, 95% CI 4.8-18.7) | 8/8 (100.0%, 95% CI 67.6-100.0) | 5702 (4923 + 782) | 0.227 |

*Statistical Note:* Across consecutive stages, all McNemar p-values exceed 0.05 (Stage 2 to 3: p=0.250; Stage 3 to 4: p=1.000; Stage 4 to 5: p=1.000; Stage 5 to 6: p=0.227). With 90 answerable questions in the main set, there is **no clear difference** statistically between the stages.

### Correct answers by question type (Main Set)

| Stage | compare_two | cross_reference | plain_text | table_lookup |
|---|---|---|---|---|
| stage2_baseline | 10/10 | 10/15 | 22/25 | 39/40 |
| stage3_hybrid | 10/10 | 11/15 | 24/25 | 39/40 |
| stage4_rerank | 10/10 | 10/15 | 24/25 | 39/40 |
| stage5_structure | 10/10 | 11/15 | 23/25 | 39/40 |
| stage6_ocr_tables | 6/10 | 10/15 | 23/25 | 39/40 |

---

## Blind Benchmark Results (71 Questions)

Filled directly from `eval/results/REPORT_blind.md`:

| Stage | n | hit@5 | MRR | Correct | Faithful | Cited correctly | Refusal acc. | False refusal | p50 total ms | p vs prev |
|---|---|---|---|---|---|---|---|---|---|---|
| stage2_baseline | 71 | 46/46 (100.0%, 95% CI 92.3-100.0) | 0.793 | 39/46 (84.8%, 95% CI 71.8-92.4) | 37/43 (86.0%, 95% CI 72.7-93.4) | 35/43 (81.4%, 95% CI 67.4-90.3) | 19/20 (95.0%, 95% CI 76.4-99.1) | 3/37 (8.1%, 95% CI 2.8-21.3) | 7779 (2065 + 5758) | - |
| stage3_hybrid | 71 | 46/46 (100.0%, 95% CI 92.3-100.0) | 0.815 | 39/46 (84.8%, 95% CI 71.8-92.4) | 38/42 (90.5%, 95% CI 77.9-96.2) | 34/42 (81.0%, 95% CI 66.7-90.0) | 19/20 (95.0%, 95% CI 76.4-99.1) | 3/37 (8.1%, 95% CI 2.8-21.3) | 7862 (4118 + 3841) | 1.000 |
| stage4_rerank | 71 | 45/46 (97.8%, 95% CI 88.7-99.6) | 0.913 | 42/46 (91.3%, 95% CI 79.7-96.6) | 39/45 (86.7%, 95% CI 73.8-93.7) | 38/45 (84.4%, 95% CI 71.2-92.3) | 16/20 (80.0%, 95% CI 58.4-91.9) | 1/37 (2.7%, 95% CI 0.5-13.8) | 7484 (4584 + 3564) | 0.250 |
| stage5_structure | 71 | 45/46 (97.8%, 95% CI 88.7-99.6) | 0.906 | 40/46 (87.0%, 95% CI 74.3-93.9) | 38/45 (84.4%, 95% CI 71.2-92.3) | 40/45 (88.9%, 95% CI 76.5-95.2) | 19/20 (95.0%, 95% CI 76.4-99.1) | 1/37 (2.7%, 95% CI 0.5-13.8) | 5941 (4726 + 1319) | 0.500 |
| stage6_ocr_tables | 71 | 45/46 (97.8%, 95% CI 88.7-99.6) | 0.855 | 40/46 (87.0%, 95% CI 74.3-93.9) | 30/44 (68.2%, 95% CI 53.4-80.0) | 36/44 (81.8%, 95% CI 68.0-90.5) | 18/20 (90.0%, 95% CI 69.9-97.2) | 2/37 (5.4%, 95% CI 1.5-17.7) | 6146 (5010 + 1501) | 1.000 |

---

## Judge Audit

The LLM judge was audited by evaluating a stratified sample of 20 model answers from `stage4_rerank` against original document source pages:

> Judge vs human agreement: **19/20** (95%, 95% CI 76-99%). Verdicts were given by a person reading each answer against the gold answer and the source page.

**Documented Disagreement:**
- **Q009**: Judge `INCORRECT`, Human `CORRECT`.
  - *Question:* "What is the daily hospital cash allowance and maximum days covered under Apex Health Shield Version 2?"
  - *Evidence in APEX_HEALTH_V2 p.2:* "Daily Hospital Cash Allowance | Rs. 2,000 per day (maximum 15 days) | Initial 30 days"
  - *Model Answer:* "The daily hospital cash allowance is Rs. 2,000 per day, and it is payable for a maximum of 15 days per admission. [APEX_HEALTH_V2 p.2]"
  - *Finding:* The model answer accurately extracted Rs. 2,000/day from the policy, but `gold_questions.csv` had a typo ("Rs. 2,00,000"), which led the automated LLM judge to flag it as incorrect.

---

## What Failed

Real failure modes observed in the evaluation results:

1. **Multi-page Cross-Reference False Refusal (Q068)**
   - *Question:* "In Apex Health Shield Version 2, how is Co-payment defined on Page 1, and what specific percentage applies to senior citizens on Page 6?"
   - *Outcome:* The model replied: `"I do not have enough information in the provided policy documents to answer this question."` (`model_refused`).
   - *Diagnosis:* The Co-payment definition is on Page 1 and the senior co-payment reduction is on Page 6. Because the information was separated by five pages, retrieval chunks did not place both passages within the top-k context window simultaneously, triggering a safe model refusal rather than hallucination.

2. **Distant Scanned Rider Cross-Reference (Q080)**
   - *Question:* "In the Critical Illness Rider, what is the initial waiting period on Page 2 compared to the organ donor waiting period in the Page 3 endorsement?"
   - *Outcome:* Model answered with refusal.
   - *Diagnosis:* Scanned image extraction required cross-page linking between Page 2 and Page 3 of `SPECIAL_RIDER_SCANNED`. While OCR extracted both pages, cross-page chunk fusion was insufficient to pass both sections to the generation prompt.

3. **Gold Question Typo Causing Automated Evaluation Discrepancy (Q009)**
   - *Question:* "What is the daily hospital cash allowance and maximum days covered under Apex Health Shield Version 2?"
   - *Outcome:* The pipeline accurately answered Rs. 2,000 per day with citation `[APEX_HEALTH_V2 p.2]`, but the evaluator marked it incorrect due to the draft string `"Rs. 2,00,000"`.
