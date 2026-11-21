| Stage | n | hit@1 | hit@5 | MRR | change in MRR vs prev (95% CI) | Correct | Faithful | Cited correctly | Refusal acc. | False refusal | p50 total ms (retrieval + LLM) | p vs prev |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| stage2_baseline | 100 | 79/90 (87.8%, 95% CI 79.4-93.0) | 89/90 (98.9%, 95% CI 94.0-99.8) | 0.931 | - | 83/90 (92.2%, 95% CI 84.8-96.2) | 77/86 (89.5%, 95% CI 81.3-94.4) | 77/86 (89.5%, 95% CI 81.3-94.4) | 8/8 (100.0%, 95% CI 67.6-100.0) | 2/72 (2.8%, 95% CI 0.8-9.6) | 8039 (2096 + 5940) | - |
| stage3_hybrid | 100 | 59/90 (65.6%, 95% CI 55.3-74.6) | 84/90 (93.3%, 95% CI 86.2-96.9) | 0.792 | -0.138 (-0.196 to -0.075) | 71/90 (78.9%, 95% CI 69.4-86.0) | 63/74 (85.1%, 95% CI 75.3-91.5) | 66/74 (89.2%, 95% CI 80.1-94.4) | 8/8 (100.0%, 95% CI 67.6-100.0) | 13/72 (18.1%, 95% CI 10.9-28.5) | 7424 (4108 + 3299) | 0.002 |
| stage4_rerank | 100 | 86/90 (95.6%, 95% CI 89.1-98.3) | 89/90 (98.9%, 95% CI 94.0-99.8) | 0.972 | +0.180 (+0.120 to +0.238) | 84/90 (93.3%, 95% CI 86.2-96.9) | 80/88 (90.9%, 95% CI 83.1-95.3) | 78/88 (88.6%, 95% CI 80.3-93.7) | 8/8 (100.0%, 95% CI 67.6-100.0) | 1/72 (1.4%, 95% CI 0.2-7.5) | 8379 (4598 + 3808) | 0.002 |
| stage5_structure | 100 | 85/90 (94.4%, 95% CI 87.6-97.6) | 89/90 (98.9%, 95% CI 94.0-99.8) | 0.963 | -0.009 (-0.026 to +0.000) | 84/90 (93.3%, 95% CI 86.2-96.9) | 72/86 (83.7%, 95% CI 74.5-90.0) | 74/86 (86.0%, 95% CI 77.2-91.8) | 8/8 (100.0%, 95% CI 67.6-100.0) | 2/72 (2.8%, 95% CI 0.8-9.6) | 6743 (4925 + 1765) | 1.000 |
| stage6_ocr_tables | 100 | 84/90 (93.3%, 95% CI 86.2-96.9) | 90/90 (100.0%, 95% CI 95.9-100.0) | 0.961 | -0.002 (-0.037 to +0.033) | 78/90 (86.7%, 95% CI 78.1-92.2) | 64/81 (79.0%, 95% CI 68.9-86.5) | 69/81 (85.2%, 95% CI 75.9-91.3) | 8/8 (100.0%, 95% CI 67.6-100.0) | 8/72 (11.1%, 95% CI 5.7-20.4) | 6420 (4909 + 1663) | 0.146 |

Correct answers by question type:

| Stage | compare_two | cross_reference | plain_text | table_lookup |
|---|---|---|---|---|
| stage2_baseline | 10/10 | 11/15 | 22/25 | 40/40 |
| stage3_hybrid | 7/10 | 5/15 | 22/25 | 37/40 |
| stage4_rerank | 10/10 | 11/15 | 23/25 | 40/40 |
| stage5_structure | 10/10 | 11/15 | 23/25 | 40/40 |
| stage6_ocr_tables | 7/10 | 10/15 | 23/25 | 38/40 |

Run integrity (read this before trusting the numbers):

| Stage | Answer model(s) | Judge model(s) | Drift | Cached answers | Threshold | Calibration (ans/unans) | Refusals: threshold / model |
|---|---|---|---|---|---|---|---|
| stage2_baseline | openai/gpt-oss-20b x100 | openai/gpt-oss-20b x172 | no | 100/100 | none | 18/2 | 0 / 14 |
| stage3_hybrid | openai/gpt-oss-20b x100 | openai/gpt-oss-20b x148 | no | 100/100 | none | 18/2 | 0 / 26 |
| stage4_rerank | openai/gpt-oss-20b x100 | openai/gpt-oss-20b x176 | no | 30/100 | none | 18/2 | 0 / 12 |
| stage5_structure | openai/gpt-oss-20b x100 | openai/gpt-oss-20b x172 | no | 100/100 | none | 18/2 | 0 / 14 |
| stage6_ocr_tables | openai/gpt-oss-20b x100 | openai/gpt-oss-20b x162 | no | 100/100 | none | 18/2 | 0 / 19 |

Notes: LLM time is the stored live call time even for cached replies. Refusal metrics use only questions outside the calibration split. With about a hundred questions, gaps of a few points are usually noise: check the confidence intervals and the p-value before claiming an improvement.
