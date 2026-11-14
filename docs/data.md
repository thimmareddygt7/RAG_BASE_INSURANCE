# Data

## What goes in the corpus
Public health insurance policy wordings and brochures, plus one self-authored fake internal document. No real people's policies or claims.

## sources.csv columns

| Column | Meaning |
|---|---|
| `doc_id` | Stable ID used in citations and the gold set |
| `kind` | `policy_wording`, `brochure`, `internal_synthetic` |
| `source_url` | Official public URL, or `local:<path>` for bundled files |
| `license_checked` | `yes` only after reading the insurer's terms. The downloader skips anything else |
| `local_filename` | Plain file name saved under `data/raw/` |
| `scanned` | `yes` if the PDF has no text layer |
| `allowed_groups` | Groups that may read the document, separated by `\|` (`policyholder\|agent\|admin`) |
| `sha256` | Filled by `python scripts/download.py --pin`, then verified on later downloads |

## Rules
- PDFs are never committed. `scripts/download.py` rebuilds `data/raw/` from the source links.
- Downloadable does not mean redistributable. Check each insurer's terms.
- `sources.csv` is the only authority for `allowed_groups` and versions. Markdown files may start with YAML front matter, but only `title` is read from it.
- Markdown files are split into pages with `<!-- page N -->` markers. Without markers the whole file is page 1.
- Versions: documents with the same `insurer` and `product` are versions of one policy. The highest `version` number is the latest. `/ask` defaults to the latest only. Comparison questions search all versions.
- Page numbers everywhere are **1-indexed PDF pages**, not the printed numbers.

## Gold files
- `gold_questions.csv`: the benchmark. `status` moves `todo` to `drafted` to `verified`. Check with `python scripts/validate_gold.py` (add `--strict` for the final frozen check).
- `permission_tests.csv`: access-control cases that use the fake agent guide. Columns: `user_group`, `forged_group_in_request` (a group the client claims in the request body, which must be ignored), `restricted_doc_visible`, `expect_refusal`, `expect_citation_doc`, `must_contain`, `must_not_contain`. A case fails if a restricted document appears in retrieval, the prompt, the citations or the answer.

## Synthetic dataset
`data/synthetic/` holds a fictional two-version policy, the fake agent guide, demo users and a 12-question gold set. It exists so the whole pipeline, the permission tests and the evaluation code can run offline in seconds. Results from it say nothing about real documents.

## The generated corpus
`scripts/generate_sample_pdfs.py` writes four fictional PDFs to `data/raw/`: two versions of "Apex Health Shield" (Apex General Insurance), a wellness brochure ("Harbor Wellness", Harbor Mutual Insurance) and a critical illness rider with a scanned page. All insurers are fictional. `sources.csv` uses `local:` URLs and `license_checked = n/a`. Regenerating the PDFs changes their hashes, so `sha256` is left empty (`python scripts/download.py --pin` fills it).

## Gold status
Rows start as `drafted`. `python scripts/check_gold_evidence.py --write-verified --ocr` marks a row `verified` only if its evidence text is found on the stated page. It cannot judge whether the gold answer is right, so read the answers yourself. Unanswerable rows stay `drafted` unless you search the PDFs for each one and pass `--confirm-absent`.

