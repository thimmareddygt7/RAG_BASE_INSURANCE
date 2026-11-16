| Stage | n | hit@5 | MRR | Correct | Faithful | Cited correctly | Refusal acc. | False refusal | p50 total ms (retrieval + LLM) | p vs prev |
|---|---|---|---|---|---|---|---|---|---|---|
| stage2_baseline | 100 | 89/90 (98.9%, 95% CI 94.0-99.8) | 0.931 | 81/90 (90.0%, 95% CI 82.1-94.6) | 69/85 (81.2%, 95% CI 71.6-88.1) | 77/85 (90.6%, 95% CI 82.5-95.2) | 8/8 (100.0%, 95% CI 67.6-100.0) | 3/72 (4.2%, 95% CI 1.4-11.5) | 7883 (2083 + 5798) | - |
| stage3_hybrid | 100 | 89/90 (98.9%, 95% CI 94.0-99.8) | 0.967 | 84/90 (93.3%, 95% CI 86.2-96.9) | 75/87 (86.2%, 95% CI 77.4-91.9) | 78/87 (89.7%, 95% CI 81.5-94.5) | 8/8 (100.0%, 95% CI 67.6-100.0) | 2/72 (2.8%, 95% CI 0.8-9.6) | 6490 (4139 + 2353) | 0.250 |
| stage4_rerank | 100 | 89/90 (98.9%, 95% CI 94.0-99.8) | 0.972 | 83/90 (92.2%, 95% CI 84.8-96.2) | 75/87 (86.2%, 95% CI 77.4-91.9) | 75/87 (86.2%, 95% CI 77.4-91.9) | 8/8 (100.0%, 95% CI 67.6-100.0) | 2/72 (2.8%, 95% CI 0.8-9.6) | 7286 (4804 + 2522) | 1.000 |
| stage5_structure | 100 | 89/90 (98.9%, 95% CI 94.0-99.8) | 0.963 | 83/90 (92.2%, 95% CI 84.8-96.2) | 75/87 (86.2%, 95% CI 77.4-91.9) | 74/87 (85.1%, 95% CI 76.1-91.1) | 8/8 (100.0%, 95% CI 67.6-100.0) | 2/72 (2.8%, 95% CI 0.8-9.6) | 6604 (4955 + 1645) | 1.000 |
| stage6_ocr_tables | 100 | 90/90 (100.0%, 95% CI 95.9-100.0) | 0.956 | 78/90 (86.7%, 95% CI 78.1-92.2) | 63/82 (76.8%, 95% CI 66.6-84.6) | 70/82 (85.4%, 95% CI 76.1-91.4) | 8/8 (100.0%, 95% CI 67.6-100.0) | 7/72 (9.7%, 95% CI 4.8-18.7) | 5702 (4923 + 782) | 0.227 |

Correct answers by question type:

| Stage | compare_two | cross_reference | plain_text | table_lookup |
|---|---|---|---|---|
| stage2_baseline | 10/10 | 10/15 | 22/25 | 39/40 |
| stage3_hybrid | 10/10 | 11/15 | 24/25 | 39/40 |
| stage4_rerank | 10/10 | 10/15 | 24/25 | 39/40 |
| stage5_structure | 10/10 | 11/15 | 23/25 | 39/40 |
| stage6_ocr_tables | 6/10 | 10/15 | 23/25 | 39/40 |

Run integrity (read this before trusting the numbers):

| Stage | Answer model(s) | Judge model(s) | Drift | Cached answers | Threshold | Calibration (ans/unans) | Refusals: threshold / model |
|---|---|---|---|---|---|---|---|
| stage2_baseline | openai/gpt-oss-20b x100 | openai/gpt-oss-20b x170 | no | 100/100 | none | 18/2 | 0 / 15 |
| stage3_hybrid | openai/gpt-oss-20b x100 | openai/gpt-oss-20b x174 | no | 100/100 | none | 18/2 | 0 / 13 |
| stage4_rerank | openai/gpt-oss-20b x100 | openai/gpt-oss-20b x174 | no | 100/100 | none | 18/2 | 0 / 13 |
| stage5_structure | openai/gpt-oss-20b x100 | openai/gpt-oss-20b x174 | no | 100/100 | none | 18/2 | 0 / 13 |
| stage6_ocr_tables | openai/gpt-oss-20b x100 | openai/gpt-oss-20b x164 | no | 100/100 | none | 18/2 | 0 / 18 |

Notes: LLM time is the stored live call time even for cached replies. Refusal metrics use only questions outside the calibration split. With about a hundred questions, gaps of a few points are usually noise: check the confidence intervals and the p-value before claiming an improvement.
