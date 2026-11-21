# Archived results (do not cite)

These five-stage results were produced before the project recorded which model answered each
question. At the time, the Groq client could silently switch to other models on a rate limit,
the answer replies were cached (so latency numbers were cache reads), and refusal thresholds
were fitted on only 2 unanswerable questions. They cannot show that one fixed model produced
them, so they are kept for reference only and must not be used in the README or on a resume.

Rerun with `python scripts/run_eval_all.py`. The new result files record the model used for
every call and the report flags model drift.
