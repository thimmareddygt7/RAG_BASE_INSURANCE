# Runbook: from zero to measured results

1. `cp .env.example .env` and fill `GROQ_API_KEY` and `AUTH_SECRET_KEY`.
2. Collect documents (see `docs/data.md`). Fill `data/gold/sources.csv`, set `license_checked` to `yes` for each, then `make download` (use `python scripts/download.py --pin` once to record hashes).
3. Test the PDF parser on 20 pages: put a few PDFs in `data/raw/`, run `python scripts/sync_index.py --stage stage6_ocr_tables`, and inspect the chunks you get for tables and scanned pages. Fix the parser choice before writing questions that depend on it.
4. Write and verify the gold questions (`make validate-gold`; finish with `python scripts/validate_gold.py --strict`). Freeze the file.
5. `docker compose up -d qdrant`, then `make eval-all`. Expect the first run to download the embedding and reranker models.
6. `make report`, copy the table into `docs/results.md`, and write the "what failed" section from real examples.
7. Run the demo (`docs/demo_script.md`) and record a short screen capture.

If a run fails halfway, rerun the same command. Index updates are incremental and judge replies are cached.
