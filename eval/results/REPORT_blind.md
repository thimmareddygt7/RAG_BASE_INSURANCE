| Stage | n | hit@5 | MRR | Correct | Faithful | Cited correctly | Refusal acc. | False refusal | p50 total ms (retrieval + LLM) | p vs prev |
|---|---|---|---|---|---|---|---|---|---|---|
| stage2_baseline | 71 | 46/46 (100.0%, 95% CI 92.3-100.0) | 0.793 | 39/46 (84.8%, 95% CI 71.8-92.4) | 37/43 (86.0%, 95% CI 72.7-93.4) | 35/43 (81.4%, 95% CI 67.4-90.3) | 19/20 (95.0%, 95% CI 76.4-99.1) | 3/37 (8.1%, 95% CI 2.8-21.3) | 7779 (2065 + 5758) | - |
| stage3_hybrid | 71 | 46/46 (100.0%, 95% CI 92.3-100.0) | 0.815 | 39/46 (84.8%, 95% CI 71.8-92.4) | 38/42 (90.5%, 95% CI 77.9-96.2) | 34/42 (81.0%, 95% CI 66.7-90.0) | 19/20 (95.0%, 95% CI 76.4-99.1) | 3/37 (8.1%, 95% CI 2.8-21.3) | 7862 (4118 + 3841) | 1.000 |
| stage4_rerank | 71 | 45/46 (97.8%, 95% CI 88.7-99.6) | 0.913 | 42/46 (91.3%, 95% CI 79.7-96.6) | 39/45 (86.7%, 95% CI 73.8-93.7) | 38/45 (84.4%, 95% CI 71.2-92.3) | 16/20 (80.0%, 95% CI 58.4-91.9) | 1/37 (2.7%, 95% CI 0.5-13.8) | 7484 (4584 + 3564) | 0.250 |
| stage5_structure | 71 | 45/46 (97.8%, 95% CI 88.7-99.6) | 0.906 | 40/46 (87.0%, 95% CI 74.3-93.9) | 38/45 (84.4%, 95% CI 71.2-92.3) | 40/45 (88.9%, 95% CI 76.5-95.2) | 19/20 (95.0%, 95% CI 76.4-99.1) | 1/37 (2.7%, 95% CI 0.5-13.8) | 5941 (4726 + 1319) | 0.500 |
| stage6_ocr_tables | 71 | 45/46 (97.8%, 95% CI 88.7-99.6) | 0.855 | 40/46 (87.0%, 95% CI 74.3-93.9) | 30/44 (68.2%, 95% CI 53.4-80.0) | 36/44 (81.8%, 95% CI 68.0-90.5) | 18/20 (90.0%, 95% CI 69.9-97.2) | 2/37 (5.4%, 95% CI 1.5-17.7) | 6146 (5010 + 1501) | 1.000 |

Correct answers by question type:

| Stage | compare_two | cross_reference | plain_text | table_lookup |
|---|---|---|---|---|
| stage2_baseline | 4/5 | 4/5 | 13/15 | 18/21 |
| stage3_hybrid | 4/5 | 4/5 | 12/15 | 19/21 |
| stage4_rerank | 5/5 | 4/5 | 14/15 | 19/21 |
| stage5_structure | 5/5 | 4/5 | 13/15 | 18/21 |
| stage6_ocr_tables | 5/5 | 3/5 | 13/15 | 19/21 |

Run integrity (read this before trusting the numbers):

| Stage | Answer model(s) | Judge model(s) | Drift | Cached answers | Threshold | Calibration (ans/unans) | Refusals: threshold / model |
|---|---|---|---|---|---|---|---|
| stage2_baseline | openai/gpt-oss-20b x68 | openai/gpt-oss-20b x86 | no | 68/68 | 0.6193 | 9/5 | 3 / 23 |
| stage3_hybrid | openai/gpt-oss-20b x67 | openai/gpt-oss-20b x84 | no | 67/67 | 0.0320 | 9/5 | 4 / 23 |
| stage4_rerank | openai/gpt-oss-20b x64 | openai/gpt-oss-20b x90 | no | 64/64 | -5.0211 | 9/5 | 7 / 14 |
| stage5_structure | openai/gpt-oss-20b x67 | openai/gpt-oss-20b x90 | no | 67/67 | -5.6880 | 9/5 | 4 / 20 |
| stage6_ocr_tables | openai/gpt-oss-20b x64 | openai/gpt-oss-20b x88 | no | 64/64 | -2.9754 | 9/5 | 7 / 18 |

Notes: LLM time is the stored live call time even for cached replies. Refusal metrics use only questions outside the calibration split. With about a hundred questions, gaps of a few points are usually noise: check the confidence intervals and the p-value before claiming an improvement.
