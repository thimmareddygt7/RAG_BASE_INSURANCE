# Design decisions

| # | Decision | Why | Trade-off |
|---|---|---|---|
| 1 | Groq with `openai/gpt-oss-20b` for answers and judge, fixed per run | Fast, low cost, temperature 0 | Free-tier rate limits. The client waits and retries the SAME model, or stops with an error. Switching models needs `llm.allow_fallback: true`, and the run is then flagged as drift |
| 2 | `BAAI/bge-small-en-v1.5` embeddings | Small, runs on CPU, no API key | Weaker than larger embedding models. Fixed so all stages are comparable |
| 3 | Qdrant native dense + sparse vectors instead of an in-memory BM25 library | The permission filter must run inside the search query. An in-memory index would force filtering after retrieval | Needs a recent Qdrant and its sparse-vector API. Check current docs |
| 4 | Stage presets in `eval/stages.yaml` with locked keys | Makes "one change per stage" enforceable and tested | Extra file to maintain |
| 5 | PyJWT instead of python-jose | python-jose is poorly maintained | None significant |
| 6 | Group comes from the token, never the request | A client-supplied group would let any user claim admin | Needs a login endpoint (Stage 8) |
| 7 | Same model for answer and judge | Simplicity and cost | Self-preference bias. Measured with a real human audit (`scripts/audit_sample.py`), never assumed |
| 8 | Statistics reported with confidence intervals and McNemar | About 110 questions cannot support claims about small gaps | Honest results look less impressive than raw percentages |
| 9 | PyMuPDF `find_tables()` for PDF tables instead of a separate parser | One dependency covers text, tables, page rendering for OCR and reading order | Table quality is unmeasured on real policies. Test on 20 pages first and swap the parser if needed |
| 10 | Stage 5 keeps tables whole only when a table is already in the text (Markdown or HTML tables). Stage 6 adds PDF table extraction | Keeps each stage to one change. Stage 5 on plain PDFs mainly gains headings and sections | Stage 5 may show a small gain on PDF table questions. That is a finding, not a bug |
| 11 | Chunks never cross page boundaries | Every citation points at one exact page | Facts that span a page break are split |
| 12 | Whitespace-and-punctuation token counting instead of a model tokenizer | Deterministic, no extra dependency, reproducible chunk sizes | Chunk sizes are approximate in model tokens |
| 13 | Passwords hashed with stdlib scrypt, tokens signed with PyJWT | Fewer dependencies than passlib and bcrypt. Standard JWT library | Demo users only. A real system needs a user database and password reset |
| 14 | Offline stand-ins (hashing embedder, extractive answerer, lexical judge) | Whole pipeline, permissions and evaluation code run in tests and demos with no keys | They are not language models. Results from them are labelled offline and must not be reported |
| 15 | Refusal threshold calibrated per stage on a 20% split, refusal metrics reported on the rest | Fused and reranker scores are on different scales | Fewer questions are scored for refusal |
| 16 | Judge replies are cached on disk by (model, prompt) | Free-tier rate limits and cost. Reruns are repeatable | Changing the judge prompt needs a fresh cache directory |
| 22 | Every LLM call records the model that actually answered, and the run fails on drift | A silent fallback made the first five-stage comparison unverifiable | A rate-limited run stops instead of finishing; rerun later or allow drift knowingly |
| 23 | Answer caching stores the live latency and model, and is opt-in (`--cache-answers`) | Cached replies had been counted as 20 ms LLM calls | Cache files must be cleared if the prompt format changes (`CACHE_VERSION`) |
| 24 | The refusal threshold needs at least 5 answerable and 5 unanswerable calibration questions and may refuse at most 10% of the answerable ones | Thresholds fitted on 2 negatives were degenerate (one sat at the maximum possible RRF score) | With the 100-question set (10 unanswerable) no threshold is fitted, so the model's own refusal is used |
| 25 | A separate blind benchmark instead of editing the frozen gold set | The main set names product and version in nearly every question, so no stage could show a retrieval gain | Paraphrased questions are still tied to the same answers and pages |
| 26 | Gold rows are `drafted` until an evidence check passes | The old script stamped every row `verified` in code | Verification needs the PDFs on your machine |

