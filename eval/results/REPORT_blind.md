| Stage | n | hit@1 | hit@5 | MRR | change in MRR vs prev (95% CI) | Correct | Faithful | Cited correctly | Refusal acc. | False refusal | p50 total ms (retrieval + LLM) | p vs prev |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| stage2_baseline | 71 | 30/46 (65.2%, 95% CI 50.8-77.3) | 46/46 (100.0%, 95% CI 92.3-100.0) | 0.793 | - | 39/46 (84.8%, 95% CI 71.8-92.4) | 40/43 (93.0%, 95% CI 81.4-97.6) | 36/43 (83.7%, 95% CI 70.0-91.9) | 18/20 (90.0%, 95% CI 69.9-97.2) | 3/37 (8.1%, 95% CI 2.8-21.3) | 7477 (2079 + 5533) | - |
| stage3_hybrid | 71 | 24/46 (52.2%, 95% CI 38.1-65.9) | 40/46 (87.0%, 95% CI 74.3-93.9) | 0.679 | -0.114 (-0.225 to -0.004) | 28/46 (60.9%, 95% CI 46.5-73.6) | 25/30 (83.3%, 95% CI 66.4-92.7) | 27/30 (90.0%, 95% CI 74.4-96.5) | 19/20 (95.0%, 95% CI 76.4-99.1) | 12/37 (32.4%, 95% CI 19.6-48.5) | 6929 (4122 + 3561) | 0.007 |
| stage4_rerank | 71 | 39/46 (84.8%, 95% CI 71.8-92.4) | 45/46 (97.8%, 95% CI 88.7-99.6) | 0.913 | +0.234 (+0.132 to +0.335) | 42/46 (91.3%, 95% CI 79.7-96.6) | 39/45 (86.7%, 95% CI 73.8-93.7) | 38/45 (84.4%, 95% CI 71.2-92.3) | 19/20 (95.0%, 95% CI 76.4-99.1) | 1/37 (2.7%, 95% CI 0.5-13.8) | 7319 (4591 + 2724) | <0.001 |
| stage5_structure | 71 | 38/46 (82.6%, 95% CI 69.3-90.9) | 45/46 (97.8%, 95% CI 88.7-99.6) | 0.906 | -0.007 (-0.033 to +0.011) | 40/46 (87.0%, 95% CI 74.3-93.9) | 34/45 (75.6%, 95% CI 61.3-85.8) | 39/45 (86.7%, 95% CI 73.8-93.7) | 18/20 (90.0%, 95% CI 69.9-97.2) | 1/37 (2.7%, 95% CI 0.5-13.8) | 5970 (4723 + 1559) | 0.500 |
| stage6_ocr_tables | 71 | 34/46 (73.9%, 95% CI 59.7-84.4) | 45/46 (97.8%, 95% CI 88.7-99.6) | 0.851 | -0.055 (-0.109 to -0.001) | 39/46 (84.8%, 95% CI 71.8-92.4) | 32/44 (72.7%, 95% CI 58.2-83.7) | 37/44 (84.1%, 95% CI 70.6-92.1) | 18/20 (90.0%, 95% CI 69.9-97.2) | 2/37 (5.4%, 95% CI 1.5-17.7) | 5504 (4706 + 844) | 1.000 |

Correct answers by question type:

| Stage | compare_two | cross_reference | plain_text | table_lookup |
|---|---|---|---|---|
| stage2_baseline | 4/5 | 4/5 | 13/15 | 18/21 |
| stage3_hybrid | 1/5 | 1/5 | 10/15 | 16/21 |
| stage4_rerank | 5/5 | 4/5 | 13/15 | 20/21 |
| stage5_structure | 5/5 | 4/5 | 13/15 | 18/21 |
| stage6_ocr_tables | 5/5 | 3/5 | 13/15 | 18/21 |

Run integrity (read this before trusting the numbers):

| Stage | Answer model(s) | Judge model(s) | Drift | Cached answers | Threshold | Calibration (ans/unans) | Refusals: threshold / model |
|---|---|---|---|---|---|---|---|
| stage2_baseline | openai/gpt-oss-20b x68 | openai/gpt-oss-20b x86 | no | 68/68 | 0.6193 | 9/5 | 3 / 22 |
| stage3_hybrid | openai/gpt-oss-20b x60 | openai/gpt-oss-20b x60 | no | 60/60 | 0.0315 | 9/5 | 11 / 28 |
| stage4_rerank | openai/gpt-oss-20b x64 | openai/gpt-oss-20b x90 | no | 64/64 | -5.0211 | 9/5 | 7 / 17 |
| stage5_structure | openai/gpt-oss-20b x67 | openai/gpt-oss-20b x90 | no | 67/67 | -5.6880 | 9/5 | 4 / 19 |
| stage6_ocr_tables | openai/gpt-oss-20b x64 | openai/gpt-oss-20b x88 | no | 64/64 | -2.9754 | 9/5 | 7 / 18 |

Notes: LLM time is the stored live call time even for cached replies. Refusal metrics use only questions outside the calibration split. With about a hundred questions, gaps of a few points are usually noise: check the confidence intervals and the p-value before claiming an improvement.
