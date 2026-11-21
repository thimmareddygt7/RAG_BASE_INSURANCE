# Changelog

## After the first real five-stage run
- **Gold fix (Q009):** the gold answer said "Rs. 2,00,000 per day" but the policy says "Rs. 2,000 per day". The judge audit exposed it (the model was right and the gold was wrong). Corrected in `data/gold/gold_questions.csv` and `scripts/populate_gold.py`. Results produced before this fix count Q009 as wrong in every stage, so rerun the stages (answer replies are cached, so only the judge call for Q009 repeats).
- **New check:** `scripts/check_gold_evidence.py` now flags any number of 100 or more in a gold answer that is missing from its evidence text, and will not mark such a row `verified`.
- **New tool:** `scripts/inspect_result.py` shows one question's retrieved pages, refusal reason, answer and model, so a "what failed" explanation can be tested against the data.
- **Report:** adds a `hit@1` column and the change in MRR versus the previous stage with a bootstrap 95% interval.
